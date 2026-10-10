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


def test_sinnvolle_reihenfolge():
    gut, mittel, schlecht = (_auswerten(n) for n in ERWARTET)
    assert len(gut["hart"]) < len(mittel["hart"]) < len(schlecht["hart"])
    assert gut["anzahl"] < mittel["anzahl"] < schlecht["anzahl"]


def test_streng_sperrt_nur_mit_harten_funden(capsys):
    for name, erwartet in ERWARTET.items():
        code = sp.main([str(BEISPIELE / f"{name}_skript.md"), "--format", "short", "--streng"])
        assert code == (1 if erwartet["hart"] else 0), name
    capsys.readouterr()


MODULE = {"skript_pruefen.py": sp, "hook_pruefen.py": hp, "pruefe_sprechtext.py": ps}
KERN = re.compile(r"^# >>> gemeinsamer Kern.*?^# <<< gemeinsamer Kern$", re.S | re.M)


def test_kern_ist_wortgleich():
    bloecke = {name: KERN.findall(Path(modul.__file__).read_text(encoding="utf-8"))
               for name, modul in MODULE.items()}
    assert all(len(b) == 1 for b in bloecke.values()), {n: len(b) for n, b in bloecke.items()}
    erster, *rest = (b[0] for b in bloecke.values())
    assert all(b == erster for b in rest), "Kern-Block weicht ab: in allen drei Skripten gleich ändern"


@pytest.mark.parametrize("name", ["ZAHLWORT", "DU", "ICH", "KAUSAL", "QUELLVIDEO", "GRUSS_START", "ICHWIR_START",
                                  "FRAGE_ENDE", "ABKUERZUNG", "GRENZE"])
def test_gemeinsame_muster_mit_flags(name):
    muster = [getattr(m, name) for m in MODULE.values()]
    assert len({(x.pattern, x.flags) for x in muster}) == 1, name


@pytest.mark.parametrize("name", ["STUFEN", "ALLE_REGELNAMEN", "ZEIGEWORT", "VORZEICHEN", "FRAGE_START",
                                  "MONAT_ODER_JH", "BANN_STANDARD", "SATZANFANG"])
def test_gemeinsame_konstanten(name):
    werte = [getattr(m, name) for m in MODULE.values()]
    assert all(w == werte[0] for w in werte), name


def test_alle_regelnamen_sind_die_vereinigung():
    vereinigt = {r.name for m in MODULE.values() for r in m.REGELN}
    assert vereinigt == sp.ALLE_REGELNAMEN


SATZPROBEN = [
    "Das kam 2007. Du trägst es jeden Tag.",
    "Am 4. September kam der Ausfall.",
    "Er landete am 3. Platz und war zufrieden.",
    "Er wurde 3. Dann kam der Regen.",
    "Im 19. Jahrhundert fuhr hier eine Bahn.",
    "Sie sagte: „Das stimmt.“ Dann ging sie.",
    'Er rief "Halt!" Die Bahn stand.',
    "Das kostet (ungefähr!) Du zahlst es.",
    "Das gilt z. B. für Busse. Und für Bahnen.",
    "Das sind ca. 40 Tonnen, d. h. zehn Elefanten.",
    "Dr. Mustermann misst 1,5 Mio. Fahrten. Das ist viel.",
    "Die Bahn fährt 1.440 Mal. Du fährst einmal.",
    "Sie hielt nach 1.440. Dann kam die nächste.",
    "Wirklich? Ja! Genau so.",
    "Vgl. Nr. 3 im Plan. Der Rest folgt.",
    "Er sagte nein. Sie sagte ja.",
    "Das Ende kam am 1. Mai. Dann war Ruhe.",
    "Hallo zusammen, dieses Reel hat 7.000 Likes. In diesem Video schauen wir.",
    "Drei Punkte... Und dann nichts.",
    "Das ist es",
]


def test_satztrennung_in_allen_skripten_gleich():
    for satz in SATZPROBEN:
        ergebnisse = [m.saetze(satz) for m in MODULE.values()]
        assert all(e == ergebnisse[0] for e in ergebnisse), satz


def test_regeldatei_wirkt_in_allen_skripten_gleich(tmp_path):
    toml = tmp_path / "r.toml"
    toml.write_text('[regeln]\nbannwort = "sperrt"\nanlauf-vorn = "aus"\nohne-verb = "sperrt"\n'
                    '[bann]\nzusaetzlich = ["Mega-Deal"]\n', encoding="utf-8")
    geladen = {name: m.stufen_laden(m.REGELN, toml, ["kausal-vorn=sperrt"] if m is not ps else [])
               for name, m in MODULE.items()}
    for name, (stufen, daten) in geladen.items():
        assert daten["bann"]["zusaetzlich"] == ["Mega-Deal"], name
        for regel, stufe in {"bannwort": "sperrt", "anlauf-vorn": "aus", "kausal-vorn": "sperrt",
                             "ohne-verb": "sperrt"}.items():
            if regel in stufen:
                assert stufen[regel] == stufe, (name, regel)
    fehlerhaft = tmp_path / "f.toml"
    fehlerhaft.write_text('[regeln]\ntippfehler = "aus"\n', encoding="utf-8")
    for m in MODULE.values():
        with pytest.raises(m.Eingabefehler):
            m.stufen_laden(m.REGELN, fehlerhaft, [])


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
