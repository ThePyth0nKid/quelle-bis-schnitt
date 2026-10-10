#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prüft einen Sprechtext gegen das Skript-Schema (Skill ``skript``). Das Skript berät, es richtet nicht.

Aufruf:
    python skript_pruefen.py F1_skript.md --format short
    python skript_pruefen.py F1_skript.md --format lang --regel du-dichte=aus --regel laenge=sperrt
    python skript_pruefen.py F1_skript.md --format short --streng     # die fünf harten Punkte sperren
    python skript_pruefen.py --liste                                  # alle Regeln mit Stufe

Jede Regel hat eine Stufe: ``aus`` (nicht prüfen), ``hinweis`` (melden, Standard) oder ``sperrt`` (melden und
Exit-Code 1). Reihenfolge: Standard ``hinweis`` → ``--streng`` → ``--regeln datei.toml`` → ``--regel name=stufe``.
Eine Regeldatei darf auch Regeln von ``hook_pruefen.py`` und ``pruefe_sprechtext.py`` tragen; was dieses Skript
nicht kennt, überspringt es (``--liste`` zeigt, was greift). Der Mensch entscheidet je Fund: übernehmen, verwerfen
oder anders.

Eingabe: Markdown. Gibt es ``## Sprechtext``, zählt nur dieser Abschnitt, sonst die ganze Datei ohne Zeilen, die mit
``#``, ``|``, ``**``, ``<`` oder drei Backticks beginnen. Leerzeilen trennen Slots. Regie-Marken in eckigen Klammern
am Zeilenanfang (``[A]``, ``[B]``) zählen nicht als Wort.

Exit-Code: 0 ohne sperrenden Fund, 1 mit sperrendem Fund, 2 bei Aufruffehler oder ohne Sprechtext.
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

# ---------------------------------------------------------------------------
# Regelwerk: Stufen, Regeln, Funde (gleich aufgebaut in hook_pruefen.py und pruefe_sprechtext.py)
# ---------------------------------------------------------------------------

STUFEN = ("aus", "hinweis", "sperrt")
FORMATE = ("snack", "short", "trailer", "lang")
ALLE = FORMATE
KURZ = ("snack", "short")


@dataclass(frozen=True)
class Regel:
    name: str
    hart: bool  # gehört zu den fünf harten Punkten (``--streng`` sperrt sie)
    punkt: str  # Punkt im Skill (1–5 hart, H = Hinweis)
    kurz: str
    formate: tuple[str, ...] = ALLE


REGELN: tuple[Regel, ...] = (
    Regel("anlauf-vorn", True, "1", "erster Satz ohne Gruß und Anlauf (Hallo, Willkommen, „Heute zeige ich …“)"),
    Regel("quellvideo-vorn", True, "1", "kein Quellvideo-Wort im ersten Satz (Reel, Video, Likes, Aufrufe …)"),
    Regel("kausal-vorn", False, "H", "Kausalwort im ersten Satz: ist es noch eine Idee?"),
    Regel("ichwir-vorn", False, "H", "Ich/Wir als erstes Wort nur mit Tat und Ding im selben Satz"),
    Regel("ding-vorn", False, "H", "Zahl oder Zeigewort bis Wort 8 als Zeichen für ein Ding",
          ("snack", "short", "lang")),
    Regel("erster-satz-lang", False, "H", "erster Satz in einem Atemzug (höchstens 14 Wörter)"),
    Regel("frage-vorn", False, "H", "gesprochene Frage vorn: steckt ein Ding darin, kommt die Antwort?"),
    Regel("zahlentabelle", True, "2", "Zahlen im Sprechtext brauchen die Tabelle „## Zahlen“"),
    Regel("zahlen-quelle", True, "2", "jede Zeile der Zahlentabelle nennt eine Quelle"),
    Regel("belegblatt", True, "2", "neben F<n>_skript.md liegt F<n>_belege.md"),
    Regel("quelle-im-satz", False, "H", "eine Quelle als Akteur im Satz („laut …“, „hat … gemessen“)"),
    Regel("floskel", True, "3", "keine Übergangsfloskel („schauen wir mal“, „in diesem Video“)"),
    Regel("du-dichte", True, "3", "Du-Ansprache: mindestens 2 (Kurzformate) bzw. 3 (Trailer, Lang) je 100 Wörter"),
    Regel("bannwort", True, "3", "kein Wort der Bann-Liste"),
    Regel("gedankenstrich", True, "3", "kein Gedankenstrich im Sprechtext"),
    Regel("laenge", True, "4", "Länge im Band des Formats"),
    Regel("letzter-satz", True, "5", "letzter Satz ohne Aufforderung und ohne Fazit", ("snack", "short", "lang")),
    Regel("aufforderung-trailer", True, "5", "Trailer: genau eine Aufforderung bei 70–90 % der Länge", ("trailer",)),
    Regel("letzter-satz-also", False, "H", "letzter Satz beginnt mit „Also“: Auszahlung oder Zusammenfassung?", KURZ),
    Regel("schlussfrage-lang", False, "H", "Schlussfrage im Langvideo höchstens 12 Wörter", ("lang",)),
    Regel("versprechen", False, "H", "Versprechen oder Frage bis Satz 3"),
    Regel("klammer", False, "H", "die Frage aus dem Hook kommt am Schluss wieder", KURZ),
    Regel("wendung", False, "H", "eine Wendung (aber, doch, trotzdem) nach dem Hook", ("snack", "short", "lang")),
    Regel("neue-luecke", False, "H", "ein Satz öffnet eine neue Lücke; im Langvideo im Takt", ("short", "lang")),
    Regel("zahlenleiter", False, "H", "Snack: bei großen Zahlen eine Leiter von bekannt nach unbekannt", ("snack",)),
    Regel("analogie", False, "H", "eine Alltags-Analogie für das Technik-Ding", KURZ),
    Regel("lacher-lage", False, "H", "Lacher am Ende (ab 75 %), nur mit --lacher"),
    Regel("auszahlung-frueh", False, "H", "Auszahlung nicht vor 25 %, nur mit --auszahlung"),
    Regel("slots", False, "H", "Absätze und Wörter je Slot nah am Schema", ("snack", "short", "trailer")),
    Regel("du-vor-ich", False, "H", "Trailer: mehr Du als Ich", ("trailer",)),
)
REGEL = {r.name: r for r in REGELN}


@dataclass
class Fund:
    regel: str
    stufe: str
    stelle: str
    text: str
    vorschlag: str = ""


class Sammler:
    """Sammelt Funde und schlägt je Regel die Stufe nach; Regeln auf ``aus`` melden nichts."""

    def __init__(self, stufen: dict[str, str], fmt: str) -> None:
        self.stufen = stufen
        self.fmt = fmt
        self.funde: list[Fund] = []

    def aktiv(self, name: str) -> bool:
        return self.fmt in REGEL[name].formate and self.stufen[name] != "aus"

    def melde(self, name: str, stelle: str, text: str, vorschlag: str = "") -> None:
        if self.aktiv(name):
            self.funde.append(Fund(name, self.stufen[name], stelle, text, vorschlag))


def stufen_laden(datei: Path | None, einzeln: list[str], streng: bool) -> tuple[dict[str, str], dict]:
    """Stufen je Regel plus Zusatzdaten aus der TOML-Datei (z. B. ``[bann]``). Wirft ValueError bei Unbekanntem."""
    stufen = {r.name: "hinweis" for r in REGELN}
    if streng:
        stufen.update({r.name: "sperrt" for r in REGELN if r.hart})
    daten: dict = {}
    if datei is not None:
        daten = tomllib.loads(datei.read_text(encoding="utf-8"))
        for name, stufe in daten.get("regeln", {}).items():
            if name in stufen:  # Regeln der anderen Prüfskripte in derselben Datei überspringen
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


# ---------------------------------------------------------------------------
# Muster
# ---------------------------------------------------------------------------

ZAHLWORT = re.compile(
    r"\b(\d[\d.,]*|null|eins|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn|elf|zwölf|hundert|tausend"
    r"|million(en)?|milliarde(n)?|dutzend)\b",
    re.I,
)
ZEIGEWORT = ("dieses", "dieser", "diese", "diesen", "diesem", "das hier", "der hier", "die hier", "schau", "guck",
             "stell dir", "in diesen", "in diesem", "in dieser")
DU = re.compile(r"\b(du|dich|dir|dein|deine|deinen|deinem|deiner|deins|euch|euer|eure)\b", re.I)  # ohne „ihr“
ICH = re.compile(r"\b(ich|mich|mir|mein|meine|meinen|meinem|meiner)\b", re.I)
FLOSKEL = re.compile(r"(los geht'?s|schauen wir (uns )?(mal|das)|gucken wir (mal|uns)|wir gehen mal rein"
                     r"|in diesem video|heute zeige ich|willkommen zurück|hallo zusammen|schön, dass du)", re.I)
WENDUNG = re.compile(r"^(aber|nein|nope|doch|trotzdem|jetzt denkst du|falsch|und trotzdem|dabei)\b"
                     r"|\b(aber|trotzdem|stattdessen)\b", re.I)
REHOOK = re.compile(r"(jetzt kommt|und jetzt|hier wird'?s|der teil, den|das verrückte|das beste|und dann gibt es"
                    r"|jetzt wird'?s|aber das ist noch nicht|\bguck dir\b|\bschau dir\b|\bpass auf\b)", re.I)
FORESHADOW = re.compile(r"\b(gleich|am ende|dann siehst du|du bekommst|du siehst|ich zeig|ich rechne|bis (du|zum|zur)"
                        r"|umrechnen|nachgerechnet|zeige dir|zeig dir|und (am ende|dann) )", re.I)
QUELLE = re.compile(r"(gemessen|gezählt|berechnet|veröffentlicht|fact sheet|studie|forscher|gefunden"
                    r"|hat .*?\d{4}|laut )", re.I)
# „denn je“ und „es sei denn“ sind nicht kausal; „Post“ ist auch die Post; „Video-Überwachung“ ist kein Quellvideo.
KAUSAL = re.compile(r"\b(weil|obwohl|(?<!\bsei )denn(?!\s+je\b)|sodass|so dass|deshalb|deswegen|daher)\b", re.I)
QUELLVIDEO = re.compile(r"(?<![-\w])(reels?|videos?|clips?|posts|likes?|aufrufe|views|follower|kommentare)"
                        r"\b(?!-)", re.I)
# „Heute“ ist nur vor einem Anlauf-Verb ein Anlauf („Heute zeige ich …“), nicht bei einer Neuigkeit („Heute kostet …“).
GRUSS_START = re.compile(r"(hallo|hey|in diesem video|willkommen|servus|moin)\b"
                         r"|heute (zeig|erklär|schau|guck|geht|red|sprech|mach|hab|möcht|will|woll|lern|kümmer)", re.I)
ICHWIR_START = re.compile(r"(ich|wir)\b", re.I)  # ganzes Wort, nicht „Wirbel“
VORZEICHEN = "„“\"'»«‚‘(["  # führende Anführungszeichen und Klammern vor den Start-Prüfungen abschneiden
FRAGE_ENDE = re.compile(r"\?[!?\s“”\"'»«)]*$")
FRAGE_START = ("wer", "wie", "was", "warum", "wieso", "weshalb", "wann", "wo", "ist", "sind", "hat", "haben", "kann",
               "kannst", "wusstest", "weißt", "glaubst")
MONAT_ODER_JH = (r"(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember"
                 r"|Jahrhundert|Jahrtausend)\b")
CTA = re.compile(r"(\bfolg(e)? (mir|rein|jetzt)\b|\babonnier|\bkommentier|in die kommentare|welche zahl soll"
                 r"|was denkst du\b|was meinst du\b|\bteil (das|es)\b|\blike\b|link in der bio)", re.I)
FAZIT = re.compile(r"^(zusammengefasst|fazit|das heißt also|kurz gesagt|danke)\b", re.I)
BANN_STANDARD = ("spannend", "unglaublich", "wusstest du", "in diesem video", "entscheidend", "revolutionär",
                 "bahnbrechend", "faszinierend", "ganzheitlich", "gigantisch", "wahnsinn")
ANALOGIE = re.compile(
    r"(?:\bgenau|\bdoppelt |\bhalb |\b)so \w+ wie\b"
    r"|\b(schwerer|größer|heißer|kälter|schneller|länger|kleiner|stärker|höher|älter|lauter|heller|dicker|dünner"
    r"|breiter|tiefer) als (ein|eine|einen|einem|der|die|das|du|dein)\b"
    r"|\bvergleichbar mit\b|\bentspricht (etwa |ungefähr |rund )?(ein|eine|einem|einer|einen)\b|\bungefähr so\b",
    re.I,
)
# klein geschrieben, damit „Wie eine Studie zeigt“ am Satzanfang nicht zählt
WIE_ANALOGIE = re.compile(r"\bwie (ein|eine|einen|einem|zwei|drei|vier|fünf|zehn|hundert|tausend|\d[\d.,]*)\b"
                          r"(?! (Studie|Umfrage|Bericht|Analyse))")
REGIE_MARKE = re.compile(r"^\s*\[[A-ZÄÖÜ0-9]{1,12}\]\s*")

# Formatvorgaben (einstellbar): Sekunden gesprochen bei --tempo Wörtern je Sekunde
LAENGE = {"snack": (30.0, 45.0), "short": (60.0, 75.0), "trailer": (35.0, 60.0), "lang": (300.0, 840.0)}
DU_MIN = {"snack": 2.0, "short": 2.0, "trailer": 3.0, "lang": 3.0}
SCHEMA_SLOTS = [("Hook mit Frage", 0.09), ("Absender", 0.03), ("Körper", 0.20), ("Technik-Ding", 0.34),
                ("Auszahlung", 0.17), ("Schluss mit Antwort", 0.17)]
TRAILER_BEATS = [("Haken", 0.08), ("Beweis", 0.22), ("Was du bekommst", 0.20), ("Haltung und Name", 0.20),
                 ("Für wen", 0.12), ("Aufforderung", 0.18)]


def bann_muster(daten: dict) -> re.Pattern[str]:
    """Bann-Liste aus dem Standard plus ``[bann] zusaetzlich`` minus ``[bann] erlaubt`` aus der Regeldatei."""
    bann = daten.get("bann", {})
    erlaubt = {w.lower() for w in bann.get("erlaubt", [])}
    woerter = [w for w in (*BANN_STANDARD, *bann.get("zusaetzlich", [])) if w.lower() not in erlaubt]
    if not woerter:
        return re.compile(r"(?!x)x")  # trifft nie
    return re.compile(r"\b(" + "|".join(re.escape(w) for w in woerter) + r")\b", re.I)


# ---------------------------------------------------------------------------
# Text lesen und zerlegen
# ---------------------------------------------------------------------------

def lies_text(voll: str) -> tuple[str, bool]:
    """Sprechtext aus dem Markdown; zweiter Wert: gab es den Abschnitt „## Sprechtext“?"""
    text = voll
    m = re.search(r"^## Sprechtext.*?$\n(.*?)(?=^## |\Z)", voll, re.S | re.M)
    if m:
        text = m.group(1)
    zeilen = [z for z in text.splitlines() if not z.lstrip().startswith(("#", "|", "**", "<", "```"))]
    zeilen = [REGIE_MARKE.sub("", z) for z in zeilen]
    return "\n".join(zeilen).strip(), bool(m)


def zahlentabelle(voll: str) -> list[list[str]] | None:
    """Datenzeilen der Tabelle unter „## Zahlen“ oder „## Quellen“ (ohne Kopf- und Trennzeile), None ohne Tabelle."""
    m = re.search(r"^#{2,3} (Zahlen|Quellen).*?$\n(.*?)(?=^#{1,2} |\Z)", voll, re.S | re.M)
    if not m:
        return None
    zeilen = [z.strip() for z in m.group(2).splitlines()
              if z.strip().startswith("|") and not re.match(r"^\|[\s:|-]+\|?$", z.strip())]
    if len(zeilen) < 2:  # Kopfzeile plus mindestens eine Zahl
        return None
    return [[c.strip() for c in z.strip("|").split("|")] for z in zeilen[1:]]


def saetze(text: str) -> list[str]:
    """Sätze; „am 4. September“ und „im 19. Jahrhundert“ bleiben einer, „kam 2007. Du …“ sind zwei."""
    muster = rf"(?<![0-9]\.)(?<=[.!?])\s+|(?<=[0-9]\.)\s+(?!{MONAT_ODER_JH})"
    return [s.strip() for s in re.split(muster, text.replace("\n", " ").strip()) if s.strip()]


def lagen(s: list[str]) -> list[float]:
    """Lage jedes Satzes in Prozent der Wörter, aufsummiert; richtig auch bei doppelten Sätzen."""
    gesamt = max(1, sum(len(x.split()) for x in s))
    lage, vor = [], 0
    for x in s:
        lage.append(100.0 * vor / gesamt)
        vor += len(x.split())
    return lage


def absaetze(text: str) -> list[str]:
    return [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]


def lage_von(text: str, satz: str) -> float | None:
    flach = re.sub(r"\s+", " ", text)
    stelle = flach.find(re.sub(r"\s+", " ", satz))
    if stelle < 0:
        return None
    return 100.0 * len(flach[:stelle].split()) / max(1, len(flach.split()))


# ---------------------------------------------------------------------------
# Prüfungen
# ---------------------------------------------------------------------------

def pruefe_erster_satz(sa: Sammler, s: list[str]) -> None:
    erster = s[0]
    unter = erster.lower().lstrip(VORZEICHEN + " ")
    if GRUSS_START.match(unter):
        sa.melde("anlauf-vorn", "Satz 1", "erster Satz beginnt mit Gruß oder Anlauf",
                 "das Ding gehört in den ersten Satz, der Gruß fällt weg")
    if ICHWIR_START.match(unter):
        sa.melde("ichwir-vorn", "Satz 1", "erster Satz beginnt mit Ich/Wir",
                 "trägt nur mit Tat und Ding im selben Satz, sonst den Absender in Satz 2")
    frage = bool(FRAGE_ENDE.search(erster))
    kausal = [m.group(0) for m in KAUSAL.finditer(erster) if not (frage and m.group(0).lower() == "denn")]
    if kausal:
        sa.melde("kausal-vorn", "Satz 1", f"Kausalwort im ersten Satz („{'“, „'.join(kausal)}“)",
                 "zwei Ideen mit einer Kette gehören auseinander, die Kette in die Erklärung")
    quelle = [m.group(0) for m in QUELLVIDEO.finditer(erster)]
    if quelle:
        sa.melde("quellvideo-vorn", "Satz 1", f"Quellvideo-Wort im ersten Satz („{'“, „'.join(quelle)}“)",
                 "das Ding ist das Phänomen (Zahl, Urteil, Behauptung), nicht das Video")
    zahl = ZAHLWORT.search(erster)
    vor = len(erster[: zahl.start()].split()) if zahl else None
    zeigt = any(unter.startswith(z) for z in ZEIGEWORT) or bool(DU.match(unter))
    if not (zahl and vor is not None and vor < 8) and not zeigt:
        sa.melde("ding-vorn", "Satz 1", "keine Zahl und kein Zeigewort bis Wort 8 erkannt",
                 "steht im ersten Satz ein Ding, das man sich vorstellen kann, und was es tut? Namen erkennt das "
                 "Skript nicht")
    w1 = erster.split()
    if len(w1) > 14:
        sa.melde("erster-satz-lang", "Satz 1", f"erster Satz hat {len(w1)} Wörter", "in einem Atemzug sagbar?")
    if (frage or w1[0].lower().strip(",") in FRAGE_START) and len(" ".join(s[:2]).split()) > 22:
        sa.melde("frage-vorn", "Satz 1", "gesprochene Frage als erster Satz, Antwort erst nach Wort 22",
                 "steckt ein Ding in der Frage? Dann trägt sie, und der Schluss beantwortet sie")


def pruefe_belege(sa: Sammler, text: str, voll: str, hat_abschnitt: bool, pfad: Path | None) -> None:
    if hat_abschnitt:
        tabelle = zahlentabelle(voll)
        if ZAHLWORT.search(text) and tabelle is None:
            sa.melde("zahlentabelle", "gesamt", "Zahlen im Sprechtext, aber keine Tabelle „## Zahlen“",
                     "unter den Text: | im Text | Wert | Quelle |")
        if tabelle:
            ohne = [z[0][:40] for z in tabelle if len(z) < 2 or not z[-1]]
            if ohne:
                sa.melde("zahlen-quelle", "## Zahlen", f"Zeilen ohne Quelle: {'; '.join(ohne)}",
                         "Quelle mit Link nachtragen oder die Zahl streichen")
        if pfad is not None:
            fassung = re.match(r"^(F\d+)_skript\.md$", pfad.name, re.I)
            if fassung:
                beleg = pfad.with_name(f"{fassung.group(1)}_belege.md")
                if not beleg.is_file():
                    sa.melde("belegblatt", "Datei", f"Belegblatt {beleg.name} fehlt",
                             "je Behauptung Quelle mit Link, wörtlichem Satz und Sicherheit")
    if not QUELLE.search(text):
        sa.melde("quelle-im-satz", "gesamt", "keine Quelle als Akteur im Satz erkannt",
                 "nennen, wenn es natürlich klingt („Das hat das Wetteramt gemessen“)")


def pruefe_sprache(sa: Sammler, text: str, fmt: str, bann: re.Pattern[str], du_min: float) -> None:
    n = len(text.split())
    f = FLOSKEL.search(text)
    if f:
        sa.melde("floskel", "gesamt", f"Floskel „{f.group(0)}“", "der Übergang trägt selbst Information")
    du100 = 100.0 * len(DU.findall(text)) / max(1, n)
    if du100 < du_min:
        sa.melde("du-dichte", "gesamt", f"Du {du100:.1f} je 100 Wörter (Vorgabe mindestens {du_min:g})",
                 "Brücken zum Zuschauer: „stell dir vor“, „dein …“, „Jetzt denkst du …“")
    b = bann.search(text)
    if b:
        sa.melde("bannwort", "gesamt", f"Bann-Wort „{b.group(0)}“", "Bedeutung mit einem Fakt zeigen, nicht behaupten")
    if "–" in text or "—" in text:
        sa.melde("gedankenstrich", "gesamt", "Gedankenstrich im Sprechtext", "Punkt oder Komma, gesprochen eine Pause")


def pruefe_ende(sa: Sammler, text: str, s: list[str], fmt: str) -> None:
    letzter = s[-1]
    if fmt == "trailer":
        lage = lagen(s)
        ctas = [lage[i] for i, x in enumerate(s) if CTA.search(x)]
        if not (len(ctas) == 1 and 70 <= ctas[0] <= 90):
            wo = ", ".join(f"{x:.0f} %" for x in ctas) or "keine"
            sa.melde("aufforderung-trailer", "gesamt", f"{len(ctas)} Aufforderung(en) ({wo})",
                     "genau eine, mit Grund oder Rhythmus, bei 77–85 % der Länge")
        return
    cta, fazit = CTA.search(letzter), FAZIT.search(letzter)
    if cta or fazit:
        art = "eine Aufforderung" if cta else "ein Fazit"
        sa.melde("letzter-satz", f"Satz {len(s)}", f"letzter Satz ist {art}: „{letzter[:70]}“",
                 "die Aufforderung gehört auf die Endkarte; der letzte Satz ist Auszahlung oder Pointe")
    elif re.match(r"^also\b", letzter, re.I):
        sa.melde("letzter-satz-also", f"Satz {len(s)}", "letzter Satz beginnt mit „Also“",
                 "Auszahlung oder Zusammenfassung? Eine Zusammenfassung streichen")
    if fmt == "lang" and FRAGE_ENDE.search(letzter) and len(letzter.split()) > 12:
        sa.melde("schlussfrage-lang", f"Satz {len(s)}", f"Schlussfrage mit {len(letzter.split())} Wörtern",
                 "höchstens 12 Wörter")


def pruefe_bau(sa: Sammler, text: str, s: list[str], fmt: str, dauer: float, takt: float,
               lacher: str | None, auszahlung: str | None) -> None:
    n = len(text.split())
    if not FORESHADOW.search(" ".join(s[:3])) and not any(FRAGE_ENDE.search(x) for x in s[:3]):
        sa.melde("versprechen", "Satz 1–3", "kein Versprechen und keine Frage bis Satz 3 erkannt",
                 "„Doch stimmt das wirklich?“ oder „am Ende siehst du …“")
    frage_hook = next((x for x in s[:3] if FRAGE_ENDE.search(x)), None)
    if frage_hook:
        # Wortstämme (erste 6 Buchstaben), damit „Batterien“ auch „Batterie“ findet; Schluss = letztes Drittel
        inhalt = {w.strip(".,!?“”„\"").lower()[:6] for w in frage_hook.split() if len(w.strip(".,!?“”„\"")) >= 5}
        schluss = " ".join(s[-max(4, len(s) // 3):]).lower()
        if inhalt and not any(w in schluss for w in inhalt):
            sa.melde("klammer", "Schluss", f"die Frage im Hook („{frage_hook[:60]}“) kommt am Schluss nicht wieder",
                     "die Frage am Schluss noch einmal stellen und beantworten")
    if not any(i > 0 and WENDUNG.search(x) for i, x in enumerate(s)):
        sa.melde("wendung", "gesamt", "keine Wendung mit aber, nein, doch oder trotzdem nach dem Hook erkannt",
                 "kippt irgendwo die Erwartung?")
    lage = lagen(s)
    luecken = [lage[i] / 100.0 * dauer for i, x in enumerate(s) if REHOOK.search(x)]
    if fmt == "short" and not luecken:
        sa.melde("neue-luecke", "gesamt", "kein Satz erkannt, der eine neue Lücke öffnet",
                 "um die Mitte: „Und jetzt kommt der Teil, den keiner erwartet.“")
    if fmt == "lang":
        soll = max(1, int(dauer // takt))
        marken = [0.0, *luecken, dauer]
        groesste = max(b - a for a, b in zip(marken, marken[1:], strict=False))
        if len(luecken) < soll or groesste > 2 * takt:
            sa.melde("neue-luecke", "gesamt",
                     f"{len(luecken)} Sätze mit neuer Lücke (Soll mindestens {soll}, einer je {takt:g} s); "
                     f"größte Lücke {groesste:.0f} s", "ein neues sichtbares Ereignis oder eine neue Frage im Takt")
    if fmt == "snack" and len([x for x in s[1:] if ZAHLWORT.search(x)]) < 2:
        sa.melde("zahlenleiter", "gesamt", "nur eine Zahl nach dem Hook",
                 "bei großen Zahlen hilft eine Leiter von bekannt nach unbekannt")
    flach = text.replace("\n", " ")
    if not ANALOGIE.search(flach) and not WIE_ANALOGIE.search(flach):
        sa.melde("analogie", "gesamt", "keine Alltags-Analogie erkannt („so groß wie …“, „schwerer als ein …“)",
                 "ein oder zwei Analogien tragen das Verstehen")
    for name, satz, grenze, zu_frueh in (("lacher-lage", lacher, 75.0, "Lacher"),
                                         ("auszahlung-frueh", auszahlung, 25.0, "Auszahlung")):
        if not satz:
            continue
        stelle = lage_von(text, satz)
        if stelle is None:
            sa.melde(name, "gesamt", f"der {zu_frueh}-Satz steht nicht wörtlich im Text", "Satz exakt übergeben")
        elif stelle < grenze:
            sa.melde(name, f"{stelle:.0f} %", f"{zu_frueh} schon bei {stelle:.0f} % (Vorgabe ab {grenze:.0f} %)",
                     "später setzen oder danach noch steigern")
    tabelle = SCHEMA_SLOTS if fmt in KURZ else TRAILER_BEATS if fmt == "trailer" else []
    if tabelle:
        bb = absaetze(text)
        if len(bb) != len(tabelle):
            sa.melde("slots", "gesamt", f"{len(bb)} Absätze gegen {len(tabelle)} Slots im Schema",
                     "je Slot ein Absatz: " + ", ".join(name for name, _ in tabelle))
        else:
            weit = [f"{name} {len(x.split())} statt ~{anteil * n:.0f}"
                    for (name, anteil), x in zip(tabelle, bb, strict=True)
                    if abs(len(x.split()) - anteil * n) > 0.35 * anteil * n + 4]
            if weit:
                sa.melde("slots", "gesamt", "Slots weit weg vom Schema: " + "; ".join(weit), "umverteilen")
    if fmt == "trailer":
        du, ich = len(DU.findall(text)), len(ICH.findall(text))
        if du < ich:
            sa.melde("du-vor-ich", "gesamt", f"Du {du} gegen Ich {ich}", "der Trailer handelt vom Zuschauer")


@dataclass
class Ergebnis:
    woerter: int
    saetze: int
    sekunden: float
    band: tuple[float, float]
    funde: list[Fund]


def pruefe(voll: str, fmt: str, stufen: dict[str, str], *, daten: dict | None = None, pfad: Path | None = None,
           tempo: float = 2.6, fremdton: float = 0.0, band: tuple[float, float] | None = None,
           du_min: float | None = None, takt: float = 180.0, lacher: str | None = None,
           auszahlung: str | None = None) -> Ergebnis | None:
    """Prüft einen Markdown-Text; None, wenn kein Sprechtext darin steht."""
    text, hat_abschnitt = lies_text(voll)
    s = saetze(text)
    if not s:
        return None
    n = len(text.split())
    dauer = n / tempo + fremdton
    lo, hi = band or LAENGE[fmt]
    sa = Sammler(stufen, fmt)
    pruefe_erster_satz(sa, s)
    pruefe_belege(sa, text, voll, hat_abschnitt, pfad)
    pruefe_sprache(sa, text, fmt, bann_muster(daten or {}), DU_MIN[fmt] if du_min is None else du_min)
    if not lo <= dauer <= hi:
        sa.melde("laenge", "gesamt", f"Länge {dauer:.0f} s außerhalb des Bands {lo:g}–{hi:g} s",
                 "kürzen oder ausbauen; das Band ist mit --band einstellbar")
    pruefe_ende(sa, text, s, fmt)
    pruefe_bau(sa, text, s, fmt, dauer, takt, lacher, auszahlung)
    return Ergebnis(n, len(s), dauer, (lo, hi), sa.funde)


# ---------------------------------------------------------------------------
# Ausgabe und Aufruf
# ---------------------------------------------------------------------------

def ausgeben(funde: list[Fund], kopf: str) -> None:
    print(kopf)
    for f in funde:
        marke = "SPERRT " if f.stufe == "sperrt" else "Hinweis"
        hart = "*" if REGEL[f.regel].hart else " "
        zeile = f"  [{marke}]{hart} {f.regel} ({f.stelle}): {f.text}"
        print(zeile + (f"  → {f.vorschlag}" if f.vorschlag else ""))
    sperrend = sum(f.stufe == "sperrt" for f in funde)
    print(f"\n  {len(funde)} Funde, davon {sperrend} sperrend (* = einer der fünf harten Punkte).")
    print("  Du entscheidest je Fund: übernehmen, verwerfen oder anders. Ob der Text trägt, zeigt nur das Lautlesen.")


def regeln_zeigen(stufen: dict[str, str]) -> None:
    for r in REGELN:
        print(f"{r.name:22} {stufen[r.name]:8} {'hart' if r.hart else '    '} {'/'.join(r.formate):24} {r.kurz}")


def _band(wert: str) -> tuple[float, float]:
    lo, trenner, hi = wert.partition("-")
    if not trenner:
        raise argparse.ArgumentTypeError("Band als VON-BIS in Sekunden, z. B. 60-75")
    return float(lo), float(hi)


def main(argv: list[str] | None = None) -> int:
    try:  # Sonderzeichen sollen in einer umgeleiteten cp1252-Konsole nicht abstürzen
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("datei", nargs="?", type=Path)
    ap.add_argument("--format", choices=FORMATE)
    ap.add_argument("--regel", action="append", default=[], metavar="NAME=STUFE", help="Stufe einer Regel setzen")
    ap.add_argument("--regeln", type=Path, metavar="TOML", help="Datei mit [regeln] name = \"stufe\" und [bann]")
    ap.add_argument("--streng", action="store_true", help="die fünf harten Punkte auf „sperrt“")
    ap.add_argument("--liste", action="store_true", help="alle Regeln mit Stufe zeigen und enden")
    ap.add_argument("--json", action="store_true", help="Ergebnis als JSON")
    ap.add_argument("--tempo", type=float, default=2.6, help="Wörter je Sekunde (Faustwert 2,6; eigenes messen)")
    ap.add_argument("--fremdton", "--freeze", type=float, default=0.0, dest="fremdton",
                    help="Sekunden fremder O-Ton, die zur Länge zählen")
    ap.add_argument("--band", type=_band, help="eigenes Längenband in Sekunden, z. B. 60-75")
    ap.add_argument("--du-min", type=float, help="Du je 100 Wörter mindestens")
    ap.add_argument("--takt", type=float, default=180.0, help="Langvideo: ein Satz mit neuer Lücke je so viele s")
    ap.add_argument("--lacher", help="der Lacher-Satz wörtlich (optional)")
    ap.add_argument("--auszahlung", help="der Auszahlungs-Satz wörtlich (optional)")
    a = ap.parse_args(argv)
    try:
        stufen, daten = stufen_laden(a.regeln, a.regel, a.streng)
    except (ValueError, OSError, tomllib.TOMLDecodeError) as fehler:
        print(f"Fehler: {fehler}", file=sys.stderr)
        return 2
    if a.liste:
        regeln_zeigen(stufen)
        return 0
    if a.datei is None or a.format is None:
        ap.error("Datei und --format sind nötig (oder --liste)")
    if not math.isfinite(a.fremdton) or a.fremdton < 0 or a.tempo <= 0 or a.takt <= 0:
        print("Fehler: --fremdton ≥ 0, --tempo und --takt > 0", file=sys.stderr)
        return 2
    if not a.datei.is_file():
        print(f"Fehler: Datei fehlt: {a.datei}", file=sys.stderr)
        return 2
    voll = a.datei.read_text(encoding="utf-8-sig")  # ohne BOM, sonst fehlt „## Sprechtext“
    erg = pruefe(voll, a.format, stufen, daten=daten, pfad=a.datei, tempo=a.tempo, fremdton=a.fremdton,
                 band=a.band, du_min=a.du_min, takt=a.takt, lacher=a.lacher, auszahlung=a.auszahlung)
    if erg is None:
        print("Fehler: kein Sprechtext gefunden.", file=sys.stderr)
        return 2
    sperrend = any(f.stufe == "sperrt" for f in erg.funde)
    if a.json:
        print(json.dumps({"datei": str(a.datei), "format": a.format, "woerter": erg.woerter, "saetze": erg.saetze,
                          "sekunden": round(erg.sekunden, 1), "band": list(erg.band),
                          "funde": [asdict(f) | {"hart": REGEL[f.regel].hart} for f in erg.funde],
                          "sperrend": sperrend}, ensure_ascii=False, indent=2))
    else:
        mit = f" + {a.fremdton:g} s Fremdton" if a.fremdton else ""
        lo, hi = erg.band
        ausgeben(erg.funde, f"\n{erg.woerter} Wörter, {erg.saetze} Sätze, {erg.sekunden:.0f} s bei {a.tempo:g} W/s"
                            f"{mit} (Band {lo:g}–{hi:g} s), Format {a.format}\n")
    return 1 if sperrend else 0


if __name__ == "__main__":
    sys.exit(main())
