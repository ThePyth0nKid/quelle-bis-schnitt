# SPDX-License-Identifier: MIT
"""Tests für zitate_pruefen.py mit erfundenen Quellen (Freie Stadt Musterhafen) und ohne Netz."""
from __future__ import annotations

import builtins
import importlib.util
import io
import ipaddress
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

OEFFENTLICH = "93.184.215.14"
ABSATZ = (
    "Der Rat der Freien Stadt Musterhafen hat am 3. März beschlossen, die Verträge mit der Nordlicht Analytik GmbH "
    "nicht zu verlängern. Bürgermeisterin Erika Mustermann sagte dazu: „Wir prüfen alle Angebote neu und entscheiden "
    "im Herbst.“ Der Kämmerer Max Mustermann ergänzte, die Kosten seien im Plan enthalten. "
)
FUELLTEXT = "Weitere Tagesordnungspunkte betrafen den Hafen, die Schulen und die Feuerwehr der Stadt. " * 20


def _html(text: str) -> bytes:
    return (f"<html><head><title>Ratssitzung</title><script>var x = 'Wir prüfen alle Angebote neu';</script>"
            f"</head><body><p>{text}</p></body></html>").encode()


def _abrufer(seiten: dict):
    aufrufe = []

    def abrufer(url):
        aufrufe.append(url)
        wert = seiten[url]
        if isinstance(wert, Exception):
            raise wert
        return wert

    abrufer.aufrufe = aufrufe
    return abrufer


class _FakeAntwort:
    def __init__(self, status: int, kopf: dict | None = None, koerper: bytes = b"", endlos: bool = False):
        self.status = status
        self._kopf = kopf or {}
        self._koerper = io.BytesIO(koerper)
        self._endlos = endlos

    def getheaders(self):
        return list(self._kopf.items())

    def read(self, n):
        return b"x" * 100 if self._endlos else self._koerper.read(n)


class _FakeVerbindungen:
    """Ersetzt zp._verbindung: liefert vorbereitete Antworten und merkt sich, zu welcher IP verbunden wurde."""

    def __init__(self, antworten: list[_FakeAntwort]):
        self.antworten = list(antworten)
        self.ziele: list[tuple[str, str]] = []

    def __call__(self, schema, host, port, ip, timeout):
        self.ziele.append((host, ip))
        antwort = self.antworten.pop(0)

        class Verbindung:
            sock = None

            def request(self, methode, pfad, headers):
                self.anfrage = (methode, pfad, headers)

            def getresponse(self):
                return antwort

            def close(self):
                pass

        return Verbindung()


def _aufloesung(tabelle: dict[str, str], zaehler: list | None = None):
    def getaddrinfo(host, port, *a, **k):
        if zaehler is not None:
            zaehler.append(host)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (tabelle[host], port))]

    return getaddrinfo


# ------------------------------------------------------------ Angleichen und Stücke

def test_angleichen_vereinheitlicht_zeichen():
    assert zp.angleichen("„Wir  prüfen“ – neu") == zp.angleichen('"wir prüfen" - neu')
    assert zp.angleichen("Ver­träge") == "verträge"
    assert zp.angleichen("Ver-\nträge mit") == "verträge mit"
    assert zp.angleichen("E-\nMail", trennung="behalten") == "e-mail"
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
    assert zp.zitat_suchen(ABSATZ, "die Stadt").status == "nicht_pruefbar"


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


def test_reihenfolge_meldung_auch_mit_fussnoten():
    text = ("Die Kosten seien im Plan 3 enthalten, sagte er. " + FUELLTEXT
            + "Wir prüfen alle Angebote neu und entscheiden im Herbst. " + FUELLTEXT)
    zitat = "Wir prüfen alle Angebote neu und entscheiden […] die Kosten seien im Plan enthalten"
    t = zp.zitat_suchen(text, zitat)
    assert t.status == "nicht_gefunden"
    assert "reihenfolge" in t.grund.lower()


def test_auslassung_mit_zu_grosser_luecke():
    zitat = "Wir prüfen alle Angebote neu und entscheiden […] Weitere Tagesordnungspunkte betrafen den Hafen"
    nah = zp.zitat_suchen(ABSATZ + FUELLTEXT, zitat, max_luecke=6000)
    fern = zp.zitat_suchen(ABSATZ + "x" * 7000 + " " + FUELLTEXT, zitat, max_luecke=6000)
    assert nah.status == "gefunden"
    assert fern.status == "nicht_gefunden"


def test_kurze_stuecke_mit_auslassung_tragen_keine_fundstelle():
    assert zp.zitat_suchen(ABSATZ, "Der Rat […] hat beschlossen").status == "nicht_pruefbar"


def test_fussnotenziffer_im_pdf_text_stoert_nicht():
    text = "Die Verträge mit der Nordlicht Analytik 4 werden nicht verlängert, so der Rat. " + FUELLTEXT
    assert zp.zitat_suchen(text, "Die Verträge mit der Nordlicht Analytik werden nicht verlängert").status == "gefunden"


def test_silbentrennung_und_bindestrich_am_zeilenende():
    text = ("Die Bürgermeisterin sagte, man werde alle Ange-\nbote neu prüfen. Fragen bitte per E-\n"
            "Mail an die Pressestelle der Stadt. " + FUELLTEXT)
    assert zp.zitat_suchen(text, "man werde alle Angebote neu prüfen").status == "gefunden"
    assert zp.zitat_suchen(text, "Fragen bitte per E-Mail an die Pressestelle").status == "gefunden"


def test_kontext_ohne_steuerzeichen():
    text = "Vorher\x07\x1b[31m " + ABSATZ + FUELLTEXT
    t = zp.zitat_suchen(text, "Der Rat der Freien Stadt Musterhafen hat am 3. März beschlossen")
    assert t.status == "gefunden"
    assert "\x07" not in t.kontext and "\x1b" not in t.kontext


# ------------------------------------------------------------ Text gewinnen

def test_html_ohne_skripte_und_mit_zeichensatz():
    daten = '<meta charset="iso-8859-1"><p>Bürgermeisterin</p><style>p{}</style>'.encode("iso-8859-1")
    text = zp.html_zu_text(daten)
    assert "Bürgermeisterin" in text
    assert "p{}" not in text


def test_zeichensatz_in_anfuehrungszeichen():
    assert zp._zeichensatz('text/html; charset="iso-8859-1"', b"") == "iso-8859-1"


def test_entitaeten_nur_einmal_entschluesselt():
    assert zp.html_zu_text(b"<p>A &amp;lt; B</p>").strip() == "A &lt; B"


def test_skripttext_zaehlt_nicht_als_fundstelle():
    antwort = zp.Antwort(200, "text/html; charset=utf-8", _html("Nur ein anderer Satz. " + FUELLTEXT), "https://x")
    assert zp.zitat_suchen(zp.quelltext(antwort), "Wir prüfen alle Angebote neu").status == "nicht_gefunden"


def test_kaum_text_ist_nicht_pruefbar():
    antwort = zp.Antwort(200, "text/html", b"<html><body><div id='app'></div></body></html>", "https://x")
    with pytest.raises(zp.AbrufFehler) as e:
        zp.quelltext(antwort)
    assert e.value.art == "nicht_pruefbar"


def test_nicht_text_ist_nicht_pruefbar():
    antwort = zp.Antwort(200, "image/png", b"\x89PNG\r\n" + b"\x00" * 600, "https://x/bild.png")
    with pytest.raises(zp.AbrufFehler) as e:
        zp.quelltext(antwort)
    assert e.value.art == "nicht_pruefbar" and "kein Text" in e.value.grund


def test_textgrenze_je_quelle():
    antwort = zp.Antwort(200, "text/plain", ("Satz. " * 2000).encode(), "https://x")
    with pytest.raises(zp.AbrufFehler) as e:
        zp.quelltext(antwort, max_text=1000)
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
        zp.url_zerlegen("file:///etc/passwd")
    assert e.value.art == "nicht_pruefbar"


@pytest.mark.parametrize("url", ["http://[x", "https://www.musterhafen.example/a b", "https://a.example\\@b.example/",
                                 "https://a.example/\x00", "https://nutzer:geheim@example.org/"])
def test_kaputte_urls_sind_fehler(url):
    with pytest.raises(zp.AbrufFehler) as e:
        zp.url_zerlegen(url)
    assert e.value.art == "fehler"


@pytest.mark.parametrize("adresse, erlaubt", [
    (str(ipaddress.IPv4Address(0x64400001)), False),  # CGNAT (Shared Address Space)
    ("64:ff9b::7f00:1", False),  # NAT64 auf Loopback
    ("64:ff9b::5db8:d70e", True),  # NAT64 auf öffentliche Adresse
    ("::ffff:7f00:1", False),  # IPv4-gemappt
    ("2002:7f00:1::1", False),  # 6to4 auf Loopback
    ("169.254.10.20", False),  # Link-local
    ("127.0.0.1", False),
    ("224.0.0.1", False),
    (OEFFENTLICH, True),
    ("2606:4700::1111", True),
])
def test_ip_erlaubt(adresse, erlaubt):
    assert zp.ip_erlaubt(ipaddress.ip_address(adresse)) is erlaubt


def test_lokale_ziele_gesperrt(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _aufloesung({"intern.example": "127.0.0.1"}))
    with pytest.raises(zp.AbrufFehler) as e:
        zp.ziel_aufloesen("intern.example", 80)
    assert "nicht öffentlich" in e.value.grund
    assert zp.ziel_aufloesen("intern.example", 80, erlaube_lokal=True) == "127.0.0.1"


def test_cgnat_ziel_gesperrt(monkeypatch):
    cgnat = str(ipaddress.IPv4Address(0x64400001))
    monkeypatch.setattr(socket, "getaddrinfo", _aufloesung({"cgnat.example": cgnat}))
    with pytest.raises(zp.AbrufFehler):
        zp.ziel_aufloesen("cgnat.example", 443)


def test_rebinding_aufloesung_wird_nur_einmal_genutzt(monkeypatch):
    # Erste Auflösung öffentlich, jede weitere zeigt auf Loopback: verbunden werden darf nur die erste IP.
    zaehler: list[str] = []

    def getaddrinfo(host, port, *a, **k):
        zaehler.append(host)
        ip = OEFFENTLICH if len(zaehler) == 1 else "127.0.0.1"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    verbindungen = _FakeVerbindungen([_FakeAntwort(200, {"Content-Type": "text/plain"}, b"Text " * 100)])
    monkeypatch.setattr(zp, "_verbindung", verbindungen)
    antwort = zp.abrufen("https://www.musterhafen.example/rat")
    assert antwort.status == 200
    assert zaehler == ["www.musterhafen.example"]
    assert verbindungen.ziele == [("www.musterhafen.example", OEFFENTLICH)]


def test_weiterleitung_wird_je_schritt_geprueft(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _aufloesung({"www.musterhafen.example": OEFFENTLICH,
                                                            "intern.example": "169.254.10.20"}))
    monkeypatch.setattr(zp, "_verbindung", _FakeVerbindungen([_FakeAntwort(302, {"Location": "http://intern.example/"})]))
    with pytest.raises(zp.AbrufFehler) as e:
        zp.abrufen("https://www.musterhafen.example/")
    assert "nicht öffentlich" in e.value.grund


def test_sperrstatus_ist_nicht_pruefbar(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _aufloesung({"www.musterhafen.example": OEFFENTLICH}))
    monkeypatch.setattr(zp, "_verbindung", _FakeVerbindungen([_FakeAntwort(403)]))
    with pytest.raises(zp.AbrufFehler) as e:
        zp.abrufen("https://www.musterhafen.example/")
    assert e.value.art == "nicht_pruefbar"


def test_gesamtfrist_bricht_endlosen_abruf_ab(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _aufloesung({"langsam.example": OEFFENTLICH}))
    monkeypatch.setattr(zp, "_verbindung", _FakeVerbindungen([_FakeAntwort(200, {}, endlos=True)]))
    uhr = iter(float(i) for i in range(10_000))
    monkeypatch.setattr(zp.time, "monotonic", lambda: next(uhr))
    with pytest.raises(zp.AbrufFehler) as e:
        zp.abrufen("https://langsam.example/", gesamtfrist=20)
    assert "Gesamtfrist" in e.value.grund


def test_groessengrenze(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _aufloesung({"gross.example": OEFFENTLICH}))
    monkeypatch.setattr(zp, "_verbindung", _FakeVerbindungen([_FakeAntwort(200, {}, b"x" * 5000)]))
    with pytest.raises(zp.AbrufFehler) as e:
        zp.abrufen("https://gross.example/", max_bytes=1000)
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


def test_einzelner_beleg_bricht_den_lauf_nicht_ab():
    def abrufer(url):
        if "kaputt" in url:
            raise UnicodeError("seltsame Kodierung")
        if "[" in url:
            raise ValueError("Invalid IPv6 URL")
        return zp.Antwort(200, "text/plain", (ABSATZ + FUELLTEXT).encode(), url)

    belege = [
        {"id": "N", "url": "https://www.musterhafen.example/", "zitat": None},
        {"url": "https://www.musterhafen.example/", "zitat": "die Kosten seien im Plan enthalten"},
        {"id": "U", "url": "https://kaputt.example/", "zitat": "irgendein langes Zitat"},
        {"id": "K", "url": "http://[x", "zitat": "irgendein langes Zitat"},
        "kein Objekt",
    ]
    ergebnisse = zp.alle_pruefen(belege, abrufer=abrufer, pause=0)
    assert [e.status for e in ergebnisse] == ["fehler", "gefunden", "fehler", "fehler", "fehler"]
    assert ergebnisse[0].grund == "Zitat fehlt"
    assert ergebnisse[1].id == "#2" and "ohne id" in ergebnisse[1].hinweise[0]


def test_kaputte_url_mit_echtem_abrufer():
    ergebnisse = zp.alle_pruefen([{"id": "K", "url": "http://[x", "zitat": "irgendein langes Zitat"}], pause=0)
    assert ergebnisse[0].status == "fehler"
    assert "ungültig" in ergebnisse[0].grund


def _belege_datei(tmp_path, eintraege) -> Path:
    pfad = tmp_path / "belege.json"
    pfad.write_text(json.dumps(eintraege, ensure_ascii=False), encoding="utf-8")
    return pfad


def test_main_exit_null_und_json(tmp_path, monkeypatch, capsys):
    url = "https://www.musterhafen.example/rat"
    seite = zp.Antwort(200, "text/html; charset=utf-8", _html(ABSATZ + FUELLTEXT), url)
    monkeypatch.setattr(zp, "abrufen", lambda u, **k: seite)
    belege = _belege_datei(tmp_path, [{"id": "B1", "url": url, "zitat": "Wort, das nicht vorkommt, und mehr Text"}])
    ziel = tmp_path / "bericht.json"
    assert zp.main([str(belege), "--json", str(ziel), "--pause", "0"]) == 0
    daten = json.loads(ziel.read_text(encoding="utf-8"))
    assert daten[0]["status"] == "nicht_gefunden"
    assert "nicht_gefunden 1" in capsys.readouterr().out
    # vorhandene Datei wird nicht still überschrieben
    assert zp.main([str(belege), "--json", str(ziel), "--pause", "0"]) == 2
    assert zp.main([str(belege), "--json", str(ziel), "--pause", "0", "--ueberschreiben"]) == 0


def test_ausgabe_mit_zeichen_ausserhalb_cp1252(tmp_path, monkeypatch):
    belege = _belege_datei(tmp_path, [{"id": "Ж-1 → ✓", "url": "ftp://musterhafen.example/a", "zitat": "ein Zitat"}])
    puffer = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(puffer, encoding="cp1252"))
    assert zp.main([str(belege), "--pause", "0"]) == 0
    sys.stdout.flush()
    assert "Ж-1 → ✓" in puffer.getvalue().decode("utf-8")


def test_main_aufruffehler(tmp_path):
    assert zp.main([str(tmp_path / "fehlt.json")]) == 2
    kaputt = tmp_path / "kaputt.json"
    kaputt.write_text("{kein json", encoding="utf-8")
    assert zp.main([str(kaputt)]) == 2
