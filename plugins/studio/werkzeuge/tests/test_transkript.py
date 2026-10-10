# SPDX-License-Identifier: MIT
"""Transkript: Gerätewahl, nie ein erwarteter Text als Prompt, Fern-Befehl mit Attrappe, Ausgabeformate."""
from __future__ import annotations

import json
import shutil
import sys
from types import SimpleNamespace

import pytest
from studio_werkzeuge import transkript as tr
from studio_werkzeuge.fehler import KonfigFehler, StudioFehler

FFMPEG_DA = shutil.which("ffmpeg") is not None


def test_geraet_waehlen():
    assert tr.geraet_waehlen("cpu") == ("cpu", "int8") and tr.geraet_waehlen("cuda") == ("cuda", "float16")
    assert tr.geraet_waehlen("auto")[0] in ("cpu", "cuda")
    with pytest.raises(StudioFehler):
        tr.geraet_waehlen("tpu")


def test_lokal_ohne_initial_prompt(monkeypatch, tmp_path):
    aufrufe: dict = {}

    class FakeModell:
        def __init__(self, modell, device, compute_type):
            aufrufe["modell"] = (modell, device, compute_type)

        def transcribe(self, datei, **kw):
            aufrufe["kw"] = kw
            wort = SimpleNamespace(start=0.0, end=0.4, word=" Hallo")
            return [SimpleNamespace(start=0.0, end=1.0, text=" Hallo Welt", words=[wort])], None

    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=FakeModell))
    segmente = tr.lokal(tmp_path / "x.wav", "small", "de", "cpu")
    assert segmente == [{"start": 0.0, "end": 1.0, "text": "Hallo Welt", "woerter": [{"start": 0.0, "end": 0.4,
                                                                                    "wort": "Hallo"}]}]
    assert "initial_prompt" not in aufrufe["kw"] and aufrufe["modell"] == ("small", "cpu", "int8")


def test_lokal_ohne_paket_klare_meldung(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    with pytest.raises(StudioFehler, match=r"studio-werkzeuge\[whisper\]"):
        tr.lokal(tmp_path / "x.wav")


def test_fern_befehl_wird_geprueft(tmp_path, hilfe):
    with pytest.raises(KonfigFehler):
        tr.fern_befehl(hilfe.konfig_aus(tmp_path, "[transkript.fern]\nbefehl = []\n"))
    with pytest.raises(KonfigFehler, match="Platzhalter"):
        tr.fern_befehl(hilfe.konfig_aus(tmp_path, '[transkript.fern]\nbefehl = ["ssh", "<rechner>"]\n'))
    assert tr.fern_befehl(hilfe.konfig_aus(tmp_path, '[transkript.fern]\nbefehl = ["a", "b"]\n')) == ["a", "b"]


@pytest.mark.skipif(not FFMPEG_DA, reason="ffmpeg fehlt")
def test_fern_mit_attrappe(tmp_path, hilfe):
    datei = hilfe.wav_schreiben(tmp_path / "x.wav", hilfe.sprache(2.0))
    kind = ("import sys, json; d = sys.stdin.buffer.read(); "
            "print(json.dumps({'segmente': [{'start': 0, 'end': 2, 'text': 'RIFF' if d[:4] == b'RIFF' else 'nein'}]}))")
    segmente = tr.fern(datei, [sys.executable, "-c", kind], zeitlimit_s=60)
    assert segmente == [{"start": 0.0, "end": 2.0, "text": "RIFF", "woerter": []}]   # WAV kam über stdin an
    with pytest.raises(StudioFehler, match="kein JSON"):
        tr.fern(datei, [sys.executable, "-c", "print('x')"])


def test_ausgabeformate():
    s = [{"start": 0.0, "end": 1.25, "text": "Eins"}, {"start": 61.5, "end": 3661.0, "text": "Zwei"}]
    assert tr.als_text(s, ".srt").startswith("1\n00:00:00,000 --> 00:00:01,250\nEins\n")
    assert "01:01:01,000" in tr.als_text(s, ".srt")
    assert json.loads(tr.als_text(s, ".json"))["segmente"][1]["text"] == "Zwei"
    assert tr.als_text(s, ".txt").splitlines()[0].endswith("] Eins")
