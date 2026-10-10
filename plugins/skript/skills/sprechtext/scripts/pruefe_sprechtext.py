#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Vollständigkeitsprobe für gesprochene Texte (Kapitel = Absatz, Leerzeile dazwischen). Berät nur.

Aufruf:
    python pruefe_sprechtext.py prompter.md [--ziel 75] [--tempo 2.6] [--budget kapitel.json]
    python pruefe_sprechtext.py prompter.md --regel ohne-verb=sperrt
    python pruefe_sprechtext.py --liste

Meldet Sätze ohne erkennbares gebeugtes Verb (Warnlampe, von Hand prüfen), Doppelpunkt-Telegramme, Beat-Häufung
(Sätze mit höchstens drei Wörtern), Kapitel über Budget und die Gesamtlänge bei ``--tempo`` Wörtern je Sekunde.
Zeilen mit ``#`` (Überschrift), ``⏱`` oder ``▶`` (Zeitmarken) zählen nicht; ein Block nur aus solchen Zeilen ist
kein Kapitel.

``--budget``: JSON-Liste ``[{"kapitel": 1, "startS": 0}, …]`` (auch unter einem Schlüssel wie ``{"kapitel": […]}``).
Das Budget je Kapitel ist (Start des nächsten Kapitels − Start dieses) × Tempo; das letzte Kapitel bekommt
``--letztes`` Sekunden. Einträge ohne ``kapitel`` zählen in ihrer Reihenfolge.

Stufen wie in ``skript_pruefen.py``: ``aus``, ``hinweis`` (Standard), ``sperrt``. Exit-Code 0 ohne sperrenden Fund,
1 mit sperrendem Fund, 2 bei Aufruf-, Datei- oder Konfigurationsfehler oder leerem Text.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

# >>> gemeinsamer Kern (wortgleich in skript_pruefen.py, hook_pruefen.py und pruefe_sprechtext.py; ein Test prüft das)
STUFEN = ("aus", "hinweis", "sperrt")
# Alle Regelnamen der drei Prüfskripte: Eine Regeldatei darf jeden davon tragen, jeder andere Name ist ein Tippfehler.
ALLE_REGELNAMEN = frozenset({
    "anlauf-vorn", "quellvideo-vorn", "kausal-vorn", "ichwir-vorn", "ding-vorn", "erster-satz-lang", "frage-vorn",
    "zahlentabelle", "zahlen-quelle", "belegblatt", "quelle-im-satz", "floskel", "du-dichte", "bannwort",
    "gedankenstrich", "laenge", "letzter-satz", "aufforderung-trailer", "letzter-satz-also", "schlussfrage-lang",
    "versprechen", "klammer", "wendung", "neue-luecke", "zahlenleiter", "analogie", "lacher-lage", "auszahlung-frueh",
    "slots", "du-vor-ich",
    "gerade-ohne-neuigkeit", "du-vorn", "bild1-text",
    "ohne-verb", "doppelpunkt-ende", "beats-hintereinander", "kapitel-beginnt-mit-beat", "beat-haeufung",
    "ueber-budget", "gesamtlaenge",
})


class Eingabefehler(Exception):
    """Fehler in Aufruf, Datei oder Regeldatei: Meldung und Exit-Code 2."""


ZAHLWORT = re.compile(
    r"\b(\d[\d.,]*|null|eins|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn|elf|zwölf|hundert|tausend"
    r"|million(en)?|milliarde(n)?|dutzend)\b",
    re.I,
)
ZEIGEWORT = ("dieses", "dieser", "diese", "diesen", "diesem", "das hier", "der hier", "die hier", "den hier", "schau",
             "guck", "stell dir", "in diesen", "in diesem", "in dieser")
DU = re.compile(r"\b(du|dich|dir|dein|deine|deinen|deinem|deiner|deins|euch|euer|eure)\b", re.I)  # ohne „ihr“
ICH = re.compile(r"\b(ich|mich|mir|mein|meine|meinen|meinem|meiner)\b", re.I)
# „denn je“ und „es sei denn“ sind nicht kausal.
KAUSAL = re.compile(r"\b(weil|obwohl|(?<!\bsei )denn(?!\s+je\b)|sodass|so dass|deshalb|deswegen|daher)\b", re.I)
# „Instagram-Reel“ und „Hass-Videos“ zählen, „Video-Überwachung“ und „die Post“ nicht.
QUELLVIDEO = re.compile(r"(?<!\w)(reels?|videos?|clips?|posts|likes?|aufrufe|views|follower|kommentare)\b(?!-)", re.I)
# „Heute“ ist nur ein Anlauf, wenn ich oder wir etwas ankündigen („Heute zeige ich …“, „Heute schauen wir …“),
# nicht bei einer Neuigkeit („Heute haben 3 Millionen Menschen …“, „Heute zeigt die Statistik …“).
GRUSS_START = re.compile(
    r"(hallo|hey|in diesem video|willkommen|servus|moin)\b"
    r"|heute\s+(zeig|erklär|schau|guck|red|sprech|mach|möcht|will|woll|lern|kümmer|geh|nehm|beschäftig)\w*\s+"
    r"(ich|wir)\b"
    r"|heute\s+geht(\s+es|'s|s)\s+um\b",
    re.I,
)
ICHWIR_START = re.compile(r"(ich|wir)\b", re.I)  # ganzes Wort, nicht „Wirbel“
VORZEICHEN = "„“\"'»«‚‘(["  # führende Anführungszeichen und Klammern vor den Start-Prüfungen abschneiden
FRAGE_ENDE = re.compile(r"\?[!?\s“”\"'»«)]*$")
FRAGE_START = ("wer", "wie", "was", "warum", "wieso", "weshalb", "wann", "wo", "ist", "sind", "hat", "haben", "kann",
               "kannst", "wusstest", "weißt", "glaubst")
MONAT_ODER_JH = (r"(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember"
                 r"|Jahrhundert|Jahrtausend)\b")
BANN_STANDARD = ("spannend", "unglaublich", "wusstest du", "in diesem video", "entscheidend", "revolutionär",
                 "bahnbrechend", "faszinierend", "ganzheitlich", "gigantisch", "wahnsinn")
# Wörter, mit denen nach einer ein- oder zweistelligen Zahl mit Punkt ein neuer Satz beginnt („Er wurde 3. Dann …“);
# sonst ist die Zahl eine Ordnungszahl („am 3. Platz“, „am 4. September“).
SATZANFANG = frozenset(
    "Du Ich Wir Er Sie Es Ihr Der Die Das Den Dem Des Ein Eine Einen Einem Und Aber Doch Dann Also Jetzt Heute Danach "
    "Deshalb Trotzdem Wenn Weil Was Wer Wie Warum Wo Dieser Diese Dieses Diesen So Nur Auch Man Mein Meine Dein Deine "
    "Unser Unsere Hier Da Damit Dabei Seitdem Nein Ja".split()
)
ABKUERZUNG = re.compile(r"(?<![\w.])(?:[zZ]\.\s?B|[dD]\.\s?h|[uU]\.\s?a|[oO]\.\s?Ä|[uU]\.\s?U|[zZ]\.\s?T|ca|Dr|Prof"
                        r"|Mio|Mrd|Nr|bzw|vgl|inkl|evtl|bspw|ggf|sog|Tsd)\.(?=\s|$)")
GRENZE = re.compile(r"[.!?]+[“”\"'»«‚‘)\]]*(?=\s)")
_PUNKT = "․"  # Platzhalter für den Punkt in Abkürzungen während der Satztrennung


def _ist_satzende(vorher: str, zeichen: str, nach: str) -> bool:
    if not nach or zeichen != ".":
        return True
    zahl = re.search(r"(?<![\d.,])(\d+)$", vorher)
    if zahl is None:
        return True
    if len(zahl.group(1)) >= 3:  # Jahreszahl oder Betrag: „kam 2007. Du …“
        return not re.match(MONAT_ODER_JH, nach)
    erstes = nach.lstrip(VORZEICHEN).split(" ", 1)[0].rstrip(",;:.!?")
    return erstes in SATZANFANG


def saetze(text: str) -> list[str]:
    """Sätze: Schlusszeichen nach dem Satzzeichen gehören dazu, Abkürzungen und Ordnungszahlen trennen nicht."""
    flach = re.sub(r"\s+", " ", text).strip()
    flach = ABKUERZUNG.sub(lambda m: m.group(0).replace(".", _PUNKT), flach)
    ergebnis, start = [], 0
    for m in GRENZE.finditer(flach):
        if _ist_satzende(flach[start:m.start()], m.group(0), flach[m.end():].lstrip()):
            ergebnis.append(flach[start:m.end()].strip())
            start = m.end()
    ergebnis.append(flach[start:].strip())
    return [s.replace(_PUNKT, ".") for s in ergebnis if s]


def text_lesen(pfad: Path) -> str:
    """Datei als UTF-8 (mit oder ohne BOM); jeder Lesefehler wird zum Eingabefehler."""
    try:
        return pfad.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raise Eingabefehler(f"{pfad}: Datei ist nicht UTF-8") from None
    except OSError as fehler:
        raise Eingabefehler(f"{pfad}: nicht lesbar ({fehler.strerror or fehler})") from None


def regeldatei_lesen(pfad: Path) -> dict:
    """Liest und prüft die TOML-Regeldatei: nur [regeln] (Name = Stufe) und [bann] (erlaubt, zusaetzlich)."""
    try:
        daten = tomllib.loads(text_lesen(pfad))
    except tomllib.TOMLDecodeError as fehler:
        raise Eingabefehler(f"{pfad}: kein gültiges TOML ({fehler})") from None
    fremd = set(daten) - {"regeln", "bann"}
    if fremd:
        raise Eingabefehler(f"{pfad}: unbekannte Abschnitte {sorted(fremd)}; erlaubt sind [regeln] und [bann]")
    regeln = daten.get("regeln", {})
    if not isinstance(regeln, dict):
        raise Eingabefehler(f"{pfad}: [regeln] muss eine Tabelle sein (name = \"stufe\")")
    for name, stufe in regeln.items():
        if name not in ALLE_REGELNAMEN:
            raise Eingabefehler(f"{pfad}: unbekannte Regel {name!r}; --liste zeigt die Regeln je Skript")
        if not isinstance(stufe, str) or stufe not in STUFEN:
            raise Eingabefehler(f"{pfad}: Stufe {stufe!r} für {name} ist nicht {', '.join(STUFEN)}")
    bann = daten.get("bann", {})
    if not isinstance(bann, dict):
        raise Eingabefehler(f"{pfad}: [bann] muss eine Tabelle sein")
    fremd = set(bann) - {"erlaubt", "zusaetzlich"}
    if fremd:
        raise Eingabefehler(f"{pfad}: unbekannte Schlüssel in [bann]: {sorted(fremd)}")
    for schluessel in ("erlaubt", "zusaetzlich"):
        wert = bann.get(schluessel, [])
        if not isinstance(wert, list) or not all(isinstance(w, str) and w.strip() for w in wert):
            raise Eingabefehler(f"{pfad}: [bann] {schluessel} muss eine Liste von Wörtern sein")
    return daten


def stufen_laden(regeln: tuple, datei: Path | None, einzeln: list[str], streng: bool = False) -> tuple[dict, dict]:
    """Stufen je Regel dieses Skripts, dazu die Regeldatei. Regeln der Schwesterskripte in der Datei überspringen."""
    stufen = {r.name: "hinweis" for r in regeln}
    if streng:
        stufen.update({r.name: "sperrt" for r in regeln if getattr(r, "hart", False)})
    daten: dict = {}
    if datei is not None:
        daten = regeldatei_lesen(datei)
        stufen.update({name: stufe for name, stufe in daten.get("regeln", {}).items() if name in stufen})
    for eintrag in einzeln:
        name, trenner, stufe = (teil.strip() for teil in eintrag.partition("="))
        if not trenner:
            raise Eingabefehler(f"--regel braucht die Form name=stufe, nicht {eintrag!r}")
        if name not in stufen:
            raise Eingabefehler(f"--regel: dieses Skript kennt keine Regel {name!r}; --liste zeigt alle")
        if stufe not in STUFEN:
            raise Eingabefehler(f"--regel: Stufe {stufe!r} für {name} ist nicht {', '.join(STUFEN)}")
        stufen[name] = stufe
    return stufen, daten


def bann_muster(daten: dict) -> re.Pattern[str]:
    """Bann-Liste aus dem Standard plus ``[bann] zusaetzlich`` minus ``[bann] erlaubt`` aus der Regeldatei."""
    bann = daten.get("bann", {})
    erlaubt = {w.lower() for w in bann.get("erlaubt", [])}
    woerter = [w for w in (*BANN_STANDARD, *bann.get("zusaetzlich", [])) if w.lower() not in erlaubt]
    if not woerter:
        return re.compile(r"(?!x)x")  # trifft nie
    return re.compile(r"\b(" + "|".join(re.escape(w) for w in woerter) + r")\b", re.I)


def zahl_pruefen(name: str, wert: float, *, groesser_null: bool = True) -> None:
    """Zahlen aus dem Aufruf müssen endlich sein, je nach Größe größer oder mindestens null."""
    if not math.isfinite(wert) or wert < 0 or (groesser_null and wert == 0):
        raise Eingabefehler(f"{name} muss eine endliche Zahl {'> 0' if groesser_null else '≥ 0'} sein, nicht {wert}")


def ausgabe_einrichten() -> None:
    """Nie an Sonderzeichen abstürzen: Die Kodierung der Umgebung bleibt, nicht darstellbare Zeichen werden ersetzt.
    Maschinenlesbar ist ``--json``; das ist reines ASCII und damit in jeder Konsole und jeder Umleitung gleich."""
    for strom in (sys.stdout, sys.stderr):
        try:
            strom.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
# <<< gemeinsamer Kern


@dataclass(frozen=True)
class Regel:
    name: str
    kurz: str
    hart: bool = False  # diese Probe kennt keine harten Punkte


REGELN: tuple[Regel, ...] = (
    Regel("ohne-verb", "jeder Satz hat ein gebeugtes Verb (Erkennung ist eine Warnlampe)"),
    Regel("doppelpunkt-ende", "kein Satz endet mit Doppelpunkt (Telegramm)"),
    Regel("beats-hintereinander", "nie zwei Beats (≤ 3 Wörter) hintereinander"),
    Regel("kapitel-beginnt-mit-beat", "kein Kapitel beginnt mit einem Beat"),
    Regel("beat-haeufung", "höchstens ein Beat je fünf Sätze"),
    Regel("ueber-budget", "Kapitel passt in sein Zeitbudget (nur mit --budget)"),
    Regel("gesamtlaenge", "Gesamtlänge unter --ziel Sekunden"),
)
REGEL = {r.name: r for r in REGELN}


@dataclass
class Fund:
    regel: str
    stufe: str
    stelle: str
    text: str


# Verbstämme und feste Formen: einfache Erkennung ohne Wörterbuch, deshalb nur eine Warnlampe.
STAEMME = (
    "sag geh komm seh guck schau nimm nehm brauch kost zieh schreib rechn halt bau steck wieg fehl verbiet erlaub "
    "schnür zeig mein denk glaub weiß find lauf mach tu gib hab hol pass stell leg mess lad öffn schließ "
    "dreh frag antwort lieg sitz steh bleib fang hör les sprech red heiß bring tret zahl schaff klapp funktionier "
    "existier gilt dauer wart start end kipp reiß hält trag lös bewegt fließ leucht wirk stimm erklär "
    "versteh zerleg check pack schick post kling wachs sink steig fall trifft spür merk zähl lern "
    "heiz schweb schwitz läuf erzeug liefer drück verbrauch speicher verbrenn brems fahr fähr flieg schätz bekomm"
).split()
ENDUNGEN = ("e", "st", "t", "en", "et", "est")
FESTE = set(
    "ist sind war waren bin bist hat haben hast hatte hatten kann kannst können konnte muss musst müssen darf "
    "darfst dürfen soll sollst sollen will willst wollen wird wirst werden wurde wurden gibt gibts gab kommt kam "
    "geht ging steht stand weiß wissen heißt hieß wiegt wog braucht brauchst kostet zieht zog schreibt schrieb "
    "rechnen rechnet halten hält hielt erlaubt fehlen fehlt verbietet schnürt baut nimm nehmen guck gucken schau "
    "lass lässt bleibt bleiben fängt macht machen tut tun gib gibst hab habs stell stellt hol holt pass passt "
    "liegt sitzt kommen sehen sieht siehst sag sagt sagen mein meint meine denkst denkt denken glaubst glaubt "
    "findest findet läuft laufen zeigt zeigen steckt stecken könnt möchte möchtest mag magst "
    "schick schickt frag fragt trifft treffen fließt reicht reichen dauert klappt stimmt merkst merkt zählt "
    "bringt bringen trägt tragen löst lösen bewegt spürst spürt schreib schreibs "
    "hätte hätten hättest wäre wären wärst würde würden würdest könnte könnten müsste müssten sollte sollten dürfte "
    "liefern speichern fährt fuhr misst isst vergisst".split()
)


def hat_verb(satz: str) -> bool:
    """Grobe Verb-Erkennung. Großgeschriebene Wörter mitten im Satz sind meist Substantive („Die Kosten.“) und zählen
    nur, wenn sie als feste Form bekannt sind; „'s“ am Wortende fällt weg („Wie läuft's?“)."""
    erstes = True
    for roh in satz.split():
        wort = re.sub(r"['’]s$", "", re.sub(r"[^\wäöüßÄÖÜ'’]", "", roh))
        if not wort:
            continue
        klein = wort.lower()
        if klein in FESTE:
            return True
        substantiv = not erstes and wort[0].isupper()
        erstes = False
        if substantiv:
            continue
        if any(klein.startswith(st) and klein[len(st):] in ENDUNGEN for st in STAEMME):
            return True
    return False


def saetze_von(text: str) -> list[str]:
    """Sätze wie in den Schwesterskripten; der Mittelpunkt „ · “ trennt zusätzlich."""
    return [teil.strip() for satz in saetze(text) for teil in satz.split(" · ") if teil.strip()]


def kapitel_bloecke(text: str) -> list[str]:
    """Absätze ohne Überschriften und Zeitmarken; Blöcke, in denen danach nichts übrig bleibt, zählen nicht."""
    bloecke = []
    for block in re.split(r"\n\s*\n", text.strip()):
        zeilen = [z.strip() for z in block.splitlines()
                  if z.strip() and not z.lstrip().startswith(("⏱", "▶", "#"))]
        if zeilen:
            bloecke.append(" ".join(zeilen))
    return bloecke


def budget_lesen(pfad: Path) -> dict[int, float]:
    """Startsekunde je Kapitelnummer aus der Budget-Datei."""
    try:
        roh = json.loads(text_lesen(pfad))
    except json.JSONDecodeError as fehler:
        raise Eingabefehler(f"{pfad}: kein gültiges JSON ({fehler})") from None
    if isinstance(roh, dict):  # z. B. {"kapitel": [...]}
        listen = [v for v in roh.values() if isinstance(v, list)]
        roh = next((li for li in listen if li and isinstance(li[0], dict) and "kapitel" in li[0]),
                   listen[0] if listen else [])
    if not isinstance(roh, list):
        raise Eingabefehler(f"{pfad}: erwartet wird eine Liste [{{\"kapitel\": 1, \"startS\": 0}}, …]")
    budget: dict[int, float] = {}
    for stelle, eintrag in enumerate(roh, 1):
        if not isinstance(eintrag, dict) or "startS" not in eintrag:
            raise Eingabefehler(f"{pfad}: Eintrag {stelle} braucht startS")
        nummer, start = eintrag.get("kapitel", stelle), eintrag["startS"]
        if isinstance(nummer, bool) or not isinstance(nummer, int) or isinstance(start, bool) \
                or not isinstance(start, int | float) or not math.isfinite(start):
            raise Eingabefehler(f"{pfad}: Eintrag {stelle}: kapitel muss ganzzahlig, startS eine endliche Zahl sein")
        budget[nummer] = float(start)
    return budget


@dataclass
class Kapitel:
    nummer: int
    woerter: int
    sekunden: float
    budget: float | None


def pruefe(text: str, stufen: dict[str, str], *, tempo: float = 2.6, ziel: float = 78.0,
           budget: dict[int, float] | None = None, letztes: float = 20.0) -> tuple[list[Kapitel], list[Fund]]:
    funde: list[Fund] = []

    def melde(name: str, stelle: str, inhalt: str) -> None:
        if stufen[name] != "aus":
            funde.append(Fund(name, stufen[name], stelle, inhalt))

    kapitel_liste: list[Kapitel] = []
    gesamt = 0
    for i, inhalt in enumerate(kapitel_bloecke(text), 1):
        woerter = len(inhalt.split())
        gesamt += woerter
        sek = woerter / tempo
        stelle = f"Kapitel {i}"
        saetze_k = saetze_von(inhalt)
        beats = [s for s in saetze_k if len(s.split()) <= 3]
        for j, s in enumerate(saetze_k):
            if not hat_verb(s):
                melde("ohne-verb", stelle, f"kein Verb erkannt: „{s}“")
            if s.endswith(":"):
                melde("doppelpunkt-ende", stelle, f"Doppelpunkt am Satzende: „{s}“")
            if j > 0 and len(s.split()) <= 3 and len(saetze_k[j - 1].split()) <= 3:
                melde("beats-hintereinander", stelle, f"zwei Beats hintereinander: „{saetze_k[j - 1]} {s}“")
        if saetze_k and len(saetze_k[0].split()) <= 3:
            melde("kapitel-beginnt-mit-beat", stelle, f"Kapitel beginnt mit Beat: „{saetze_k[0]}“")
        if len(saetze_k) >= 5 and len(beats) > max(1, len(saetze_k) // 5):
            melde("beat-haeufung", stelle, f"{len(beats)} Beats bei {len(saetze_k)} Sätzen")
        frei = None
        if budget and i in budget:
            spaeter = [k for k in budget if k > i]
            frei = (budget[min(spaeter)] if spaeter else budget[i] + letztes) - budget[i]
            if 0 < frei < sek:
                melde("ueber-budget", stelle, f"über Budget: {sek:.1f} s > {frei:.1f} s")
        kapitel_liste.append(Kapitel(i, woerter, sek, frei))
    if gesamt / tempo > ziel:
        melde("gesamtlaenge", "gesamt", f"{gesamt} Wörter = {gesamt / tempo:.0f} s, Ziel höchstens {ziel:g} s")
    return kapitel_liste, funde


def _main(argv: list[str] | None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("datei", nargs="?", type=Path)
    ap.add_argument("--budget", type=Path, help="JSON mit [{kapitel, startS}]")
    ap.add_argument("--tempo", type=float, default=2.6, help="Wörter je Sekunde (Faustwert; eigenes messen)")
    ap.add_argument("--ziel", type=float, default=78.0, help="höchstens so viele Sekunden insgesamt")
    ap.add_argument("--letztes", type=float, default=20.0, help="Sekunden für das letzte Kapitel")
    ap.add_argument("--regel", action="append", default=[], metavar="NAME=STUFE")
    ap.add_argument("--regeln", type=Path, metavar="TOML")
    ap.add_argument("--liste", action="store_true")
    ap.add_argument("--json", action="store_true", help="Ergebnis als JSON (nur ASCII)")
    a = ap.parse_args(argv)
    stufen, _ = stufen_laden(REGELN, a.regeln, a.regel)
    if a.liste:
        for r in REGELN:
            print(f"{r.name:26} {stufen[r.name]:8} {r.kurz}")
        return 0
    if a.datei is None:
        raise Eingabefehler("Datei fehlt (oder --liste)")
    zahl_pruefen("--tempo", a.tempo)
    zahl_pruefen("--ziel", a.ziel)
    zahl_pruefen("--letztes", a.letztes, groesser_null=False)
    budget = budget_lesen(a.budget) if a.budget else None
    text = text_lesen(a.datei)
    if not kapitel_bloecke(text):
        raise Eingabefehler(f"{a.datei}: kein Sprechtext gefunden")
    kapitel, funde = pruefe(text, stufen, tempo=a.tempo, ziel=a.ziel, budget=budget, letztes=a.letztes)
    sperrend = any(f.stufe == "sperrt" for f in funde)
    if a.json:
        print(json.dumps({"kapitel": [asdict(k) for k in kapitel], "funde": [asdict(f) for f in funde],
                          "sperrend": sperrend}, ensure_ascii=True, indent=2))
        return 1 if sperrend else 0
    print(f"{'Kap':>3} {'Wörter':>6} {'Sek':>6} {'Budget':>7}")
    for k in kapitel:
        print(f"{k.nummer:>3} {k.woerter:>6} {k.sekunden:>6.1f} {'' if k.budget is None else f'{k.budget:.1f}s':>7}")
    gesamt = sum(k.woerter for k in kapitel)
    print(f"\nGesamt {gesamt} Wörter = {gesamt / a.tempo:.0f} s bei {a.tempo:g} W/s (Ziel ≤ {a.ziel:g} s)\n")
    for f in funde:
        print(f"  [{'SPERRT ' if f.stufe == 'sperrt' else 'Hinweis'}] {f.regel} ({f.stelle}): {f.text}")
    print(f"\n  {len(funde)} Funde, davon {sum(f.stufe == 'sperrt' for f in funde)} sperrend. "
          "Jede Meldung von Hand lesen; das Skript ist eine Warnlampe, kein Richter.")
    return 1 if sperrend else 0


def main(argv: list[str] | None = None) -> int:
    ausgabe_einrichten()
    try:
        return _main(argv)
    except Eingabefehler as fehler:
        print(f"Fehler: {fehler}", file=sys.stderr)
        return 2
    except Exception as fehler:  # nie Exit 1 (= „sperrend“) für einen Absturz
        print(f"Interner Fehler ({type(fehler).__name__}): {fehler}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
