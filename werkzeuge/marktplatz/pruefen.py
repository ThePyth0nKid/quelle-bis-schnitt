#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prüft den Marktplatz auf Dinge, die ``claude plugin validate`` nicht prüft.

* Jeder Eintrag in ``.claude-plugin/marketplace.json`` zeigt auf einen vorhandenen Ordner mit ``plugin.json``.
* Name und Version stimmen zwischen Marktplatz-Eintrag und ``plugin.json`` überein.
* Jeder Skill hat Frontmatter mit ``name`` (gleich dem Ordnernamen) und ``description``.
* Jeder Agent hat ``name`` und ``description``, jeder Befehl eine ``description``.
* Jede ``.mcp.json`` ist gültiges JSON mit ``mcpServers`` und trägt keine Schlüssel im Klartext:
  Werte in ``headers`` und ``env`` müssen leer sein oder ``${user_config.…}`` / ``${…}`` verwenden.

Nur Standardbibliothek. Aufruf: ``python werkzeuge/marktplatz/pruefen.py [--wurzel PFAD]``.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PLATZHALTER = re.compile(r"^(.*\$\{[A-Za-z_][A-Za-z0-9_.]*\}.*)?$")


def frontmatter(text: str) -> dict[str, str]:
    """Liest einfaches YAML-Frontmatter (``schluessel: wert``, auch mehrzeilig eingerückt)."""
    if not text.startswith("---"):
        return {}
    ende = text.find("\n---", 3)
    if ende < 0:
        return {}
    werte: dict[str, str] = {}
    letzter = None
    for zeile in text[3:ende].splitlines():
        if not zeile.strip():
            continue
        if zeile[:1] in (" ", "\t") and letzter:
            werte[letzter] = (werte[letzter] + " " + zeile.strip()).strip()
            continue
        schluessel, trenner, wert = zeile.partition(":")
        if trenner:
            letzter = schluessel.strip()
            wert = wert.strip()
            werte[letzter] = "" if wert in (">", "|", ">-", "|-") else wert.strip('"').strip("'")
    return werte


def _json(pfad: Path, fehler: list[str]) -> dict | None:
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as fehlerobjekt:
        fehler.append(f"{pfad}: kein gültiges JSON ({fehlerobjekt})")
        return None


def plugin_pruefen(ordner: Path, eintrag: dict, fehler: list[str]) -> None:
    manifest_pfad = ordner / ".claude-plugin" / "plugin.json"
    if not manifest_pfad.is_file():
        fehler.append(f"{ordner}: .claude-plugin/plugin.json fehlt")
        return
    manifest = _json(manifest_pfad, fehler)
    if manifest is None:
        return
    if manifest.get("name") != eintrag.get("name"):
        fehler.append(f"{manifest_pfad}: name {manifest.get('name')!r} passt nicht zum "
                      f"Marktplatz-Eintrag {eintrag.get('name')!r}")
    if "version" in eintrag and eintrag["version"] != manifest.get("version"):
        fehler.append(f"{manifest_pfad}: version weicht vom Marktplatz-Eintrag ab")
    for feld in ("version", "description", "license"):
        if not manifest.get(feld):
            fehler.append(f"{manifest_pfad}: Feld {feld!r} fehlt")

    for skill in sorted((ordner / "skills").glob("*/SKILL.md")):
        fm = frontmatter(skill.read_text(encoding="utf-8"))
        if fm.get("name") != skill.parent.name:
            fehler.append(f"{skill}: name {fm.get('name')!r} muss dem Ordner {skill.parent.name!r} entsprechen")
        if not fm.get("description"):
            fehler.append(f"{skill}: description fehlt")
    for agent in sorted((ordner / "agents").glob("*.md")):
        fm = frontmatter(agent.read_text(encoding="utf-8"))
        for feld in ("name", "description"):
            if not fm.get(feld):
                fehler.append(f"{agent}: {feld} fehlt")
    for befehl in sorted((ordner / "commands").glob("*.md")):
        if not frontmatter(befehl.read_text(encoding="utf-8")).get("description"):
            fehler.append(f"{befehl}: description fehlt")

    mcp = ordner / ".mcp.json"
    if mcp.is_file():
        daten = _json(mcp, fehler)
        if daten is not None:
            server = daten.get("mcpServers")
            if not isinstance(server, dict) or not server:
                fehler.append(f"{mcp}: mcpServers fehlt oder ist leer")
            else:
                for name, eintrag_mcp in server.items():
                    for bereich in ("headers", "env"):
                        for schluessel, wert in (eintrag_mcp.get(bereich) or {}).items():
                            if not PLATZHALTER.match(str(wert)):
                                fehler.append(f"{mcp}: {name}.{bereich}.{schluessel} enthält einen festen Wert; "
                                              "Schlüssel nur über ${user_config.…} oder Umgebungsvariablen")


def marktplatz_pruefen(wurzel: Path) -> list[str]:
    fehler: list[str] = []
    datei = wurzel / ".claude-plugin" / "marketplace.json"
    daten = _json(datei, fehler)
    if daten is None:
        return fehler
    namen = set()
    for eintrag in daten.get("plugins", []):
        name = eintrag.get("name")
        if name in namen:
            fehler.append(f"{datei}: Plugin {name!r} doppelt")
        namen.add(name)
        quelle = eintrag.get("source")
        if not isinstance(quelle, str) or not quelle.startswith("./"):
            fehler.append(f"{datei}: {name}: source muss ein relativer Pfad wie ./plugins/<name> sein")
            continue
        ordner = (wurzel / quelle).resolve()
        if not ordner.is_dir():
            fehler.append(f"{datei}: {name}: Ordner {quelle} fehlt")
            continue
        plugin_pruefen(ordner, eintrag, fehler)
    # Ordner unter plugins/, die im Marktplatz fehlen
    for ordner in sorted((wurzel / "plugins").glob("*/")):
        if ordner.is_dir() and ordner.name not in namen:
            fehler.append(f"plugins/{ordner.name}: nicht im Marktplatz eingetragen")
    return fehler


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--wurzel", type=Path, default=Path(__file__).resolve().parents[2])
    a = p.parse_args(argv)
    fehler = marktplatz_pruefen(a.wurzel)
    for zeile in fehler:
        print(zeile)
    if fehler:
        print(f"\n{len(fehler)} Fehler.", file=sys.stderr)
        return 1
    print("Marktplatz in Ordnung.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
