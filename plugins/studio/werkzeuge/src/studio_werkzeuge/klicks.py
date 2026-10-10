# SPDX-License-Identifier: MIT
"""Knackser (Aussetzer) im Ton zählen: eine Implementierung für `studio klick-check` und `studio paar`.

Ein Klick ist ein Sprung von Abtastwert zu Abtastwert, der den lokalen Pegel (±50 ms) um das ``faktor``-fache übersteigt
und absolut über ``minimum`` liegt; Treffer innerhalb von 20 ms zählen als einer. Der Anfang und das Ende der Datei
(je 50 ms) zählen nicht. Schwellen und Ampel: eigene Messung, Methode in docs/messungen/studio-klicks.md; alle Werte
sind in ``[klicks]`` der Konfiguration einstellbar.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from scipy.signal import fftconvolve

from studio_werkzeuge import medien
from studio_werkzeuge.fehler import StudioFehler
from studio_werkzeuge.konfig import Konfig

RATE = 48_000
FAKTOR = 12.0                 # eigene Messung, docs/messungen/studio-klicks.md
MINIMUM = 0.03                # absolut (≈ −30 dBFS), damit Rauschen in Pausen nicht zählt
GRUEN_UNTER = 5.0             # Klicks je Minute; eigene Messung, docs/messungen/studio-klicks.md
ROT_UEBER = 15.0
PEGEL_BEZUG_DBFS = -23.0      # Anhaltspunkt nach EBU R 128 (−23 LUFS); einstellbar, nicht gemessen
PEGEL_TOLERANZ_DB = 10.0      # einstellbare Voreinstellung, nicht gemessen
AAC_BLOCK_MS = 1024 / 48_000 * 1000   # 21,33 ms: ein AAC-Block bei 48 kHz


def klick_orte(x: np.ndarray, rate: int = RATE, faktor: float = FAKTOR, minimum: float = MINIMUM) -> np.ndarray:
    """Positionen (Abtastwerte) der Klicks; je Gruppe (Treffer binnen 20 ms) der stärkste Sprung."""
    if len(x) < rate:
        return np.array([], dtype=int)
    d = np.abs(np.diff(np.asarray(x, dtype=np.float32)))
    fenster = int(0.05 * rate)
    kern = np.ones(2 * fenster + 1, dtype=np.float32) / (2 * fenster + 1)
    lokal = np.sqrt(np.maximum(fftconvolve(d ** 2, kern, mode="same"), 0.0)) + 1e-6
    treffer = np.flatnonzero((d > faktor * lokal) & (d > minimum))
    treffer = treffer[(treffer > fenster) & (treffer < len(d) - fenster)]
    if not treffer.size:
        return np.array([], dtype=int)
    gruppen = np.split(treffer, np.where(np.diff(treffer) > 0.02 * rate)[0] + 1)
    return np.array([int(g[np.argmax(d[g])]) for g in gruppen])


def klicks_zaehlen(x: np.ndarray, rate: int = RATE, faktor: float = FAKTOR, minimum: float = MINIMUM) -> int:
    return int(len(klick_orte(x, rate, faktor, minimum)))


def im_aac_raster(orte: np.ndarray, rate: int = RATE) -> int:
    """Wie viele Klick-Abstände im Raster eines oder zweier AAC-Blöcke liegen. Viele davon deuten auf beschädigte
    Tonblöcke im Aufnahmeweg, nicht auf das Mikrofon."""
    if len(orte) < 2:
        return 0
    ab = np.diff(orte) / rate * 1000
    return int(np.sum(np.abs(ab - AAC_BLOCK_MS) < 0.4) + np.sum(np.abs(ab - 2 * AAC_BLOCK_MS) < 0.4))


@dataclass(frozen=True)
class Befund:
    datei: str
    klicks: int
    dauer_s: float
    je_minute: float
    im_aac_raster: int
    pegel_dbfs: float
    ampel: str
    hinweise: tuple[str, ...]


def ampel(je_minute: float, gruen_unter: float = GRUEN_UNTER, rot_ueber: float = ROT_UEBER) -> str:
    if je_minute < gruen_unter:
        return "GRÜN"
    return "GELB" if je_minute <= rot_ueber else "ROT"


def bewerten(x: np.ndarray, name: str, schwellen: dict, rate: int = RATE) -> Befund:
    """Klicks je Minute, Ampel und Pegel-Hinweis für ein Signal."""
    orte = klick_orte(x, rate, schwellen["faktor"], schwellen["minimum"])
    dauer = len(x) / rate
    je_min = len(orte) / dauer * 60 if dauer > 0 else 0.0
    rms = float(np.sqrt(np.mean(np.square(x, dtype=np.float64)))) if len(x) else 0.0
    pegel = 20 * math.log10(rms) if rms > 0 else float("-inf")
    hinweise = []
    if abs(pegel - schwellen["pegel_bezug_dbfs"]) > schwellen["pegel_toleranz_db"]:
        hinweise.append(f"Pegel {pegel:.1f} dBFS liegt weit vom Bezug {schwellen['pegel_bezug_dbfs']:.0f} dBFS: "
                        "Eingangsverstärkung prüfen (zu leise heißt später viel anheben, zu laut heißt Übersteuern).")
    return Befund(name, int(len(orte)), round(dauer, 2), round(je_min, 2), im_aac_raster(orte, rate), round(pegel, 1),
                  ampel(je_min, schwellen["gruen_unter"], schwellen["rot_ueber"]), tuple(hinweise))


def schwellen_aus(konfig: Konfig) -> dict:
    return {
        "faktor": konfig.zahl("klicks", "faktor", FAKTOR),
        "minimum": konfig.zahl("klicks", "minimum", MINIMUM),
        "gruen_unter": konfig.zahl("klicks", "gruen_unter", GRUEN_UNTER),
        "rot_ueber": konfig.zahl("klicks", "rot_ueber", ROT_UEBER),
        "pegel_bezug_dbfs": konfig.zahl("klicks", "pegel_bezug_dbfs", PEGEL_BEZUG_DBFS),
        "pegel_toleranz_db": konfig.zahl("klicks", "pegel_toleranz_db", PEGEL_TOLERANZ_DB),
    }


def einrichten(unter) -> None:
    p = unter.add_parser("klick-check", help="Knackser im Ton zählen (Ampel je Minute)",
                         description="Zählt Klicks je Minute in Ton- oder Videodateien. Ampel: unter 5 grün, 5–15 "
                                     "gelb, über 15 rot (einstellbar in [klicks]). Rot heißt: nicht schneiden, "
                                     "erst den Aufnahmeweg prüfen.")
    p.add_argument("dateien", nargs="+", type=Path, metavar="DATEI")
    p.add_argument("--json", action="store_true", help="Ergebnis als JSON")
    p.set_defaults(ausfuehren=ausfuehren, braucht_konfig=False)


def ausfuehren(args, konfig: Konfig) -> int:
    schwellen = schwellen_aus(konfig)
    befunde, fehler = [], []
    for datei in args.dateien:
        try:
            x = medien.audio_laden(datei, RATE)
        except StudioFehler as e:
            fehler.append({"datei": str(datei), "fehler": str(e)})
            continue
        if len(x) < RATE:
            fehler.append({"datei": str(datei), "fehler": "kein Ton oder kürzer als 1 s"})
            continue
        befunde.append(bewerten(x, str(datei), schwellen))
    if args.json:
        print(json.dumps({"befunde": [asdict(b) for b in befunde], "fehler": fehler}, ensure_ascii=False, indent=1))
    else:
        for b in befunde:
            print(f"{b.ampel:4s} {b.je_minute:6.1f} Klicks je Minute ({b.klicks} in {b.dauer_s:.0f} s, davon "
                  f"{b.im_aac_raster} im AAC-Raster) · Pegel {b.pegel_dbfs:.1f} dBFS · {b.datei}")
            for h in b.hinweise:
                print(f"     · {h}")
        for f in fehler:
            print(f"FEHLER {f['datei']}: {f['fehler']}")
    if fehler:
        return 2
    return 1 if any(b.ampel == "ROT" for b in befunde) else 0
