#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Wartet, bis Resolve von außen antwortet, und meldet Version, Seite und offenes Projekt.

    <resolve-python> -u resolve_bereit.py [--warten 120] [--projekt <Name>]

Exit 0 erreichbar, 1 nach Ablauf der Wartezeit nicht. Mit --projekt wird das Projekt geladen (angelegt, wenn es fehlt).
Nach einem Absturz: Resolve neu starten, dann dieses Skript; erst danach wieder bauen.

Warum erst warten: Wer ``scriptapp()`` abfragt, während Resolve noch startet, nimmt ihm den eigenen Skriptserver weg;
die Instanz ist danach von außen taub und muss neu gestartet werden (referenz/api-fakten.md, F4). Deshalb wartet das
Skript zuerst passiv, bis der Skriptserver-Prozess ``fuscript`` läuft.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # F3
import resolve_api as ra  # noqa: E402

SKRIPTSERVER = "fuscript"


def prozess_laeuft(name: str) -> bool:
    """Läuft ein Prozess dieses Namens? Windows über tasklist, sonst über pgrep."""
    try:
        if sys.platform.startswith("win"):
            aus = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {name}.exe", "/NH"],
                                 capture_output=True, text=True, errors="replace", timeout=15).stdout
            return f"{name}.exe".lower() in aus.lower()
        return subprocess.run(["pgrep", "-x", name], capture_output=True, timeout=15).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def warten_bis_bereit(warten_s: float, verbinden=ra.verbinden, laeuft=prozess_laeuft, schlaf=time.sleep,
                      uhr=time.time):
    """Gibt das Resolve-Objekt zurück oder None nach Ablauf der Wartezeit."""
    ende = uhr() + warten_s
    while uhr() < ende and not laeuft(SKRIPTSERVER):
        schlaf(2)
    if uhr() >= ende:
        return None
    schlaf(3)
    while uhr() < ende:
        try:
            r = verbinden()
            if r.GetProjectManager() is not None:
                return r
        except ra.ResolveFehler:
            pass
        schlaf(2)
    return None


def main(argv: list[str] | None = None) -> int:
    ra.utf8()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--warten", type=float, default=120.0, help="Sekunden (Vorgabe 120)")
    ap.add_argument("--projekt")
    a = ap.parse_args(argv)
    r = warten_bis_bereit(a.warten)
    if r is None:
        print(f"Resolve antwortet nach {a.warten:.0f} s nicht. Läuft das Skript mit dem Python von Resolve "
              "(F20), und ist externes Skripten auf Local gestellt?")
        return 1
    pm = r.GetProjectManager()
    if a.projekt:
        try:
            ra.projekt_holen(r, a.projekt)
        except ra.ResolveFehler as e:
            print(f"Resolve: {e} (F21)")
            return 1
    proj = pm.GetCurrentProject()
    print(f"{r.GetProductName()} {r.GetVersionString()} | Seite {r.GetCurrentPage()} | Projekt "
          f"{proj.GetName() if proj else None} | Timelines {proj.GetTimelineCount() if proj else 0}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
