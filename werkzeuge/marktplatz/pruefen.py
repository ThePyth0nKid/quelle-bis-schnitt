#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prüft den Marktplatz auf Dinge, die ``claude plugin validate`` nicht prüft.

* Jeder Eintrag in ``.claude-plugin/marketplace.json`` zeigt auf einen vorhandenen Ordner innerhalb des Repos
  mit ``plugin.json``. Nur relative Quellen (``./plugins/<name>``) sind erlaubt; Git- oder URL-Quellen gehören
  nicht in diesen Marktplatz.
* Name und Version stimmen zwischen Marktplatz-Eintrag und ``plugin.json`` überein.
* Jeder Skill hat Frontmatter mit ``name`` (gleich dem Ordnernamen) und ``description``.
* Jeder Agent hat ``name`` und ``description``, jeder Befehl eine ``description``.
* Jede ``.mcp.json`` ist gültiges JSON mit ``mcpServers`` und trägt keine Schlüssel im Klartext:
  Werte in ``headers`` und ``env`` sind leer oder bestehen nur aus einem Platzhalter (``${user_config.x}``,
  ``${VAR}``, optional mit ``Bearer ``/``Basic ``/``Token `` davor); ``url`` und ``args`` enthalten keine
  schlüsselartigen Parameter mit festem Wert.

Nur Standardbibliothek. Aufruf: ``python werkzeuge/marktplatz/pruefen.py [--wurzel PFAD]``.
Exit-Code 0 = in Ordnung, 1 = Fehler gefunden, 2 = Aufruffehler.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Ganzer Wert = ein Platzhalter, höchstens mit Schema-Wort davor.
NUR_PLATZHALTER = re.compile(r"^(?:(?:Bearer|Basic|Token) )?\$\{[A-Za-z_][A-Za-z0-9_.]*\}$")
# Schlüsselartige Parameter in URLs und Argumenten, z. B. ?apiKey=…, --token=…
SCHLUESSEL_PARAMETER = re.compile(
    r"(?i)(?:^|[?&;\s-])(?:[a-z_]*(?:key|token|secret|passw(?:or)?d)[a-z_]*|auth(?:orization)?)=([^&;\s]+)")
FRONTMATTER = re.compile(r"^---\r?\n(.*?)\r?\n---\r?(?:\n|$)", re.DOTALL)


def frontmatter(text: str) -> dict[str, str]:
    """Liest einfaches YAML-Frontmatter (``schluessel: wert``, auch mehrzeilig eingerückt)."""
    treffer = FRONTMATTER.match(text.lstrip("﻿"))
    if not treffer:
        return {}
    werte: dict[str, str] = {}
    letzter = None
    for zeile in treffer.group(1).splitlines():
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


def _text(pfad: Path, fehler: list[str]) -> str | None:
    try:
        return pfad.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as fehlerobjekt:
        fehler.append(f"{pfad}: nicht lesbar ({fehlerobjekt})")
        return None


def _json(pfad: Path, fehler: list[str]) -> dict | None:
    text = _text(pfad, fehler)
    if text is None:
        return None
    try:
        daten = json.loads(text)
    except json.JSONDecodeError as fehlerobjekt:
        fehler.append(f"{pfad}: kein gültiges JSON ({fehlerobjekt})")
        return None
    if not isinstance(daten, dict):
        fehler.append(f"{pfad}: oberste Ebene muss ein Objekt sein")
        return None
    return daten


def _fester_schluessel(wert: str) -> bool:
    """True, wenn ein schlüsselartiger Parameter einen festen Wert statt eines Platzhalters trägt."""
    return any(not m.group(1).startswith("${") for m in SCHLUESSEL_PARAMETER.finditer(wert))


def mcp_pruefen(mcp: Path, fehler: list[str]) -> None:
    daten = _json(mcp, fehler)
    if daten is None:
        return
    server = daten.get("mcpServers")
    if not isinstance(server, dict) or not server:
        fehler.append(f"{mcp}: mcpServers fehlt oder ist leer")
        return
    for name, eintrag in server.items():
        if not isinstance(eintrag, dict):
            fehler.append(f"{mcp}: {name} ist kein Objekt")
            continue
        for bereich in ("headers", "env"):
            werte = eintrag.get(bereich) or {}
            if not isinstance(werte, dict):
                fehler.append(f"{mcp}: {name}.{bereich} ist kein Objekt")
                continue
            for schluessel, wert in werte.items():
                if str(wert) and not NUR_PLATZHALTER.match(str(wert)):
                    fehler.append(f"{mcp}: {name}.{bereich}.{schluessel} enthält einen festen Wert; "
                                  "Schlüssel nur über ${user_config.…} oder ${VARIABLE}")
        if _fester_schluessel(str(eintrag.get("url", ""))):
            fehler.append(f"{mcp}: {name}.url enthält einen schlüsselartigen Parameter mit festem Wert")
        args = eintrag.get("args") or []
        if not isinstance(args, list):
            fehler.append(f"{mcp}: {name}.args ist keine Liste")
        elif any(_fester_schluessel(str(a)) for a in args):
            fehler.append(f"{mcp}: {name}.args enthält einen schlüsselartigen Parameter mit festem Wert")


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
        fm = frontmatter(_text(skill, fehler) or "")
        if fm.get("name") != skill.parent.name:
            fehler.append(f"{skill}: name {fm.get('name')!r} muss dem Ordner {skill.parent.name!r} entsprechen")
        if not fm.get("description"):
            fehler.append(f"{skill}: description fehlt")
    for agent in sorted((ordner / "agents").glob("*.md")):
        fm = frontmatter(_text(agent, fehler) or "")
        for feld in ("name", "description"):
            if not fm.get(feld):
                fehler.append(f"{agent}: {feld} fehlt")
    for befehl in sorted((ordner / "commands").glob("*.md")):
        if not frontmatter(_text(befehl, fehler) or "").get("description"):
            fehler.append(f"{befehl}: description fehlt")

    mcp = ordner / ".mcp.json"
    if mcp.is_file():
        mcp_pruefen(mcp, fehler)


def marktplatz_pruefen(wurzel: Path) -> list[str]:
    fehler: list[str] = []
    wurzel = wurzel.resolve()
    datei = wurzel / ".claude-plugin" / "marketplace.json"
    daten = _json(datei, fehler)
    if daten is None:
        return fehler
    eintraege = daten.get("plugins", [])
    if not isinstance(eintraege, list):
        return fehler + [f"{datei}: plugins muss eine Liste sein"]
    namen: set[str] = set()
    quellordner: set[Path] = set()
    for eintrag in eintraege:
        if not isinstance(eintrag, dict):
            fehler.append(f"{datei}: Plugin-Eintrag ist kein Objekt")
            continue
        name = eintrag.get("name")
        if name in namen:
            fehler.append(f"{datei}: Plugin {name!r} doppelt")
        namen.add(name)
        quelle = eintrag.get("source")
        if not isinstance(quelle, str) or not quelle.startswith("./"):
            fehler.append(f"{datei}: {name}: source muss ein relativer Pfad wie ./plugins/<name> sein")
            continue
        ordner = (wurzel / quelle).resolve()
        if not ordner.is_relative_to(wurzel):
            fehler.append(f"{datei}: {name}: source {quelle} zeigt aus dem Repo heraus")
            continue
        if not ordner.is_dir():
            fehler.append(f"{datei}: {name}: Ordner {quelle} fehlt")
            continue
        quellordner.add(ordner)
        plugin_pruefen(ordner, eintrag, fehler)
    # Ordner unter plugins/, auf die kein Eintrag zeigt
    for ordner in sorted(p.resolve() for p in (wurzel / "plugins").glob("*/") if p.is_dir()):
        if ordner not in quellordner:
            fehler.append(f"plugins/{ordner.name}: nicht im Marktplatz eingetragen")
    return fehler


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--wurzel", type=Path, default=Path(__file__).resolve().parents[2])
    a = p.parse_args(argv)
    if not (a.wurzel / ".claude-plugin" / "marketplace.json").is_file():
        print(f"FEHLER: {a.wurzel} enthält keine .claude-plugin/marketplace.json", file=sys.stderr)
        return 2
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
