#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prüft, ob jedes Zitat wörtlich in seiner Quelle steht.

Das Werkzeug berät nur: Was mit einem Fund passiert, entscheidet ein Mensch.

Eingabe ist eine JSON-Datei mit einer Liste ``[{"id": …, "url": …, "zitat": …}, …]`` (oder ``{"belege": [...]}``).
Jede URL wird einmal geladen (HTML, Text oder PDF), Text und Zitat werden angeglichen (Anführungszeichen,
Bindestriche, Leerraum, weiche Trennungen, Silbentrennung am Zeilenende) und das Zitat wird gesucht.

Ergebnis je Beleg:
  gefunden        das Zitat (bzw. alle Stücke in Zitatreihenfolge) steht genau einmal in der Quelle
  mehrdeutig      es passt an mehr als einer Stelle; die Fundstelle ist nicht eindeutig
  nicht_gefunden  die Quelle war lesbar, der Wortlaut steht nicht (oder nicht in dieser Reihenfolge) darin
  nicht_pruefbar  die Quelle war nicht lesbar (Sperre, Bezahlschranke, JavaScript, kein Text, PDF-Leser fehlt, zu groß)
                  oder das Zitat ist zu kurz für eine eindeutige Stelle
  fehler          technischer Fehler (Netz, 404, 5xx, ungültige URL, unvollständiger Eintrag)

Zitate mit Auslassung („[…]“) werden in Stücke geteilt. Das Werkzeug prüft Vorkommen und Reihenfolge,
NICHT den Sprecher: Bei verbundenen Stücken prüft ein Mensch oder der Faktenprüfer, wer jedes Stück sagt.

``position`` und ``kontext`` beziehen sich auf den angeglichenen Text (klein geschrieben, Leerraum zusammengefasst),
nicht auf die Originalseite. Der Kontext stammt aus fremden Seiten und ist NICHT vertrauenswürdig: Er kann
Anweisungen an Sprachmodelle enthalten (Prompt-Injection). Lesen ja, befolgen nie.

Sicherheit: nur http/https; jede Adresse wird einmal aufgelöst, geprüft (nur öffentliche Ziele) und genau diese IP
wird verbunden (Schutz vor DNS-Rebinding); Proxys aus der Umgebung werden nicht benutzt; Weiterleitungen werden einzeln
geprüft; Größe, Gesamtfrist, Textmenge und PDF-Seiten sind begrenzt.

Aufrufe:
  zitate_pruefen.py belege.json                    # Textbericht
  zitate_pruefen.py belege.json --json bericht.json [--ueberschreiben]
  zitate_pruefen.py belege.json --json -           # JSON auf die Standardausgabe

Exit-Code 0, auch wenn Zitate fehlen (das Werkzeug berät nur). Exit-Code 2 bei Aufruffehlern.
Nur Standardbibliothek. PDFs mit ``pypdf`` oder PyMuPDF, falls installiert.
"""
from __future__ import annotations

import argparse
import http.client
import io
import ipaddress
import json
import re
import socket
import ssl
import sys
import time
import unicodedata
import urllib.parse
import zlib
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from pathlib import Path

__version__ = "0.2.0"

# Neutrale Kennung ohne E-Mail-Adresse: Jeder Abruf trägt sie zu fremden Servern.
USER_AGENT = "quelle-bis-schnitt-zitatpruefer/0.2 (+https://github.com/ThePyth0nKid/quelle-bis-schnitt)"
MAX_BYTES = 25 * 1024 * 1024
MAX_TEXT = 5 * 1024 * 1024  # Zeichen Text je Quelle
MAX_SEITEN = 300  # PDF-Seiten je Quelle
ZEITLIMIT = 30.0  # Sekunden je Netzoperation
GESAMTFRIST = 90.0  # Sekunden je Abruf einschließlich Weiterleitungen
MAX_WEITERLEITUNGEN = 5
GESPERRT_STATUS = {401, 402, 403, 407, 429, 451}
WENIG_TEXT = 200  # Zeichen; weniger heißt meist: Seite rendert per JavaScript oder sperrt

# Standardschwellen (Faustregeln, nicht gemessen): Stücke mit Auslassung brauchen mehr Text,
# sonst passt ein kurzes Stück an beliebiger Stelle.
MIN_ZITAT = 12
MIN_STUECK = 25
MAX_LUECKE = 6000  # angeglichene Zeichen zwischen zwei Stücken (grob zwei Druckseiten)

STATUS = ("gefunden", "mehrdeutig", "nicht_gefunden", "nicht_pruefbar", "fehler")
_STEUERZEICHEN = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
_NAT64 = (ipaddress.ip_network("64:ff9b::/96"), ipaddress.ip_network("64:ff9b:1::/48"))


# ---------------------------------------------------------------- Angleichen

_ERSETZEN = {
    "„": '"', "“": '"', "”": '"', "‟": '"', "»": '"', "«": '"', "″": '"',
    "‚": "'", "‘": "'", "’": "'", "‛": "'", "›": "'", "‹": "'", "′": "'", "`": "'", "´": "'",
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "―": "-", "−": "-",
    " ": " ", " ": " ", " ": " ", " ": " ",
}
_UNSICHTBAR = dict.fromkeys(map(ord, "­￾​‌‍⁠﻿"), None)
_TRENNUNG = re.compile(r"(?<=\w)-[ \t]*\r?\n[ \t]*(?=\w)")  # Bindestrich am Zeilenende
_LEER = re.compile(r"\s+")


def angleichen(text: str, trennung: str = "weg") -> str:
    """Bringt Quelle und Zitat auf dieselbe Form; Groß-/Kleinschreibung zählt nicht.

    ``trennung="weg"`` entfernt einen Bindestrich am Zeilenende (Silbentrennung: „Ver-⏎träge“ → „verträge“),
    ``trennung="behalten"`` behält ihn (Kompositum: „E-⏎Mail“ → „e-mail“). Die Suche probiert beide.
    """
    t = unicodedata.normalize("NFKC", text).translate(_UNSICHTBAR)
    for alt, neu in _ERSETZEN.items():
        t = t.replace(alt, neu)
    t = t.replace("...", "…")
    t = _TRENNUNG.sub("" if trennung == "weg" else "-", t)
    return _LEER.sub(" ", t).strip().casefold()


def ohne_fussnoten(text: str) -> str:
    """Fußnotenziffern mitten im Satz („das reichste 4 zu …“) aus angeglichenem PDF-Text entfernen."""
    return re.sub(r"(?<=[a-zäöüß]) \d{1,2} (?=[a-zäöüß])", " ", text)


def varianten(quelltext: str) -> list[str]:
    """Angeglichene Fassungen der Quelle: Silbentrennung weg bzw. behalten, jeweils mit und ohne Fußnotenziffern."""
    ergebnis: list[str] = []
    for trennung in ("weg", "behalten"):
        basis = angleichen(quelltext, trennung)
        for v in (basis, ohne_fussnoten(basis)):
            if v not in ergebnis:
                ergebnis.append(v)
    return ergebnis


_AUSLASSUNG = re.compile(r"\s*(?:\[\s*(?:…|\.\.\.)\s*\]|\(\s*(?:…|\.\.\.)\s*\)|…|\.\.\.)\s*")


def stuecke(zitat: str) -> list[str]:
    """Teilt ein Zitat an Auslassungen und entfernt Rand-Anführungszeichen und Schlusszeichen."""
    teile = []
    for teil in _AUSLASSUNG.split(zitat):
        teil = teil.strip().strip("\"'„“”‚‘’»«").strip().rstrip(".,;:!?").strip()
        if teil:
            teile.append(teil)
    return teile


# ---------------------------------------------------------------- Suchen

@dataclass
class Treffer:
    status: str
    grund: str = ""
    position: int | None = None
    kontext: str = ""
    hinweise: list[str] = field(default_factory=list)


def _alle(text: str, nadel: str) -> list[int]:
    stellen, start = [], 0
    while (pos := text.find(nadel, start)) >= 0:
        stellen.append(pos)
        start = pos + 1
    return stellen


def _kette(text: str, teile: list[str], anker_pos: int, max_luecke: int) -> bool:
    """Prüft, ob alle weiteren Stücke in Zitatreihenfolge und mit begrenzter Lücke hinter dem Anker stehen."""
    ende = anker_pos + len(teile[0])
    for teil in teile[1:]:
        pos = text.find(teil, ende)
        if pos < 0 or pos - ende > max_luecke:
            return False
        ende = pos + len(teil)
    return True


def _sauber(text: str) -> str:
    """Steuerzeichen aus Text entfernen, der aus fremden Quellen in Berichte geht."""
    return _STEUERZEICHEN.sub(" ", text)


def _kontext(text: str, pos: int, laenge: int, rand: int = 80) -> str:
    links = max(0, pos - rand)
    rechts = min(len(text), pos + laenge + rand)
    return _sauber(("…" if links else "") + text[links:rechts] + ("…" if rechts < len(text) else ""))


def zitat_suchen(quelltext: str, zitat: str, *, min_zitat: int = MIN_ZITAT, min_stueck: int = MIN_STUECK,
                 max_luecke: int = MAX_LUECKE) -> Treffer:
    """Sucht ein Zitat im (rohen) Quelltext und liefert Status, Fundstelle und Hinweise.

    Position und Kontext beziehen sich auf den angeglichenen Text.
    """
    roh_teile = stuecke(zitat)
    mit_auslassung = len(roh_teile) > 1
    teile = [angleichen(t) for t in roh_teile]
    hinweise = []
    if mit_auslassung:
        hinweise.append("Zitat mit Auslassung: Sprecher und Bezug jedes Stücks prüfen; "
                        "das Werkzeug prüft nur Vorkommen.")
        kurze = [t for t in teile if len(t) < min_stueck]
        if kurze:
            hinweise.append(f"{len(kurze)} Stück(e) unter {min_stueck} Zeichen nicht als Beleg gewertet.")
        teile = [t for t in teile if len(t) >= min_stueck]
        if not teile:
            return Treffer("nicht_pruefbar", f"kein Stück mit mindestens {min_stueck} Zeichen; "
                           "Fundstelle wäre zufällig", hinweise=hinweise)
    elif not teile or len(teile[0]) < min_zitat:
        return Treffer("nicht_pruefbar", f"Zitat kürzer als {min_zitat} Zeichen; Fundstelle wäre zufällig",
                       hinweise=hinweise)

    texte = varianten(quelltext)
    for text in texte:  # erstes tragfähiges Stück ist der Anker, die übrigen folgen in Zitatreihenfolge
        stellen = [p for p in _alle(text, teile[0]) if _kette(text, teile, p, max_luecke)]
        if len(stellen) == 1:
            return Treffer("gefunden", position=stellen[0], kontext=_kontext(text, stellen[0], len(teile[0])),
                           hinweise=hinweise)
        if len(stellen) > 1:
            return Treffer("mehrdeutig", f"passt an {len(stellen)} Stellen", position=stellen[0],
                           kontext=_kontext(text, stellen[0], len(teile[0])), hinweise=hinweise)

    if mit_auslassung and any(all(t in text for t in teile) for text in texte):
        return Treffer("nicht_gefunden", "alle Stücke kommen vor, aber nicht in Zitatreihenfolge oder zu weit "
                       "auseinander: Bezug kann verschoben sein", hinweise=hinweise)
    fehlend = [roh for roh in roh_teile if not any(angleichen(roh) in text for text in texte)]
    grund = "Wortlaut nicht in der Quelle"
    if mit_auslassung and fehlend:
        grund += f"; fehlendes Stück: „{_sauber(fehlend[0][:80])}“"
    return Treffer("nicht_gefunden", grund, hinweise=hinweise)


# ---------------------------------------------------------------- Abrufen

@dataclass
class Antwort:
    status: int
    typ: str
    daten: bytes
    url: str


class AbrufFehler(Exception):
    """Abruf nicht möglich; ``art`` ist ``nicht_pruefbar`` oder ``fehler``."""

    def __init__(self, art: str, grund: str):
        super().__init__(grund)
        self.art = art
        self.grund = grund


_URL_VERBOTEN = re.compile(r"[\\\s\x00-\x1f\x7f]")


def url_zerlegen(url: str) -> tuple[str, str, int, str]:
    """Prüft die Form einer URL und liefert (Schema, Host, Port, Pfad mit Abfrage)."""
    if _URL_VERBOTEN.search(url):
        raise AbrufFehler("fehler", "URL enthält Leerraum, Steuerzeichen oder Backslash")
    try:
        teile = urllib.parse.urlsplit(url)
        port = teile.port
    except ValueError as e:
        raise AbrufFehler("fehler", f"URL ungültig ({e})") from None
    if teile.scheme not in ("http", "https"):
        raise AbrufFehler("nicht_pruefbar", f"nur http/https, nicht {teile.scheme or 'ohne Schema'}")
    if not teile.hostname:
        raise AbrufFehler("fehler", "URL ohne Host")
    if teile.username or teile.password:
        raise AbrufFehler("fehler", "URL mit Anmeldedaten wird nicht abgerufen")
    pfad = teile.path or "/"
    if teile.query:
        pfad += "?" + teile.query
    return teile.scheme, teile.hostname, port or (443 if teile.scheme == "https" else 80), pfad


def ip_erlaubt(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Nur global erreichbare Ziele; eingebettete IPv4 (gemappt, 6to4, Teredo, NAT64) wird mitgeprüft."""
    if not ip.is_global or ip.is_multicast:
        return False
    eingebettet = []
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped:
            eingebettet.append(ip.ipv4_mapped)
        if ip.sixtofour:
            eingebettet.append(ip.sixtofour)
        if ip.teredo:
            eingebettet.extend(ip.teredo)
        if any(ip in netz for netz in _NAT64):
            eingebettet.append(ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF))
    return all(e.is_global and not e.is_multicast for e in eingebettet)


def ziel_aufloesen(host: str, port: int, erlaube_lokal: bool = False) -> str:
    """Löst den Host EINMAL auf und prüft jede Adresse; verbunden wird danach genau die gelieferte IP."""
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError) as e:
        raise AbrufFehler("fehler", f"Host nicht auflösbar ({e})") from None
    adressen = []
    for info in infos:
        try:
            adressen.append(ipaddress.ip_address(info[4][0].split("%")[0]))
        except ValueError:
            continue
    if not adressen:
        raise AbrufFehler("fehler", "Host ohne IP-Adresse")
    if not erlaube_lokal:
        for ip in adressen:
            if not ip_erlaubt(ip):
                raise AbrufFehler("nicht_pruefbar", f"Ziel {ip} ist nicht öffentlich (freigeben mit --erlaube-lokal)")
    return str(adressen[0])


class _FesteIPVerbindung(http.client.HTTPConnection):
    """HTTP-Verbindung zu einer vorab geprüften IP; Host-Kopf bleibt der ursprüngliche Hostname."""

    def __init__(self, host: str, port: int, ip: str, timeout: float):
        super().__init__(host, port, timeout=timeout)
        self._ip = ip

    def connect(self):
        self.sock = socket.create_connection((self._ip, self.port), self.timeout)


class _FesteIPVerbindungTLS(http.client.HTTPSConnection):
    """HTTPS zu einer vorab geprüften IP; SNI und Zertifikatsprüfung gegen den ursprünglichen Hostnamen."""

    def __init__(self, host: str, port: int, ip: str, timeout: float):
        super().__init__(host, port, timeout=timeout, context=ssl.create_default_context())
        self._ip = ip

    def connect(self):
        roh = socket.create_connection((self._ip, self.port), self.timeout)
        try:
            self.sock = self._context.wrap_socket(roh, server_hostname=self.host)
        except Exception:
            roh.close()
            raise


def _verbindung(schema: str, host: str, port: int, ip: str, timeout: float) -> http.client.HTTPConnection:
    klasse = _FesteIPVerbindungTLS if schema == "https" else _FesteIPVerbindung
    return klasse(host, port, ip, timeout)


def _restzeit(frist_ende: float) -> float:
    rest = frist_ende - time.monotonic()
    if rest <= 0:
        raise AbrufFehler("nicht_pruefbar", "Gesamtfrist für den Abruf überschritten")
    return rest


def _einmal(url: str, *, zeitlimit: float, frist_ende: float, erlaube_lokal: bool,
            max_bytes: int) -> tuple[int, dict[str, str], bytes]:
    schema, host, port, pfad = url_zerlegen(url)
    ip = ziel_aufloesen(host, port, erlaube_lokal)
    verbindung = _verbindung(schema, host, port, ip, min(zeitlimit, _restzeit(frist_ende)))
    try:
        verbindung.request("GET", pfad, headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,text/plain;q=0.8,*/*;q=0.5",
            "Accept-Encoding": "identity",
        })
        antwort = verbindung.getresponse()
        kopf = {k.lower(): v for k, v in antwort.getheaders()}
        if antwort.status >= 300:
            return antwort.status, kopf, b""
        laenge = kopf.get("content-length", "")
        if laenge.isdigit() and int(laenge) > max_bytes:
            raise AbrufFehler("nicht_pruefbar", f"Quelle größer als {max_bytes // 1024 // 1024} MB")
        bloecke, gesamt = [], 0
        while True:
            rest = _restzeit(frist_ende)
            if verbindung.sock is not None:
                verbindung.sock.settimeout(min(zeitlimit, rest))
            block = antwort.read(65536)
            if not block:
                break
            gesamt += len(block)
            if gesamt > max_bytes:
                raise AbrufFehler("nicht_pruefbar", f"Quelle größer als {max_bytes // 1024 // 1024} MB")
            bloecke.append(block)
        daten = b"".join(bloecke)
        kodierung = kopf.get("content-encoding", "").lower()
        if kodierung in ("gzip", "deflate", "x-gzip"):
            entpacker = zlib.decompressobj(wbits=47)
            daten = entpacker.decompress(daten, max_bytes + 1)
            if len(daten) > max_bytes or entpacker.unconsumed_tail:
                raise AbrufFehler("nicht_pruefbar", f"entpackte Quelle größer als {max_bytes // 1024 // 1024} MB")
        elif kodierung not in ("", "identity"):
            raise AbrufFehler("nicht_pruefbar", f"Kodierung {kodierung} wird nicht unterstützt")
        return antwort.status, kopf, daten
    except TimeoutError:
        raise AbrufFehler("fehler", "Zeitüberschreitung") from None
    except ssl.SSLError as e:
        raise AbrufFehler("fehler", f"TLS-Fehler ({e.__class__.__name__})") from None
    except (OSError, http.client.HTTPException, zlib.error) as e:
        raise AbrufFehler("fehler", f"Netzfehler ({e.__class__.__name__})") from None
    finally:
        verbindung.close()


def abrufen(url: str, *, zeitlimit: float = ZEITLIMIT, gesamtfrist: float = GESAMTFRIST,
            erlaube_lokal: bool = False, max_bytes: int = MAX_BYTES) -> Antwort:
    """Lädt eine URL über http.client; jede Weiterleitung wird neu aufgelöst und geprüft (höchstens fünf)."""
    frist_ende = time.monotonic() + gesamtfrist
    aktuell = url
    for _ in range(MAX_WEITERLEITUNGEN + 1):
        status, kopf, daten = _einmal(aktuell, zeitlimit=zeitlimit, frist_ende=frist_ende,
                                      erlaube_lokal=erlaube_lokal, max_bytes=max_bytes)
        if status in (301, 302, 303, 307, 308):
            if not kopf.get("location"):
                raise AbrufFehler("fehler", f"HTTP {status} ohne Ziel")
            aktuell = urllib.parse.urljoin(aktuell, kopf["location"])
            continue
        if status in GESPERRT_STATUS:
            raise AbrufFehler("nicht_pruefbar", f"HTTP {status} (Anmeldung, Bezahlschranke, Sperre oder Drossel)")
        if status >= 300:
            raise AbrufFehler("fehler", f"HTTP {status}")
        return Antwort(status, kopf.get("content-type", ""), daten, aktuell)
    raise AbrufFehler("fehler", "zu viele Weiterleitungen")


# ---------------------------------------------------------------- Text gewinnen

class _TextSammler(HTMLParser):
    _WEG = {"script", "style", "noscript", "template", "svg", "head"}
    _BLOCK = {"p", "div", "br", "li", "tr", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article",
              "blockquote", "pre", "dd", "dt", "figcaption", "header", "footer", "main", "aside", "nav", "hr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)  # Entitäten werden hier genau einmal entschlüsselt
        self.teile: list[str] = []
        self._tiefe_weg = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._WEG:
            self._tiefe_weg += 1
        elif tag in self._BLOCK:
            self.teile.append("\n")

    def handle_endtag(self, tag):
        if tag in self._WEG and self._tiefe_weg:
            self._tiefe_weg -= 1
        elif tag in self._BLOCK:
            self.teile.append("\n")

    def handle_data(self, data):
        if not self._tiefe_weg:
            self.teile.append(data)


_CHARSET = re.compile(r"""charset\s*=\s*["']?([\w.:-]+)""", re.I)


def _zeichensatz(typ: str, daten: bytes) -> str:
    m = _CHARSET.search(typ)
    if m:
        return m.group(1)
    m = re.search(rb"""<meta[^>]+charset\s*=\s*["']?([\w.:-]+)""", daten[:4096], re.I)
    if m:
        return m.group(1).decode("ascii", "ignore")
    return "utf-8"


def _dekodieren(daten: bytes, typ: str) -> str:
    try:
        return daten.decode(_zeichensatz(typ, daten), errors="replace")
    except LookupError:
        return daten.decode("utf-8", errors="replace")


def html_zu_text(daten: bytes, typ: str = "") -> str:
    sammler = _TextSammler()
    sammler.feed(_dekodieren(daten, typ))
    sammler.close()
    return "".join(sammler.teile)


def pdf_zu_text(daten: bytes, max_seiten: int = MAX_SEITEN) -> str:
    """PDF-Text über pypdf oder PyMuPDF; ohne beide: nicht prüfbar."""
    try:
        from pypdf import PdfReader
    except ImportError:
        PdfReader = None
    if PdfReader is not None:
        try:
            seiten = PdfReader(io.BytesIO(daten)).pages
            if len(seiten) > max_seiten:
                raise AbrufFehler("nicht_pruefbar", f"PDF hat {len(seiten)} Seiten (Grenze {max_seiten})")
            return "\n".join((seite.extract_text() or "") for seite in seiten)
        except AbrufFehler:
            raise
        except Exception as e:  # beschädigte oder verschlüsselte PDFs
            raise AbrufFehler("nicht_pruefbar", f"PDF nicht lesbar ({e.__class__.__name__})") from None
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise AbrufFehler("nicht_pruefbar", "PDF-Leser fehlt (pip install pypdf)") from None
    try:
        with fitz.open(stream=daten, filetype="pdf") as dok:
            if dok.page_count > max_seiten:
                raise AbrufFehler("nicht_pruefbar", f"PDF hat {dok.page_count} Seiten (Grenze {max_seiten})")
            return "\n".join(seite.get_text() for seite in dok)
    except AbrufFehler:
        raise
    except Exception as e:
        raise AbrufFehler("nicht_pruefbar", f"PDF nicht lesbar ({e.__class__.__name__})") from None


_TEXTTYPEN = ("application/json", "application/ld+json", "application/javascript", "application/x-www-form-urlencoded")


def quelltext(antwort: Antwort, *, max_text: int = MAX_TEXT, max_seiten: int = MAX_SEITEN) -> str:
    """Text einer geladenen Quelle; Bilder, Archive und andere Binärdaten sind nicht prüfbar."""
    typ = antwort.typ.lower().split(";")[0].strip()
    pfad = antwort.url.lower().split("?")[0]
    if typ == "application/pdf" or antwort.daten[:5] == b"%PDF-" or (not typ and pfad.endswith(".pdf")):
        text = pdf_zu_text(antwort.daten, max_seiten)
    elif "html" in typ or typ.endswith("xml") or (not typ and antwort.daten.lstrip()[:1] == b"<"):
        text = html_zu_text(antwort.daten, antwort.typ)
    elif typ.startswith("text/") or typ in _TEXTTYPEN or (not typ and b"\x00" not in antwort.daten[:1024]):
        text = _dekodieren(antwort.daten, antwort.typ)
    else:
        raise AbrufFehler("nicht_pruefbar", f"Inhaltstyp {typ or 'unbekannt'} ist kein Text")
    if len(text) > max_text:
        raise AbrufFehler("nicht_pruefbar", f"Text größer als {max_text // 1024 // 1024} MB")
    if len(text.strip()) < WENIG_TEXT:
        raise AbrufFehler("nicht_pruefbar", "Quelle liefert kaum Text (JavaScript-Seite, Sperre oder Bild-PDF)")
    return text


# ---------------------------------------------------------------- Ablauf

@dataclass
class Ergebnis:
    id: str
    url: str
    status: str
    grund: str = ""
    kontext: str = ""
    position: int | None = None
    hinweise: list[str] = field(default_factory=list)


def belege_laden(pfad: Path) -> list:
    """Liest die Belegdatei; wirft ValueError mit verständlicher Meldung."""
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as e:
        raise ValueError(f"{pfad} ist nicht lesbar oder kein JSON ({e})") from None
    if isinstance(daten, dict):
        daten = daten.get("belege")
    if not isinstance(daten, list):
        raise ValueError("erwartet eine Liste von Belegen oder {\"belege\": [...]}")
    return daten


_EINZELFEHLER = (ValueError, UnicodeError, http.client.HTTPException, OSError)


def alle_pruefen(belege: list, *, abrufer: Callable[[str], Antwort] | None = None, pause: float = 0.5,
                 max_text: int = MAX_TEXT, max_seiten: int = MAX_SEITEN, **schwellen) -> list[Ergebnis]:
    """Prüft alle Belege; jede URL wird nur einmal geladen. Ein einzelner Beleg bricht den Lauf nie ab."""
    abrufer = abrufer or abrufen
    cache: dict[str, str | AbrufFehler] = {}
    letzter_abruf: dict[str, float] = {}
    ergebnisse = []
    for nr, beleg in enumerate(belege, start=1):
        if not isinstance(beleg, dict):
            ergebnisse.append(Ergebnis(f"#{nr}", "", "fehler", "Eintrag ist kein Objekt {id, url, zitat}"))
            continue
        bid = str(beleg.get("id") or f"#{nr}")
        url = str(beleg.get("url") or "")
        zitat = str(beleg.get("zitat") or "")
        hinweise = [] if beleg.get("id") else [f"ohne id, gezählt als Eintrag {nr}"]
        if not url:
            ergebnisse.append(Ergebnis(bid, url, "fehler", "URL fehlt", hinweise=hinweise))
            continue
        if not zitat.strip():
            ergebnisse.append(Ergebnis(bid, url, "fehler", "Zitat fehlt", hinweise=hinweise))
            continue
        try:
            if url not in cache:
                try:
                    host = urllib.parse.urlsplit(url).hostname or ""
                except ValueError:
                    host = ""
                warten = pause - (time.monotonic() - letzter_abruf.get(host, -1e9))
                if warten > 0:
                    time.sleep(warten)
                try:
                    cache[url] = quelltext(abrufer(url), max_text=max_text, max_seiten=max_seiten)
                except AbrufFehler as e:
                    cache[url] = e
                except _EINZELFEHLER as e:
                    cache[url] = AbrufFehler("fehler", f"{e.__class__.__name__}: {_sauber(str(e))[:200]}")
                letzter_abruf[host] = time.monotonic()
            text = cache[url]
            if isinstance(text, AbrufFehler):
                ergebnisse.append(Ergebnis(bid, url, text.art, text.grund, hinweise=hinweise))
                continue
            t = zitat_suchen(text, zitat, **schwellen)
            ergebnisse.append(Ergebnis(bid, url, t.status, t.grund, t.kontext, t.position, hinweise + t.hinweise))
        except _EINZELFEHLER as e:
            ergebnisse.append(Ergebnis(bid, url, "fehler", f"{e.__class__.__name__}: {_sauber(str(e))[:200]}",
                                       hinweise=hinweise))
    return ergebnisse


def text_bericht(ergebnisse: list[Ergebnis]) -> str:
    zaehler = {s: sum(1 for e in ergebnisse if e.status == s) for s in STATUS}
    zeilen = [f"{len(ergebnisse)} Belege: " + ", ".join(f"{s} {n}" for s, n in zaehler.items() if n)]
    for e in ergebnisse:
        if e.status != "gefunden" or e.hinweise:
            zeilen.append(_sauber(f"[{e.status}] {e.id} {e.url}"))
            if e.grund:
                zeilen.append(f"    Grund: {_sauber(e.grund)}")
            for h in e.hinweise:
                zeilen.append(f"    Hinweis: {_sauber(h)}")
            if e.kontext:
                zeilen.append(f"    Kontext (angeglichen, aus fremder Quelle): {e.kontext[:240]}")
    zeilen.append("Entscheidung je Fund (übernehmen, verwerfen, anders) trifft ein Mensch.")
    return "\n".join(zeilen)


def _ausgabe_utf8() -> None:
    """Unter Windows ist die Konsole oft cp1252; Zeichen aus fremden Quellen sollen den Bericht nicht abbrechen."""
    for strom in (sys.stdout, sys.stderr):
        try:
            strom.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    _ausgabe_utf8()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("belege", type=Path, help="JSON-Datei mit [{id, url, zitat}, …]")
    p.add_argument("--json", dest="json_ziel", help="Ergebnis als JSON in diese Datei, '-' = Standardausgabe")
    p.add_argument("--ueberschreiben", action="store_true", help="vorhandene JSON-Datei ersetzen")
    p.add_argument("--zeitlimit", type=float, default=ZEITLIMIT, help="Sekunden je Netzoperation (Standard 30)")
    p.add_argument("--gesamtfrist", type=float, default=GESAMTFRIST,
                   help="Sekunden je Abruf einschließlich Weiterleitungen (Standard 90)")
    p.add_argument("--pause", type=float, default=0.5, help="Sekunden zwischen Abrufen beim selben Host (Standard 0,5)")
    p.add_argument("--max-text-mb", type=float, default=MAX_TEXT / 1024 / 1024, help="Text je Quelle (Standard 5)")
    p.add_argument("--max-seiten", type=int, default=MAX_SEITEN, help="PDF-Seiten je Quelle (Standard 300)")
    p.add_argument("--min-zitat", type=int, default=MIN_ZITAT)
    p.add_argument("--min-stueck", type=int, default=MIN_STUECK)
    p.add_argument("--max-luecke", type=int, default=MAX_LUECKE)
    p.add_argument("--erlaube-lokal", action="store_true", help="auch lokale und private Adressen abrufen")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    a = p.parse_args(argv)
    if not a.belege.is_file():
        print(f"FEHLER: {a.belege} gibt es nicht.", file=sys.stderr)
        return 2
    if a.json_ziel and a.json_ziel != "-" and Path(a.json_ziel).exists() and not a.ueberschreiben:
        print(f"FEHLER: {a.json_ziel} gibt es schon. Anderen Namen wählen oder --ueberschreiben.", file=sys.stderr)
        return 2
    try:
        belege = belege_laden(a.belege)
    except ValueError as e:
        print(f"FEHLER: {e}", file=sys.stderr)
        return 2

    def abrufer(url: str) -> Antwort:
        return abrufen(url, zeitlimit=a.zeitlimit, gesamtfrist=a.gesamtfrist, erlaube_lokal=a.erlaube_lokal)

    ergebnisse = alle_pruefen(belege, abrufer=abrufer, pause=a.pause, max_text=int(a.max_text_mb * 1024 * 1024),
                              max_seiten=a.max_seiten, min_zitat=a.min_zitat, min_stueck=a.min_stueck,
                              max_luecke=a.max_luecke)
    if a.json_ziel:
        inhalt = json.dumps([asdict(e) for e in ergebnisse], ensure_ascii=False, indent=2)
        if a.json_ziel == "-":
            print(inhalt)
            return 0
        Path(a.json_ziel).write_text(inhalt + "\n", encoding="utf-8")
    print(text_bericht(ergebnisse))
    return 0


if __name__ == "__main__":
    sys.exit(main())
