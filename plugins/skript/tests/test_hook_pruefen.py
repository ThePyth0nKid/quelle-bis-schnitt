# SPDX-License-Identifier: MIT
"""Tests für hook_pruefen.py. Nur synthetische Hooks."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SKRIPT = Path(__file__).resolve().parents[1] / "skills" / "hook" / "scripts" / "hook_pruefen.py"
_spec = importlib.util.spec_from_file_location("hook_pruefen", SKRIPT)
hp = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = hp  # Dataclasses brauchen das Modul in sys.modules
_spec.loader.exec_module(hp)


def regeln(hook: str, **kw) -> list[str]:
    return [f.regel for f in hp.pruefe(hook, {r.name: "hinweis" for r in hp.REGELN}, **kw)]


@pytest.mark.parametrize(("hook", "regel", "erwartet"), [
    ("Hallo, heute geht es um Brücken.", "anlauf-vorn", True),
    ("Halloween kostet Musterhafen 2 Millionen Euro.", "anlauf-vorn", False),
    ("Diese Brücke in Musterhafen trägt 300 Lastwagen gleichzeitig.", "anlauf-vorn", False),
    ("Dieses Video zeigt eine Brücke.", "quellvideo-vorn", True),
    ("Video-Überwachung zählt 98 Fahrräder in Musterhafen.", "quellvideo-vorn", False),
    ("Die Brücke ist gerade eingestürzt.", "gerade-ohne-neuigkeit", True),
    ("Die Brücke trägt gerade mal 40 Tonnen.", "gerade-ohne-neuigkeit", False),
    ("Diese Brücke ist bahnbrechend schön.", "bannwort", True),
    ("Ich hab 10.000 Bälle gekauft, um darin zu schwimmen.", "ichwir-vorn", True),
    ("Diese Brücke schwingt, weil der Wind von der Seite kommt.", "kausal-vorn", True),
    ("Die Brücke in Musterhafen ist alt und hat schon viel gesehen.", "ding-vorn", True),
])
def test_einzelregeln(hook, regel, erwartet):
    assert (regel in regeln(hook)) is erwartet


def test_neu_erlaubt_gerade():
    assert "gerade-ohne-neuigkeit" not in regeln("Die Brücke ist gerade eingestürzt.", neu=True)


def test_frage_mit_schneller_antwort():
    assert "frage-vorn" not in regeln("Kann eine Brücke schwimmen? Nein, aber diese hier schon.")
    lang = ("Kann eine Brücke aus Beton bei Sturm wirklich schwimmen, wenn das Wasser steigt? "
            "Die Ingenieure der Stadtwerke von Musterhafen haben dafür über viele Jahre lang ein Modell gebaut.")
    assert "frage-vorn" in regeln(lang)


def test_bild1_text():
    assert "bild1-text" not in regeln("Diese Brücke schwimmt.", titel="WARUM SCHWIMMT DIESE BRÜCKE?")
    assert "bild1-text" in regeln("Diese Brücke schwimmt.", titel="BRÜCKE")


def test_harte_punkte_sperren_nur_mit_streng(capsys):
    hook = "Hallo, dieses Reel hat 7.000 Likes."
    assert hp.main([hook]) == 0
    assert hp.main([hook, "--streng"]) == 1
    assert hp.main([hook, "--streng", "--regel", "anlauf-vorn=aus", "--regel", "quellvideo-vorn=aus"]) == 0
    assert hp.main([hook, "--regel", "nichtda=aus"]) == 2
    assert hp.main([]) == 2
    capsys.readouterr()
    assert hp.main([hook, "--json"]) == 0
    daten = json.loads(capsys.readouterr().out)
    assert {"anlauf-vorn", "quellvideo-vorn"} <= {f["regel"] for f in daten["funde"]}
