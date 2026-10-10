# SPDX-License-Identifier: MIT
"""Tests für zitate_pruefen.py mit erfundenen Quellen (Freie Stadt Musterhafen) und ohne Netz."""
from __future__ import annotations

import builtins
import importlib.util
import json
import socket
import sys
from pathlib import Path

import pytest

_PFAD = Path(__file__).resolve().parents[1] / "werkzeuge" / "zitate_pruefen.py"
_spec = importlib.util.spec_from_file_location("zitate_pruefen", _PFAD)
zp = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = zp  # dataclasses brauchen das Modul in sys.modules
_spec.loader.exec_module(zp)

ABSATZ = (
    "Der Rat der Freien Stadt Musterhafen hat am 3. März beschlossen, die Verträge mit der Nordlicht Analytik GmbH "
    "nicht zu verlängern. Bürgermeisterin Erika Mustermann sagte dazu: „Wir prüfen alle Angebote neu und entscheiden "
    "im Herbst.“ Der Kämmerer Max Mustermann ergänzte, die Kosten seien im Plan enthalten. "
)
FUELLTEXT = "Weitere Tagesordnungspunkte betrafen den Hafen, die Schulen und die Feuerwehr der Stadt. " * 20


def _html(text: str) -> bytes:
    return (f"<html><head><title>Ratssitzung</title><script>var x = 'Wir prüfen alle Angebote neu';</script>"
            f"</head><body><p>{text}</p></body></html>").encode()


def _abrufer(seiten: dict[str, zp.Antwort | Exception]):
    aufrufe = []

    def abrufer(url):
        aufrufe.append(url)
        wert = seiten[url]
        if isinstance(wert, Exception):
            raise wert
        return wert

    abrufer.aufrufe = aufrufe
    return abrufer


# ------------------------------------------------------------ Angleichen und Stücke

def test_angleichen_vereinheitlicht_zeichen():
    assert zp.angleichen("„Wir  prüfen“ – neu") == zp.angleichen('"wir prüfen" - neu')
    assert zp.angleichen("Ver­träge") == "verträge"
    assert zp.angleichen("Ver-\nträge mit") == "verträge mit"
    assert zp.angleichen("Nord-\nSüd") == "nord- süd"  # Bindestrich vor Großbuchstaben bleibt
    assert zp.angleichen("A￾B") == "ab"


def test_stuecke_teilt_an_auslassungen():
    assert zp.stuecke("„Wir prüfen alle Angebote neu […] im Herbst.“") == ["Wir prüfen alle Angebote neu", "im Herbst"]
    assert zp.stuecke("eins ... zwei (…) drei") == ["eins", "zwei", "drei"]


# ------------------------------------------------------------ Suchen

def test_einfaches_zitat_gefunden():
    t = zp.zitat_suchen(ABSATZ + FUELLTEXT, "Wir prüfen alle Angebote neu und entscheiden im Herbst.")
    assert t.status == "gefunden"
    assert "angebote" in t.kontext
    assert t.hinweise == []


def test_wortlaut_falsch_nicht_gefunden():
    t = zp.zitat_suchen(ABSATZ + FUELLTEXT, "Wir lehnen alle Angebote ab und entscheiden sofort.")
    assert t.status == "nicht_gefunden"


def test_zu_kurzes_zitat_nicht_pruefbar():
    t = zp.zitat_suchen(ABSATZ, "die Stadt")
    assert t.status == "nicht_pruefbar"


def test_doppelte_stelle_mehrdeutig():
    t = zp.zitat_suchen(ABSATZ + FUELLTEXT + ABSATZ, "die Kosten seien im Plan enthalten")
    assert t.status == "mehrdeutig"
    assert "2 Stellen" in t.grund


def test_auslassung_in_reihenfolge_gefunden_mit_sprecher_hinweis():
    zitat = "„Wir prüfen alle Angebote neu […] und entscheiden im Herbst“"
    t = zp.zitat_suchen(ABSATZ + FUELLTEXT, zitat, min_stueck=10)
    assert t.status == "gefunden"
    assert any("Sprecher" in h for h in t.hinweise)


def test_auslassung_gegen_die_reihenfolge_wird_gemeldet():
    # Stücke vertauscht: Der Satz des Kämmerers wird scheinbar der Bürgermeisterin zugeschrieben.
    zitat = "die Kosten seien im Plan enthalten […] Wir prüfen alle Angebote neu und entscheiden"
    t = zp.zitat_suchen(ABSATZ + FUELLTEXT, zitat)
    assert t.status == "nicht_gefunden"
    assert "reihenfolge" in t.grund.lower()


def test_auslassung_mit_zu_grosser_luecke():
    zitat = "Wir prüfen alle Angebote neu und entscheiden […] Weitere Tagesordnungspunkte betrafen den Hafen"
    nah = zp.zitat_suchen(ABSATZ + FUELLTEXT, zitat, max_luecke=6000)
    fern = zp.zitat_suchen(ABSATZ + "x" * 7000 + " " + FUELLTEXT, zitat, max_luecke=6000)
    assert nah.status == "gefunden"
    assert fern.status == "nicht_gefunden"


def test_kurze_stuecke_mit_auslassung_tragen_keine_fundstelle():
    t = zp.zitat_suchen(ABSATZ, "Der Rat […] hat beschlossen")
    assert t.status == "nicht_pruefbar"


def test_fussnotenziffer_im_pdf_text_stoert_nicht():
    text = "Die Verträge mit der Nordlicht Analytik 4 werden nicht verlängert, so der Rat. " + FUELLTEXT
    t = zp.zitat_suchen(text, "Die Verträge mit der Nordlicht Analytik werden nicht verlängert")
    assert t.status == "gefunden"


def test_silbentrennung_im_pdf_text():
    text = "Die Bürgermeisterin sagte, man werde alle Ange-\nbote neu prüfen und im Herbst entscheiden. " + FUELLTEXT
    t = zp.zitat_suchen(text, "man werde alle Angebote neu prüfen")
    assert t.status == "gefunden"


# ------------------------------------------------------------ Text gewinnen

def test_html_ohne_skripte_und_mit_zeichensatz():
    daten = '<meta charset="iso-8859-1"><p>Bürgermeisterin</p><style>p{}</style>'.encode("iso-8859-1")
    text = zp.html_zu_text(daten)
    assert "Bürgermeisterin" in text
    assert "p{}" not in text


def test_skripttext_zaehlt_nicht_als_fundstelle():
    antwort = zp.Antwort(200, "text/html; charset=utf-8", _html("Nur ein anderer Satz. " + FUELLTEXT), "https://x")
    text = zp.quelltext(antwort)
    assert zp.zitat_suchen(text, "Wir prüfen alle Angebote neu").status == "nicht_gefunden"


def test_kaum_text_ist_nicht_pruefbar():
    antwort = zp.Antwort(200, "text/html", b"<html><body><div id='app'></div></body></html>", "https://x")
    with pytest.raises(zp.AbrufFehler) as e:
        zp.quelltext(antwort)
    assert e.value.art == "nicht_pruefbar"


def test_pdf_ohne_leser_nicht_pruefbar(monkeypatch):
    echtes_import = builtins.__import__

    def ohne_pdf(name, *args, **kwargs):
        if name in ("pypdf", "fitz"):
            raise ImportError(name)
        return echtes_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", ohne_pdf)
    with pytest.raises(zp.AbrufFehler) as e:
        zp.pdf_zu_text(b"%PDF-1.7 ...")
    assert e.value.art == "nicht_pruefbar"
    assert "pypdf" in e.value.grund


# ------------------------------------------------------------ Adressen

def test_nur_http_und_https():
    with pytest.raises(zp.AbrufFehler) as e:
        zp.adresse_pruefen("file:///etc/passwd")
    assert e.value.art == "nicht_pruefbar"


def test_lokale_ziele_gesperrt(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(None, None, None, "", ("127.0.0.1", 80))])
    with pytest.raises(zp.AbrufFehler) as e:
        zp.adresse_pruefen("http://intern.example/")
    assert "lokal oder privat" in e.value.grund
    zp.adresse_pruefen("http://intern.example/", erlaube_lokal=True)


def test_oeffentliche_ziele_erlaubt(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(None, None, None, "", ("93.184.215.14", 443))])
    zp.adresse_pruefen("https://www.musterhafen.example/rat")


def test_weiterleitung_wird_je_schritt_geprueft(monkeypatch):
    def getaddrinfo(host, *a, **k):
        ip = "169.254.10.20" if host == "intern.example" else "93.184.215.14"
        return [(None, None, None, "", (ip, 80))]

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(zp, "_einmal_requests", lambda url, z: (302, {"location": "http://intern.example/"}, b""))
    monkeypatch.setattr(zp, "_einmal_urllib", lambda url, z: (302, {"location": "http://intern.example/"}, b""))
    with pytest.raises(zp.AbrufFehler) as e:
        zp.abrufen("https://www.musterhafen.example/")
    assert "lokal oder privat" in e.value.grund


def test_sperrstatus_ist_nicht_pruefbar(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(None, None, None, "", ("93.184.215.14", 443))])
    monkeypatch.setattr(zp, "_einmal_requests", lambda url, z: (403, {}, b""))
    monkeypatch.setattr(zp, "_einmal_urllib", lambda url, z: (403, {}, b""))
    with pytest.raises(zp.AbrufFehler) as e:
        zp.abrufen("https://www.musterhafen.example/")
    assert e.value.art == "nicht_pruefbar"


# ------------------------------------------------------------ Ablauf

def test_alle_pruefen_laedt_jede_url_einmal():
    url = "https://www.musterhafen.example/rat/2026-03-03"
    abrufer = _abrufer({
        url: zp.Antwort(200, "text/html; charset=utf-8", _html(ABSATZ + FUELLTEXT), url),
        "https://gesperrt.example/": zp.AbrufFehler("nicht_pruefbar", "HTTP 403"),
    })
    belege = [
        {"id": "B1", "url": url, "zitat": "Wir prüfen alle Angebote neu und entscheiden im Herbst."},
        {"id": "B2", "url": url, "zitat": "Wir kündigen alle Verträge sofort."},
        {"id": "B3", "url": "https://gesperrt.example/", "zitat": "Ein Satz hinter der Bezahlschranke."},
        {"id": "B4", "url": url, "zitat": ""},
    ]
    ergebnisse = zp.alle_pruefen(belege, abrufer=abrufer, pause=0)
    assert [e.status for e in ergebnisse] == ["gefunden", "nicht_gefunden", "nicht_pruefbar", "fehler"]
    assert abrufer.aufrufe.count(url) == 1
    bericht = zp.text_bericht(ergebnisse)
    assert "B2" in bericht and "B1" not in bericht
    assert "Mensch" in bericht


def test_main_exit_null_und_json(tmp_path, monkeypatch, capsys):
    url = "https://www.musterhafen.example/rat"
    seite = zp.Antwort(200, "text/html; charset=utf-8", _html(ABSATZ + FUELLTEXT), url)
    monkeypatch.setattr(zp, "abrufen", lambda u, **k: seite)
    belege = tmp_path / "belege.json"
    belege.write_text(json.dumps([{"id": "B1", "url": url, "zitat": "Wort, das nicht vorkommt, und mehr Text"}]),
                      encoding="utf-8")
    ziel = tmp_path / "bericht.json"
    assert zp.main([str(belege), "--json", str(ziel), "--pause", "0"]) == 0
    daten = json.loads(ziel.read_text(encoding="utf-8"))
    assert daten[0]["status"] == "nicht_gefunden"
    assert "nicht_gefunden 1" in capsys.readouterr().out


def test_main_aufruffehler(tmp_path):
    assert zp.main([str(tmp_path / "fehlt.json")]) == 2
    kaputt = tmp_path / "kaputt.json"
    kaputt.write_text("{kein json", encoding="utf-8")
    assert zp.main([str(kaputt)]) == 2
