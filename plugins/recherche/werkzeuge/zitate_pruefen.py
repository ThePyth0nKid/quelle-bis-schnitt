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
  nicht_pruefbar  die Quelle war nicht lesbar (Sperre, Bezahlschranke, JavaScript, PDF-Leser fehlt) oder das Zitat ist
                  zu kurz für eine eindeutige Stelle
  fehler          technischer Fehler (Netz, 404, 5xx, unvollständiger Eintrag)

Zitate mit Auslassung („[…]“) werden in Stücke geteilt. Das Werkzeug prüft Vorkommen und Reihenfolge,
NICHT den Sprecher: Bei verbundenen Stücken prüft ein Mensch oder der Faktenprüfer, wer jedes Stück sagt.

Aufrufe:
  zitate_pruefen.py belege.json                    # Textbericht
  zitate_pruefen.py belege.json --json bericht.json
  zitate_pruefen.py belege.json --json -           # JSON auf die Standardausgabe

Exit-Code 0, auch wenn Zitate fehlen (das Werkzeug berät nur). Exit-Code 2 bei Aufruffehlern.
Nur Standardbibliothek; ``requests`` wird benutzt, wenn installiert. PDFs mit ``pypdf`` oder PyMuPDF, falls installiert.
"""
from __future__ import annotations

import argparse
import html
import io
import ipaddress
import json
import re
import socket
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from pathlib import Path

__version__ = "0.1.0"

# Neutrale Kennung ohne E-Mail-Adresse: Jeder Abruf trägt sie zu fremden Servern.
USER_AGENT = "quelle-bis-schnitt-zitatpruefer/0.1 (+https://github.com/ThePyth0nKid/quelle-bis-schnitt)"
MAX_BYTES = 25 * 1024 * 1024
MAX_WEITERLEITUNGEN = 5
GESPERRT_STATUS = {401, 402, 403, 407, 429, 451}
WENIG_TEXT = 200  # Zeichen; weniger heißt meist: Seite rendert per JavaScript oder sperrt

# Standardschwellen: Stücke mit Auslassung brauchen mehr Text, sonst passt ein kurzes Stück an beliebiger Stelle.
MIN_ZITAT = 12
MIN_STUECK = 25
MAX_LUECKE = 6000  # angeglichene Zeichen zwischen zwei Stücken (grob zwei Druckseiten)

STATUS = ("gefunden", "mehrdeutig", "nicht_gefunden", "nicht_pruefbar", "fehler")


# ---------------------------------------------------------------- Angleichen

_ERSETZEN = {
    "„": '"', "“": '"', "”": '"', "‟": '"', "»": '"', "«": '"', "″": '"',
    "‚": "'", "‘": "'", "’": "'", "‛": "'", "›": "'", "‹": "'", "′": "'", "`": "'", "´": "'",
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "―": "-", "−": "-",
    " ": " ", " ": " ", " ": " ", " ": " ",
}
_UNSICHTBAR = dict.fromkeys(map(ord, "­￾​‌‍⁠﻿"), None)
_TRENNUNG = re.compile(r"(?<=\w)-[ \t]*\r?\n[ \t]*(?=[a-zäöüß])")  # Silbentrennung am Zeilenende
_LEER = re.compile(r"\s+")


def angleichen(text: str) -> str:
    """Bringt Quelle und Zitat auf dieselbe Form; Groß-/Kleinschreibung zählt nicht."""
    t = unicodedata.normalize("NFKC", text).translate(_UNSICHTBAR)
    for alt, neu in _ERSETZEN.items():
        t = t.replace(alt, neu)
    t = t.replace("...", "…")
    t = _TRENNUNG.sub("", t)
    return _LEER.sub(" ", t).strip().casefold()


def ohne_fussnoten(text: str) -> str:
    """Fußnotenziffern mitten im Satz („das reichste 4 zu …“) aus angeglichenem PDF-Text entfernen."""
    return re.sub(r"(?<=[a-zäöüß]) \d{1,2} (?=[a-zäöüß])", " ", text)


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


def _kette(text: str, teile: list[str], anker_idx: int, anker_pos: int, max_luecke: int) -> bool:
    """Prüft, ob alle Stücke um den Anker herum in Zitatreihenfolge und mit begrenzter Lücke stehen."""
    ende = anker_pos + len(teile[anker_idx])
    for teil in teile[anker_idx + 1:]:
        pos = text.find(teil, ende)
        if pos < 0 or pos - ende > max_luecke:
            return False
        ende = pos + len(teil)
    anfang = anker_pos
    for teil in reversed(teile[:anker_idx]):
        pos = text.rfind(teil, 0, anfang)
        if pos < 0 or anfang - (pos + len(teil)) > max_luecke:
            return False
        anfang = pos
    return True


def _kontext(text: str, pos: int, laenge: int, rand: int = 80) -> str:
    links = max(0, pos - rand)
    rechts = min(len(text), pos + laenge + rand)
    return ("…" if links else "") + text[links:rechts] + ("…" if rechts < len(text) else "")


def zitat_suchen(quelltext: str, zitat: str, *, min_zitat: int = MIN_ZITAT, min_stueck: int = MIN_STUECK,
                 max_luecke: int = MAX_LUECKE) -> Treffer:
    """Sucht ein Zitat im (rohen) Quelltext und liefert Status, Fundstelle und Hinweise."""
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
    else:
        if not teile or len(teile[0]) < min_zitat:
            return Treffer("nicht_pruefbar", f"Zitat kürzer als {min_zitat} Zeichen; Fundstelle wäre zufällig",
                           hinweise=hinweise)

    anker_idx = 0  # erstes tragfähiges Stück; alle übrigen müssen in Zitatreihenfolge dahinter stehen
    angeglichen = angleichen(quelltext)
    for text in (angeglichen, ohne_fussnoten(angeglichen)):
        stellen = [p for p in _alle(text, teile[anker_idx]) if _kette(text, teile, anker_idx, p, max_luecke)]
        if len(stellen) == 1:
            return Treffer("gefunden", position=stellen[0], kontext=_kontext(text, stellen[0], len(teile[anker_idx])),
                           hinweise=hinweise)
        if len(stellen) > 1:
            return Treffer("mehrdeutig", f"passt an {len(stellen)} Stellen", position=stellen[0],
                           kontext=_kontext(text, stellen[0], len(teile[anker_idx])), hinweise=hinweise)

    if mit_auslassung and all(t in angeglichen for t in teile):
        return Treffer("nicht_gefunden", "alle Stücke kommen vor, aber nicht in Zitatreihenfolge oder zu weit "
                       "auseinander: Bezug kann verschoben sein", hinweise=hinweise)
    fehlend = [roh for roh, t in zip(stuecke(zitat), [angleichen(s) for s in stuecke(zitat)], strict=True)
               if t and t not in angeglichen]
    grund = "Wortlaut nicht in der Quelle"
    if mit_auslassung and fehlend:
        grund += f"; fehlendes Stück: „{fehlend[0][:80]}“"
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


def adresse_pruefen(url: str, erlaube_lokal: bool = False) -> None:
    """Nur http/https; lokale und private Ziele nur auf ausdrücklichen Wunsch (Schutz vor untergeschobenen URLs)."""
    teile = urllib.parse.urlsplit(url)
    if teile.scheme not in ("http", "https"):
        raise AbrufFehler("nicht_pruefbar", f"nur http/https, nicht {teile.scheme or 'ohne Schema'}")
    if not teile.hostname:
        raise AbrufFehler("fehler", "URL ohne Host")
    if erlaube_lokal:
        return
    try:
        infos = socket.getaddrinfo(teile.hostname, teile.port or (443 if teile.scheme == "https" else 80))
    except socket.gaierror as e:
        raise AbrufFehler("fehler", f"Host nicht auflösbar ({e})") from None
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast \
                or ip.is_unspecified:
            raise AbrufFehler("nicht_pruefbar", f"Ziel {ip} ist lokal oder privat (freigeben mit --erlaube-lokal)")


def _lesen_begrenzt(strom, grenze: int = MAX_BYTES) -> bytes:
    daten = strom.read(grenze + 1)
    if len(daten) > grenze:
        raise AbrufFehler("nicht_pruefbar", f"Quelle größer als {grenze // 1024 // 1024} MB")
    return daten


class _KeineWeiterleitung(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # Weiterleitungen prüft abrufen() selbst
        return None


def _einmal_urllib(url: str, zeitlimit: float) -> tuple[int, dict[str, str], bytes]:
    anfrage = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,text/plain;q=0.8,*/*;q=0.5",
    })
    oeffner = urllib.request.build_opener(_KeineWeiterleitung)
    try:
        with oeffner.open(anfrage, timeout=zeitlimit) as r:
            return r.status, {k.lower(): v for k, v in r.headers.items()}, _lesen_begrenzt(r)
    except urllib.error.HTTPError as e:
        kopf = {k.lower(): v for k, v in (e.headers or {}).items()}
        return e.code, kopf, b""
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise AbrufFehler("fehler", f"Netzfehler: {getattr(e, 'reason', e)}") from None


def _einmal_requests(url: str, zeitlimit: float) -> tuple[int, dict[str, str], bytes]:
    import requests  # optional

    try:
        with requests.get(url, timeout=zeitlimit, allow_redirects=False, stream=True, headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,text/plain;q=0.8,*/*;q=0.5",
        }) as r:
            daten = b""
            if r.status_code < 300:
                stuecke_ = []
                gesamt = 0
                for block in r.iter_content(65536):
                    gesamt += len(block)
                    if gesamt > MAX_BYTES:
                        raise AbrufFehler("nicht_pruefbar", f"Quelle größer als {MAX_BYTES // 1024 // 1024} MB")
                    stuecke_.append(block)
                daten = b"".join(stuecke_)
            return r.status_code, {k.lower(): v for k, v in r.headers.items()}, daten
    except requests.RequestException as e:
        raise AbrufFehler("fehler", f"Netzfehler: {e.__class__.__name__}") from None


def abrufen(url: str, *, zeitlimit: float = 30.0, erlaube_lokal: bool = False) -> Antwort:
    """Lädt eine URL; Weiterleitungen werden einzeln geprüft (höchstens fünf)."""
    try:
        import requests  # noqa: F401
        einmal = _einmal_requests
    except ImportError:
        einmal = _einmal_urllib
    aktuell = url
    for _ in range(MAX_WEITERLEITUNGEN + 1):
        adresse_pruefen(aktuell, erlaube_lokal)
        status, kopf, daten = einmal(aktuell, zeitlimit)
        if status in (301, 302, 303, 307, 308) and kopf.get("location"):
            aktuell = urllib.parse.urljoin(aktuell, kopf["location"])
            continue
        if status in GESPERRT_STATUS:
            raise AbrufFehler("nicht_pruefbar", f"HTTP {status} (Anmeldung, Bezahlschranke, Sperre oder Drossel)")
        if status >= 400:
            raise AbrufFehler("fehler", f"HTTP {status}")
        return Antwort(status, kopf.get("content-type", ""), daten, aktuell)
    raise AbrufFehler("fehler", "zu viele Weiterleitungen")


# ---------------------------------------------------------------- Text gewinnen

class _TextSammler(HTMLParser):
    _WEG = {"script", "style", "noscript", "template", "svg", "head"}
    _BLOCK = {"p", "div", "br", "li", "tr", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article",
              "blockquote", "pre", "dd", "dt", "figcaption", "header", "footer", "main", "aside", "nav", "hr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
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


def _zeichensatz(typ: str, daten: bytes) -> str:
    m = re.search(r"charset=([\w-]+)", typ, re.I) or re.search(rb"<meta[^>]+charset=[\"']?([\w-]+)", daten[:4096], re.I)
    if m:
        name = m.group(1)
        return name.decode("ascii", "ignore") if isinstance(name, bytes) else name
    return "utf-8"


def html_zu_text(daten: bytes, typ: str = "") -> str:
    try:
        roh = daten.decode(_zeichensatz(typ, daten), errors="replace")
    except LookupError:
        roh = daten.decode("utf-8", errors="replace")
    sammler = _TextSammler()
    sammler.feed(roh)
    return html.unescape("".join(sammler.teile))


def pdf_zu_text(daten: bytes) -> str:
    """PDF-Text über pypdf oder PyMuPDF; ohne beide: nicht prüfbar."""
    try:
        from pypdf import PdfReader
    except ImportError:
        PdfReader = None
    if PdfReader is not None:
        try:
            return "\n".join((seite.extract_text() or "") for seite in PdfReader(io.BytesIO(daten)).pages)
        except Exception as e:  # beschädigte oder verschlüsselte PDFs
            raise AbrufFehler("nicht_pruefbar", f"PDF nicht lesbar ({e.__class__.__name__})") from None
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise AbrufFehler("nicht_pruefbar", "PDF-Leser fehlt (pip install pypdf)") from None
    try:
        with fitz.open(stream=daten, filetype="pdf") as dok:
            return "\n".join(seite.get_text() for seite in dok)
    except Exception as e:
        raise AbrufFehler("nicht_pruefbar", f"PDF nicht lesbar ({e.__class__.__name__})") from None


def quelltext(antwort: Antwort) -> str:
    typ = antwort.typ.lower()
    if "pdf" in typ or antwort.daten[:5] == b"%PDF-" or antwort.url.lower().split("?")[0].endswith(".pdf"):
        text = pdf_zu_text(antwort.daten)
    elif "html" in typ or "xml" in typ or antwort.daten.lstrip()[:1] == b"<":
        text = html_zu_text(antwort.daten, typ)
    else:
        text = antwort.daten.decode(_zeichensatz(typ, antwort.daten), errors="replace")
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


def belege_laden(pfad: Path) -> list[dict]:
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise SystemExit(f"FEHLER: {pfad} ist nicht lesbar oder kein JSON ({e})") from None
    if isinstance(daten, dict):
        daten = daten.get("belege")
    if not isinstance(daten, list):
        raise SystemExit("FEHLER: erwartet eine Liste von Belegen oder {\"belege\": [...]}")
    return daten


def alle_pruefen(belege: list[dict], *, abrufer: Callable[[str], Antwort] | None = None, pause: float = 0.5,
                 **schwellen) -> list[Ergebnis]:
    """Prüft alle Belege; jede URL wird nur einmal geladen."""
    abrufer = abrufer or abrufen
    cache: dict[str, str | AbrufFehler] = {}
    letzter_abruf: dict[str, float] = {}
    ergebnisse = []
    for nr, beleg in enumerate(belege, start=1):
        bid = str(beleg.get("id", f"#{nr}")) if isinstance(beleg, dict) else f"#{nr}"
        if not isinstance(beleg, dict) or not beleg.get("url") or not str(beleg.get("zitat", "")).strip():
            ergebnisse.append(Ergebnis(bid, str(beleg.get("url", "")) if isinstance(beleg, dict) else "", "fehler",
                                       "Eintrag braucht id, url und zitat"))
            continue
        url, zitat = str(beleg["url"]), str(beleg["zitat"])
        if url not in cache:
            host = urllib.parse.urlsplit(url).hostname or ""
            warten = pause - (time.monotonic() - letzter_abruf.get(host, -1e9))
            if warten > 0:
                time.sleep(warten)
            try:
                cache[url] = quelltext(abrufer(url))
            except AbrufFehler as e:
                cache[url] = e
            letzter_abruf[host] = time.monotonic()
        text = cache[url]
        if isinstance(text, AbrufFehler):
            ergebnisse.append(Ergebnis(bid, url, text.art, text.grund))
            continue
        t = zitat_suchen(text, zitat, **schwellen)
        ergebnisse.append(Ergebnis(bid, url, t.status, t.grund, t.kontext, t.position, t.hinweise))
    return ergebnisse


def text_bericht(ergebnisse: list[Ergebnis]) -> str:
    zaehler = {s: sum(1 for e in ergebnisse if e.status == s) for s in STATUS}
    zeilen = [f"{len(ergebnisse)} Belege: " + ", ".join(f"{s} {n}" for s, n in zaehler.items() if n)]
    for e in ergebnisse:
        if e.status != "gefunden" or e.hinweise:
            zeilen.append(f"[{e.status}] {e.id} {e.url}")
            if e.grund:
                zeilen.append(f"    Grund: {e.grund}")
            for h in e.hinweise:
                zeilen.append(f"    Hinweis: {h}")
            if e.kontext:
                zeilen.append(f"    Kontext: {e.kontext[:240]}")
    zeilen.append("Entscheidung je Fund (übernehmen, verwerfen, anders) trifft ein Mensch.")
    return "\n".join(zeilen)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("belege", type=Path, help="JSON-Datei mit [{id, url, zitat}, …]")
    p.add_argument("--json", dest="json_ziel", help="Ergebnis als JSON in diese Datei, '-' = Standardausgabe")
    p.add_argument("--zeitlimit", type=float, default=30.0, help="Sekunden je Abruf (Standard 30)")
    p.add_argument("--pause", type=float, default=0.5, help="Sekunden zwischen Abrufen beim selben Host (Standard 0,5)")
    p.add_argument("--min-zitat", type=int, default=MIN_ZITAT)
    p.add_argument("--min-stueck", type=int, default=MIN_STUECK)
    p.add_argument("--max-luecke", type=int, default=MAX_LUECKE)
    p.add_argument("--erlaube-lokal", action="store_true", help="auch lokale und private Adressen abrufen")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    a = p.parse_args(argv)
    if not a.belege.is_file():
        print(f"FEHLER: {a.belege} gibt es nicht.", file=sys.stderr)
        return 2
    try:
        belege = belege_laden(a.belege)
    except SystemExit as e:
        print(e, file=sys.stderr)
        return 2

    def abrufer(url: str) -> Antwort:
        return abrufen(url, zeitlimit=a.zeitlimit, erlaube_lokal=a.erlaube_lokal)

    ergebnisse = alle_pruefen(belege, abrufer=abrufer, pause=a.pause, min_zitat=a.min_zitat,
                              min_stueck=a.min_stueck, max_luecke=a.max_luecke)
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
