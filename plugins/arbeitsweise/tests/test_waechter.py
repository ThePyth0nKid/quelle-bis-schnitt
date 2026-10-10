# SPDX-License-Identifier: MIT
"""Tests für den Deploy-Wächter mit temporären Git-Repos und temporärem Lock-Ordner."""
from __future__ import annotations

import builtins
import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

_PFAD = Path(__file__).resolve().parents[1] / "werkzeuge" / "deploy_waechter" / "waechter.py"
_spec = importlib.util.spec_from_file_location("deploy_waechter_waechter", _PFAD)
w = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = w  # dataclasses braucht das Modul in sys.modules
_spec.loader.exec_module(w)

GRUND = "erster Deploy dieses Projekts"
HAENGT = "Strang hängt fest"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def _commit(repo: Path, datei: str, inhalt: str, nachricht: str) -> str:
    pfad = repo / datei
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(inhalt, encoding="utf-8")
    _git(repo, "add", datei)
    _git(repo, "commit", "-q", "-m", nachricht)
    return _git(repo, "rev-parse", "HEAD")


class _Terminal:
    """Ersatz für sys.stdin: ein Mensch sitzt am Terminal."""

    def isatty(self) -> bool:
        return True


@pytest.fixture
def mensch(monkeypatch):
    """Simuliert einen Menschen am Terminal, der die Rückfrage beantwortet (Standard: ja)."""
    antworten = {"text": "ja"}
    monkeypatch.setattr(sys, "stdin", _Terminal())
    monkeypatch.setattr(builtins, "input", lambda _frage="": antworten["text"])
    return antworten


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "beispiel-repo"
    r.mkdir()
    _git(r, "init", "-q")
    _git(r, "symbolic-ref", "HEAD", "refs/heads/main")
    # Identität nur in diesem Test-Repo
    _git(r, "config", "user.name", "Erika Mustermann")
    _git(r, "config", "user.email", "erika@example.org")
    _git(r, "config", "commit.gpgsign", "false")
    _commit(r, "LIESMICH.txt", "start\n", "start")
    return r


@pytest.fixture
def konfig_datei(tmp_path: Path) -> Path:
    datei = tmp_path / "waechter.toml"
    datei.write_text(
        'projekt = "musterhafen"\n'
        '[lock]\nordner = "locks"\n'
        '[log]\ndatei = "deploy-log.md"\n'
        '[obermenge]\nausgeliefert_refs = ["refs/tags/ausgeliefert/*"]\n'
        '[obermenge.arten.backend]\npfade = ["backend"]\n'
        '[obermenge.arten.app]\npfade = ["app"]\n',
        encoding="utf-8")
    return datei


@pytest.fixture
def konfig(konfig_datei: Path, repo: Path):
    return w.konfig_laden(konfig_datei, repo)


@pytest.fixture
def zustand(tmp_path: Path, monkeypatch) -> Path:
    """Benutzer-Zustandsordner in den Testordner umlenken (Windows und POSIX)."""
    ordner = tmp_path / "zustand"
    monkeypatch.setenv("LOCALAPPDATA", str(ordner))
    monkeypatch.setenv("XDG_STATE_HOME", str(ordner))
    return w.zustand_ordner()


def _main(konfig_datei: Path, repo: Path, *args: str) -> int:
    return w.main(["--konfig", str(konfig_datei), "--repo", str(repo), *args])


def _log(konfig_datei: Path) -> str:
    pfad = konfig_datei.parent / "deploy-log.md"
    return pfad.read_text(encoding="utf-8") if pfad.exists() else ""


# ── Konfiguration ──────────────────────────────────────────────────────────


def test_konfig_relative_pfade_und_arten(konfig, konfig_datei):
    assert konfig.projekt == "musterhafen"
    assert konfig.lock_ordner == (konfig_datei.parent / "locks").resolve()
    assert konfig.log_datei == (konfig_datei.parent / "deploy-log.md").resolve()
    assert konfig.verwaist_minuten == 90
    assert konfig.arten == {"backend": ["backend"], "app": ["app"]}


def test_konfig_aus_git_wurzel_mit_hinweis(repo, zustand, capsys):
    (repo / ".deploy-waechter.toml").write_text('projekt = "Nordlicht Analytik"\n[lock]\nordner = "locks"\n',
                                               encoding="utf-8")
    unterordner = repo / "unter"
    unterordner.mkdir()
    k = w.konfig_laden(None, unterordner)
    assert k.quelle == repo / ".deploy-waechter.toml"
    assert "Konfiguration aus dem Repo" in capsys.readouterr().err
    assert w.projekt_bestimmen(None, k, unterordner) == "nordlicht-analytik"
    assert k.lock_ordner == (zustand / "locks").resolve()


@pytest.mark.parametrize("wert", ["~/locks", "$HOME/locks", "%APPDATA%/locks", "../../anderswo", "/tmp/locks",
                                  "C:/locks"])
def test_repo_konfig_darf_nicht_aus_dem_zustandsordner(repo, zustand, wert):
    (repo / ".deploy-waechter.toml").write_text(f'[log]\ndatei = "{wert}"\n', encoding="utf-8")
    with pytest.raises(w.WaechterFehler):
        w.konfig_laden(None, repo)


def test_beispiel_konfig_ist_als_repo_konfig_gueltig(repo, zustand):
    beispiel = _PFAD.with_name("deploy-waechter.beispiel.toml").read_text(encoding="utf-8")
    (repo / ".deploy-waechter.toml").write_text(beispiel, encoding="utf-8")
    k = w.konfig_laden(None, repo)
    assert k.projekt == "mein-projekt" and set(k.arten) == {"backend", "app"}
    assert k.lock_ordner.is_relative_to(zustand.resolve())


def test_explizite_konfig_darf_absolute_pfade(tmp_path, repo):
    ziel = (tmp_path / "irgendwo" / "log.md").resolve()
    datei = tmp_path / "eigen.toml"
    datei.write_text(f'[log]\ndatei = "{ziel.as_posix()}"\n', encoding="utf-8")
    assert w.konfig_laden(datei, repo).log_datei == ziel


@pytest.mark.parametrize("inhalt", [
    "[lock]\nverwaist_nach_minuten = -5\n",
    "[lock]\nverwaist_nach_minuten = true\n",
    'lock = "x"\n',
    '[obermenge]\nlog_als_quelle = "false"\n',
    "[obermenge]\ntage = 0\n",
    "[obermenge.arten]\nbackend = 3\n",
    '[obermenge.arten.backend]\npfade = "backend"\n',
    "projekt = 7\n",
])
def test_konfig_typfehler(tmp_path, repo, inhalt):
    falsch = tmp_path / "falsch.toml"
    falsch.write_text(inhalt, encoding="utf-8")
    with pytest.raises(w.WaechterFehler):
        w.konfig_laden(falsch, repo)


def test_konfig_fehlt(tmp_path, repo):
    with pytest.raises(w.WaechterFehler):
        w.konfig_laden(tmp_path / "gibt-es-nicht.toml", repo)


def test_projekt_ohne_konfig_aus_git_wurzel(repo, monkeypatch):
    monkeypatch.delenv("DEPLOY_PROJEKT", raising=False)
    assert w.projekt_bestimmen(None, w.Konfig(quelle=None), repo) == "beispiel-repo"
    monkeypatch.setenv("DEPLOY_PROJEKT", "Freie Stadt Musterhafen")
    assert w.projekt_bestimmen(None, w.Konfig(quelle=None), repo) == "freie-stadt-musterhafen"


@pytest.mark.parametrize(("name", "erwartet"), [
    ("CON", "p-con"), ("nul.txt", "p-nul.txt"), ("Com1", "p-com1"), ("lpt9", "p-lpt9"),
    ("console", "console"), ("com10", "com10"), ("..", "unbekannt"),
])
def test_reservierte_namen(name, erwartet):
    assert w.normalisieren(name) == erwartet


# ── Lock ───────────────────────────────────────────────────────────────────


def test_lock_holen_belegt_und_freigeben(konfig, capsys):
    assert w.lock_holen(konfig, "musterhafen", "strang-a", "backend") == 0
    assert w.lock_holen(konfig, "musterhafen", "strang-b", "app") == 1
    assert "LOCK-BELEGT" in capsys.readouterr().out
    assert w.lock_status(konfig, "musterhafen", alle=False) == 1
    assert w.lock_freigeben(konfig, "musterhafen", "strang-b") == 1  # fremder Lock
    assert w.lock_freigeben(konfig, "musterhafen", "strang-a", "ok") == 0
    assert w.lock_status(konfig, "musterhafen", alle=False) == 0
    assert w.lock_holen(konfig, "musterhafen", "strang-b", "app") == 0


def test_andere_projekte_sperren_nicht(konfig, capsys):
    assert w.lock_holen(konfig, "musterhafen", "strang-a", "backend") == 0
    assert w.lock_holen(konfig, "nordlicht", "strang-b", "backend") == 0
    assert "kein Konflikt" in capsys.readouterr().out
    assert w.lock_status(konfig, "", alle=True) == 1
    w.lock_freigeben(konfig, "musterhafen", "strang-a")
    w.lock_freigeben(konfig, "nordlicht", "strang-b")
    assert w.lock_status(konfig, "", alle=True) == 0


def test_verwaister_lock_wird_uebernommen(konfig):
    t0 = time.time() - 3600 * 3
    assert w.lock_holen(konfig, "musterhafen", "abgestuerzt", "backend", jetzt=t0) == 0
    assert w.lock_holen(konfig, "musterhafen", "neu", "backend", jetzt=t0 + 89 * 60) == 1
    assert w.lock_holen(konfig, "musterhafen", "neu", "backend", jetzt=t0 + 91 * 60) == 0
    assert "VERWAISTER LOCK" in konfig.log_datei.read_text(encoding="utf-8")
    assert not list(konfig.lock_ordner.glob("*.stale.*"))


def test_verwaisung_abschaltbar(konfig):
    konfig.verwaist_minuten = 0
    t0 = time.time() - 86400 * 7
    assert w.lock_holen(konfig, "musterhafen", "alt", "backend", jetzt=t0) == 0
    assert w.lock_holen(konfig, "musterhafen", "neu", "backend") == 1


def test_leere_lockdatei_bleibt_belegt_bis_zur_verwaisung(konfig):
    konfig.lock_ordner.mkdir(parents=True)
    pfad = w.lock_pfad(konfig, "musterhafen")
    pfad.write_text("", encoding="utf-8")
    assert w.lock_holen(konfig, "musterhafen", "b", "backend") == 1  # wird gerade angelegt
    zehn_minuten = time.time() - 600
    os.utime(pfad, (zehn_minuten, zehn_minuten))
    assert w.lock_holen(konfig, "musterhafen", "b", "backend") == 1  # defekt, aber noch nicht verwaist
    zwei_stunden = time.time() - 7200
    os.utime(pfad, (zwei_stunden, zwei_stunden))
    assert w.lock_holen(konfig, "musterhafen", "b", "backend") == 0
    assert "DEFEKTER LOCK" in konfig.log_datei.read_text(encoding="utf-8")


@pytest.mark.parametrize("daten", [{"halter": "a"}, {"halter": "a", "epoch": "abc"}, {"halter": "a", "epoch": None},
                                   {"halter": "a", "epoch": True}])
def test_fehlendes_oder_falsches_epoch_ist_defekt(konfig, daten):
    konfig.lock_ordner.mkdir(parents=True)
    w.lock_pfad(konfig, "musterhafen").write_text(json.dumps(daten), encoding="utf-8")
    assert w.lock_zustand(w.lock_pfad(konfig, "musterhafen"), 90, time.time()).art == "defekt"
    assert w.lock_holen(konfig, "musterhafen", "b", "backend") == 1
    assert w.lock_status(konfig, "musterhafen", alle=False) == 1


def test_unlesbare_datei_gilt_in_status_und_release_als_belegt(konfig):
    konfig.lock_ordner.mkdir(parents=True)
    pfad = w.lock_pfad(konfig, "musterhafen")
    pfad.write_text("{kaputt", encoding="utf-8")
    assert w.lock_status(konfig, "musterhafen", alle=False) == 1
    assert w.lock_status(konfig, "", alle=True) == 1
    assert w.lock_freigeben(konfig, "musterhafen", "irgendwer") == 1
    assert pfad.exists()


def test_gleichzeitige_uebernahme_hoechstens_ein_gewinner(konfig):
    konfig.lock_ordner.mkdir(parents=True)
    pfad = w.lock_pfad(konfig, "musterhafen")
    pfad.write_text(json.dumps({"halter": "alt", "bereich": "backend", "epoch": time.time() - 3 * 3600}),
                    encoding="utf-8")
    anzahl = 8
    start = threading.Barrier(anzahl)
    ergebnisse: dict[str, int] = {}

    def strang(name: str) -> None:
        start.wait()
        ergebnisse[name] = w.lock_holen(konfig, "musterhafen", name, "backend")

    faeden = [threading.Thread(target=strang, args=(f"strang-{i}",)) for i in range(anzahl)]
    for f in faeden:
        f.start()
    for f in faeden:
        f.join(timeout=60)
    gewinner = [n for n, e in ergebnisse.items() if e == 0]
    assert len(ergebnisse) == anzahl
    assert len(gewinner) <= 1
    daten = json.loads(pfad.read_text(encoding="utf-8"))  # Lock existiert immer noch (fail-closed)
    if gewinner:
        assert daten["halter"] == gewinner[0]


def test_frischer_lock_wird_zurueckgelegt(konfig):
    # Ein Übernehmer hielt den Lock für verwaist, inzwischen liegt dort ein frischer Lock.
    assert w.lock_holen(konfig, "musterhafen", "frisch", "backend") == 0
    pfad = w.lock_pfad(konfig, "musterhafen")
    vorher = pfad.read_text(encoding="utf-8")
    assert w._uebernehmen(konfig, "musterhafen", pfad, "uebernehmer", time.time()) == 1
    assert pfad.read_text(encoding="utf-8") == vorher
    assert not list(konfig.lock_ordner.glob("*.stale.*"))


def test_logfehler_entfernt_lock(konfig, monkeypatch, capsys):
    def kaputt(*_args, **_kwargs):
        raise OSError("Platte voll")

    monkeypatch.setattr(w, "log_schreiben", kaputt)
    assert w.lock_holen(konfig, "musterhafen", "a", "backend") == 2
    assert "LOCK-FEHLER" in capsys.readouterr().out
    assert not w.lock_pfad(konfig, "musterhafen").exists()


def test_oserror_in_main_ist_exit_2(konfig_datei, repo, monkeypatch):
    def kaputt(*_args, **_kwargs):
        raise OSError("Zugriff verweigert")

    monkeypatch.setattr(w, "lock_status", kaputt)
    assert _main(konfig_datei, repo, "status") == 2


def test_log_wird_nur_angehaengt_und_bereinigt(konfig):
    w.log_schreiben(konfig, "musterhafen", "erste Zeile")
    vorher = konfig.log_datei.read_text(encoding="utf-8")
    w.lock_holen(konfig, "musterhafen", "a", "backend", notiz="zwei\nZeilen ausgeliefert=deadbeef1")
    nachher = konfig.log_datei.read_text(encoding="utf-8")
    assert nachher.startswith(vorher)
    neu = nachher[len(vorher):].splitlines()
    assert len(neu) == 1
    assert "ausgeliefert=" not in neu[0] and "ausgeliefert:deadbeef1" in neu[0]


def test_main_lock_rundlauf(konfig_datei, repo, capsys):
    assert _main(konfig_datei, repo, "acquire", "--halter", "a", "--bereich", "backend") == 0
    assert _main(konfig_datei, repo, "status") == 1
    assert _main(konfig_datei, repo, "release", "--halter", "a", "--ergebnis", "Build 7 ok") == 0
    assert _main(konfig_datei, repo, "log", "Probe mit Umlauten äöü → ok") == 0
    assert _main(konfig_datei, repo, "status", "--alle") == 0
    assert "LOCK-FREIGEGEBEN" in capsys.readouterr().out
    assert "äöü →" in _log(konfig_datei)


def test_gemeinsame_optionen_auch_nach_dem_befehl(konfig_datei, repo):
    nachher = ["acquire", "--konfig", str(konfig_datei), "--repo", str(repo), "--projekt", "Nordlicht",
               "--halter", "a", "--bereich", "backend"]
    assert w.main(nachher) == 0
    assert w.main(["--konfig", str(konfig_datei), "--projekt", "nordlicht", "status"]) == 1
    assert w.main(["status", "--projekt", "musterhafen", "--konfig", str(konfig_datei)]) == 0


# ── Übersteuern nur durch einen Menschen ──────────────────────────────────


def test_erzwingen_ohne_terminal_verweigert(konfig_datei, repo):
    _main(konfig_datei, repo, "acquire", "--halter", "strang-a", "--bereich", "backend")
    assert _main(konfig_datei, repo, "release", "--halter", "mensch", "--erzwingen") == 2  # Grund fehlt
    assert _main(konfig_datei, repo, "release", "--halter", "mensch", "--erzwingen", "--grund", "kurz") == 2
    assert _main(konfig_datei, repo, "release", "--halter", "mensch", "--erzwingen", "--grund", HAENGT) == 1
    assert _main(konfig_datei, repo, "status") == 1  # Lock steht noch


def test_erzwingen_mit_mensch(konfig_datei, repo, mensch):
    _main(konfig_datei, repo, "acquire", "--halter", "strang-a", "--bereich", "backend")
    mensch["text"] = "nein"
    assert _main(konfig_datei, repo, "release", "--halter", "mensch", "--erzwingen", "--grund", HAENGT) == 1
    mensch["text"] = "ja"
    assert _main(konfig_datei, repo, "release", "--halter", "mensch", "--erzwingen", "--grund", HAENGT) == 0
    log = _log(konfig_datei)
    assert "ERZWUNGEN durch mensch (Benutzer " in log and "Strang hängt fest" in log


# ── Obermenge ──────────────────────────────────────────────────────────────


def test_obermenge_ohne_basis_sperrt(konfig_datei, repo):
    assert _main(konfig_datei, repo, "obermenge") == 1
    assert _main(konfig_datei, repo, "obermenge", "--trotzdem") == 2  # Grund fehlt
    assert _main(konfig_datei, repo, "obermenge", "--trotzdem", "--grund", GRUND) == 1  # kein Terminal
    assert "OBERMENGE ÜBERSTEUERT" not in _log(konfig_datei)


def test_obermenge_trotzdem_mit_mensch(konfig_datei, repo, mensch):
    mensch["text"] = "vielleicht"
    assert _main(konfig_datei, repo, "obermenge", "--trotzdem", "--grund", GRUND) == 1
    mensch["text"] = "ja"
    assert _main(konfig_datei, repo, "obermenge", "--trotzdem", "--grund", GRUND) == 0
    log = _log(konfig_datei)
    assert "OBERMENGE ÜBERSTEUERT" in log and GRUND in log and "Benutzer " in log


def test_obermenge_ausgelieferter_stand_ist_vorfahre(konfig_datei, repo):
    stand = _commit(repo, "backend/a.py", "a = 1\n", "backend a")
    assert _main(konfig_datei, repo, "release", "--halter", "a", "--ausgeliefert", stand) == 0
    _commit(repo, "backend/b.py", "b = 1\n", "backend b")
    assert _main(konfig_datei, repo, "obermenge") == 0


def test_obermenge_fehlender_stand_sperrt(konfig_datei, repo, konfig, mensch):
    basis = _git(repo, "rev-parse", "HEAD")
    stand = _commit(repo, "backend/a.py", "a = 1\n", "backend a")
    _main(konfig_datei, repo, "release", "--halter", "a", "--ausgeliefert", stand)
    # Ein Strang baut aus einem Branch, der die ausgelieferte Arbeit nicht kennt
    _git(repo, "checkout", "-q", "-b", "alter-zweig", basis)
    _commit(repo, "backend/c.py", "c = 1\n", "eigene Arbeit")
    befund = w.obermenge_pruefen(repo, konfig, "musterhafen")
    assert [c for c, _ in befund.hart] == [stand]
    assert _main(konfig_datei, repo, "obermenge") == 1
    # Ein Mensch nimmt den Stand bewusst aus
    assert _main(konfig_datei, repo, "obermenge", "--bewusst-draussen", stand, "--grund", "zurückgezogen, Fehler") == 0
    assert _main(konfig_datei, repo, "obermenge") == 0


def test_bewusst_draussen_ohne_terminal_verweigert(konfig_datei, repo):
    stand = _commit(repo, "backend/a.py", "a = 1\n", "backend a")
    assert _main(konfig_datei, repo, "obermenge", "--bewusst-draussen", stand, "--grund", "zurückgezogen, Fehler") == 1
    assert "bewusst-draussen=" not in _log(konfig_datei)


def test_obermenge_art_zaehlt_nur_eigene_pfade(konfig_datei, repo, konfig):
    basis = _git(repo, "rev-parse", "HEAD")
    stand = _commit(repo, "app/screen.txt", "neu\n", "nur app")
    _main(konfig_datei, repo, "release", "--halter", "a", "--ausgeliefert", stand)
    _git(repo, "checkout", "-q", "-b", "backend-zweig", basis)
    _commit(repo, "backend/x.py", "x = 1\n", "backend")
    befund = w.obermenge_pruefen(repo, konfig, "musterhafen", art="backend")
    assert befund.ohne_wirkung == [stand] and not befund.blockiert
    assert _main(konfig_datei, repo, "obermenge", "--art", "backend") == 0
    assert _main(konfig_datei, repo, "obermenge", "--art", "app") == 1
    assert _main(konfig_datei, repo, "obermenge", "--art", "gibt-es-nicht") == 2


def test_obermenge_tags_als_quelle(repo, konfig):
    konfig.log_als_quelle = False
    stand = _commit(repo, "backend/a.py", "a = 1\n", "backend a")
    _git(repo, "tag", "ausgeliefert/backend-1", stand)
    _commit(repo, "backend/b.py", "b = 1\n", "weiter")
    befund = w.obermenge_pruefen(repo, konfig, "musterhafen")
    assert befund.ok == [stand] and not befund.blockiert


def test_obermenge_arbeitskopie(konfig_datei, repo):
    stand = _commit(repo, "backend/a.py", "a = 1\n", "backend a")
    _main(konfig_datei, repo, "release", "--halter", "a", "--ausgeliefert", stand)
    (repo / "backend" / "halbfertig.py").write_text("x = ?\n", encoding="utf-8")
    assert _main(konfig_datei, repo, "obermenge") == 1
    assert _main(konfig_datei, repo, "obermenge", "--art", "app") == 0  # nicht in den App-Pfaden
    assert _main(konfig_datei, repo, "obermenge", "--ohne-arbeitskopie") == 0


def test_obermenge_weiche_liste(repo, konfig):
    stand = _commit(repo, "backend/a.py", "a = 1\n", "backend a")
    _git(repo, "tag", "ausgeliefert/1", stand)
    _git(repo, "checkout", "-q", "-b", "nebenarbeit")
    _commit(repo, "backend/n.py", "n = 1\n", "neben")
    _git(repo, "checkout", "-q", "main")
    befund = w.obermenge_pruefen(repo, konfig, "musterhafen")
    assert befund.weich == [("nebenarbeit", 1)]
    assert not befund.blockiert


def test_eingeschleuster_marker_zaehlt_nicht(konfig_datei, repo, konfig):
    fremd = _commit(repo, "backend/a.py", "a = 1\n", "a")
    _git(repo, "reset", "-q", "--hard", "HEAD~1")
    _main(konfig_datei, repo, "log", f"Notiz ausgeliefert={fremd}")
    staende, _ = w.ausgelieferte_staende(repo, konfig, "musterhafen", time.time())
    assert staende == []
