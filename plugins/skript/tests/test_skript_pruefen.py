# SPDX-License-Identifier: MIT
"""Tests für skript_pruefen.py: Fehlalarme, echte Treffer, Stufen, Formate. Nur synthetische Texte."""
from __future__ import annotations

import codecs
import importlib.util
import json
import sys
from pathlib import Path

import pytest

SKRIPT = Path(__file__).resolve().parents[1] / "skills" / "skript" / "scripts" / "skript_pruefen.py"
_spec = importlib.util.spec_from_file_location("skript_pruefen", SKRIPT)
sp = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = sp  # Dataclasses brauchen das Modul in sys.modules
_spec.loader.exec_module(sp)

FUELLUNG = " Und du merkst es jeden Tag, also rechne ich es dir vor." * 14


def standard() -> dict[str, str]:
    return {r.name: "hinweis" for r in sp.REGELN}


def regeln(text: str, fmt: str = "short", **kw) -> list[str]:
    erg = sp.pruefe(text, fmt, standard(), **kw)
    assert erg is not None
    return [f.regel for f in erg.funde]


@pytest.mark.parametrize(("satz", "regel", "erwartet"), [
    ("Das erste Telefon kam 1876. Du trägst seinen Enkel jeden Tag, weil er in jede Tasche passt.", "kausal-vorn",
     False),
    ("Am 4. September kam der Ausfall, weil ein Passwort offen lag.", "kausal-vorn", True),
    ("Wirbelstürme drehen mit 300 Kilometern pro Stunde.", "anlauf-vorn", False),
    ("Wirbelstürme drehen mit 300 Kilometern pro Stunde.", "ichwir-vorn", False),
    ("Wir haben nachgerechnet, wie schnell Wirbelstürme sind.", "ichwir-vorn", True),
    ("Wir haben nachgerechnet, wie schnell Wirbelstürme sind.", "anlauf-vorn", False),
    ("Hallo, heute geht es um Wirbelstürme.", "anlauf-vorn", True),
    ("„Hallo“, sagt der Roboter am Bahnhof von Musterhafen.", "anlauf-vorn", True),
    ("Heute kostet ein Liter Milch in Musterhafen 2 Euro.", "anlauf-vorn", False),
    ("Heute zeige ich dir die Bahn von Musterhafen.", "anlauf-vorn", True),
    ("Solarstrom ist billiger denn je.", "kausal-vorn", False),
    ("Die Post sortiert 50 Millionen Briefe am Tag.", "quellvideo-vorn", False),
    ("Video-Überwachung zählt in Musterhafen 98 Fahrräder.", "quellvideo-vorn", False),
    ("Dieses Reel hat 7.899 Likes, und das Urteil darin ist falsch.", "quellvideo-vorn", True),
])
def test_erster_satz(satz, regel, erwartet):
    assert (regel in regeln(satz + FUELLUNG)) is erwartet


def test_kausal_und_ichwir_sind_keine_harten_punkte():
    assert not sp.REGEL["kausal-vorn"].hart
    assert not sp.REGEL["ichwir-vorn"].hart
    assert sp.REGEL["anlauf-vorn"].hart


def test_bannliste_und_bekannte_grenze():
    assert "bannwort" in regeln("Diese revolutionär neue Technik zählt mit." + FUELLUNG)
    # bekannte Grenze: Wortgrenzen fassen nur die Grundform, flektierte Formen rutschen durch
    assert "bannwort" not in regeln("Das ist bahnbrechende Technik und zählt mit." + FUELLUNG)


KOPF = "# T\n\n## Sprechtext\n\nDieser Magnet wiegt 500 Tonnen, so viel wie ein Flugzeug." + FUELLUNG + "\n\n"
TABELLE = "| im Text | Wert | Quelle |\n|---|---|---|\n| 500 Tonnen | 500 t | Werk Musterhafen |\n"


def test_zahlentabelle_mit_anderer_ueberschrift():
    namen = regeln(KOPF + "## Zahlentabelle\n" + TABELLE)
    assert "zahlentabelle" not in namen
    assert "zahlen-quelle" not in namen


def test_zahlentabelle_fehlt():
    assert "zahlentabelle" in regeln(KOPF)


def test_bom_wird_ueber_main_entfernt(tmp_path, capsys):
    datei = tmp_path / "z.md"
    datei.write_bytes(codecs.BOM_UTF8 + (KOPF + "## Zahlen\n" + TABELLE).encode("utf-8"))
    assert sp.main([str(datei), "--format", "short", "--json"]) == 0
    namen = [f["regel"] for f in json.loads(capsys.readouterr().out)["funde"]]
    assert "zahlentabelle" not in namen


def test_ihr_zaehlt_nicht_als_du():
    text = "Die Sonne ist groß. Ihr Kern ist 15 Millionen Grad heiß. Ihr Licht braucht acht Minuten. " * 12
    namen = regeln(text)
    assert "du-dichte" in namen
    assert "analogie" in namen


def test_analogie_erkannt_und_wendung_frueh():
    assert "analogie" not in regeln(KOPF + "## Zahlen\n" + TABELLE)
    assert "wendung" in regeln(KOPF + "## Zahlen\n" + TABELLE)
    assert "wendung" not in regeln("Dieser Magnet wiegt 500 Tonnen. Aber er schwebt." + FUELLUNG)


def test_regie_marken_zaehlen_nicht():
    mit = sp.pruefe("[A] Diese Bahn fährt 50.\n[B] Und du merkst es.", "short", standard())
    ohne = sp.pruefe("Diese Bahn fährt 50.\nUnd du merkst es.", "short", standard())
    assert mit.woerter == ohne.woerter
    assert [f.regel for f in mit.funde] == [f.regel for f in ohne.funde]


def test_fremdton_zaehlt_zur_laenge():
    text = "Diese Bahn fährt 50 Kilometer pro Stunde, und du merkst es. " * 14  # 154 Wörter ≈ 59 s
    assert "laenge" in regeln(text)
    assert "laenge" not in regeln(text, fremdton=6.0)


def test_belegblatt_neben_der_datei(tmp_path):
    skript = tmp_path / "F4_skript.md"
    skript.write_text(KOPF + "## Zahlen\n" + TABELLE, encoding="utf-8")
    erg = sp.pruefe(skript.read_text(encoding="utf-8"), "short", standard(), pfad=skript)
    assert "belegblatt" in [f.regel for f in erg.funde]
    (tmp_path / "F4_belege.md").write_text("# Belege\n", encoding="utf-8")
    erg = sp.pruefe(skript.read_text(encoding="utf-8"), "short", standard(), pfad=skript)
    assert "belegblatt" not in [f.regel for f in erg.funde]


def test_trailer_genau_eine_aufforderung():
    saetze = ["Was passiert, wenn eine Stadt jeden Tag ihre Busse zählt?"] + [
        f"In Folge {i} rechnest du mit mir nach, wie dein Alltag in Zahlen aussieht." for i in range(1, 9)]
    ohne = " ".join(saetze) + " Bis bald."
    mit = " ".join(saetze[:-1]) + " Abonnier, wenn du das auch wissen willst. " + saetze[-1]
    assert "aufforderung-trailer" in regeln(ohne, "trailer")
    assert "aufforderung-trailer" not in regeln(mit, "trailer")
    assert "letzter-satz" not in regeln(mit, "trailer")  # gilt im Trailer nicht


def test_langvideo_neue_luecke_im_takt():
    block = "Die Bahn von Musterhafen fährt jeden Tag, und du siehst sie kaum. " * 40  # 480 Wörter
    luecke = "Und jetzt kommt der Teil, den keiner erwartet. "
    ohne = block * 2
    mit = block + luecke + block + luecke
    assert "neue-luecke" in regeln(ohne, "lang", takt=120.0)
    assert "neue-luecke" not in regeln(mit, "lang", takt=180.0)


def test_stufen_und_exitcodes(tmp_path, capsys):
    datei = tmp_path / "t.md"
    datei.write_text("Diese revolutionär neue Technik zählt mit." + FUELLUNG, encoding="utf-8")
    assert sp.main([str(datei), "--format", "short"]) == 0  # Standard hinweis
    assert sp.main([str(datei), "--format", "short", "--regel", "bannwort=sperrt"]) == 1
    assert sp.main([str(datei), "--format", "short", "--streng"]) == 1
    assert sp.main([str(datei), "--format", "short", "--streng", "--regel", "bannwort=aus",
                    "--regel", "laenge=aus"]) == 0
    assert sp.main([str(datei), "--format", "short", "--regel", "gibtsnicht=sperrt"]) == 2
    assert sp.main([str(datei), "--format", "short", "--regel", "bannwort=streng"]) == 2
    capsys.readouterr()


def test_regeldatei_mit_bann_und_fremden_regeln(tmp_path):
    toml = tmp_path / "regeln.toml"
    toml.write_text('[regeln]\nbannwort = "sperrt"\nohne-verb = "aus"\n\n'
                    '[bann]\nzusaetzlich = ["Mega-Deal"]\nerlaubt = ["revolutionär"]\n', encoding="utf-8")
    stufen, daten = sp.stufen_laden(toml, [], False)
    assert stufen["bannwort"] == "sperrt"
    text = "Diese revolutionär neue Technik zählt mit." + FUELLUNG
    assert "bannwort" not in [f.regel for f in sp.pruefe(text, "short", stufen, daten=daten).funde]
    text2 = "Dieser Mega-Deal zählt mit." + FUELLUNG
    funde = sp.pruefe(text2, "short", stufen, daten=daten).funde
    assert any(f.regel == "bannwort" and f.stufe == "sperrt" for f in funde)


def test_aus_meldet_nichts():
    stufen = standard() | {"bannwort": "aus"}
    erg = sp.pruefe("Diese revolutionär neue Technik zählt mit." + FUELLUNG, "short", stufen)
    assert "bannwort" not in [f.regel for f in erg.funde]


def test_liste_und_fehlender_sprechtext(tmp_path, capsys):
    assert sp.main(["--liste"]) == 0
    assert "anlauf-vorn" in capsys.readouterr().out
    leer = tmp_path / "leer.md"
    leer.write_text("# nur Überschrift\n", encoding="utf-8")
    assert sp.main([str(leer), "--format", "short"]) == 2


def test_jede_regel_hat_formate_und_kurztext():
    for r in sp.REGELN:
        assert r.formate and set(r.formate) <= set(sp.FORMATE)
        assert r.kurz
    assert len({r.name for r in sp.REGELN}) == len(sp.REGELN)
