# SPDX-License-Identifier: MIT
"""Tests für den Scrub-Prüfer: Treffer, Ausnahmen und was im Log erscheinen darf."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("scrub_pruefen", Path(__file__).with_name("pruefen.py"))
scrub = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = scrub  # für dataclasses nötig
_spec.loader.exec_module(scrub)

# Ein Schlüssel-förmiger Testwert, zusammengesetzt, damit diese Datei selbst sauber bleibt.
SCHLUESSEL = "gh" + "p_" + "A" * 36


def _oeffentlich():
    return scrub.regeln_laden(nur_oeffentlich=True)[0]


def test_oeffentliche_regel_trifft_und_wird_maskiert(tmp_path, capsys):
    datei = tmp_path / "a.txt"
    datei.write_text(f"token = {SCHLUESSEL}\n", encoding="utf-8")
    funde = scrub.dateien_pruefen([datei], tmp_path, _oeffentlich())
    assert len(funde) == 1
    scrub.ausgeben(funde, zeigen=False)
    ausgabe = capsys.readouterr().out
    assert SCHLUESSEL not in ausgabe and "Zeichen" in ausgabe
    scrub.ausgeben(funde, zeigen=True)
    assert SCHLUESSEL in capsys.readouterr().out


def test_platzhalterpfad_ist_erlaubt(tmp_path):
    datei = tmp_path / "b.md"
    datei.write_text("Lege die Datei unter C:/Users/<name>/studio.toml ab.\n", encoding="utf-8")
    assert scrub.dateien_pruefen([datei], tmp_path, _oeffentlich()) == []


def test_erlaubt_marke_gilt_nur_fuer_oeffentliche_regeln(tmp_path):
    regeln = _oeffentlich() + scrub._regeln_lesen("geheimwort", True, "privat")
    datei = tmp_path / "c.txt"
    datei.write_text(f"{SCHLUESSEL} geheimwort  # scrub:erlaubt\n", encoding="utf-8")
    funde = scrub.dateien_pruefen([datei], tmp_path, regeln)
    assert [f.regel.privat for f in funde] == [True]


def test_private_regex_fehler_verraet_kein_muster():
    with pytest.raises(SystemExit) as fehler:
        scrub._regeln_lesen("geheim(", True, "privat")
    assert "geheim" not in str(fehler.value)
