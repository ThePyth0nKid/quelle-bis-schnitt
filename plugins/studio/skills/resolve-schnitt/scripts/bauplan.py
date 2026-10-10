#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Der Bauplan: die werkzeugneutrale Schnittliste, aus der resolve_bauen.py eine Timeline baut.

Nur Standardbibliothek (läuft im Python von Resolve und im System-Python).

    python bauplan.py pruefen <bauplan.json> [--ohne-dateien]
    python bauplan.py statistik <bauplan.json> --spur <Spurname>

Format (JSON):
{
  "projekt": "<Resolve-Projektname>", "name": "<Timeline-Stamm>",
  "format": {"breite": 1920, "hoehe": 1080, "fps": 25},
  "spuren": [
    {"art": "video" | "audio", "name": "Kamera", "lueckenlos": true, "aus": false, "items": [
      {"id": "k001", "quelle": "<absoluter Pfad>", "quell_ab": 26.12, "dauer": 3.4, "start": 0.0,
       "lage": {"zoom": 1.0, "pan": 0, "tilt": 0, "crop": {"l": 0, "r": 0, "o": 0, "u": 0}, "deckkraft": 100},
       "fahrt": {"von": 1.0, "bis": 1.08, "pivot": [0.5, 0.5]},
       "uebergang": {"typ": "Cross Dissolve", "kategorie": "simple", "dauer": 0.32},
       "pegel_db": -12.0, "blende": [0.01, 0.01], "paar": "t001", "lut": "<Pfad einer .cube im LUT-Ordner>",
       "satz": 1, "rolle": "A weit", "was": "<was passiert im Bild>"}
    ]}
  ],
  "marker": [{"t": 0.0, "farbe": "Blue", "name": "S1", "notiz": "<Wortlaut>", "data": "satz:1"}],
  "regler": {"…": "frei, nur zur Dokumentation"}
}

Einheiten: Zeiten in Sekunden; ``pan``/``tilt``/``crop`` in Timeline-Pixeln mit Resolves Vorzeichen (pan + = rechts,
tilt + = oben); ``zoom`` als Faktor. ``quell_ab`` zählt in der Quelldatei, ``start`` in der Timeline.
``lut`` (nur Video): 3D-LUT auf Knoten 1 der Farbkorrektur; die Datei muss unter Resolves LUT-Ordner liegen
(``$RESOLVE_LUT_ORDNER`` oder der Standardort des Systems), der Bau ruft vorher ``RefreshLUTList``.
Die Umrechnung in Bilder geschieht NUR hier (kumulativ gerundet: Bild = round(Zeit × fps); die Dauer eines Items ist
die Differenz zweier gerundeter Kanten, so summiert sich kein Rundungsfehler und lückenlose Zeiten bleiben lückenlos).

``pruefen`` trennt Fehler (der Bau würde scheitern oder falsch liegen: Abbruch) von Hinweisen (Gestaltung: der Mensch
entscheidet). Exit 0 ohne Fehler, 1 mit Fehlern, 2 Aufruffehler.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from fractions import Fraction
from pathlib import Path

BILD_ENDUNGEN = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"}
MARKER_FARBEN = {"Blue", "Cyan", "Green", "Yellow", "Red", "Pink", "Purple", "Fuchsia", "Rose", "Lavender", "Sky",
                 "Mint", "Lemon", "Sand", "Cocoa", "Cream"}
EINBLENDUNG_ROLLEN = ("einblendung", "karte", "beleg", "grafik")


class BauplanFehler(ValueError):
    pass


def lut_ordner() -> Path:
    """Resolves LUT-Ordner: ``$RESOLVE_LUT_ORDNER`` oder der Standardort des Systems."""
    if os.environ.get("RESOLVE_LUT_ORDNER"):
        return Path(os.environ["RESOLVE_LUT_ORDNER"]).resolve()
    if sys.platform.startswith("win"):
        basis = Path(os.environ.get("ProgramData", r"C:\ProgramData"))
        return (basis / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "LUT").resolve()
    if sys.platform == "darwin":
        return Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT").resolve()
    return Path("/opt/resolve/LUT").resolve()


def bild(sekunden: float, fps: float) -> int:
    """Sekunden → Bildnummer, kaufmännisch gerundet über Brüche (0,5 immer aufwärts, kein Gleitkomma-Schlupf)."""
    return int(Fraction(str(round(float(sekunden), 6))) * Fraction(str(fps)) + Fraction(1, 2))


def kanten(item: dict, fps: float) -> tuple[int, int]:
    """Timeline-Kanten eines Items in Bildern ab Timeline-Anfang: (ab, bis) mit bis exklusiv."""
    ab = bild(item["start"], fps)
    bis = bild(item["start"] + item["dauer"], fps)
    return ab, bis


def quellbilder(item: dict, fps: float, quell_fps: float) -> tuple[int, int]:
    """Quellbereich für AppendToTimeline: (startFrame, endFrame) mit endFrame exklusiv (referenz/api-fakten.md)."""
    ab, bis = kanten(item, fps)
    q_ab = bild(item.get("quell_ab", 0.0), quell_fps)
    n = int(Fraction(bis - ab) * Fraction(str(quell_fps)) / Fraction(str(fps)) + Fraction(1, 2))
    return q_ab, q_ab + max(1, n)


def lage_aus_fenster(quelle_bh: tuple[int, int], timeline_bh: tuple[int, int],
                     fenster: tuple[float, float, float, float]) -> dict:
    """Ausschnitt [x, y, b, h] in Quellpixeln (Ursprung oben links) → zoom/pan/tilt, sodass er die Timeline füllt.

    Die Quelle liegt eingepasst in der Timeline (ganzes Bild sichtbar). Gilt so nur, wenn die eingepasste Höhe der
    Timeline-Höhe entspricht (Querformat-Quelle in Querformat-Timeline); im Hochformat wirkt Tilt mit einem Faktor
    (referenz/api-fakten.md, Abschnitt Hochformat). Weicht das Seitenverhältnis des Ausschnitts ab, füllt die
    schmalere Seite und der Rest wird beschnitten."""
    qb, qh = quelle_bh
    tb, th = timeline_bh
    x, y, b, h = fenster
    if b <= 0 or h <= 0:
        raise BauplanFehler(f"Fenster ohne Fläche: {fenster}")
    passung = min(tb / qb, th / qh)                 # Timeline-Pixel je Quellpixel bei zoom 1
    zoom = max(tb / (b * passung), th / (h * passung))
    cx, cy = x + b / 2.0, y + h / 2.0
    pan = (qb / 2.0 - cx) * passung * zoom
    tilt = (cy - qh / 2.0) * passung * zoom
    return {"zoom": round(zoom, 4), "pan": round(pan, 2), "tilt": round(tilt, 2)}


def laden(pfad: str | Path, dateien: bool = True) -> dict:
    plan = json.loads(Path(pfad).read_text(encoding="utf-8"))
    pruefen(plan, dateien=dateien)
    return plan


def schreiben(plan: dict, pfad: str | Path) -> None:
    pruefen(plan, dateien=False)
    p = Path(pfad)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")


def _lut_pruefen(iid: str, art: str, lut: str, dateien: bool, fehler: list[str]) -> None:
    if art != "video":
        fehler.append(f"{iid}: lut nur für Video ({lut})")
    elif dateien and not Path(lut).is_file():
        fehler.append(f"{iid}: lut-Datei fehlt ({lut})")
    elif dateien and not Path(lut).resolve().is_relative_to(lut_ordner()):
        fehler.append(f"{iid}: lut liegt nicht unter Resolves LUT-Ordner {lut_ordner()} ({lut})")


def pruefen(plan: dict, dateien: bool = True) -> list[str]:
    """Bricht bei Fehlern ab (BauplanFehler mit allen Befunden), gibt Hinweise als Liste zurück."""
    fehler: list[str] = []
    hinweise: list[str] = []
    for k in ("projekt", "name", "format", "spuren"):
        if k not in plan:
            fehler.append(f"Schlüssel „{k}“ fehlt")
    if fehler:
        raise BauplanFehler("; ".join(fehler))
    f = plan["format"]
    fps = f.get("fps")
    if not (f.get("breite") and f.get("hoehe") and fps):
        raise BauplanFehler("format braucht breite, hoehe, fps")
    ids: set[str] = set()
    for s_nr, spur in enumerate(plan["spuren"], 1):
        art = spur.get("art")
        name = spur.get("name", f"Spur {s_nr}")
        if art not in ("video", "audio"):
            fehler.append(f"{name}: art muss video oder audio sein")
            continue
        vorher_bis, vorher_id = None, None
        for it in sorted(spur.get("items", []), key=lambda x: x.get("start", 0.0)):
            iid = it.get("id") or f"{name}@{it.get('start')}"
            if it.get("id"):
                if it["id"] in ids:
                    fehler.append(f"id doppelt: {it['id']}")
                ids.add(it["id"])
            fehlt = [k for k in ("quelle", "dauer", "start") if k not in it]
            if fehlt:
                fehler.extend(f"{iid}: „{k}“ fehlt" for k in fehlt)
                continue
            q = Path(it["quelle"])
            if dateien and not q.is_file():
                fehler.append(f"{iid}: Quelle fehlt: {q}")
            if art == "video" and q.suffix.lower() in BILD_ENDUNGEN:
                fehler.append(f"{iid}: Standbild als Quelle ({q.name}); Resolve setzt Standbilder immer 5 s lang. "
                              "Vorher als Videoclip rendern")
            ab, bis = kanten(it, fps)
            if bis <= ab:
                fehler.append(f"{iid}: Dauer unter einem Bild ({it['dauer']} s)")
            if it.get("quell_ab", 0) < 0:
                fehler.append(f"{iid}: quell_ab negativ")
            if it.get("lut"):
                _lut_pruefen(iid, art, it["lut"], dateien, fehler)
            if vorher_bis is not None:
                if ab < vorher_bis:
                    fehler.append(f"{name}: {iid} überlappt {vorher_id} um {vorher_bis - ab} Bilder")
                elif spur.get("lueckenlos") and ab > vorher_bis:
                    fehler.append(f"{name}: Lücke von {ab - vorher_bis} Bildern vor {iid}")
            vorher_bis, vorher_id = bis, iid
            if art == "video" and str(it.get("rolle", "")).lower().startswith(EINBLENDUNG_ROLLEN) \
                    and not str(it.get("was", "")).strip():
                hinweise.append(f"{iid}: Einblendung ohne Handlung („was“ ist leer): tut die Einblendung etwas?")
            ue = it.get("uebergang")
            if ue and not (ue.get("typ") and ue.get("dauer")):
                fehler.append(f"{iid}: uebergang braucht typ und dauer")
        if spur.get("lueckenlos") and spur.get("items"):
            erster = min(spur["items"], key=lambda x: x.get("start", 0.0))
            if "start" in erster and bild(erster["start"], fps) != 0:
                fehler.append(f"{name}: beginnt nicht bei 0")
    for it in (i for s in plan["spuren"] for i in s.get("items", [])):
        if it.get("paar") and it["paar"] not in ids:
            fehler.append(f"{it.get('id')}: paar „{it['paar']}“ gibt es nicht")
    for m in plan.get("marker", []):
        if m.get("farbe", "Blue") not in MARKER_FARBEN:
            fehler.append(f"Marker {m.get('name')}: Farbe {m.get('farbe')} unbekannt")
    if fehler:
        raise BauplanFehler(f"{len(fehler)} Fehler im Bauplan:\n  " + "\n  ".join(fehler[:40]))
    return hinweise


def dauer_bilder(plan: dict) -> int:
    fps = plan["format"]["fps"]
    return max((kanten(i, fps)[1] for s in plan["spuren"] for i in s.get("items", [])), default=0)


def statistik(plan: dict, spurname: str) -> dict:
    """Schnittzahlen einer Spur: Einstellungen, Wechsel je Minute, längste Einstellung, Anteile je Rolle."""
    fps = plan["format"]["fps"]
    spur = next((s for s in plan["spuren"] if s.get("name") == spurname), None)
    if not spur or not spur.get("items"):
        return {}
    items = sorted(spur["items"], key=lambda x: x["start"])
    dauern = [(kanten(i, fps)[1] - kanten(i, fps)[0]) / fps for i in items]
    gesamt = sum(dauern)
    rollen: dict[str, float] = {}
    for i, d in zip(items, dauern, strict=True):
        rollen[i.get("rolle", "?")] = rollen.get(i.get("rolle", "?"), 0.0) + d
    laengste = max(range(len(items)), key=lambda n: dauern[n])
    return {"einstellungen": len(items), "dauer_s": round(gesamt, 2),
            "wechsel_je_minute": round((len(items) - 1) / gesamt * 60, 1) if gesamt else 0,
            "laengste_s": round(dauern[laengste], 2), "laengste_id": items[laengste].get("id"),
            "median_s": round(sorted(dauern)[len(dauern) // 2], 2),
            "anteile": {k: round(v / gesamt, 3) for k, v in sorted(rollen.items())}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Bauplan prüfen oder auswerten")
    unter = ap.add_subparsers(dest="befehl", required=True)
    p1 = unter.add_parser("pruefen", help="Fehler und Hinweise eines Bauplans")
    p1.add_argument("bauplan")
    p1.add_argument("--ohne-dateien", action="store_true", help="Quellen und LUTs nicht auf der Platte suchen")
    p2 = unter.add_parser("statistik", help="Schnittzahlen einer Spur")
    p2.add_argument("bauplan")
    p2.add_argument("--spur", required=True)
    a = ap.parse_args(argv)
    try:
        plan = json.loads(Path(a.bauplan).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"Bauplan nicht lesbar: {e}", file=sys.stderr)
        return 2
    if a.befehl == "statistik":
        print(json.dumps(statistik(plan, a.spur), ensure_ascii=False, indent=1))
        return 0
    try:
        hinweise = pruefen(plan, dateien=not a.ohne_dateien)
    except BauplanFehler as e:
        print(e)
        return 1
    for h in hinweise:
        print(f"Hinweis: {h}")
    print(f"Bauplan in Ordnung: {dauer_bilder(plan)} Bilder, {len(hinweise)} Hinweis(e).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
