# SPDX-License-Identifier: MIT
"""Wächter: reine Teile (übernommen und angepasst), BMP-Leser, `--einmal --probe`, Ablauf mit OBS-Attrappen."""
from __future__ import annotations

import struct
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from studio_werkzeuge import waechter as w
from studio_werkzeuge.cli import main


def test_stempel_naechster():
    kandidaten = ["20260314-103049", "20260314-103052", "20260314-091546", "kaputt"]
    assert w.stempel_naechster(kandidaten, "20260314-103051") == "20260314-103052"
    assert w.stempel_naechster(kandidaten, "20260314-103100") is None
    assert w.stempel_aus_zeit(datetime(2026, 3, 14, 10, 30, 51)) == "20260314-103051"


def test_bild_mikro_datei_urteil():
    rng = np.random.default_rng(1)
    assert w.bild_urteil([rng.normal(80, 3, (90, 160)).astype(np.float32) for _ in range(3)]) is None
    assert "Standbild" in w.bild_urteil([np.full((90, 160), 30.0, np.float32)] * 3)
    assert w.bild_urteil([np.zeros((90, 160), np.float32)] * 3) == "Bild schwarz"
    assert w.bild_urteil([]) == "kein Bild"
    assert w.mikro_urteil(10 ** (-32 / 20)) is None and "stumm" in w.mikro_urteil(0.0)
    assert w.mikro_urteil(None) == "kein Pegel gemeldet"
    assert w.datei_urteil({"A": 10, "B": 10}, {"A": 20, "B": 10}) == ["Kamera B: Datei wächst nicht"]
    assert w.datei_urteil({}, {"A": 5}) == ["Kamera B: keine Datei"]


def _bmp(grau: np.ndarray, bits: int = 24, oben_zuerst: bool = False) -> bytes:
    hoehe, breite = grau.shape
    kanaele = bits // 8
    zeile = (breite * kanaele + 3) // 4 * 4
    pixel = np.zeros((hoehe, zeile), np.uint8)
    for k in range(min(3, kanaele)):
        pixel[:, k: breite * kanaele: kanaele] = grau
    zeilen = pixel if oben_zuerst else pixel[::-1]
    kopf = struct.pack("<2sIHHI", b"BM", 54 + zeilen.size, 0, 0, 54)
    info = struct.pack("<IiiHHIIiiII", 40, breite, -hoehe if oben_zuerst else hoehe, 1, bits, 0, zeilen.size, 0, 0, 0,
                       0)
    return kopf + info + zeilen.tobytes()


def test_bmp_grau_liest_beide_richtungen():
    grau = np.arange(15 * 7, dtype=np.uint8).reshape(7, 15) * 2           # Breite 15: Zeilen mit Füllbytes
    assert np.array_equal(w.bmp_grau(_bmp(grau)), grau.astype(np.float32))
    assert np.array_equal(w.bmp_grau(_bmp(grau, 32, oben_zuerst=True)), grau.astype(np.float32))


def test_toast_und_ergebnis_text(tmp_path):
    assert "A &amp; B &lt;ok&gt;" in w.toast_xml("T", "A & B <ok>")
    bericht = {"luecke_bilder": 7, "quelle": "bild", "warnungen": [],
               "ton": {"quelle": "A", "klicks": {"A": 0, "B": 8}}}
    titel, text = w.ergebnis_text("20260314-103051", 0, bericht, "", tmp_path)
    assert titel == "Take 10:30:51 synchron" and "Lücke 7 Bilder (nach dem Bild)" in text and text.endswith("B 8)")
    rot = w.ergebnis_text("20260314-103051", 1, {**bericht, "warnungen": ["Kamera A zeigt ein Standbild"]}, "",
                          tmp_path)
    assert rot == ("Take 10:30:51: prüfen", "Ordner „2026-03-14 10-30-51 PRUEFEN“ · Kamera A zeigt ein Standbild")
    assert w.ergebnis_text("20260314-103051", 2, None, "FEHLER: x", tmp_path)[1] == "FEHLER: x"


def test_offene_takes(tmp_path):
    inbox = tmp_path / "inbox"
    (inbox / "synchron").mkdir(parents=True)
    for n in ("cam-A-20260314-085727.mp4", "cam-B-20260314-085727.mp4", "cam-A-20260314-091500.mp4", "cam-A-x.mp4"):
        (inbox / n).write_bytes(b"x")
    for ordner, gebaut in (("2026-03-13 20-00-30", True), ("2026-03-14 08-59-42", False),
                           ("2026-03-14 09-02-43 PRUEFEN", True), ("2026-03-13 19-08-28 PRUEFEN ALT 20-15-00", False),
                           ("2026-03-14 09-05-00", "halb")):
        name = ordner[:19]
        stempel = name.replace("-", "").replace(" ", "-")
        (inbox / ordner / "Roh").mkdir(parents=True)
        (inbox / ordner / "Roh" / f"cam-A-{stempel}.mp4").write_bytes(b"x")
        if gebaut:
            (inbox / ordner / f"{name} Cam A.mp4").write_bytes(b"x")
        if gebaut is True:
            (inbox / ordner / f"{name} Cam B.mp4").write_bytes(b"x")
    assert w.offene_takes(inbox, inbox) == ["20260314-085727", "20260314-085942", "20260314-090500",
                                            "20260314-091500"]
    assert w.offene_takes(inbox, inbox, laufend="20260314-091501")[-1] == "20260314-090500"
    assert w.offene_takes(tmp_path / "leer", tmp_path / "leer") == []


def test_neu_bauen_lesen_leert_die_datei(tmp_path):
    datei = tmp_path / "neu_bauen.txt"
    assert w.neu_bauen_lesen(datei) == []
    datei.write_text("# Kommentar\n20260314-095800\n20260314-091201  # nochmal\nkaputt\n20260314-095800\n",
                     encoding="utf-8")
    assert w.neu_bauen_lesen(datei) == ["20260314-091201", "20260314-095800"]
    assert datei.read_text(encoding="utf-8") == ""


def test_arbeitsordner_aufraeumen_nur_eigener_take(tmp_path):
    eigener, fremder = tmp_path / "~in Arbeit 2026-03-14 08-57-27 ab12", tmp_path / "~in Arbeit 2026-03-14 08-59-42 cd"
    for p in (eigener, fremder):
        p.mkdir()
    assert w.arbeitsordner_aufraeumen(tmp_path, "20260314-085727") == [eigener] and fremder.is_dir()
    (tmp_path / "2026-03-14 08-59-42").mkdir()
    assert w.arbeitsordner_aufraeumen(tmp_path) == [fremder] and (tmp_path / "2026-03-14 08-59-42").is_dir()


def test_einmal_probe_ohne_obs(tmp_path, capsys):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for n in ("cam-A-20260314-085727.mp4", "cam-B-20260314-085727.mp4", "cam-A-20260314-091500.mp4"):
        (inbox / n).write_bytes(b"x")
    k = tmp_path / "studio.toml"
    k.write_text(f'[pfade]\ninbox = "{inbox.as_posix()}"\n', encoding="utf-8")
    assert main(["--konfig", str(k), "waechter", "--einmal", "--probe"]) == 0
    aus = capsys.readouterr().out
    assert "Take 20260314-085727: würde einsortiert" in aus and "Take 20260314-091500: nicht nachgeholt" in aus
    assert sorted(p.name for p in inbox.iterdir()) == ["cam-A-20260314-085727.mp4", "cam-A-20260314-091500.mp4",
                                                       "cam-B-20260314-085727.mp4"]   # Probe: nichts bewegt


class FakeReq:
    def __init__(self, aufnahme: bool = False) -> None:
        self.aufnahme = aufnahme

    def send(self, art, daten=None, raw=False):
        if art == "GetSourceFilterList":
            return {"filters": [{"filterName": "Aufnahme A", "filterKind": "source_record_filter",
                                 "filterSettings": {"audio_source": "Mikrofon"}}]}
        if art == "GetRecordStatus":
            return {"outputActive": self.aufnahme, "outputDuration": 2000}
        return {}

    def disconnect(self):
        pass


class FakeEreignisse:
    def __init__(self) -> None:
        self.callback = SimpleNamespace(register=lambda f: setattr(self, "rueckruf", f))

    def disconnect(self):
        pass


def _waechter(tmp_path, hilfe, req: FakeReq) -> w.Waechter:
    inbox = tmp_path / "inbox"
    inbox.mkdir(exist_ok=True)
    k = hilfe.konfig_aus(tmp_path, f'[pfade]\ninbox = "{inbox.as_posix()}"\n[kameras]\nquelle_a = "Kamera vorn"\n'
                                    'filter_a = "Aufnahme A"\n[waechter]\nwindows_hinweis = false\n'
                                    'startpruefung = false\n')
    return w.Waechter(k, req_fabrik=lambda: req, ereignis_fabrik=lambda **kw: FakeEreignisse())


def test_verbinden_liest_mikrofon_und_aufnahmezustand(tmp_path, hilfe):
    wa = _waechter(tmp_path, hilfe, FakeReq(aufnahme=True))
    wa.verbinden()
    assert wa.mikro_name == "Mikrofon" and wa.nimmt_auf.is_set() and wa.start_zeit is not None
    assert wa.ev.rueckruf == wa.on_record_state_changed


def test_nach_stop_sortiert_ein_und_merkt_vor(tmp_path, hilfe, monkeypatch):
    monkeypatch.setattr(w, "NACH_STOP_S", 0.0)
    wa = _waechter(tmp_path, hilfe, FakeReq())
    start = datetime(2026, 3, 14, 8, 57, 27)
    for n in ("cam-A-20260314-085727.mp4", "cam-B-20260314-085728.mp4"):
        (wa.inbox / n).write_bytes(b"x")
    wa.start_zeit = start
    wa.nach_stop(start)
    assert wa.auftraege.get_nowait() == "20260314-085727"
    assert (wa.inbox / "2026-03-14 08-57-27" / "Roh" / "cam-B-20260314-085728.mp4").is_file()
    wa.vormerken("20260314-085727")
    assert wa.auftraege.empty()                                              # schon vorgemerkt: nicht doppelt


def test_bau_bricht_ab_wenn_eine_aufnahme_beginnt(tmp_path, hilfe, monkeypatch):
    wa = _waechter(tmp_path, hilfe, FakeReq())
    echt = subprocess.Popen

    gestartet: list[list[str]] = []

    def schlaeft(aufruf, **kw):
        if aufruf[1:4] == ["-m", "studio_werkzeuge", "paar"]:               # der Bau über den eigenen Befehl
            gestartet.append(aufruf)
            return echt([sys.executable, "-c", "import time; time.sleep(30)"], **kw)
        return echt(aufruf, **kw)                                           # z. B. taskkill zum Beenden

    monkeypatch.setattr(w.subprocess, "Popen", schlaeft)
    threading.Timer(0.5, wa.nimmt_auf.set).start()
    beginn = time.monotonic()
    rc, fertig = wa.bauen("20260314-085727")
    assert not fertig and time.monotonic() - beginn < 15 and len(gestartet) == 1
    assert (wa.ziel / "synchron" / "waechter-20260314-085727.log").is_file()


def test_einzige_instanz(tmp_path):
    erste = w.einzige_instanz(tmp_path / "w.lock")
    assert erste is not None
    assert w.einzige_instanz(tmp_path / "w.lock") is None
    erste.close()
    assert Path(tmp_path / "w.lock").exists()
