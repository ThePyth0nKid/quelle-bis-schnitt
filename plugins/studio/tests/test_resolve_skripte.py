# SPDX-License-Identifier: MIT
"""Tests für resolve_api, resolve_bauen, resolve_rendern und resolve_bereit gegen den Fake aus conftest.py."""
from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest
import resolve_api as ra
import resolve_bauen as rb
import resolve_bereit as rbe
import resolve_fake as fake
import resolve_rendern as rr


def _quellen(tmp_path):
    namen = {}
    for n in ("a.mp4", "b.mp4", "stimme.wav"):
        p = tmp_path / n
        p.write_bytes(b"x")
        namen[n] = str(p)
    return namen


def _plan(q):
    return {
        "projekt": "Probe", "name": "probe", "format": {"breite": 1920, "hoehe": 1080, "fps": 25},
        "spuren": [
            {"art": "video", "name": "Kamera", "lueckenlos": True, "items": [
                {"id": "k1", "quelle": q["a.mp4"], "start": 0.0, "dauer": 1.0, "lage": {"zoom": 1.3, "pan": 10}},
                {"id": "k2", "quelle": q["b.mp4"], "start": 1.0, "dauer": 2.0, "quell_ab": 4.0}]},
            {"art": "audio", "name": "Stimme", "items": [
                {"id": "t1", "quelle": q["stimme.wav"], "start": 0.0, "dauer": 3.0, "paar": "k1", "pegel_db": -3,
                 "blende": [0.04, 0.04]}]},
            {"art": "audio", "name": "Klang", "items": [
                {"id": "x1", "quelle": q["stimme.wav"], "start": 1.0, "dauer": 0.5}]},
        ],
        "marker": [{"t": 1.0, "farbe": "Green", "name": "S2", "notiz": "zweiter Satz", "data": "satz:2"}],
    }


# ---- resolve_api ---------------------------------------------------------------------------------------------

def test_frames_und_timecode():
    assert ra.frames(0.02, 25) == 1
    assert ra.tc_in_sekunden("01:00:02:05", 25) == pytest.approx(3602.2)


def test_projekt_holen_speichert_kein_unbenanntes_projekt(resolve):
    proj = ra.projekt_holen(resolve, "Neu")
    assert proj.GetName() == "Neu"
    assert resolve.pm.gespeichert == []        # „Untitled Project“ wurde nicht gespeichert (F5)
    ra.projekt_holen(resolve, "Zweites")
    assert resolve.pm.gespeichert == ["Neu"]


def test_projekt_holen_ohne_anlegen(resolve):
    with pytest.raises(ra.ResolveFehler):
        ra.projekt_holen(resolve, "Fehlt", anlegen=False)


def test_neue_timeline_ueberschreibt_nie(resolve):
    proj = ra.projekt_holen(resolve, "P")
    jetzt = datetime.datetime(2026, 1, 1, 9, 5)
    t1 = ra.neue_timeline(proj, proj.GetMediaPool(), "schnitt", 1920, 1080, 25, jetzt=jetzt)
    t2 = ra.neue_timeline(proj, proj.GetMediaPool(), "schnitt", 1920, 1080, 25, jetzt=jetzt)
    assert (t1.GetName(), t2.GetName()) == ("schnitt-0905", "schnitt-0905-2")
    assert t1.GetSetting("timelineFrameRate") == "25"
    assert "timelinePlaybackFrameRate" not in t1.settings


def test_neue_timeline_nicht_waehrend_render(resolve):
    proj = ra.projekt_holen(resolve, "P")
    proj.rendert = True
    with pytest.raises(ra.ResolveFehler, match="Render läuft"):
        ra.neue_timeline(proj, proj.GetMediaPool(), "x", 1920, 1080, 25)


def test_importieren_nur_was_fehlt(resolve, tmp_path):
    q = _quellen(tmp_path)
    proj = ra.projekt_holen(resolve, "P")
    mp = proj.GetMediaPool()
    ordner = ra.ordner_holen(mp, "probe")
    ra.importieren(mp, ordner, [q["a.mp4"]])
    pool = ra.importieren(mp, ordner, [q["a.mp4"], q["b.mp4"]])
    assert mp.importiert == [q["a.mp4"], q["b.mp4"]]
    assert set(pool) == {ra.norm(q["a.mp4"]), ra.norm(q["b.mp4"])}
    with pytest.raises(ra.ResolveFehler, match="Datei fehlt"):
        ra.importieren(mp, ordner, [str(tmp_path / "gibt-es-nicht.mp4")])


def test_sichern_schreibt_drp(resolve, tmp_path):
    proj = ra.projekt_holen(resolve, "P")
    ziel = ra.sichern(resolve, proj, tmp_path / "sicherung")
    assert ziel.suffix == ".drp" and ziel.is_file()


# ---- resolve_bauen -------------------------------------------------------------------------------------------

def test_bauen_setzt_alles_bildgenau(resolve, tmp_path):
    q = _quellen(tmp_path)
    bericht = tmp_path / "bau.json"
    assert rb.bauen(_plan(q), tmp_path / "sicherung", bericht, r=resolve) == 0
    proj = resolve.pm.GetCurrentProject()
    tl = proj.GetCurrentTimeline()
    assert tl.GetName().startswith("probe-")
    starts = sorted((i.art, i.info["trackIndex"], i.GetStart() - fake.START, i.GetDuration()) for i in tl.items)
    assert starts == [("audio", 1, 0, 75), ("audio", 2, 25, 13), ("video", 1, 0, 25), ("video", 1, 25, 50)]
    k2 = next(i for i in tl.items if i.art == "video" and i.GetStart() - fake.START == 25)
    assert k2.info["startFrame"] == 100                       # quell_ab 4 s bei 25 fps
    assert ("audio", "stereo") in tl.spur_arten                # Tonspuren stereo (F13)
    assert tl.namen[("audio", 2)] == "Klang"
    assert 25 in tl.marker and tl.marker[25]["customData"] == "satz:2"   # relativ zum Start
    assert len(tl.links) == 1
    daten = json.loads(bericht.read_text(encoding="utf-8"))
    assert daten["fehler"] == [] and daten["bilder"] == 75


def test_bauen_meldet_nicht_gesetzte_items(resolve, tmp_path):
    q = _quellen(tmp_path)
    proj = ra.projekt_holen(resolve, "Probe")
    proj.mp.verweigere_ab = fake.START + 25                    # alles ab Bild 25 kommt als totes Objekt zurück
    bericht = tmp_path / "bau.json"
    assert rb.bauen(_plan(q), None, bericht, r=resolve) == 1
    fehler = json.loads(bericht.read_text(encoding="utf-8"))["fehler"]
    assert any("k2" in f and "nicht gesetzt" in f for f in fehler)


def test_bauen_sichert_vorhandenes_projekt(resolve, tmp_path):
    q = _quellen(tmp_path)
    assert rb.bauen(_plan(q), tmp_path / "s", None, r=resolve) == 0
    assert rb.bauen(_plan(q), tmp_path / "s", None, r=resolve) == 0
    assert len(list((tmp_path / "s").glob("*.drp"))) == 1      # erst beim zweiten Bau gibt es etwas zu sichern
    assert len(resolve.pm.GetCurrentProject().timelines) == 2  # die erste Timeline bleibt unberührt


def test_main_eingabefehler(tmp_path):
    assert rb.main([str(tmp_path / "fehlt.json")]) == 2


# ---- resolve_rendern -----------------------------------------------------------------------------------------

class RenderProjekt(fake.Projekt):
    def __init__(self, ziel, codec_ok=True):
        super().__init__("R")
        self.ziel = ziel
        self.codec_ok = codec_ok
        self.geloescht = []
        self.einst = None

    def SetCurrentRenderFormatAndCodec(self, fmt, codec):
        return self.codec_ok

    def GetRenderCodecs(self, fmt):
        return {"H.264": "H264"}

    def SetRenderSettings(self, einst):
        self.einst = einst
        return True

    def AddRenderJob(self):
        return "job-1"

    def StartRendering(self, jobs, interaktiv):
        return True

    def GetRenderJobStatus(self, job):
        return {"JobStatus": "Complete", "CompletionPercentage": 100}

    def GetRenderJobList(self):
        return [{"JobId": "job-1", "TargetDir": str(self.ziel), "OutputFilename": "x.mp4"}]

    def DeleteRenderJob(self, job):
        self.geloescht.append(job)
        return True


def _render_timeline():
    tl = fake.Timeline("t")
    tl.settings.update(timelineFrameRate="25", timelineResolutionWidth="2560", timelineResolutionHeight="1440")
    return tl


def test_freier_name(tmp_path):
    assert rr.freier_name(tmp_path, "film", ".mp4") == "film"
    (tmp_path / "film.mp4").write_bytes(b"x")
    (tmp_path / "film-2.mp4").write_bytes(b"x")
    assert rr.freier_name(tmp_path, "film", ".mp4") == "film-3"


def test_rendern_ok_und_job_wird_entfernt(tmp_path):
    proj = RenderProjekt(tmp_path)
    assert rr.rendern(proj, _render_timeline(), tmp_path, "film", "mp4", "H264", takt_s=0) == 0
    assert proj.geloescht == ["job-1"]
    assert proj.einst["FormatWidth"] == 2560 and proj.einst["SelectAllFrames"] is True


def test_rendern_codec_abgelehnt(tmp_path):
    assert rr.rendern(RenderProjekt(tmp_path, codec_ok=False), _render_timeline(), tmp_path, "f", "mp4", "X") == 2


def test_render_einstellungen_bereich_und_prores():
    einst = rr.render_einstellungen(_render_timeline(), Path("."), "f",
                                    "mov", "ProRes422HQ", 1.0, 2.0)
    assert einst["MarkIn"] == fake.START + 25
    assert einst["MarkOut"] == fake.START + 49
    assert einst["AudioCodec"] == "lpcm"


def test_tc():
    assert rr.tc(fake.START + 30, 25) == "01:00:01:05"


# ---- resolve_bereit ------------------------------------------------------------------------------------------

class Uhr:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def schlafen(self, s):
        self.t += s


def test_bereit_wartet_auf_skriptserver_und_gibt_auf():
    uhr = Uhr()
    gerufen = []
    r = rbe.warten_bis_bereit(10, verbinden=lambda: gerufen.append(1), laeuft=lambda n: False,
                              schlaf=uhr.schlafen, uhr=uhr)
    assert r is None and gerufen == []          # nie scriptapp() fragen, solange der Skriptserver fehlt (F4)


def test_bereit_verbindet_wenn_skriptserver_laeuft(resolve):
    uhr = Uhr()
    r = rbe.warten_bis_bereit(30, verbinden=lambda: resolve, laeuft=lambda n: True, schlaf=uhr.schlafen, uhr=uhr)
    assert r is resolve


class StillProjekt:
    """Schreibt als Standbild den aktuellen Timecode; ``haengt`` liefert immer das Bild der ersten Stelle."""

    def __init__(self, tl, haengt=False):
        self.tl = tl
        self.haengt = haengt
        self.erstes = None

    def ExportCurrentFrameAsStill(self, pfad):
        inhalt = self.tl.tc
        if self.haengt:
            self.erstes = self.erstes or inhalt
            inhalt = self.erstes
        Path(pfad).write_text(inhalt, encoding="utf-8")
        return True


class StillTimeline(fake.Timeline):
    def __init__(self):
        super().__init__("s")
        self.settings["timelineFrameRate"] = "25"
        self.tc = ""

    def SetCurrentTimecode(self, tc):
        self.tc = tc
        return True


def test_stills_aufwaermen_und_gleiche_bilder(tmp_path):
    tl = StillTimeline()
    aus = rr.stills(StillProjekt(tl), tl, [1.0, 2.0], tmp_path, "p", warte_s=0)
    assert [Path(x).name for x in aus] == ["p_bild000025.png", "p_bild000050.png"]
    assert not (tmp_path / "p_aufwaermen.png").exists()
    tl2 = StillTimeline()
    haengt = tmp_path / "h"
    haengt.mkdir()
    aus2 = rr.stills(StillProjekt(tl2, haengt=True), tl2, [1.0, 2.0], haengt, "p", warte_s=0)
    assert aus2 == []                            # jedes Bild gleich dem Aufwärmbild: keines zählt (F19)
