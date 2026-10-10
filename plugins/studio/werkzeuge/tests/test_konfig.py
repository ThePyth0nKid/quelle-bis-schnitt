# SPDX-License-Identifier: MIT
"""Konfiguration: Suche, Platzhalter, Vorlage, Maskierung."""
from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from studio_werkzeuge import konfig
from studio_werkzeuge.fehler import KonfigFehler

WERKZEUGE = Path(__file__).resolve().parents[1]


def test_ohne_datei_leere_konfig_und_klare_meldung():
    k = konfig.laden()
    assert k.pfad is None and k.daten == {}
    assert k.wert("klicks", "faktor", 12.0) == 12.0
    with pytest.raises(KonfigFehler, match="Keine Konfiguration gefunden") as e:
        k.wert("pfade", "inbox")
    assert "studio konfig vorlage" in str(e.value)


def test_suchreihenfolge(tmp_path, monkeypatch):
    eigen = tmp_path / "eigen.toml"
    eigen.write_text('[pfade]\ninbox = "a"\n', encoding="utf-8")
    (Path.cwd() / "studio.toml").write_text('[pfade]\ninbox = "b"\n', encoding="utf-8")
    assert konfig.laden().wert("pfade", "inbox") == "b"                      # ./studio.toml
    monkeypatch.setenv("STUDIO_KONFIG", str(eigen))
    assert konfig.laden().wert("pfade", "inbox") == "a"                      # $STUDIO_KONFIG zuerst
    monkeypatch.setenv("STUDIO_KONFIG", str(tmp_path / "fehlt.toml"))
    with pytest.raises(KonfigFehler, match="STUDIO_KONFIG"):
        konfig.laden()


def test_benutzer_konfigordner(monkeypatch, tmp_path):
    (Path.cwd() / "studio.toml").unlink(missing_ok=True)
    ordner = konfig.benutzer_konfigordner()
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "studio.toml").write_text('[pfade]\ninbox = "c"\n', encoding="utf-8")
    assert konfig.laden().wert("pfade", "inbox") == "c"


def test_platzhalter_gilt_als_nicht_eingetragen(tmp_path, hilfe):
    k = hilfe.konfig_aus(tmp_path, '[pfade]\ninbox = "<inbox>"\nziel = ""\n[obs_modus.modi.lang]\nbitrate = 20000\n')
    with pytest.raises(KonfigFehler, match="Platzhalter"):
        k.wert("pfade", "inbox")
    assert k.wert("pfade", "ziel", "x") == "x"
    assert k.wert("obs_modus.modi.lang", "bitrate") == 20000
    assert k.abschnitt("obs_modus.modi") == {"lang": {"bitrate": 20000}}


def test_kaputtes_toml(tmp_path, hilfe):
    with pytest.raises(KonfigFehler, match="kein gültiges TOML"):
        hilfe.konfig_aus(tmp_path, "[pfade\n")


def test_vorlage_ueberschreibt_nie(tmp_path):
    ziel = tmp_path / "studio.toml"
    konfig.vorlage_schreiben(ziel)
    ziel.write_text("eigenes", encoding="utf-8")
    with pytest.raises(KonfigFehler, match="nichts überschrieben|Nichts überschrieben"):
        konfig.vorlage_schreiben(ziel)
    assert ziel.read_text(encoding="utf-8") == "eigenes"
    konfig.vorlage_schreiben(ziel, ueberschreiben=True)
    assert "[pfade]" in ziel.read_text(encoding="utf-8")


def test_vorlage_ist_gueltig_und_ohne_pfade():
    text = konfig.vorlage_text()
    assert text == (WERKZEUGE / "studio.beispiel.toml").read_text(encoding="utf-8")   # Kopie im Ordner gleich
    daten = tomllib.loads(text)
    k = konfig.Konfig(daten, Path("studio.toml"))
    with pytest.raises(KonfigFehler):
        k.wert("pfade", "inbox")                        # Platzhalter: muss eingetragen werden
    with pytest.raises(KonfigFehler):
        k.wert("prompter", "datenordner")
    assert k.wert("mastern", "ziel_lufs") == -14.0
    assert "passwort" not in {s.lower() for s in daten["obs"]}   # nur der Name der Variable steht drin


def test_maskiert_und_zeigen(tmp_path, monkeypatch, hilfe):
    k = hilfe.konfig_aus(tmp_path, '[obs]\npasswort = "geheim"\npasswort_umgebung = "OBS_PW"\n[x]\napi_key = "abc"\n')
    m = konfig.maskiert(k.daten)
    assert m["obs"]["passwort"] == "***" and m["x"]["api_key"] == "***" and m["obs"]["passwort_umgebung"] == "OBS_PW"
    monkeypatch.delenv("OBS_PW", raising=False)
    text = konfig.zeigen(k)
    assert "geheim" not in text and "Variable NICHT gesetzt" in text
    monkeypatch.setenv("OBS_PW", "x")
    assert "(Variable gesetzt)" in konfig.zeigen(k)


def test_typen_werden_geprueft(tmp_path, hilfe):
    k = hilfe.konfig_aus(tmp_path, '[paar]\ncq = "achtzehn"\ngegenprobe = "ja"\n[mastern]\nziel_lufs = true\n'
                                   '[obs]\nport = 4455\nhost = 7\n')
    for aufruf in (lambda: k.ganzzahl("paar", "cq"), lambda: k.wahrheit("paar", "gegenprobe"),
                   lambda: k.zahl("mastern", "ziel_lufs"), lambda: k.text("obs", "host")):
        with pytest.raises(KonfigFehler, match="muss"):
            aufruf()
    assert k.ganzzahl("obs", "port") == 4455 and k.zahl("obs", "port") == 4455.0


def test_bom_und_maskierung_und_hostwarnung(tmp_path, hilfe):
    datei = tmp_path / "studio.toml"
    datei.write_bytes("\ufeff[obs]\nhost = \"192.0.2.1\"\nkennwort = \"x\"\n[transkript.fern]\n"
                      "befehl = [\"ssh\", \"rechner\"]\n".encode())
    k = konfig.laden(datei)
    text = konfig.zeigen(k)
    assert "[… 2 Argumente …]" in text and "rechner" not in text and "'***'" in text
    assert "nicht dieser Rechner" in text
