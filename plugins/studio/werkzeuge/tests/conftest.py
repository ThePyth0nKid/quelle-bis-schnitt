# SPDX-License-Identifier: MIT
"""Gemeinsame Hilfen als Fixture ``hilfe``: Konfiguration im Testordner, WAV schreiben ohne ffmpeg, Sprachsignal.

Die Testordner sind keine Pakete (andere Plugins haben auch ``tests/``); darum Fixtures statt Importen.
"""
from __future__ import annotations

import wave
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from studio_werkzeuge.konfig import Konfig, laden


@pytest.fixture(autouse=True)
def keine_fremde_konfig(monkeypatch, tmp_path_factory):
    """Kein Test darf eine echte studio.toml finden: Suche auf leere Testordner umbiegen."""
    leer = tmp_path_factory.mktemp("leer")
    monkeypatch.delenv("STUDIO_KONFIG", raising=False)
    monkeypatch.setenv("APPDATA", str(leer))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(leer))
    monkeypatch.chdir(leer)


def _konfig_aus(ordner: Path, text: str) -> Konfig:
    datei = ordner / "studio.toml"
    datei.write_text(text, encoding="utf-8")
    return laden(datei)


def _wav_schreiben(pfad: Path, x: np.ndarray, rate: int = 48_000) -> Path:
    """Mono, 16 Bit, Werte −1..1."""
    daten = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    with wave.open(str(pfad), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(daten)
    return pfad


def _sprache(sekunden: float, rate: int = 48_000, seed: int = 5) -> np.ndarray:
    """Sprachähnlich: tiefer Ton mit langsamer Hüllkurve plus leises Rauschen (ohne Klicks)."""
    t = np.arange(int(sekunden * rate)) / rate
    rng = np.random.default_rng(seed)
    return (0.5 * np.sin(2 * np.pi * 140 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.5 * t))
            + rng.normal(0, 0.003, t.size)).astype(np.float32)


@pytest.fixture
def hilfe() -> SimpleNamespace:
    return SimpleNamespace(konfig_aus=_konfig_aus, wav_schreiben=_wav_schreiben, sprache=_sprache)
