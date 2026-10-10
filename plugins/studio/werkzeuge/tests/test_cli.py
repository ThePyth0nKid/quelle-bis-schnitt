# SPDX-License-Identifier: MIT
"""Der Befehl `studio`: Version, Hilfe je Unterbefehl, Fehler ohne Konfiguration."""
from __future__ import annotations

import subprocess
import sys

import pytest
from studio_werkzeuge import __version__
from studio_werkzeuge.cli import main, parser_bauen

UNTERBEFEHLE = [["konfig", "zeigen"], ["konfig", "vorlage"], ["klick-check"], ["mastern"], ["paar"],
                ["inbox-ordnen"], ["waechter"], ["obs-modus"], ["prompter", "saetze"], ["prompter", "einspielen"],
                ["transkript"]]


def test_version(capsys):
    with pytest.raises(SystemExit) as e:
        main(["--version"])
    assert e.value.code == 0 and __version__ in capsys.readouterr().out


@pytest.mark.parametrize("befehl", UNTERBEFEHLE, ids=lambda b: " ".join(b))
def test_hilfe_je_unterbefehl(befehl, capsys):
    with pytest.raises(SystemExit) as e:
        main([*befehl, "--help"])
    assert e.value.code == 0 and "usage: studio" in capsys.readouterr().out


def test_alle_unterbefehle_sind_eingetragen():
    namen = set(parser_bauen()._subparsers._group_actions[0].choices)
    assert namen == {"konfig", "klick-check", "mastern", "paar", "inbox-ordnen", "waechter", "obs-modus", "prompter",
                     "transkript"}


@pytest.mark.parametrize("befehl", [["waechter", "--einmal"], ["obs-modus", "status"], ["paar"],
                                    ["prompter", "einspielen", "--probe"]])
def test_ohne_konfiguration_klare_meldung(befehl, capsys):
    assert main(befehl) == 2
    fehler = capsys.readouterr().err
    assert "FEHLER:" in fehler and "studio konfig vorlage" in fehler


def test_konfig_vorlage_und_zeigen(tmp_path, capsys):
    ziel = tmp_path / "studio.toml"
    assert main(["konfig", "vorlage", "--ziel", str(ziel)]) == 0
    assert main(["konfig", "vorlage", "--ziel", str(ziel)]) == 2              # nie überschreiben
    assert main(["--konfig", str(ziel), "konfig", "zeigen"]) == 0
    aus = capsys.readouterr().out
    assert "noch Platzhalter" in aus and str(ziel.resolve()) in aus


def test_als_modul_aufrufbar():
    r = subprocess.run([sys.executable, "-m", "studio_werkzeuge", "--version"], capture_output=True, text=True)
    assert r.returncode == 0 and __version__ in r.stdout
