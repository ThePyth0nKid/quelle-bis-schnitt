# SPDX-License-Identifier: MIT
"""Mastern: Rechnung, Befehle, Auswertung von ebur128 und Ende-zu-Ende mit synthetischem Ton (braucht ffmpeg)."""
from __future__ import annotations

import json
import shutil
import subprocess

import numpy as np
import pytest
from studio_werkzeuge import medien
from studio_werkzeuge.fehler import StudioFehler
from studio_werkzeuge.mastern import begrenzer_bedarf, ffmpeg_befehl, kette, mastern

FFMPEG_DA = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
braucht_ffmpeg = pytest.mark.skipif(not FFMPEG_DA, reason="ffmpeg fehlt")

ZUSAMMENFASSUNG = """[Parsed_ebur128_1 @ 0000] Summary:

  Integrated loudness:
    I:         -23.4 LUFS
    Threshold: -33.6 LUFS

  Loudness range:
    LRA:         5.1 LU
    Threshold: -43.7 LUFS
    LRA low:   -26.8 LUFS
    LRA high:  -21.7 LUFS

  True peak:
    Peak:       -6.2 dBFS
"""


def test_ebur128_lesen():
    assert medien.ebur128_lesen("vorher\n" + ZUSAMMENFASSUNG) == {"lufs": -23.4, "lra": 5.1, "dbtp": -6.2}
    still = ZUSAMMENFASSUNG.replace("-23.4 LUFS", "-inf LUFS").replace("-6.2 dBFS", "-inf dBFS")
    assert medien.ebur128_lesen(still)["lufs"] == float("-inf")
    with pytest.raises(StudioFehler):
        medien.ebur128_lesen("keine Zusammenfassung")


def test_begrenzer_bedarf_und_kette():
    assert begrenzer_bedarf({"dbtp": -6.2}, 9.4, -1.5) == pytest.approx(4.7)
    assert begrenzer_bedarf({"dbtp": -12.0}, 5.0, -1.5) == 0.0
    k = kette(9.4, -1.5, 0.2)
    assert k.startswith("volume=9.40dB,aresample=192000,alimiter=limit=0.8222") and k.endswith("aresample=48000")


def test_befehle(tmp_path):
    video = ffmpeg_befehl(tmp_path / "e.mov", tmp_path / "a.mp4", "volume=1dB", True, 16, 1440)
    assert video[video.index("-crf") + 1] == "16" and "+faststart" in video and "scale=-2:1440:flags=lanczos" in \
        video[video.index("-vf") + 1]
    wav = ffmpeg_befehl(tmp_path / "e.wav", tmp_path / "a.wav", "volume=1dB", False, 16, None)
    assert wav[wav.index("-c:a") + 1] == "pcm_s24le" and "-vn" in wav
    with pytest.raises(StudioFehler, match="Endung"):
        ffmpeg_befehl(tmp_path / "e.wav", tmp_path / "a.xyz", "volume=1dB", False, 16, None)


def _ton(hilfe, pfad, pegel: float = 0.05, sekunden: float = 12.0, spitzen: bool = False):
    x = hilfe.sprache(sekunden) / 0.5 * pegel
    if spitzen:                                              # wenige sehr hohe Spitzen: Begrenzer müsste viel greifen
        for s in (2, 5, 8):
            x[48_000 * s: 48_000 * s + 200] = 0.99
    return hilfe.wav_schreiben(pfad, x)


@braucht_ffmpeg
def test_ende_zu_ende_ton(tmp_path, hilfe):
    eingang = _ton(hilfe, tmp_path / "roh.wav")
    ausgang = tmp_path / "master.wav"
    b = mastern(eingang, ausgang)
    assert b["ok"], b
    assert abs(b["nachher"]["lufs"] + 14.0) <= 0.5 and b["nachher"]["dbtp"] <= -1.5
    assert ausgang.is_file() and not (tmp_path / "master.part.wav").exists()
    bericht = json.loads((tmp_path / "master.wav.json").read_text(encoding="utf-8"))
    assert bericht["vorher"]["lufs"] < -20 and bericht["anhebung_db"] > 5
    nach = medien.lautheit_messen(ausgang)                  # unabhängig nachgemessen
    assert abs(nach["lufs"] + 14.0) <= 0.5
    with pytest.raises(StudioFehler, match="Nie überschreiben"):
        mastern(eingang, ausgang)


@braucht_ffmpeg
def test_probe_schreibt_nichts(tmp_path, hilfe):
    eingang = _ton(hilfe, tmp_path / "roh.wav")
    b = mastern(eingang, tmp_path / "master.wav", probe=True)
    assert b["probe"] and b["ok"] and not (tmp_path / "master.wav").exists()
    assert abs(b["plan_messung"]["lufs"] + 14.0) <= 0.5


@braucht_ffmpeg
def test_abbruch_wenn_begrenzer_zu_viel_greifen_muesste(tmp_path, hilfe):
    eingang = _ton(hilfe, tmp_path / "roh.wav", pegel=0.02, spitzen=True)
    b = mastern(eingang, tmp_path / "master.wav")
    assert not b["ok"] and "Begrenzer müsste" in b["abbruch"] and b["begrenzer_db"] > 3.0
    assert not (tmp_path / "master.wav").exists()
    # Einstellbar: der Mensch darf mehr Begrenzung erlauben. Dann entscheidet die Nachmessung.
    b2 = mastern(eingang, tmp_path / "master2.wav", max_begrenzer=40.0)
    assert "Begrenzer müsste" not in (b2.get("abbruch") or "") and "nachher" in b2
    assert b2["begrenzer_db"] >= b["begrenzer_db"] > 3.0              # mit der endgültigen Verstärkung berechnet


@braucht_ffmpeg
def test_ende_zu_ende_video(tmp_path):
    eingang = tmp_path / "roh.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=25:duration=6",
                    "-f", "lavfi", "-i", "sine=frequency=220:sample_rate=48000:duration=6", "-af", "volume=-24dB",
                    "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                    str(eingang)], check=True)
    ausgang = tmp_path / "abgabe.mp4"
    b = mastern(eingang, ausgang, hoehe=360)
    assert b["ok"] and b["video"], b
    info = medien.video_info(ausgang)
    assert (info["breite"], info["hoehe"]) == (640, 360) and medien.bilder_zaehlen(ausgang) == 150
    assert b["nachher"]["dbtp"] <= -1.5 and abs(b["nachher"]["lufs"] + 14.0) <= 0.5


def test_stummer_eingang_und_fehlende_datei(tmp_path, hilfe):
    with pytest.raises(StudioFehler, match="fehlt"):
        mastern(tmp_path / "gibt-es-nicht.wav", tmp_path / "x.wav")
    if FFMPEG_DA:
        still = hilfe.wav_schreiben(tmp_path / "still.wav", np.zeros(48_000 * 3, np.float32))
        with pytest.raises(StudioFehler, match="stumm"):
            mastern(still, tmp_path / "x.wav")


def test_bedarf_wird_mit_der_endgueltigen_verstaerkung_geprueft(tmp_path, monkeypatch):
    """Vorher 2,9 dB Bedarf (erlaubt), nach der Nachführung (+0,5 dB) 3,4 dB: Abbruch, nichts geschrieben."""
    eingang = tmp_path / "roh.wav"
    eingang.write_bytes(b"x")
    monkeypatch.setattr(medien, "medien_info", lambda p: {"dauer_s": 10.0, "hat_ton": True, "hat_bild": False})
    messungen = iter([{"lufs": -20.0, "lra": 3.0, "dbtp": -7.6},     # vorher: Anhebung 6 dB → 6 − 7,6 + 1,5 = −0,1 …
                      {"lufs": -14.5, "lra": 3.0, "dbtp": -1.5},     # Kette: 0,5 LU zu leise
                      {"lufs": -14.0, "lra": 3.0, "dbtp": -1.5}])
    monkeypatch.setattr(medien, "lautheit_messen", lambda p, vorfilter="": next(messungen))
    b = mastern(eingang, tmp_path / "m.wav", max_begrenzer=0.3)
    assert b["anhebung_db"] == 6.5 and b["begrenzer_db"] == 0.4 and "nachgeführten" in b["abbruch"]
    assert not (tmp_path / "m.wav").exists()


def test_part_datei_vorhanden_bricht_ab(tmp_path, hilfe, monkeypatch):
    eingang = tmp_path / "roh.wav"
    eingang.write_bytes(b"x")
    (tmp_path / "m.part.wav").write_bytes(b"rest")
    monkeypatch.setattr(medien, "medien_info", lambda p: {"dauer_s": 10.0, "hat_ton": True, "hat_bild": False})
    monkeypatch.setattr(medien, "lautheit_messen", lambda p, vorfilter="": {"lufs": -14.0, "lra": 3.0, "dbtp": -9.0})
    with pytest.raises(StudioFehler, match="abgebrochener Lauf"):
        mastern(eingang, tmp_path / "m.wav")
    assert (tmp_path / "m.part.wav").read_bytes() == b"rest"
