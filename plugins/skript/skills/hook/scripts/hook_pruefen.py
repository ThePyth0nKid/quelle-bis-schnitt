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
``--regel name=stufe``, ``--streng``. Exit-Code 0 ohne sperrenden Fund, 1 mit sperrendem Fund, 2 bei Aufruffehler.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

STUFEN = ("aus", "hinweis", "sperrt")


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


def stufen_laden(datei: Path | None, einzeln: list[str], streng: bool) -> tuple[dict[str, str], dict]:
    """Stufen je Regel plus Zusatzdaten aus der TOML-Datei. Wirft ValueError bei Unbekanntem."""
    stufen = {r.name: "hinweis" for r in REGELN}
    if streng:
        stufen.update({r.name: "sperrt" for r in REGELN if r.hart})
    daten: dict = {}
    if datei is not None:
        daten = tomllib.loads(datei.read_text(encoding="utf-8"))
        for name, stufe in daten.get("regeln", {}).items():
            if name in stufen:  # Regeln anderer Prüfskripte in derselben Datei überspringen
                _setze(stufen, name, str(stufe), str(datei))
    for eintrag in einzeln:
        name, trenner, stufe = eintrag.partition("=")
        if not trenner:
            raise ValueError(f"--regel braucht die Form name=stufe, nicht {eintrag!r}")
        _setze(stufen, name.strip(), stufe.strip(), "--regel")
    return stufen, daten


def _setze(stufen: dict[str, str], name: str, stufe: str, herkunft: str) -> None:
    if name not in stufen:
        raise ValueError(f"{herkunft}: unbekannte Regel {name!r}; --liste zeigt alle")
    if stufe not in STUFEN:
        raise ValueError(f"{herkunft}: Stufe {stufe!r} für {name} ist nicht {', '.join(STUFEN)}")
    stufen[name] = stufe


ZAHLWORT = re.compile(
    r"\b(\d[\d.,]*|null|eins|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn|elf|zwölf|hundert|tausend"
    r"|million(en)?|milliarde(n)?|dutzend)\b",
    re.I,
)
ZEIGEWORT = ("dieses", "dieser", "diese", "diesen", "diesem", "das hier", "der hier", "die hier", "den hier", "schau",
             "guck", "stell dir")
DU = re.compile(r"\b(du|dich|dir|dein|deine|deinen|deinem|deiner|deins)\b", re.I)
KAUSAL = re.compile(r"\b(weil|obwohl|(?<!\bsei )denn(?!\s+je\b)|sodass|so dass|deshalb|deswegen|daher)\b", re.I)
QUELLVIDEO = re.compile(r"(?<![-\w])(reels?|videos?|clips?|posts|likes?|aufrufe|views|follower|kommentare)"
                        r"\b(?!-)", re.I)
# „gerade mal“, „gerade Zahl“ usw. sind keine Neuigkeit
NEU = re.compile(r"\b(gerade(?!\s+(?:mal|einmal|so|noch|zahl|zahlen|linie|linien)\b)|soeben|seit gestern|seit heute"
                 r"|diese woche)\b", re.I)
GRUSS_START = re.compile(r"(hallo|hey|in diesem video|willkommen|servus|moin)\b"
                         r"|heute (zeig|erklär|schau|guck|geht|red|sprech|mach|hab|möcht|will|woll|lern|kümmer)", re.I)
ICHWIR_START = re.compile(r"(ich|wir)\b", re.I)
VORZEICHEN = "„“\"'»«‚‘(["
FRAGE_ENDE = re.compile(r"\?[!?\s“”\"'»«)]*$")
MONAT_ODER_JH = (r"(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember"
                 r"|Jahrhundert|Jahrtausend)\b")
FRAGE_START = ("wer", "wie", "was", "warum", "wieso", "weshalb", "wann", "wo", "ist", "sind", "hat", "haben", "kann",
               "kannst", "wusstest", "weißt", "glaubst")
BANN_STANDARD = ("spannend", "unglaublich", "wusstest du", "in diesem video", "entscheidend", "revolutionär",
                 "bahnbrechend", "faszinierend", "ganzheitlich", "gigantisch", "wahnsinn")


def bann_muster(daten: dict) -> re.Pattern[str]:
    bann = daten.get("bann", {})
    erlaubt = {w.lower() for w in bann.get("erlaubt", [])}
    woerter = [w for w in (*BANN_STANDARD, *bann.get("zusaetzlich", [])) if w.lower() not in erlaubt]
    if not woerter:
        return re.compile(r"(?!x)x")
    return re.compile(r"\b(" + "|".join(re.escape(w) for w in woerter) + r")\b", re.I)


def saetze(text: str) -> list[str]:
    muster = rf"(?<![0-9]\.)(?<=[.!?])\s+|(?<=[0-9]\.)\s+(?!{MONAT_ODER_JH})"
    return [s.strip() for s in re.split(muster, text.strip()) if s.strip()]


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


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("hook", nargs="?", help="erster gesprochener Satz (gern mit Satz 2)")
    p.add_argument("--titel", help="Text auf Bild 1")
    p.add_argument("--neu", action="store_true", help="die Sache ist wirklich neu (unter 14 Tagen)")
    p.add_argument("--regel", action="append", default=[], metavar="NAME=STUFE")
    p.add_argument("--regeln", type=Path, metavar="TOML")
    p.add_argument("--streng", action="store_true", help="harte Punkte auf „sperrt“")
    p.add_argument("--liste", action="store_true")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    try:
        stufen, daten = stufen_laden(a.regeln, a.regel, a.streng)
    except (ValueError, OSError, tomllib.TOMLDecodeError) as fehler:
        print(f"Fehler: {fehler}", file=sys.stderr)
        return 2
    if a.liste:
        for r in REGELN:
            print(f"{r.name:22} {stufen[r.name]:8} {'hart' if r.hart else '    '} {r.kurz}")
        return 0
    funde = pruefe(a.hook or "", stufen, titel=a.titel, neu=a.neu, daten=daten)
    if funde is None:
        print("Fehler: kein Text.", file=sys.stderr)
        return 2
    sperrend = any(f.stufe == "sperrt" for f in funde)
    if a.json:
        print(json.dumps({"hook": a.hook, "funde": [asdict(f) | {"hart": REGEL[f.regel].hart} for f in funde],
                          "sperrend": sperrend}, ensure_ascii=False, indent=2))
        return 1 if sperrend else 0
    print(f"\nHook: {a.hook}\n")
    for f in funde:
        marke = "SPERRT " if f.stufe == "sperrt" else "Hinweis"
        hart = "*" if REGEL[f.regel].hart else " "
        print(f"  [{marke}]{hart} {f.regel} ({f.stelle}): {f.text}" + (f"  → {f.vorschlag}" if f.vorschlag else ""))
    print(f"\n  {len(funde)} Funde, davon {sum(f.stufe == 'sperrt' for f in funde)} sperrend (* = harter Punkt).")
    print("  Nacherzähl-Test (macht kein Skript): Kann ein Fremder den Hook in einem Satz weitererzählen?")
    return 1 if sperrend else 0


if __name__ == "__main__":
    sys.exit(main())
