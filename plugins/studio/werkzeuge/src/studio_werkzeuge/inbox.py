# SPDX-License-Identifier: MIT
"""Lose Rohdateien der Inbox nach Takes ordnen (`studio inbox-ordnen`): A und B desselben Takes in EINEN Ordner.

Die Rohdateien kommen nach ``<ziel>/<JJJJ-MM-TT hh-mm-ss>/Roh/``, dieselbe Form wie beim Wächter; ein vorhandener
Take-Ordner (auch „… PRUEFEN“) wird benutzt. Nur Umbenennen, nie überschreiben. Dateien, die jünger als
``--min-alter`` sind, bleiben liegen (frische Takes sortiert der Wächter selbst ein). Jeder Lauf schreibt ein Protokoll
``<inbox>/_geordnet-<zeit>.tsv``; ``--zurueck <tsv>`` dreht ihn zurück, aber nur für Pfade in Inbox und Ziel.
"""
from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from studio_werkzeuge.fehler import StudioFehler
from studio_werkzeuge.konfig import Konfig
from studio_werkzeuge.paar import MAX_STEMPEL_ABSTAND_S, Benennung, abstand_s, benennung_aus, ordner_name, take_ordner
from studio_werkzeuge.sicher import umbenennen

MIN_ALTER_S = 3600.0


def plan_ordnen(namen: list[str], benennung: Benennung | None = None) -> tuple[dict[str, str], list[str]]:
    """Dateiname → Take-Stempel (B übernimmt den Stempel ihres A, gegenseitig nächster innerhalb 2 s); dazu die
    Namen ohne Kamera-Muster."""
    benennung = benennung or Benennung()
    a_st, b_st, fremd = {}, {}, []
    for n in namen:
        t = benennung.treffer(n)
        if not t:
            fremd.append(n)
            continue
        (a_st if t[0] == "A" else b_st)[t[1]] = n
    zuordnung = {n: s for s, n in a_st.items()}
    for s_b, n_b in b_st.items():
        naechstes_a = min(a_st, key=lambda s: abstand_s(s, s_b), default=None)
        passt = (naechstes_a is not None and abstand_s(naechstes_a, s_b) <= MAX_STEMPEL_ABSTAND_S
                 and min(b_st, key=lambda s: abstand_s(s, naechstes_a)) == s_b)
        zuordnung[n_b] = naechstes_a if passt else s_b
    return zuordnung, fremd


def zielordner(stempel: str, ziel: Path) -> Path:
    return take_ordner(ziel, ordner_name(stempel)) / "Roh"


def _liegt_in(pfad: Path, basis: Path) -> bool:
    try:
        pfad.resolve().relative_to(basis.resolve())
        return True
    except ValueError:
        return False


def zurueckdrehen(protokoll: Path, inbox: Path, ziel: Path) -> tuple[int, int, list[str]]:
    """Ein Protokoll rückwärts abarbeiten. Erlaubt ist nur: alter Ort direkt in der Inbox, neuer Ort in
    ``<ziel>/<Take>/Roh/``. Nie überschreiben. Danach werden leer gewordene ``Roh/`` und Take-Ordner entfernt, nie
    mehr. Rückgabe: (zurück, gesamt, Fehler)."""
    zeilen = [z.split("\t") for z in protokoll.read_text(encoding="utf-8-sig").splitlines() if "\t" in z]
    zurueck, fehler, geleert = 0, [], set()
    for teile in reversed(zeilen):
        if len(teile) != 2:
            fehler.append(f"kaputte Zeile: {teile!r}")
            continue
        alt, neu = Path(teile[0]), Path(teile[1])
        if alt.parent.resolve() != inbox.resolve() or neu.parent.name != "Roh" or not _liegt_in(neu, ziel):
            fehler.append(f"{neu}: liegt nicht in Inbox/Ziel, wird nicht angefasst")
            continue
        try:
            umbenennen(neu, alt)
            zurueck += 1
            geleert.add(neu.parent)
        except OSError as e:
            fehler.append(f"{neu}: {e}")
    for roh in geleert:
        for ordner in (roh, roh.parent):
            if ordner.is_dir() and ordner.resolve() != ziel.resolve() and not any(ordner.iterdir()):
                ordner.rmdir()
    return zurueck, len(zeilen), fehler


def einrichten(unter) -> None:
    p = unter.add_parser("inbox-ordnen", help="Lose Rohdateien paarweise in Take-Ordner legen (mit Rücklauf)",
                         description=__doc__.split("\n\n")[0])
    p.add_argument("ordner", nargs="?", type=Path, metavar="INBOX", help="ohne: [pfade] inbox")
    p.add_argument("--ziel", type=Path, help="ohne: [pfade] ziel bzw. die Inbox")
    p.add_argument("--min-alter", type=float, default=MIN_ALTER_S, help="jüngere Dateien bleiben liegen (Sekunden)")
    p.add_argument("--zurueck", type=Path, metavar="TSV", help="Protokoll eines Laufs: alles an den alten Platz")
    p.add_argument("--probe", action="store_true", help="nur zeigen, nichts verschieben")
    p.set_defaults(ausfuehren=ausfuehren, braucht_konfig=False)


def ausfuehren(args, konfig: Konfig) -> int:
    inbox = args.ordner or konfig.pfad_wert("pfade", "inbox")
    ziel = args.ziel or konfig.pfad_wert("pfade", "ziel", inbox)
    if args.zurueck:
        zurueck, gesamt, fehler = zurueckdrehen(args.zurueck, inbox, ziel)
        print(f"{zurueck}/{gesamt} Dateien zurückgelegt.")
        for f in fehler:
            print(f"  nicht zurückgelegt: {f}")
        return 0 if not fehler else 1
    if not inbox.is_dir():
        raise StudioFehler(f"Inbox gibt es nicht: {inbox}")
    benennung = benennung_aus(konfig)
    dateien = sorted(q for q in inbox.iterdir() if q.is_file())
    zuordnung, fremd = plan_ordnen([d.name for d in dateien], benennung)
    jetzt = time.time()
    plan, zu_jung = [], []
    for d in dateien:
        if d.name not in zuordnung:
            continue
        if jetzt - d.stat().st_mtime < args.min_alter:
            zu_jung.append(d.name)
            continue
        plan.append((d, zielordner(zuordnung[d.name], ziel) / d.name))
    kollision = [(q, z) for q, z in plan if z.exists()]
    ordner = sorted({z.parent for _, z in plan})
    print(f"{len(dateien)} Dateien in {inbox}: {len(plan)} einzuordnen in {len(ordner)} Take-Ordner, "
          f"{len(zu_jung)} zu jung, {len(fremd)} ohne Kamera-Muster, {len(kollision)} Namenskollisionen")
    for o in ordner:
        print(f"  {o.parent.name}/{o.name}: {', '.join(sorted(q.name for q, z in plan if z.parent == o))}")
    if kollision:
        print("ABBRUCH: Ziel existiert schon:", *[str(z) for _, z in kollision], sep="\n  ")
        return 2
    if args.probe:
        print("Probe: nichts verschoben.")
        return 0
    protokoll = inbox / f"_geordnet-{datetime.now():%Y%m%d-%H%M%S}.tsv"
    with protokoll.open("x", encoding="utf-8") as f:
        for q, z in plan:
            z.parent.mkdir(parents=True, exist_ok=True)
            umbenennen(q, z)
            f.write(f"{q}\t{z}\n")
            f.flush()
    nachher = sum(1 for _, z in plan if z.is_file())
    print(f"verschoben: {nachher}/{len(plan)}; Protokoll (zum Zurückdrehen): {protokoll}")
    return 0 if nachher == len(plan) else 1
