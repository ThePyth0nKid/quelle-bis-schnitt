# SPDX-License-Identifier: MIT
"""Tests für den Marktplatz-Prüfer mit einem kleinen künstlichen Marktplatz."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_spec = importlib.util.spec_from_file_location("marktplatz_pruefen", Path(__file__).with_name("pruefen.py"))
pruefen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pruefen)


def _marktplatz(wurzel: Path, mcp: dict | None = None, skill_name: str = "beispiel") -> None:
    (wurzel / ".claude-plugin").mkdir(parents=True)
    (wurzel / ".claude-plugin" / "marketplace.json").write_text(json.dumps({
        "name": "probe", "owner": {"name": "x"},
        "plugins": [{"name": "eins", "description": "d", "source": "./plugins/eins", "version": "0.1.0"}],
    }), encoding="utf-8")
    plugin = wurzel / "plugins" / "eins"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text(json.dumps({
        "name": "eins", "version": "0.1.0", "description": "d", "license": "MIT"}), encoding="utf-8")
    (plugin / "skills" / "beispiel").mkdir(parents=True)
    (plugin / "skills" / "beispiel" / "SKILL.md").write_text(
        f"---\nname: {skill_name}\ndescription: Ein Beispiel.\n  Zweite Zeile.\n---\n# Text\n", encoding="utf-8")
    if mcp is not None:
        (plugin / ".mcp.json").write_text(json.dumps(mcp), encoding="utf-8")


def test_sauberer_marktplatz(tmp_path):
    _marktplatz(tmp_path, {"mcpServers": {"x": {"type": "http", "url": "https://example.org/mcp",
                                                "headers": {"Authorization": "Bearer ${user_config.api_key}"}}}})
    assert pruefen.marktplatz_pruefen(tmp_path) == []


def test_fester_schluessel_wird_gemeldet(tmp_path):
    _marktplatz(tmp_path, {"mcpServers": {"x": {"type": "http", "url": "https://example.org/mcp",
                                                "headers": {"Authorization": "Bearer abc123"}}}})
    fehler = pruefen.marktplatz_pruefen(tmp_path)
    assert len(fehler) == 1 and "festen Wert" in fehler[0]


def test_skillname_muss_ordner_entsprechen(tmp_path):
    _marktplatz(tmp_path, skill_name="anders")
    fehler = pruefen.marktplatz_pruefen(tmp_path)
    assert any("Ordner" in f for f in fehler)


def test_fehlender_ordner_und_nicht_eingetragenes_plugin(tmp_path):
    _marktplatz(tmp_path)
    (tmp_path / "plugins" / "zwei").mkdir()
    daten = json.loads((tmp_path / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    daten["plugins"].append({"name": "drei", "description": "d", "source": "./plugins/drei"})
    (tmp_path / ".claude-plugin" / "marketplace.json").write_text(json.dumps(daten), encoding="utf-8")
    fehler = pruefen.marktplatz_pruefen(tmp_path)
    assert any("drei" in f and "fehlt" in f for f in fehler)
    assert any("zwei" in f and "nicht im Marktplatz" in f for f in fehler)


def test_frontmatter_mehrzeilig():
    fm = pruefen.frontmatter("---\nname: a\ndescription: >\n  eins\n  zwei\n---\nText")
    assert fm["name"] == "a"
    assert "eins zwei" in fm["description"]
