# SPDX-License-Identifier: MIT
"""Tests für pruefe_sprechtext.py. Nur synthetische Texte."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SKRIPT = Path(__file__).resolve().parents[1] / "skills" / "sprechtext" / "scripts" / "pruefe_sprechtext.py"
_spec = importlib.util.spec_from_file_location("pruefe_sprechtext", SKRIPT)
ps = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = ps  # Dataclasses brauchen das Modul in sys.modules
_spec.loader.exec_module(ps)

STANDARD = {r.name: "hinweis" for r in ps.REGELN}


def regeln(text: str, **kw) -> list[str]:
    return [f.regel for f in ps.pruefe(text, STANDARD, **kw)[1]]


def test_satz_ohne_verb_und_telegramm():
    assert "ohne-verb" in regeln("Gemessen 1997. Die Menge: eine Bergmasse.")


def test_ganze_saetze_ohne_fund():
    text = ("Das hat das Wetteramt 1997 gemessen. Dafür brauchst du eine ganze Bergmasse. "
            "Die Maschinen hätten dich gar nicht gebraucht. Am 19. August fährt die Bahn wieder.")
    assert regeln(text) == []


@pytest.mark.parametrize(("satz", "verb"), [
    ("Wie läuft's heute in Musterhafen?", True),
    ("Gibt’s das wirklich?", True),
    ("Die Kosten.", False),
    ("Das Ende.", False),
    ("Die Rede.", False),
    ("Schau dir das an.", True),
    ("Kosten steigen.", True),
    ("Die Kosten steigen jedes Jahr.", True),
])
def test_verb_erkennung(satz, verb):
    assert ps.hat_verb(satz) is verb


def test_doppelpunkt_am_satzende():
    assert "doppelpunkt-ende" in regeln("Die Bahn hält an. Und jetzt kommt das Beste:")


def test_beats():
    namen = regeln("Gone. Weg. Die Bahn hält in Musterhafen an jeder Ecke, und du steigst aus.")
    assert "kapitel-beginnt-mit-beat" in namen
    assert "beats-hintereinander" in namen


def test_budget_und_gesamtlaenge():
    text = ("Die Bahn hält an jeder Ecke, und du steigst aus. " * 10) + "\n\n" + "Dann fährt sie weiter."
    kapitel, funde = ps.pruefe(text, STANDARD, budget={1: 0.0, 2: 10.0}, ziel=20.0)
    assert [f.regel for f in funde].count("ueber-budget") == 1
    assert "gesamtlaenge" in [f.regel for f in funde]
    assert kapitel[0].budget == 10.0
    assert kapitel[1].budget == 20.0  # letztes Kapitel: --letztes


def test_titel_und_zeitmarken_sind_keine_kapitel():
    text = ("# Titel\n\n⏱ 0:00\n\nDie Bahn hält an jeder Ecke, und du steigst aus. " * 1
            + "\n\n▶ Take 2\n\nDann fährt sie weiter, und du schaust ihr nach.")
    kapitel, funde = ps.pruefe(text, STANDARD, budget={1: 0.0, 2: 30.0}, letztes=5.0)
    assert [k.nummer for k in kapitel] == [1, 2]
    assert kapitel[0].budget == 30.0  # Budget hängt an Kapitel 1, nicht am Titelblock
    assert kapitel[1].budget == 5.0
    assert funde == []


def test_budget_an_kapitelnummer_gebunden():
    text = "Die Bahn hält an jeder Ecke.\n\nDann fährt sie weiter.\n\nUnd du schaust ihr nach."
    kapitel, _ = ps.pruefe(text, STANDARD, budget={3: 40.0, 1: 0.0}, letztes=7.0)
    assert [k.budget for k in kapitel] == [40.0, None, 7.0]


def test_budget_aus_objekt_und_reihenfolge(tmp_path):
    datei = tmp_path / "b.json"
    datei.write_text(json.dumps({"kapitel": [{"kapitel": 2, "startS": 5}, {"kapitel": 1, "startS": 0}]}),
                     encoding="utf-8")
    assert ps.budget_lesen(datei) == {2: 5.0, 1: 0.0}
    datei.write_text(json.dumps([{"startS": 0}, {"startS": 12.5}]), encoding="utf-8")
    assert ps.budget_lesen(datei) == {1: 0.0, 2: 12.5}


@pytest.mark.parametrize("inhalt", ['[{"kapitel": 1}]', '[{"kapitel": "a", "startS": 0}]', '"text"', "{kaputt",
                                    '[{"kapitel": 1, "startS": "nan"}]'])
def test_kaputtes_budget_ist_eingabefehler(tmp_path, capsys, inhalt):
    budget = tmp_path / "b.json"
    budget.write_text(inhalt, encoding="utf-8")
    datei = tmp_path / "p.md"
    datei.write_text("Die Bahn hält.\n", encoding="utf-8")
    assert ps.main([str(datei), "--budget", str(budget)]) == 2
    capsys.readouterr()


def test_stufen_und_exitcodes(tmp_path, capsys):
    datei = tmp_path / "p.md"
    datei.write_text("Gemessen 1997.\n", encoding="utf-8")
    assert ps.main([str(datei)]) == 0
    assert ps.main([str(datei), "--regel", "ohne-verb=sperrt"]) == 1
    assert ps.main([str(datei), "--regel", "ohne-verb=aus", "--regel", "kapitel-beginnt-mit-beat=sperrt"]) == 1
    assert ps.main([str(datei), "--regel", "ohne-verb=aus", "--regel", "kapitel-beginnt-mit-beat=aus"]) == 0
    assert ps.main([str(datei), "--regel", "falsch=aus"]) == 2
    assert ps.main([str(tmp_path / "fehlt.md")]) == 2
    assert ps.main([str(datei), "--tempo", "nan"]) == 2
    assert ps.main([str(datei), "--letztes", "-1"]) == 2
    capsys.readouterr()


def test_leere_datei_und_nur_titel_sind_eingabefehler(tmp_path, capsys):
    leer = tmp_path / "leer.md"
    leer.write_text("", encoding="utf-8")
    assert ps.main([str(leer)]) == 2
    leer.write_text("# Titel\n\n⏱ 0:00\n", encoding="utf-8")
    assert ps.main([str(leer)]) == 2
    leer.write_bytes(b"\xff\xfe kaputt")
    assert ps.main([str(leer)]) == 2
    assert "nicht UTF-8" in capsys.readouterr().err
