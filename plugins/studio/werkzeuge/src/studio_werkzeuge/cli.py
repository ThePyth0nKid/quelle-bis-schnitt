# SPDX-License-Identifier: MIT
"""Der Befehl `studio` mit seinen Unterbefehlen. Exit: 0 gut · 1 Befund (rot, Ziel verfehlt) · 2 Fehler."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from studio_werkzeuge import (
    __version__,
    inbox,
    klicks,
    konfig,
    mastern,
    obs_modus,
    paar,
    prompter,
    transkript,
    waechter,
)
from studio_werkzeuge.fehler import StudioFehler

BESCHREIBUNG = """Werkzeuge für Dreh und Schnitt.

Konfiguration: studio.toml, gesucht in $STUDIO_KONFIG, ./studio.toml und im Benutzer-Konfigordner.
Vorlage anlegen: studio konfig vorlage --ziel studio.toml
"""


def _konfig_einrichten(unter) -> None:
    p = unter.add_parser("konfig", help="Konfiguration zeigen oder Vorlage anlegen")
    pu = p.add_subparsers(dest="konfig_befehl", required=True, metavar="BEFEHL")
    z = pu.add_parser("zeigen", help="gefundene Datei und wirksame Werte (Geheimnisse maskiert)")
    z.set_defaults(ausfuehren=lambda a, k: (print(konfig.zeigen(k)), 0)[1], braucht_konfig=False)
    v = pu.add_parser("vorlage", help="studio.beispiel.toml als Ausgangspunkt schreiben")
    v.add_argument("--ziel", type=Path, default=Path(konfig.DATEINAME), help="Zieldatei (ohne: ./studio.toml)")
    v.add_argument("--ueberschreiben", action="store_true", help="eine vorhandene Datei ersetzen")

    def vorlage(a, k) -> int:
        ziel = konfig.vorlage_schreiben(a.ziel, a.ueberschreiben)
        print(f"Vorlage geschrieben: {ziel}\nJetzt die <Platzhalter> ersetzen; prüfen mit: studio konfig zeigen")
        return 0

    v.set_defaults(ausfuehren=vorlage, braucht_konfig=False)


def parser_bauen() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="studio", description=BESCHREIBUNG,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"studio {__version__}")
    p.add_argument("--konfig", type=Path, help="diese studio.toml statt der Suche verwenden")
    unter = p.add_subparsers(dest="befehl", required=True, metavar="BEFEHL")
    _konfig_einrichten(unter)
    for modul in (klicks, mastern, paar, inbox, waechter, obs_modus, prompter, transkript):
        modul.einrichten(unter)
    return p


def main(argv: list[str] | None = None) -> int:
    for strom in (sys.stdout, sys.stderr):
        if strom is not None and hasattr(strom, "reconfigure"):
            strom.reconfigure(encoding="utf-8", errors="replace")
    args = parser_bauen().parse_args(argv)
    try:
        k = konfig.laden(args.konfig)
        if getattr(args, "braucht_konfig", False) and k.pfad is None:
            raise StudioFehler(k.fehlt_text(f"eine Konfiguration für `studio {args.befehl}`"))
        return int(args.ausfuehren(args, k))
    except StudioFehler as e:
        print(f"FEHLER: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
