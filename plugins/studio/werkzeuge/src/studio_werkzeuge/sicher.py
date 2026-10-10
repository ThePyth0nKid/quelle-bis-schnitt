# SPDX-License-Identifier: MIT
"""Sichere Datei- und Prozess-Grundbausteine: Sperre je Ordner, Umbenennen ohne Überschreiben, Kopieren über
Laufwerksgrenzen mit Prüfung, Prozess lebt noch?, Verknüpfungen erkennen."""
from __future__ import annotations

import errno
import os
import shutil
import time
from pathlib import Path

from studio_werkzeuge.fehler import StudioFehler


class Sperre:
    """Exklusive Sperrdatei (eine je Zweck und Ordner). ``with Sperre(pfad, was):`` wirft ``StudioFehler``, wenn ein
    anderer Prozess sie hält. Die Datei bleibt liegen; gesperrt ist nur, solange der Prozess lebt."""

    def __init__(self, pfad: Path, was: str = "Ein anderer Lauf") -> None:
        self.pfad, self.was, self.datei = pfad, was, None

    def versuchen(self) -> bool:
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        f = open(self.pfad, "a+b")  # noqa: SIM115 - bleibt offen, solange die Sperre gilt
        f.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            f.close()
            return False
        self.datei = f
        return True

    def freigeben(self) -> None:
        if self.datei is not None:
            try:
                if os.name == "nt":
                    import msvcrt
                    self.datei.seek(0)
                    msvcrt.locking(self.datei.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
            self.datei.close()
            self.datei = None

    def __enter__(self) -> Sperre:
        if not self.versuchen():
            raise StudioFehler(f"{self.was} hält gerade die Sperre {self.pfad}. Später erneut versuchen.")
        return self

    def __exit__(self, *_: object) -> None:
        self.freigeben()


def umbenennen(quelle: Path, ziel: Path) -> None:
    """Auf derselben Platte umbenennen, NIE ein vorhandenes Ziel überschreiben (``Path.replace`` täte das)."""
    if ziel.exists():
        raise FileExistsError(errno.EEXIST, "Ziel gibt es schon", str(ziel))
    if os.name == "nt":
        os.rename(quelle, ziel)          # scheitert unter Windows ohnehin, wenn das Ziel existiert
        return
    try:
        os.link(quelle, ziel)            # atomar: scheitert, wenn das Ziel inzwischen existiert
        os.unlink(quelle)
    except OSError as e:
        if e.errno == errno.EEXIST:
            raise
        if ziel.exists():
            raise FileExistsError(errno.EEXIST, "Ziel gibt es schon", str(ziel)) from e
        os.rename(quelle, ziel)          # Dateisystem ohne Hardlinks (z. B. exFAT)


def ist_anderes_laufwerk(e: OSError) -> bool:
    return getattr(e, "winerror", None) == 17 or e.errno == errno.EXDEV   # 17 = ERROR_NOT_SAME_DEVICE


def verschieben(quelle: Path, ziel: Path) -> None:
    """Verschieben ohne Überschreiben. Auf derselben Platte nur umbenennen (eine noch offene Datei wird nicht halb
    kopiert). Über Laufwerksgrenzen: erst nach ``<ziel>.part`` kopieren, Größe prüfen, umbenennen, dann die Quelle
    löschen. Gibt es das Ziel schon, Abbruch. Hardlinks werden nie als Ergebnis angelegt (exFAT kennt keine)."""
    if ziel.exists():
        raise FileExistsError(errno.EEXIST, "Ziel gibt es schon", str(ziel))
    try:
        umbenennen(quelle, ziel)
        return
    except OSError as e:
        if not ist_anderes_laufwerk(e):
            raise
    teil = ziel.with_name(ziel.name + ".part")
    if teil.exists():
        raise FileExistsError(errno.EEXIST, "Zwischendatei gibt es schon (abgebrochener Lauf?)", str(teil))
    try:
        shutil.copyfile(quelle, teil)
        if teil.stat().st_size != quelle.stat().st_size:
            raise OSError(errno.EIO, "Kopie hat eine andere Größe", str(teil))
        umbenennen(teil, ziel)
    except BaseException:
        teil.unlink(missing_ok=True)
        raise
    quelle.unlink()


def prozess_lebt(pid: int) -> bool:
    """Lebt der Prozess mit dieser Nummer noch? Im Zweifel ja (dann wird nichts aufgeräumt)."""
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        griff = kernel32.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
        if not griff:
            return ctypes.GetLastError() == 5            # Zugriff verweigert = es gibt ihn
        try:
            code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(griff, ctypes.byref(code)):
                return True
            return code.value == 259                     # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(griff)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def ist_verknuepfung(p: Path) -> bool:
    """Symlink oder (unter Windows) Junction: solche Ordner werden nie aufgeräumt."""
    try:
        if p.is_symlink():
            return True
        ist_junction = getattr(os.path, "isjunction", None)
        return bool(ist_junction and ist_junction(p))
    except OSError:
        return True


def alter_s(p: Path) -> float:
    try:
        return time.time() - p.stat().st_mtime
    except OSError:
        return 0.0
