# SPDX-License-Identifier: MIT
"""Erwartete Fehler. Die Meldung ist für Menschen geschrieben; die CLI zeigt sie ohne Traceback (Exit 2)."""
from __future__ import annotations


class StudioFehler(Exception):
    """Oberklasse aller erwarteten Fehler."""


class KonfigFehler(StudioFehler):
    """Konfiguration fehlt, ist kaputt oder ein Pflichtwert ist nicht eingetragen."""


class KeinTon(StudioFehler):
    """Eine Datei hat keinen oder nur stummen Ton."""


class ZuKurzeUeberlappung(StudioFehler):
    """Zu wenig gemeinsamer Ton, um einen Versatz zu messen."""


class NurWindows(StudioFehler):
    """Der Befehl läuft vorerst nur unter Windows."""
