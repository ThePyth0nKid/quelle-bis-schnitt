#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Gemeinsame Hüllen für die Resolve-Skripte (DaVinci Resolve Studio, Aufruf von außen).

Nur Standardbibliothek: läuft im mitgelieferten Python von Resolve und in jedem System-Python, das die
Skript-Schnittstelle von Resolve findet (siehe ``verbinden``).

Regeln, die jede Hülle durchsetzt:
  * nie während eines Renders schreiben
  * vor schreibenden Läufen eine .drp-Sicherung (die API hat kein Undo)
  * nie eine vorhandene Timeline überschreiben (neuer Name mit Uhrzeit, sonst -2, -3 …)
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import time
from fractions import Fraction
from pathlib import Path

VIDEO, TON, UNTERTITEL = "video", "audio", "subtitle"


class ResolveFehler(RuntimeError):
    pass


def resolve_python() -> Path | None:
    """Pfad des mitgelieferten Pythons von Resolve, falls bekannt. Überschreibbar mit ``$RESOLVE_PYTHON``."""
    if os.environ.get("RESOLVE_PYTHON"):
        return Path(os.environ["RESOLVE_PYTHON"])
    if sys.platform.startswith("win"):
        basis = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        return basis / "Blackmagic Design" / "DaVinci Resolve" / "ResolvePython" / "ResolvePython.exe"
    return None


def utf8() -> None:
    for strom in (sys.stdout, sys.stderr):
        try:
            strom.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def verbinden():
    """Das Resolve-Objekt der laufenden Instanz; bricht mit klarer Meldung ab, wenn Resolve nicht erreichbar ist."""
    r = globals().get("resolve")
    if r is None:
        try:
            import DaVinciResolveScript as dvr  # type: ignore[import-not-found]
        except ImportError as e:
            rp = resolve_python()
            hinweis = f"mit {rp} starten" if rp else "Umgebung setzen"
            raise ResolveFehler(
                f"DaVinciResolveScript fehlt ({e}): {hinweis}, oder RESOLVE_SCRIPT_API, RESOLVE_SCRIPT_LIB und "
                "PYTHONPATH so setzen, wie es die Scripting-README von Resolve beschreibt") from e
        r = dvr.scriptapp("Resolve")
    if r is None:
        raise ResolveFehler("Resolve antwortet nicht: läuft es, und steht Preferences › System › General › "
                            "External scripting using auf Local?")
    return r


def darf_schreiben(proj) -> None:
    if proj.IsRenderingInProgress():
        raise ResolveFehler("Render läuft: jetzt wird nichts gebaut")


def projekt_holen(r, name: str, anlegen: bool = True):
    """Lädt das Projekt, legt es sonst an. Das offene Projekt wird vorher gespeichert.

    Ein unbenanntes Projekt („Untitled Project“) wird NICHT gespeichert: SaveProject öffnet dort einen Dialog,
    und solange der offen ist, hängt jeder API-Aufruf (referenz/api-fakten.md, F5)."""
    pm = r.GetProjectManager()
    offen = pm.GetCurrentProject()
    if offen and offen.GetName() == name:
        return offen
    if offen and not offen.GetName().lower().startswith("untitled"):
        pm.SaveProject()
    proj = pm.LoadProject(name)
    if not proj and anlegen:
        proj = pm.CreateProject(name)
    if not proj:
        raise ResolveFehler(f"Projekt „{name}“ lässt sich weder laden noch anlegen")
    return proj


def sichern(r, proj, ordner: Path) -> Path:
    """Exportiert das Projekt als .drp (die API hat kein Undo). Gibt den Pfad zurück."""
    ordner.mkdir(parents=True, exist_ok=True)
    pm = r.GetProjectManager()
    pm.SaveProject()
    ziel = ordner / f"{proj.GetName()}_{datetime.datetime.now():%Y-%m-%d_%H%M%S}.drp"
    if not pm.ExportProject(proj.GetName(), str(ziel), False):
        raise ResolveFehler(f"Sicherung nach {ziel} fehlgeschlagen")
    return ziel


def ordner_holen(mp, name: str, eltern=None):
    eltern = eltern or mp.GetRootFolder()
    for f in eltern.GetSubFolderList() or []:
        if f.GetName() == name:
            return f
    f = mp.AddSubFolder(eltern, name)
    if not f:
        raise ResolveFehler(f"Media-Pool-Ordner „{name}“ lässt sich nicht anlegen")
    return f


def _pfad(item) -> str:
    return str(item.GetClipProperty("File Path") or "")


def norm(p) -> str:
    """Pfad als Vergleichsschlüssel (Groß-/Kleinschreibung egal, Trenner vereinheitlicht)."""
    return str(Path(p)).replace("\\", "/").lower()


def importieren(mp, ordner, dateien: list[str | Path]) -> dict[str, object]:
    """Importiert nur, was im Ordner noch fehlt. Rückgabe: normalisierter Pfad → MediaPoolItem."""
    vorhanden = {norm(_pfad(it)): it for it in (ordner.GetClipList() or []) if _pfad(it)}
    neu = [str(Path(d)) for d in dict.fromkeys(map(str, dateien)) if norm(d) not in vorhanden]
    fehlend = [d for d in neu if not Path(d).is_file()]
    if fehlend:
        raise ResolveFehler("Datei fehlt: " + ", ".join(fehlend[:3]))
    if neu:
        mp.SetCurrentFolder(ordner)
        # Pfadliste, nicht [{"FilePath": …}]: die Dict-Form ist für Bildfolgen und hängt bei Einzeldateien
        # minutenlang, ohne etwas zu importieren (referenz/api-fakten.md, F1)
        for it in mp.ImportMedia(neu) or []:
            vorhanden[norm(_pfad(it))] = it
    nicht = [d for d in neu if norm(d) not in vorhanden]
    if nicht:
        raise ResolveFehler("Import fehlgeschlagen: " + ", ".join(Path(d).name for d in nicht[:3]))
    return {norm(d): vorhanden[norm(d)] for d in map(str, dateien)}


def timeline_namen(proj) -> list[str]:
    return [proj.GetTimelineByIndex(i).GetName() for i in range(1, int(proj.GetTimelineCount() or 0) + 1)]


def neue_timeline(proj, mp, stamm: str, breite: int, hoehe: int, fps: float | str, jetzt=None):
    """Leere Timeline „<stamm>-HHMM“ mit eigener Auflösung und Bildrate; vorhandene Namen bleiben unberührt."""
    darf_schreiben(proj)
    jetzt = jetzt or datetime.datetime.now()
    namen = set(timeline_namen(proj))
    name = f"{stamm}-{jetzt:%H%M}"
    n = 2
    while name in namen:
        name, n = f"{stamm}-{jetzt:%H%M}-{n}", n + 1
    tl = mp.CreateEmptyTimeline(name)
    if not tl:
        raise ResolveFehler(f"Timeline „{name}“ lässt sich nicht anlegen")
    proj.SetCurrentTimeline(tl)
    # timelinePlaybackFrameRate wird abgelehnt, sie folgt timelineFrameRate (referenz/api-fakten.md, F2)
    einstellungen = {"useCustomSettings": "1", "timelineResolutionWidth": str(breite),
                     "timelineResolutionHeight": str(hoehe), "timelineFrameRate": str(fps)}
    for k, v in einstellungen.items():        # einzeln: so ist ein Fehlschlag benannt
        if not tl.SetSetting(k, v):
            raise ResolveFehler(f"Timeline-Einstellung {k}={v} abgelehnt")
    return tl


def frames(sekunden: float, fps: float | str) -> int:
    """Sekunden → ganze Bilder bei der echten Bildrate (auch 23,976 / 29,97), kaufmännisch gerundet über Brüche."""
    return int(Fraction(str(sekunden)) * Fraction(str(fps)) + Fraction(1, 2))


# ---- Timecode ------------------------------------------------------------------------------------------------
# Ein Timecode zählt Bilder mit dem NENNWERT der Bildrate (23,976 → 24, 29,97 → 30, 59,94 → 60). Bei Drop-Frame
# (nur 29,97 und 59,94; Trenner „;“) werden zu jeder vollen Minute außer jeder zehnten 2 bzw. 4 Bildnummern
# übersprungen, damit der Timecode der Uhrzeit folgt (SMPTE ST 12-1).

def nennwert(fps: float | str) -> int:
    """Zählwert des Timecodes: 23,976 → 24, 25 → 25, 29,97 → 30, 59,94 → 60."""
    return int(round(float(fps)))


def _drop_bilder(fps: float | str) -> int:
    n = nennwert(fps)
    if n not in (30, 60) or float(fps) == n:
        raise ValueError(f"Drop-Frame gibt es nur bei 29,97 und 59,94 fps, nicht bei {fps}")
    return 2 if n == 30 else 4


def bild_zu_tc(bild: int, fps: float | str, drop: bool = False) -> str:
    """Bildnummer (ab 00:00:00:00 gezählt) → Timecode. Non-Drop mit „:“, Drop-Frame mit „;“ vor den Bildern."""
    n = nennwert(fps)
    if bild < 0:
        raise ValueError("Bildnummer negativ")
    if drop:
        d = _drop_bilder(fps)
        je_10_min = n * 600 - 9 * d          # 17982 bei 29,97
        je_min = n * 60 - d                   # 1798 bei 29,97
        zehner, rest = divmod(bild, je_10_min)
        bild += 9 * d * zehner + (d * ((rest - d) // je_min) if rest > d else 0)
    h, rest = divmod(bild, 3600 * n)
    m, rest = divmod(rest, 60 * n)
    s, f = divmod(rest, n)
    return f"{h:02d}:{m:02d}:{s:02d}{';' if drop else ':'}{f:02d}"


def tc_zu_bild(tc: str, fps: float | str, drop: bool | None = None) -> int:
    """Timecode → Bildnummer ab 00:00:00:00. Ohne Angabe gilt Drop-Frame, wenn ein „;“ im Timecode steht."""
    if drop is None:
        drop = ";" in tc
    h, m, s, f = (int(x) for x in tc.replace(";", ":").split(":"))
    n = nennwert(fps)
    bild = (h * 3600 + m * 60 + s) * n + f
    if drop:
        minuten = h * 60 + m
        bild -= _drop_bilder(fps) * (minuten - minuten // 10)
    return bild


def tc_in_sekunden(tc: str, fps: float | str, drop: bool | None = None) -> float:
    """Timecode → Sekunden echter Laufzeit ab 00:00:00:00 (Bildnummer geteilt durch die echte Bildrate).

    Bei 29,97 fps Non-Drop sind das für „01:00:00:00“ rund 3603,6 s, nicht 3600 s: Non-Drop läuft der Uhr davon."""
    return float(Fraction(tc_zu_bild(tc, fps, drop)) / Fraction(str(fps)))


def timeline_drop_frame(tl) -> bool:
    """Ob die Timeline Drop-Frame-Timecode zeigt (Einstellung oder „;“ im Start-Timecode)."""
    wert = str(tl.GetSetting("timelineDropFrameTimecode") or "").strip().lower()
    if wert in ("1", "true"):
        return True
    start = tl.GetStartTimecode() if hasattr(tl, "GetStartTimecode") else ""
    return ";" in str(start or "")


def warten(bedingung, timeout_s: float, schritt_s: float = 1.0) -> bool:
    ende = time.time() + timeout_s
    while time.time() < ende:
        if bedingung():
            return True
        time.sleep(schritt_s)
    return False


def json_schreiben(pfad: Path, daten) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")
