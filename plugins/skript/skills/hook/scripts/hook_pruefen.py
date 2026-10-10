#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prüft einen deutschen Hook (erster gesprochener Satz, gern mit Satz 2) und den Text auf Bild 1. Berät nur.

Aufruf:
    python hook_pruefen.py "In Musterhafen fährt eine Straßenbahn ohne Fahrer. Doch wer bremst?" [--titel "…"]
    python hook_pruefen.py "…" --neu                    # die Sache ist wirklich neu (unter 14 Tagen)
    python hook_pruefen.py "…" --streng                 # harte Punkte sperren
    python hook_pruefen.py --liste

Kein Punktwert: Den wichtigsten Test macht kein Skript. Kann ein Fremder den Hook einem Freund in einem Satz
nacherzählen, und ergibt er dann Sinn? (Agent ``hook-blind``.)

Stufen wie in ``skript_pruefen.py``: ``aus``, ``hinweis`` (Standard), ``sperrt``; ``--regeln datei.toml``,
``--regel name=stufe``, ``--streng``. Exit-Code 0 ohne sperrenden Fund, 1 mit sperrendem Fund, 2 bei Aufruf- oder
Konfigurationsfehler.
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
    hart: bool
    kurz: str


REGELN: tuple[Regel, ...] = (
    Regel("anlauf-vorn", True, "kein Gruß und kein Anlauf vorn (Hallo, Willkommen, „Heute zeige ich …“)"),
    Regel("quellvideo-vorn", True, "kein Quellvideo-Wort im ersten Satz (Reel, Video, Likes, Aufrufe …)"),
    Regel("bannwort", True, "kein Wort der Bann-Liste"),
    Regel("gerade-ohne-neuigkeit", True, "„gerade“ nur bei echter Neuigkeit unter 14 Tagen (--neu)"),
    Regel("ichwir-vorn", False, "Ich/Wir vorn nur mit Tat und Ding im selben Satz"),
    Regel("kausal-vorn", False, "Kausalwort im ersten Satz: ist es noch eine Idee?"),
    Regel("ding-vorn", False, "Zahl oder Zeigewort bis Wort 8 als Zeichen für ein Ding"),
    Regel("erster-satz-lang", False, "erster Satz in einem Atemzug (höchstens 14 Wörter)"),
    Regel("frage-vorn", False, "Frage vorn: steckt ein Ding darin, folgt die Antwort sofort?"),
    Regel("du-vorn", False, "ein Du in den ersten zwei Sätzen"),
    Regel("bild1-text", False, "Bild-1-Text 4–7 Wörter, als Frage oder mit Wie/Warum (nur mit --titel)"),
)
REGEL = {r.name: r for r in REGELN}


@dataclass
class Fund:
    regel: str
    stufe: str
    stelle: str
    text: str
    vorschlag: str = ""


# „gerade mal“, „gerade Zahl“ usw. sind keine Neuigkeit
NEU = re.compile(r"\b(gerade(?!\s+(?:mal|einmal|so|noch|zahl|zahlen|linie|linien)\b)|soeben|seit gestern|seit heute"
                 r"|diese woche)\b", re.I)


def pruefe(hook: str, stufen: dict[str, str], *, titel: str | None = None, neu: bool = False,
           daten: dict | None = None) -> list[Fund] | None:
    """Funde zum Hook; None ohne Text."""
    s = saetze(hook)
    if not s:
        return None
    funde: list[Fund] = []

    def melde(name: str, stelle: str, text: str, vorschlag: str = "") -> None:
        if stufen[name] != "aus":
            funde.append(Fund(name, stufen[name], stelle, text, vorschlag))

    erster = s[0]
    unter = erster.lower().lstrip(VORZEICHEN + " ")
    w = erster.split()
    if GRUSS_START.match(unter):
        melde("anlauf-vorn", "Satz 1", "Gruß oder Anlauf vorn", "das Ding gehört in den ersten Satz")
    if ICHWIR_START.match(unter):
        melde("ichwir-vorn", "Satz 1", "erstes Wort Ich/Wir",
              "trägt nur mit Tat und Ding im selben Satz, sonst den Absender in Satz 2")
    frage = bool(FRAGE_ENDE.search(erster))
    kausal = [m.group(0) for m in KAUSAL.finditer(erster) if not (frage and m.group(0).lower() == "denn")]
    if kausal:
        melde("kausal-vorn", "Satz 1", f"Kausalwort im ersten Satz („{'“, „'.join(kausal)}“)",
              "ist es noch eine Idee? Die Kette gehört in die Erklärung")
    quelle = [m.group(0) for m in QUELLVIDEO.finditer(erster)]
    if quelle:
        melde("quellvideo-vorn", "Satz 1", f"Quellvideo-Wort im ersten Satz („{'“, „'.join(quelle)}“)",
              "das Ding ist das Phänomen (Zahl, Urteil, Behauptung), nicht das Video")
    bann = bann_muster(daten or {}).search(hook)
    if bann:
        melde("bannwort", "Hook", f"Bann-Wort „{bann.group(0)}“", "Bedeutung mit einem Fakt zeigen")
    if NEU.search(erster) and not neu:
        melde("gerade-ohne-neuigkeit", "Satz 1", "„gerade“ oder „soeben“ ohne --neu",
              "nur bei echter Neuigkeit unter 14 Tagen, sonst streichen")
    zahl = ZAHLWORT.search(erster)
    vor = len(erster[: zahl.start()].split()) if zahl else None
    zeigt = any(unter.startswith(z) for z in ZEIGEWORT) or bool(DU.match(unter))
    if not (zahl and vor is not None and vor < 8) and not zeigt:
        if zahl:
            melde("ding-vorn", "Satz 1", f"Zahl erst bei Wort {vor + 1}",
                  "nach vorn ziehen, wenn sie das Ding größer macht")
        else:
            melde("ding-vorn", "Satz 1", "keine Zahl und kein Zeigewort bis Wort 8 erkannt",
                  "steht ein Ding im ersten Satz, das man sich vorstellen kann, und was es tut?")
    if len(w) > 14:
        melde("erster-satz-lang", "Satz 1", f"erster Satz hat {len(w)} Wörter", "in einem Atemzug sagbar?")
    if frage or w[0].lower().strip(",") in FRAGE_START:
        zweiter = s[1] if len(s) > 1 else ""
        bezahlt = bool(zweiter) and bool(ZAHLWORT.search(zweiter)
                                         or re.match(r"^(nein|nope|ja|doch|falsch)\b", zweiter, re.I)
                                         or len(zweiter.split()) <= 10)
        if not bezahlt:
            melde("frage-vorn", "Satz 1–2", "gesprochene Frage vorn ohne schnelle Antwort",
                  "steckt ein Ding in der Frage? Dann trägt sie, und der Schluss beantwortet sie")
    if len(s) > 1 and not DU.search(" ".join(s[:2])):
        melde("du-vorn", "Satz 1–2", "kein Du in den ersten zwei Sätzen", "trifft es den Zuschauer selbst?")
    if titel is not None:
        tw = titel.split()
        frage_t = titel.strip().endswith("?") or bool(tw and tw[0].lower() in ("wie", "warum", "was", "wieso",
                                                                              "weshalb", "wer"))
        if not (4 <= len(tw) <= 7 and frage_t):
            melde("bild1-text", "Bild 1", f"{len(tw)} Wörter, Frage oder Wie/Warum: {'ja' if frage_t else 'nein'}",
                  "4–7 Wörter, stumm lesbar, als Frage oder Widerspruch")
    return funde


def _main(argv: list[str] | None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("hook", nargs="?", help="erster gesprochener Satz (gern mit Satz 2)")
    p.add_argument("--titel", help="Text auf Bild 1")
    p.add_argument("--neu", action="store_true", help="die Sache ist wirklich neu (unter 14 Tagen)")
    p.add_argument("--regel", action="append", default=[], metavar="NAME=STUFE")
    p.add_argument("--regeln", type=Path, metavar="TOML")
    p.add_argument("--streng", action="store_true", help="harte Punkte auf „sperrt“")
    p.add_argument("--liste", action="store_true")
    p.add_argument("--json", action="store_true", help="Ergebnis als JSON (nur ASCII)")
    a = p.parse_args(argv)
    stufen, daten = stufen_laden(REGELN, a.regeln, a.regel, a.streng)
    if a.liste:
        for r in REGELN:
            print(f"{r.name:22} {stufen[r.name]:8} {'hart' if r.hart else '    '} {r.kurz}")
        return 0
    funde = pruefe(a.hook or "", stufen, titel=a.titel, neu=a.neu, daten=daten)
    if funde is None:
        raise Eingabefehler("kein Text")
    sperrend = any(f.stufe == "sperrt" for f in funde)
    if a.json:
        print(json.dumps({"hook": a.hook, "funde": [asdict(f) | {"hart": REGEL[f.regel].hart} for f in funde],
                          "sperrend": sperrend}, ensure_ascii=True, indent=2))
        return 1 if sperrend else 0
    print(f"\nHook: {a.hook}\n")
    for f in funde:
        marke = "SPERRT " if f.stufe == "sperrt" else "Hinweis"
        hart = "*" if REGEL[f.regel].hart else " "
        print(f"  [{marke}]{hart} {f.regel} ({f.stelle}): {f.text}" + (f"  → {f.vorschlag}" if f.vorschlag else ""))
    print(f"\n  {len(funde)} Funde, davon {sum(f.stufe == 'sperrt' for f in funde)} sperrend (* = harter Punkt).")
    print("  Nacherzähl-Test (macht kein Skript): Kann ein Fremder den Hook in einem Satz weitererzählen?")
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
