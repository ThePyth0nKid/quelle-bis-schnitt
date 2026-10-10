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


def test_mischwert_mit_platzhalter_wird_gemeldet(tmp_path):
    _marktplatz(tmp_path, {"mcpServers": {"x": {"type": "http", "url": "https://example.org/mcp",
                                                "headers": {"Authorization": "Bearer geheim123 ${x}"}}}})
    assert any("festen Wert" in f for f in pruefen.marktplatz_pruefen(tmp_path))


def test_schluessel_in_url_und_args_wird_gemeldet(tmp_path):
    _marktplatz(tmp_path, {"mcpServers": {
        "a": {"type": "http", "url": "https://example.org/mcp?apiKey=abc123"},
        "b": {"command": "server", "args": ["--token=abc123", "--author=Erika"]},
        "c": {"type": "http", "url": "https://example.org/mcp?apiKey=${user_config.k}&client=x"},
    }})
    fehler = pruefen.marktplatz_pruefen(tmp_path)
    assert len(fehler) == 2
    assert any("a.url" in f for f in fehler) and any("b.args" in f for f in fehler)


def test_quelle_ausserhalb_des_repos(tmp_path):
    _marktplatz(tmp_path / "repo")
    datei = tmp_path / "repo" / ".claude-plugin" / "marketplace.json"
    daten = json.loads(datei.read_text(encoding="utf-8"))
    daten["plugins"][0]["source"] = "./../draussen"
    datei.write_text(json.dumps(daten), encoding="utf-8")
    (tmp_path / "draussen").mkdir()
    assert any("aus dem Repo heraus" in f for f in pruefen.marktplatz_pruefen(tmp_path / "repo"))


def test_quellordner_mit_anderem_namen(tmp_path):
    _marktplatz(tmp_path)
    (tmp_path / "plugins" / "eins").rename(tmp_path / "plugins" / "eins-ordner")
    datei = tmp_path / ".claude-plugin" / "marketplace.json"
    daten = json.loads(datei.read_text(encoding="utf-8"))
    daten["plugins"][0]["source"] = "./plugins/eins-ordner"
    datei.write_text(json.dumps(daten), encoding="utf-8")
    assert pruefen.marktplatz_pruefen(tmp_path) == []


def test_frontmatter_mit_bom_und_crlf():
    fm = pruefen.frontmatter("\ufeff---\r\nname: a\r\ndescription: b\r\n---\r\nText")
    assert fm == {"name": "a", "description": "b"}
    assert pruefen.frontmatter("----\nname: a\n---\n") == {}


def test_falsche_json_typen_brechen_nicht_ab(tmp_path):
    _marktplatz(tmp_path, {"mcpServers": {"x": "kein objekt"}})
    datei = tmp_path / ".claude-plugin" / "marketplace.json"
    daten = json.loads(datei.read_text(encoding="utf-8"))
    daten["plugins"].append("kein objekt")
    datei.write_text(json.dumps(daten), encoding="utf-8")
    fehler = pruefen.marktplatz_pruefen(tmp_path)
    assert any("kein Objekt" in f for f in fehler)
