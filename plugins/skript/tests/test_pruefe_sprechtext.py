# SPDX-License-Identifier: MIT
"""Tests für pruefe_sprechtext.py. Nur synthetische Texte."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

SKRIPT = Path(__file__).resolve().parents[1] / "skills" / "sprechtext" / "scripts" / "pruefe_sprechtext.py"
_spec = importlib.util.spec_from_file_location("pruefe_sprechtext", SKRIPT)
ps = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = ps  # Dataclasses brauchen das Modul in sys.modules
_spec.loader.exec_module(ps)

STANDARD = {r.name: "hinweis" for r in ps.REGELN}


def regeln(text: str, **kw) -> list[str]:
    return [f.regel for f in ps.pruefe(text, STANDARD, **kw)[1]]


def test_satz_ohne_verb_und_telegramm():
    namen = regeln("Gemessen 1997. Die Menge: eine Bergmasse.")
    assert "ohne-verb" in namen


def test_ganze_saetze_ohne_fund():
    text = ("Das hat das Wetteramt 1997 gemessen. Dafür brauchst du eine ganze Bergmasse. "
            "Die Maschinen hätten dich gar nicht gebraucht. Am 19. August fährt die Bahn wieder.")
    assert regeln(text) == []


def test_doppelpunkt_am_satzende():
    assert "doppelpunkt-ende" in regeln("Die Bahn hält an. Und jetzt kommt das Beste:")


def test_beats():
    text = "Gone. Weg. Die Bahn hält in Musterhafen an jeder Ecke, und du steigst aus."
    namen = regeln(text)
    assert "kapitel-beginnt-mit-beat" in namen
    assert "beats-hintereinander" in namen


def test_budget_und_gesamtlaenge():
    text = ("Die Bahn hält an jeder Ecke, und du steigst aus. " * 10) + "\n\n" + "Dann fährt sie weiter."
    budget = [{"kapitel": 1, "startS": 0}, {"kapitel": 2, "startS": 10}]
    kapitel, funde = ps.pruefe(text, STANDARD, budget=budget, ziel=20.0)
    assert [f.regel for f in funde].count("ueber-budget") == 1
    assert "gesamtlaenge" in [f.regel for f in funde]
    assert kapitel[0].budget == 10.0


def test_budget_aus_objekt(tmp_path):
    datei = tmp_path / "b.json"
    datei.write_text(json.dumps({"kapitel": [{"kapitel": 2, "startS": 5}, {"kapitel": 1, "startS": 0}]}),
                     encoding="utf-8")
    assert [k["kapitel"] for k in ps.budget_lesen(datei)] == [1, 2]


def test_stufen_und_exitcodes(tmp_path, capsys):
    datei = tmp_path / "p.md"
    datei.write_text("Gemessen 1997.\n", encoding="utf-8")
    assert ps.main([str(datei)]) == 0
    assert ps.main([str(datei), "--regel", "ohne-verb=sperrt"]) == 1
    assert ps.main([str(datei), "--regel", "ohne-verb=aus", "--regel", "kapitel-beginnt-mit-beat=sperrt"]) == 1
    assert ps.main([str(datei), "--regel", "ohne-verb=aus", "--regel", "kapitel-beginnt-mit-beat=aus"]) == 0
    assert ps.main([str(datei), "--regel", "falsch=aus"]) == 2
    assert ps.main([str(tmp_path / "fehlt.md")]) == 2
    capsys.readouterr()
