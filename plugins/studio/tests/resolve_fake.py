# SPDX-License-Identifier: MIT
"""Kleiner Resolve-Nachbau (Fake) für die Tests der Resolve-Skripte.

Er bildet nur das gemessene Verhalten nach, auf das sich die Skripte verlassen (referenz/api-fakten.md):
endFrame exklusiv, fehlende Spur oder Überlappung ergibt ein totes Objekt, Marker relativ zum Timeline-Start.
Er spricht nie mit einem echten Resolve.
"""
from __future__ import annotations

from pathlib import Path

START = 90000  # 01:00:00:00 bei 25 fps


class TotesItem:
    def GetStart(self):
        return None


class Item:
    def __init__(self, tl, info):
        self.tl = tl
        self.info = info
        self.start = info["recordFrame"]
        self.dauer = info["endFrame"] - info["startFrame"]
        self.props: dict = {}
        self.fades = None
        self.uebergang = None

    def GetStart(self):
        return self.start

    def GetDuration(self):
        return self.dauer

    def GetEnd(self):
        return self.start + self.dauer

    def SetProperties(self, d):
        self.props.update(d)
        return True

    def SetFades(self, d):
        self.fades = d
        return True

    def AddTransition(self, d):
        self.uebergang = d
        return object()

    def AddFusionComp(self):
        return None


class PoolItem:
    def __init__(self, pfad: str, fps: float = 25.0):
        self.pfad = pfad
        self.fps = fps

    def GetClipProperty(self, k):
        return {"File Path": self.pfad, "FPS": str(self.fps)}.get(k)


class Ordner:
    def __init__(self, name):
        self.name = name
        self.clips: list[PoolItem] = []
        self.unter: list[Ordner] = []

    def GetName(self):
        return self.name

    def GetSubFolderList(self):
        return self.unter

    def GetClipList(self):
        return self.clips


class Timeline:
    def __init__(self, name):
        self.name = name
        self.settings: dict = {}
        self.spuren = {"video": 1, "audio": 1}
        self.spur_arten: list[tuple] = []
        self.namen: dict = {}
        self.aus: list = []
        self.items: list[Item] = []
        self.marker: dict = {}
        self.links: list = []

    def GetName(self):
        return self.name

    def GetStartFrame(self):
        return START

    def GetEndFrame(self):
        return max((i.GetEnd() for i in self.items), default=START)

    def SetSetting(self, k, v):
        self.settings[k] = v
        return True

    def GetSetting(self, k):
        return self.settings.get(k)

    def GetTrackCount(self, art):
        return self.spuren[art]

    def AddTrack(self, art, art2=None):
        self.spuren[art] += 1
        self.spur_arten.append((art, art2))
        return True

    def SetTrackName(self, art, idx, name):
        self.namen[(art, idx)] = name
        return True

    def SetTrackEnable(self, art, idx, an):
        self.aus.append((art, idx, an))
        return True

    def AddMarker(self, frame, farbe, name, notiz, dauer, data):
        if frame in self.marker:
            return False
        self.marker[frame] = {"color": farbe, "name": name, "note": notiz, "duration": dauer, "customData": data}
        return True

    def SetClipsLinked(self, items, an):
        self.links.append(items)
        return True

    def GetItemListInTrack(self, art, idx):
        return sorted((i for i in self.items if getattr(i, "art", None) == art and i.info["trackIndex"] == idx),
                      key=lambda i: i.start)

    def platzieren(self, info):
        art = "video" if info.get("mediaType") == 1 else "audio"
        if info["trackIndex"] > self.spuren[art]:
            return TotesItem()
        neu = Item(self, info)
        neu.art = art
        for alt in self.items:
            if getattr(alt, "art", None) == art and alt.info["trackIndex"] == info["trackIndex"] \
                    and neu.start < alt.GetEnd() and alt.start < neu.GetEnd():
                return TotesItem()
        self.items.append(neu)
        return neu


class MediaPool:
    def __init__(self, projekt):
        self.projekt = projekt
        self.wurzel = Ordner("Master")
        self.aktuell = self.wurzel
        self.importiert: list[str] = []
        self.verweigere_ab: int | None = None  # ab diesem recordFrame wird nichts gesetzt
        # Stapel-Verhalten wie im Fehlerfall gemessen: diese recordFrames scheitern im Stapel, und die Rückgabeliste
        # enthält dann NUR die gesetzten Items (kürzer als die Eingabe); einzeln nachgesetzt klappt es
        self.stapel_luecken: set[int] = set()
        self.nie: set[int] = set()            # diese recordFrames scheitern immer
        self.aufrufe: list[int] = []          # Länge jedes AppendToTimeline-Aufrufs

    def GetRootFolder(self):
        return self.wurzel

    def AddSubFolder(self, eltern, name):
        o = Ordner(name)
        eltern.unter.append(o)
        return o

    def SetCurrentFolder(self, o):
        self.aktuell = o
        return True

    def ImportMedia(self, pfade):
        assert isinstance(pfade, list) and all(isinstance(x, str) for x in pfade), "nur Pfadliste (F1)"
        neu = [PoolItem(x) for x in pfade]
        self.aktuell.clips.extend(neu)
        self.importiert.extend(pfade)
        return neu

    def CreateEmptyTimeline(self, name):
        tl = Timeline(name)
        self.projekt.timelines.append(tl)
        return tl

    def AppendToTimeline(self, infos):
        tl = self.projekt.aktuelle
        self.aufrufe.append(len(infos))
        aus = []
        stapel = len(infos) > 1
        for info in infos:
            rf = info["recordFrame"]
            if rf in self.nie or (stapel and rf in self.stapel_luecken):
                if not (stapel and self.stapel_luecken):
                    aus.append(TotesItem())
            elif self.verweigere_ab is not None and rf >= self.verweigere_ab:
                aus.append(TotesItem())
            else:
                aus.append(tl.platzieren(info))
        return aus


class Projekt:
    def __init__(self, name):
        self.name = name
        self.timelines: list[Timeline] = []
        self.aktuelle: Timeline | None = None
        self.settings: dict = {}
        self.mp = MediaPool(self)
        self.rendert = False
        self.render: dict = {"jobs": [], "status": {"JobStatus": "Complete", "CompletionPercentage": 100}}

    def GetName(self):
        return self.name

    def GetTimelineCount(self):
        return len(self.timelines)

    def GetTimelineByIndex(self, i):
        return self.timelines[i - 1]

    def SetCurrentTimeline(self, tl):
        self.aktuelle = tl
        return True

    def GetCurrentTimeline(self):
        return self.aktuelle

    def GetMediaPool(self):
        return self.mp

    def SetSetting(self, k, v):
        self.settings[k] = v
        return True

    def GetSetting(self, k):
        return self.settings.get(k)

    def IsRenderingInProgress(self):
        return self.rendert

    def RefreshLUTList(self):
        return True


class ProjektManager:
    def __init__(self):
        self.projekte: dict[str, Projekt] = {}
        self.offen: Projekt | None = Projekt("Untitled Project")
        self.gespeichert: list[str] = []

    def GetCurrentProject(self):
        return self.offen

    def SaveProject(self):
        self.gespeichert.append(self.offen.GetName() if self.offen else "")
        return True

    def LoadProject(self, name):
        if name in self.projekte:
            self.offen = self.projekte[name]
            return self.offen
        return None

    def CreateProject(self, name):
        self.projekte[name] = self.offen = Projekt(name)
        return self.offen

    def ExportProject(self, name, pfad, mit_stills):
        Path(pfad).write_text("drp", encoding="utf-8")
        return True


class Resolve:
    def __init__(self):
        self.pm = ProjektManager()

    def GetProjectManager(self):
        return self.pm

