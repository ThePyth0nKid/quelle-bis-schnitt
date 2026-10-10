#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Vollständigkeitsprobe für gesprochene Texte (Kapitel = Absatz, Leerzeile dazwischen). Berät nur.

Aufruf:
    python pruefe_sprechtext.py prompter.md [--ziel 75] [--tempo 2.6] [--budget kapitel.json]
    python pruefe_sprechtext.py prompter.md --regel ohne-verb=sperrt
    python pruefe_sprechtext.py --liste

Meldet Sätze ohne erkennbares gebeugtes Verb (Warnlampe, von Hand prüfen), Doppelpunkt-Telegramme, Beat-Häufung
(Sätze mit höchstens drei Wörtern), Kapitel über Budget und die Gesamtlänge bei ``--tempo`` Wörtern je Sekunde.

``--budget``: JSON-Liste ``[{"kapitel": 1, "startS": 0}, …]`` (auch unter einem Schlüssel wie ``{"kapitel": […]}``).
Das Budget je Kapitel ist (Start des nächsten − Start dieses) × Tempo; das letzte Kapitel bekommt ``--letztes`` s.

Stufen wie in ``skript_pruefen.py``: ``aus``, ``hinweis`` (Standard), ``sperrt``. Exit-Code 0 ohne sperrenden Fund,
1 mit sperrendem Fund, 2 bei Aufruffehler.
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
    kurz: str


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


def stufen_laden(datei: Path | None, einzeln: list[str]) -> dict[str, str]:
    stufen = {r.name: "hinweis" for r in REGELN}
    if datei is not None:
        daten = tomllib.loads(datei.read_text(encoding="utf-8"))
        for name, stufe in daten.get("regeln", {}).items():
            if name in stufen:  # Regeln der anderen Prüfskripte überspringen
                _setze(stufen, name, str(stufe), str(datei))
    for eintrag in einzeln:
        name, trenner, stufe = eintrag.partition("=")
        if not trenner:
            raise ValueError(f"--regel braucht die Form name=stufe, nicht {eintrag!r}")
        _setze(stufen, name.strip(), stufe.strip(), "--regel")
    return stufen


def _setze(stufen: dict[str, str], name: str, stufe: str, herkunft: str) -> None:
    if name not in stufen:
        raise ValueError(f"{herkunft}: unbekannte Regel {name!r}; --liste zeigt alle")
    if stufe not in STUFEN:
        raise ValueError(f"{herkunft}: Stufe {stufe!r} für {name} ist nicht {', '.join(STUFEN)}")
    stufen[name] = stufe


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
    "lass lässt bleibt bleiben fängt macht machen tut tun gib gibst hab habs hab's hol holt pass passt stell stellt "
    "liegt sitzt kommen sehen sieht siehst sag sagt sagen mein meint meine denkst denkt denken glaubst glaubt "
    "findest findet läuft laufen zeigt zeigen steckt stecken kannst könnt möchte möchtest mag magst "
    "schick schickt frag fragt trifft treffen fließt reicht reichen dauert klappt stimmt merkst merkt zählt "
    "bringt bringen trägt tragen löst lösen bewegt spürst spürt schreib schreibs schreib's "
    "hätte hätten hättest wäre wären wärst würde würden würdest könnte könnten müsste müssten sollte sollten dürfte "
    "liefern speichern fährt fuhr misst isst vergisst".split()
)


def hat_verb(satz: str) -> bool:
    woerter = [w for w in (re.sub(r"[^\wäöüß']", "", w.lower()) for w in satz.split()) if w]
    for w in woerter:
        if w in FESTE:
            return True
        if any(w.startswith(st) and w[len(st):] in ENDUNGEN for st in STAEMME):
            return True
    return False


def saetze_von(text: str) -> list[str]:
    # Ordnungszahlen sind kein Satzende: „Am 19. August“ ist EIN Satz. Der Mittelpunkt „ · “ trennt Sätze.
    roh = re.split(r"(?<![0-9]\.)(?<=[.!?])\s+|\s·\s", text.strip())
    return [s.strip() for s in roh if s.strip()]


def budget_lesen(pfad: Path) -> list[dict]:
    roh = json.loads(pfad.read_text(encoding="utf-8"))
    if isinstance(roh, dict):  # z. B. {"kapitel": [...]}
        listen = [v for v in roh.values() if isinstance(v, list)]
        roh = next((li for li in listen if li and isinstance(li[0], dict) and "kapitel" in li[0]),
                   listen[0] if listen else [])
    return sorted((k for k in roh if isinstance(k, dict) and "startS" in k),
                  key=lambda k: (k.get("kapitel", 0), k["startS"]))


@dataclass
class Kapitel:
    nummer: int
    woerter: int
    sekunden: float
    budget: float | None


def pruefe(text: str, stufen: dict[str, str], *, tempo: float = 2.6, ziel: float = 78.0,
           budget: list[dict] | None = None, letztes: float = 20.0) -> tuple[list[Kapitel], list[Fund]]:
    funde: list[Fund] = []

    def melde(name: str, stelle: str, inhalt: str) -> None:
        if stufen[name] != "aus":
            funde.append(Fund(name, stufen[name], stelle, inhalt))

    kapitel_liste: list[Kapitel] = []
    bloecke = [k for k in re.split(r"\n\s*\n", text.strip()) if k.strip()]
    gesamt = 0
    for i, block in enumerate(bloecke, 1):
        zeilen = [z for z in block.splitlines() if z.strip() and not z.startswith(("⏱", "▶", "#"))]
        inhalt = " ".join(zeilen)
        woerter = len(inhalt.split())
        gesamt += woerter
        sek = woerter / tempo
        stelle = f"Kapitel {i}"
        saetze = saetze_von(inhalt)
        beats = [s for s in saetze if len(s.split()) <= 3]
        for j, s in enumerate(saetze):
            if not hat_verb(s):
                melde("ohne-verb", stelle, f"kein Verb erkannt: „{s}“")
            if s.endswith(":"):
                melde("doppelpunkt-ende", stelle, f"Doppelpunkt am Satzende: „{s}“")
            if j > 0 and len(s.split()) <= 3 and len(saetze[j - 1].split()) <= 3:
                melde("beats-hintereinander", stelle, f"zwei Beats hintereinander: „{saetze[j - 1]} {s}“")
        if saetze and len(saetze[0].split()) <= 3:
            melde("kapitel-beginnt-mit-beat", stelle, f"Kapitel beginnt mit Beat: „{saetze[0]}“")
        if len(saetze) >= 5 and len(beats) > max(1, len(saetze) // 5):
            melde("beat-haeufung", stelle, f"{len(beats)} Beats bei {len(saetze)} Sätzen")
        frei = None
        if budget and i <= len(budget):
            start = float(budget[i - 1]["startS"])
            ende = float(budget[i]["startS"]) if i < len(budget) else start + letztes
            frei = ende - start
            if 0 < frei < sek:
                melde("ueber-budget", stelle, f"über Budget: {sek:.1f} s > {frei:.1f} s")
        kapitel_liste.append(Kapitel(i, woerter, sek, frei))
    if gesamt / tempo > ziel:
        melde("gesamtlaenge", "gesamt", f"{gesamt} Wörter = {gesamt / tempo:.0f} s, Ziel höchstens {ziel:g} s")
    return kapitel_liste, funde


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("datei", nargs="?", type=Path)
    ap.add_argument("--budget", type=Path, help="JSON mit [{kapitel, startS}]")
    ap.add_argument("--tempo", type=float, default=2.6, help="Wörter je Sekunde (Faustwert; eigenes messen)")
    ap.add_argument("--ziel", type=float, default=78.0, help="höchstens so viele Sekunden insgesamt")
    ap.add_argument("--letztes", type=float, default=20.0, help="Sekunden für das letzte Kapitel")
    ap.add_argument("--regel", action="append", default=[], metavar="NAME=STUFE")
    ap.add_argument("--regeln", type=Path, metavar="TOML")
    ap.add_argument("--liste", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        stufen = stufen_laden(a.regeln, a.regel)
        budget = budget_lesen(a.budget) if a.budget else None
    except (ValueError, OSError, tomllib.TOMLDecodeError, json.JSONDecodeError) as fehler:
        print(f"Fehler: {fehler}", file=sys.stderr)
        return 2
    if a.liste:
        for r in REGELN:
            print(f"{r.name:26} {stufen[r.name]:8} {r.kurz}")
        return 0
    if a.datei is None or not a.datei.is_file() or a.tempo <= 0:
        print("Fehler: Datei fehlt oder --tempo ≤ 0", file=sys.stderr)
        return 2
    kapitel, funde = pruefe(a.datei.read_text(encoding="utf-8-sig"), stufen, tempo=a.tempo, ziel=a.ziel,
                            budget=budget, letztes=a.letztes)
    sperrend = any(f.stufe == "sperrt" for f in funde)
    if a.json:
        print(json.dumps({"kapitel": [asdict(k) for k in kapitel], "funde": [asdict(f) for f in funde],
                          "sperrend": sperrend}, ensure_ascii=False, indent=2))
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


if __name__ == "__main__":
    sys.exit(main())
