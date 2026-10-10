# SPDX-License-Identifier: MIT
"""Sichere Grundbausteine: nie überschreiben, Laufwerkswechsel mit geprüfter Kopie, Sperre, Prozess lebt?"""
from __future__ import annotations

import errno
import os
import subprocess
import sys

import pytest
from studio_werkzeuge import sicher
from studio_werkzeuge.fehler import StudioFehler


def test_umbenennen_ueberschreibt_nie(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_bytes(b"a")
    b.write_bytes(b"b")
    with pytest.raises(FileExistsError):
        sicher.umbenennen(a, b)
    assert a.read_bytes() == b"a" and b.read_bytes() == b"b"
    sicher.umbenennen(a, tmp_path / "c")
    assert (tmp_path / "c").read_bytes() == b"a" and not a.exists()


def _laufwerkswechsel(monkeypatch):
    echt = sicher.umbenennen

    def wechsel(quelle, ziel):
        if not str(ziel).endswith(".part") and not str(quelle).endswith(".part"):
            raise OSError(errno.EXDEV, "anderes Laufwerk")
        echt(quelle, ziel)

    monkeypatch.setattr(sicher, "umbenennen", wechsel)


def test_verschieben_ueber_laufwerke_kopiert_prueft_und_loescht_erst_danach(tmp_path, monkeypatch):
    _laufwerkswechsel(monkeypatch)
    quelle, ziel = tmp_path / "q.mp4", tmp_path / "z" / "q.mp4"
    ziel.parent.mkdir()
    quelle.write_bytes(b"x" * 1000)
    sicher.verschieben(quelle, ziel)
    assert ziel.read_bytes() == b"x" * 1000 and not quelle.exists() and not (ziel.parent / "q.mp4.part").exists()


def test_verschieben_bricht_ab_bei_vorhandenem_ziel_oder_part(tmp_path, monkeypatch):
    _laufwerkswechsel(monkeypatch)
    quelle, ziel = tmp_path / "q.mp4", tmp_path / "z.mp4"
    quelle.write_bytes(b"neu")
    ziel.write_bytes(b"alt, andere Groesse")
    with pytest.raises(FileExistsError):
        sicher.verschieben(quelle, ziel)
    ziel.unlink()
    (tmp_path / "z.mp4.part").write_bytes(b"rest")
    with pytest.raises(FileExistsError):
        sicher.verschieben(quelle, ziel)
    assert quelle.read_bytes() == b"neu"                                     # Quelle bleibt in jedem Fehlerfall


def test_verschieben_falsche_groesse_raeumt_auf_und_behaelt_quelle(tmp_path, monkeypatch):
    _laufwerkswechsel(monkeypatch)
    monkeypatch.setattr(sicher.shutil, "copyfile", lambda q, z: z.write_bytes(b"kurz"))
    quelle = tmp_path / "q.mp4"
    quelle.write_bytes(b"x" * 100)
    with pytest.raises(OSError):
        sicher.verschieben(quelle, tmp_path / "z.mp4")
    assert quelle.is_file() and not (tmp_path / "z.mp4").exists() and not (tmp_path / "z.mp4.part").exists()


def test_sperre_ist_exklusiv(tmp_path):
    pfad = tmp_path / "s" / "bau.lock"
    with sicher.Sperre(pfad, "Test"):
        zweite = sicher.Sperre(pfad)
        assert not zweite.versuchen()
        with pytest.raises(StudioFehler, match="Sperre"):
            with sicher.Sperre(pfad, "Noch einer"):
                pass
    with sicher.Sperre(pfad):                                                # wieder frei
        pass


def test_prozess_lebt():
    assert sicher.prozess_lebt(os.getpid())
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    assert not sicher.prozess_lebt(p.pid)
    assert not sicher.prozess_lebt(0)


def test_verknuepfung_wird_erkannt(tmp_path):
    ordner = tmp_path / "echt"
    ordner.mkdir()
    assert not sicher.ist_verknuepfung(ordner)
    try:
        (tmp_path / "link").symlink_to(ordner, target_is_directory=True)
    except OSError:
        pytest.skip("Symlinks hier nicht erlaubt")
    assert sicher.ist_verknuepfung(tmp_path / "link")
