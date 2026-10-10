# SPDX-License-Identifier: MIT
"""Klick-Zähler an synthetischen Signalen: eingesetzte Spitzen und Aussetzer werden genau gezählt, Rauschen nicht."""
from __future__ import annotations

import json
import shutil

import numpy as np
import pytest
from studio_werkzeuge import klicks
from studio_werkzeuge.cli import main

FFMPEG_DA = shutil.which("ffmpeg") is not None
SCHWELLEN = {"faktor": 12.0, "minimum": 0.03, "gruen_unter": 5.0, "rot_ueber": 15.0, "pegel_bezug_dbfs": -23.0,
             "pegel_toleranz_db": 10.0}


def test_eingesetzte_spitzen_werden_genau_gezaehlt(hilfe):
    x = hilfe.sprache(10.0)
    assert klicks.klicks_zaehlen(x) == 0
    orte = [48_000 * s + 333 for s in (1, 2, 3, 4, 5, 6, 7)]          # 7 Spitzen, je mindestens 1 s auseinander
    for o in orte:
        x[o] += 0.6
    gefunden = klicks.klick_orte(x)
    assert len(gefunden) == 7
    assert all(abs(int(g) - o) <= 1 for g, o in zip(gefunden, orte, strict=True))   # Ort auf ±1 Abtastwert


def test_aussetzer_zaehlen_als_klick_rauschen_nicht(hilfe):
    x = hilfe.sprache(4.0)
    for s in (48_000 + 60, 100_000 + 60, 150_000 + 60):                # drei Aussetzer à 3 ms
        x[s: s + 144] = 0.0
    assert klicks.klicks_zaehlen(x) == 3
    rauschen = np.random.default_rng(5).normal(0, 0.05, 48_000 * 2).astype(np.float32)
    assert klicks.klicks_zaehlen(rauschen) == 0
    assert klicks.klicks_zaehlen(np.zeros(100, np.float32)) == 0         # kürzer als 1 s


def test_spitzen_binnen_20_ms_zaehlen_einmal(hilfe):
    x = hilfe.sprache(3.0)
    for o in (60_000, 60_300, 60_600):                                   # 6,25 ms Abstand
        x[o] += 0.6
    assert klicks.klicks_zaehlen(x) == 1


def test_ampel_und_raster():
    assert klicks.ampel(4.9) == "GRÜN" and klicks.ampel(5.0) == "GELB" and klicks.ampel(15.0) == "GELB"
    assert klicks.ampel(15.1) == "ROT"
    block = int(round(klicks.AAC_BLOCK_MS / 1000 * 48_000))
    assert klicks.im_aac_raster(np.array([0, block, 2 * block, 4 * block])) == 3
    assert klicks.im_aac_raster(np.array([0, 5000])) == 0


def test_bewerten_je_minute_und_pegelhinweis(hilfe):
    x = hilfe.sprache(60.0) * 0.3                                        # RMS ≈ −23 dBFS
    for s in range(1, 21):                                               # 20 Spitzen in einer Minute → ROT
        x[int(48_000 * s * 2.9) + 7] += 0.3
    b = klicks.bewerten(x, "probe.wav", SCHWELLEN)
    assert (b.klicks, b.ampel) == (20, "ROT") and abs(b.je_minute - 20.0) < 0.01
    assert b.hinweise == () and abs(b.pegel_dbfs + 23) < 1
    leise = klicks.bewerten(x * 0.01, "leise.wav", SCHWELLEN)
    assert any("Pegel" in h for h in leise.hinweise)


@pytest.mark.skipif(not FFMPEG_DA, reason="ffmpeg fehlt")
def test_cli_findet_die_erwartete_zahl(tmp_path, hilfe, capsys):
    x = hilfe.sprache(30.0)
    for s in (3, 9, 15, 21):
        x[48_000 * s + 11] += 0.6
    datei = hilfe.wav_schreiben(tmp_path / "probe.wav", x)
    assert klicks.ausfuehren(type("A", (), {"dateien": [datei], "json": True})(), hilfe.konfig_aus(tmp_path, "")) == 0
    daten = json.loads(capsys.readouterr().out)
    assert daten["befunde"][0]["klicks"] == 4 and daten["befunde"][0]["ampel"] == "GELB"   # 8 je Minute


@pytest.mark.skipif(not FFMPEG_DA, reason="ffmpeg fehlt")
def test_cli_fehlende_datei_ist_fehler_keine_gruene_ampel(tmp_path, capsys):
    assert main(["klick-check", str(tmp_path / "fehlt.wav")]) == 2
    assert "FEHLER" in capsys.readouterr().out
