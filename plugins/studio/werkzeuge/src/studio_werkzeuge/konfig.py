# SPDX-License-Identifier: MIT
"""Konfiguration `studio.toml`: suchen, laden, Pflichtwerte prüfen, Vorlage schreiben.

Suchreihenfolge: ``$STUDIO_KONFIG`` → ``./studio.toml`` → Benutzer-Konfigordner
(Windows ``%APPDATA%/studio/studio.toml``, sonst ``$XDG_CONFIG_HOME/studio/studio.toml`` bzw.
``~/.config/studio/studio.toml``). Es gibt keinen Standardpfad für Daten: Wer Pfade braucht, bekommt ohne
Konfiguration eine klare Meldung. Werte in ``<spitzen Klammern>`` gelten als nicht eingetragen.
Zahlen, Wahrheitswerte und Texte werden über ``zahl``/``ganzzahl``/``wahrheit``/``text`` gelesen; ein falscher Typ
ist ein ``KonfigFehler`` mit Ort, nie ein Traceback.
"""
from __future__ import annotations

import math
import os
import re
import tomllib
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

from studio_werkzeuge.fehler import KonfigFehler

DATEINAME = "studio.toml"
VORLAGE = "studio.beispiel.toml"
_FEHLT = object()
_GEHEIM = re.compile(r"(passwort|password|kennwort|pass|token|secret|schluessel|auth|key)", re.IGNORECASE)
LOKALE_HOSTS = {"localhost", "127.0.0.1", "::1"}


def benutzer_konfigordner() -> Path:
    if os.name == "nt" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / "studio"
    basis = os.environ.get("XDG_CONFIG_HOME")
    return (Path(basis) if basis else Path.home() / ".config") / "studio"


def suchorte() -> list[Path]:
    """Die Orte in Suchreihenfolge (ohne zu prüfen, ob es sie gibt)."""
    orte = []
    if os.environ.get("STUDIO_KONFIG"):
        orte.append(Path(os.environ["STUDIO_KONFIG"]))
    orte.append(Path.cwd() / DATEINAME)
    orte.append(benutzer_konfigordner() / DATEINAME)
    return orte


def ist_platzhalter(wert: Any) -> bool:
    return isinstance(wert, str) and wert.strip().startswith("<") and wert.strip().endswith(">")


def toml_lesen(datei: Path) -> dict:
    """TOML mit ``utf-8-sig`` (eine BOM aus Windows-Editoren stört nicht)."""
    try:
        return tomllib.loads(datei.read_text(encoding="utf-8-sig"))
    except tomllib.TOMLDecodeError as e:
        raise KonfigFehler(f"{datei} ist kein gültiges TOML: {e}") from e
    except UnicodeDecodeError as e:
        raise KonfigFehler(f"{datei} ist nicht in UTF-8 gespeichert.") from e


@dataclass
class Konfig:
    """Geladene Konfiguration. ``pfad`` ist None, wenn keine Datei gefunden wurde (Messbefehle laufen trotzdem)."""

    daten: dict = field(default_factory=dict)
    pfad: Path | None = None

    def wert(self, abschnitt: str, schluessel: str, standard: Any = _FEHLT) -> Any:
        """Wert aus ``[abschnitt]`` (Punkte trennen Unterabschnitte). Fehlt er oder ist er ein Platzhalter,
        gilt ``standard``; ohne Standard bricht das mit einer klaren Meldung ab."""
        knoten = self.abschnitt(abschnitt)
        wert = knoten.get(schluessel, _FEHLT)
        if wert is _FEHLT or ist_platzhalter(wert) or wert == "":
            if standard is not _FEHLT:
                return standard
            raise KonfigFehler(self.fehlt_text(f"[{abschnitt}] {schluessel}"))
        return wert

    def abschnitt(self, name: str) -> dict:
        knoten: Any = self.daten
        for teil in name.split("."):
            knoten = knoten.get(teil, {}) if isinstance(knoten, dict) else {}
        return knoten if isinstance(knoten, dict) else {}

    def _falsch(self, abschnitt: str, schluessel: str, erwartet: str, wert: Any) -> KonfigFehler:
        ort = f" in {self.pfad}" if self.pfad else ""
        return KonfigFehler(f"[{abschnitt}] {schluessel}{ort} muss {erwartet} sein, ist {wert!r}.")

    def zahl(self, abschnitt: str, schluessel: str, standard: Any = _FEHLT) -> float:
        wert = self.wert(abschnitt, schluessel, standard)
        if isinstance(wert, bool) or not isinstance(wert, (int, float)) or not math.isfinite(wert):
            raise self._falsch(abschnitt, schluessel, "eine Zahl", wert)
        return float(wert)

    def ganzzahl(self, abschnitt: str, schluessel: str, standard: Any = _FEHLT) -> int:
        wert = self.wert(abschnitt, schluessel, standard)
        if isinstance(wert, bool) or not isinstance(wert, int):
            raise self._falsch(abschnitt, schluessel, "eine ganze Zahl", wert)
        return wert

    def wahrheit(self, abschnitt: str, schluessel: str, standard: Any = _FEHLT) -> bool:
        wert = self.wert(abschnitt, schluessel, standard)
        if not isinstance(wert, bool):
            raise self._falsch(abschnitt, schluessel, "true oder false", wert)
        return wert

    def text(self, abschnitt: str, schluessel: str, standard: Any = _FEHLT) -> str:
        wert = self.wert(abschnitt, schluessel, standard)
        if not isinstance(wert, str):
            raise self._falsch(abschnitt, schluessel, "ein Text in Anführungszeichen", wert)
        return wert

    def pfad_wert(self, abschnitt: str, schluessel: str, standard: Any = _FEHLT) -> Path:
        wert = self.wert(abschnitt, schluessel, standard)
        if isinstance(wert, Path):
            return wert
        if not isinstance(wert, str):
            raise self._falsch(abschnitt, schluessel, "ein Pfad als Text", wert)
        return Path(os.path.expandvars(wert)).expanduser()

    def fehlt_text(self, was: str) -> str:
        if self.pfad is None:
            orte = "\n".join(f"  {o}" for o in suchorte())
            return (f"Keine Konfiguration gefunden, aber {was} wird gebraucht.\nGesucht in:\n{orte}\n"
                    "Anlegen mit: studio konfig vorlage --ziel studio.toml  (dann die <Platzhalter> ersetzen)")
        return f"{was} fehlt in {self.pfad} oder ist noch ein <Platzhalter>. Bitte eintragen."


def laden(pfad: Path | None = None) -> Konfig:
    """Die erste gefundene Konfiguration laden; ohne Fund eine leere ``Konfig`` (``pfad`` None)."""
    umgebung = os.environ.get("STUDIO_KONFIG")
    if pfad is None and umgebung and not Path(umgebung).is_file():
        # Ausdrücklich gesetzt: nie still auf eine andere Datei ausweichen.
        raise KonfigFehler(f"STUDIO_KONFIG zeigt auf {umgebung}, dort liegt keine Datei.")
    kandidaten = [pfad] if pfad is not None else suchorte()
    for ort in kandidaten:
        if ort is not None and ort.is_file():
            return Konfig(toml_lesen(ort), ort.resolve())
    if pfad is not None:
        raise KonfigFehler(f"Konfiguration nicht gefunden: {pfad}")
    return Konfig()


def vorlage_text() -> str:
    return resources.files("studio_werkzeuge").joinpath(VORLAGE).read_text(encoding="utf-8")


def vorlage_schreiben(ziel: Path, ueberschreiben: bool = False) -> Path:
    """Die Vorlage nach ``ziel`` schreiben; eine vorhandene Datei bleibt ohne ``ueberschreiben`` unberührt."""
    if ziel.exists() and not ueberschreiben:
        raise KonfigFehler(f"{ziel} gibt es schon. Nichts überschrieben (mit --ueberschreiben ersetzen).")
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(vorlage_text(), encoding="utf-8")
    return ziel


def maskiert(daten: Any, schluessel: str = "", weg: str = "") -> Any:
    """Kopie für die Anzeige: Werte geheim klingender Schlüssel werden ersetzt, der Fern-Befehl des Transkripts nur
    gezählt. ``*_umgebung`` enthält nur den Namen einer Umgebungsvariable und bleibt sichtbar."""
    if isinstance(daten, dict):
        return {k: maskiert(v, k, f"{weg}.{k}" if weg else k) for k, v in daten.items()}
    if weg == "transkript.fern.befehl" and isinstance(daten, list):
        return f"[… {len(daten)} Argumente …]"
    if isinstance(daten, list):
        return [maskiert(v, schluessel, weg) for v in daten]
    if _GEHEIM.search(schluessel) and not schluessel.endswith("_umgebung") and daten not in ("", None):
        return "***"
    return daten


def zeigen(konfig: Konfig) -> str:
    """Lesbare Übersicht: gefundene Datei, Werte (maskiert), Zustand der Passwort-Umgebungsvariablen, Warnungen."""
    if konfig.pfad is None:
        orte = "\n".join(f"  {o}" for o in suchorte())
        return f"Keine Konfiguration gefunden. Gesucht in:\n{orte}\nAnlegen: studio konfig vorlage --ziel studio.toml"
    zeilen = [f"Konfiguration: {konfig.pfad}"]

    def ausgeben(knoten: dict, vorne: str) -> None:
        for k, v in knoten.items():
            if isinstance(v, dict):
                zeilen.append(f"[{vorne}{k}]")
                ausgeben(v, f"{vorne}{k}.")
            else:
                hinweis = "  (noch Platzhalter)" if ist_platzhalter(v) else ""
                if k.endswith("_umgebung") and isinstance(v, str) and v:
                    hinweis = "  (Variable gesetzt)" if os.environ.get(v) else "  (Variable NICHT gesetzt)"
                zeilen.append(f"  {k} = {v!r}{hinweis}")

    ausgeben(maskiert(konfig.daten), "")
    host = konfig.abschnitt("obs").get("host")
    if isinstance(host, str) and host and host not in LOKALE_HOSTS:
        zeilen.append(f"! [obs] host = {host!r} ist nicht dieser Rechner: das Passwort geht dann übers Netz.")
    return "\n".join(zeilen)
