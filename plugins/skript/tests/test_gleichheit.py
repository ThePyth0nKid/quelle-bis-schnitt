# SPDX-License-Identifier: MIT
"""Gleichheitstest: drei synthetische Skripte (gut, mittel, schlecht) mit festen Erwartungen je Regel.

Die Erwartungen der harten Punkte sind dieselben, die das Prüfskript vor der Veröffentlichung auf diesen drei Texten
als „FEHL“ gemeldet hat (0, 2 und 10). Ändert sich eine Zeile hier, hat sich das Verhalten geändert: bewusst
entscheiden und die Erwartung anpassen, nie stillschweigend.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[1]
BEISPIELE = Path(__file__).resolve().parent / "beispiele"


def _lade(name: str, pfad: Path):
    spec = importlib.util.spec_from_file_location(name, pfad)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[name] = modul
    spec.loader.exec_module(modul)
    return modul


sp = _lade("gleich_skript", WURZEL / "skills" / "skript" / "scripts" / "skript_pruefen.py")
hp = _lade("gleich_hook", WURZEL / "skills" / "hook" / "scripts" / "hook_pruefen.py")
ps = _lade("gleich_sprech", WURZEL / "skills" / "sprechtext" / "scripts" / "pruefe_sprechtext.py")

ERWARTET = {
    "gut/F1": {
        "hart": set(),
        "skript": {"quelle-im-satz"},
        "hook": set(),
        "sprech": [],
    },
    "mittel/F2": {
        "hart": {"zahlen-quelle", "bannwort"},
        "skript": {"ichwir-vorn", "kausal-vorn", "ding-vorn", "zahlen-quelle", "quelle-im-satz", "bannwort",
                   "versprechen", "neue-luecke", "slots"},
        "hook": {"ichwir-vorn", "kausal-vorn", "ding-vorn", "du-vorn"},
        "sprech": [],
    },
    "schlecht/F3": {
        "hart": {"anlauf-vorn", "quellvideo-vorn", "zahlentabelle", "belegblatt", "floskel", "du-dichte", "bannwort",
                 "gedankenstrich", "laenge", "letzter-satz"},
        "skript": {"anlauf-vorn", "quellvideo-vorn", "ding-vorn", "zahlentabelle", "belegblatt", "quelle-im-satz",
                   "floskel", "du-dichte", "bannwort", "gedankenstrich", "laenge", "letzter-satz", "versprechen",
                   "wendung", "neue-luecke", "analogie", "slots"},
        "hook": {"anlauf-vorn", "quellvideo-vorn", "bannwort", "ding-vorn", "du-vorn"},
        "sprech": ["ohne-verb", "ohne-verb"],  # „Beweis: keiner.“ und „Folg mir für mehr.“
    },
}


def _auswerten(name: str) -> dict:
    pfad = BEISPIELE / f"{name}_skript.md"
    voll = pfad.read_text(encoding="utf-8")
    erg = sp.pruefe(voll, "short", {r.name: "hinweis" for r in sp.REGELN}, pfad=pfad)
    text, _ = sp.lies_text(voll)
    saetze = sp.saetze(text)
    bild1 = re.search(r"^## Bild 1\s*\n\*\*(.+?)\*\*", voll, re.M)
    hook = hp.pruefe(" ".join(saetze[:2]), {r.name: "hinweis" for r in hp.REGELN},
                     titel=bild1.group(1) if bild1 else None)
    _, sprech = ps.pruefe(text, {r.name: "hinweis" for r in ps.REGELN}, ziel=75)
    return {
        "hart": {f.regel for f in erg.funde if sp.REGEL[f.regel].hart},
        "skript": {f.regel for f in erg.funde},
        "hook": {f.regel for f in hook},
        "sprech": [f.regel for f in sprech],
        "anzahl": len(erg.funde),
    }


@pytest.mark.parametrize("name", list(ERWARTET))
def test_erwartete_funde(name):
    ist = _auswerten(name)
    for schluessel in ("hart", "skript", "hook", "sprech"):
        assert ist[schluessel] == ERWARTET[name][schluessel], f"{name}: {schluessel}"


def test_stabil_bei_wiederholung():
    assert all(_auswerten(n) == _auswerten(n) for n in ERWARTET)


def test_sinnvolle_reihenfolge():
    gut, mittel, schlecht = (_auswerten(n) for n in ERWARTET)
    assert len(gut["hart"]) < len(mittel["hart"]) < len(schlecht["hart"])
    assert gut["anzahl"] < mittel["anzahl"] < schlecht["anzahl"]


def test_streng_sperrt_nur_mit_harten_funden(capsys):
    for name, erwartet in ERWARTET.items():
        code = sp.main([str(BEISPIELE / f"{name}_skript.md"), "--format", "short", "--streng"])
        assert code == (1 if erwartet["hart"] else 0), name
    capsys.readouterr()


def test_gemeinsame_muster_sind_gleich():
    assert sp.BANN_STANDARD == hp.BANN_STANDARD
    assert sp.STUFEN == hp.STUFEN == ps.STUFEN
    for name in ("GRUSS_START", "KAUSAL", "QUELLVIDEO", "FRAGE_ENDE", "ZAHLWORT", "ICHWIR_START"):
        assert getattr(sp, name).pattern == getattr(hp, name).pattern, name


def _regelnamen_im_skill(skill: str) -> set[str]:
    text = (WURZEL / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    return set(re.findall(r"`([a-z]+(?:-[a-z0-9]+)+)`", text))


@pytest.mark.parametrize(("skill", "modul"), [("skript", "sp"), ("hook", "hp"), ("sprechtext", "ps")])
def test_regelnamen_im_skill_gibt_es_im_code(skill, modul):
    regeln = {r.name for r in {"sp": sp, "hp": hp, "ps": ps}[modul].REGELN}
    skillnamen = ("skript-", "anti-", "hook-", "viral-", "recherche-")
    erwaehnt = {n for n in _regelnamen_im_skill(skill) if not n.startswith(skillnamen)}
    assert erwaehnt, skill
    assert erwaehnt <= regeln, erwaehnt - regeln
