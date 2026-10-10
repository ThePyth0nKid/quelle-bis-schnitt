# SPDX-License-Identifier: MIT
"""Prompter: ein Satz je Abschnitt (`studio prompter saetze`) und Texte in den Prompter laden (`… einspielen`).

``saetze`` teilt einen Sprechtext in Sätze; jeder Satz wird ein eigener Abschnitt (im Prompter blättert man mit ← / →).
Kameramarken wie ``[A]`` oder ``[B]`` gelten ab ihrer Stelle und stehen danach vor jedem Satz. Regiezeilen in Klammern
bleiben eigene Abschnitte. Nicht getrennt wird nach Ordnungszahlen („3. Oktober“) und nach üblichen Kürzeln.

``einspielen`` legt die Texte eines Projekts (``prompter.toml``) in den Prompter von Elgato Camera Hub. Vorerst nur
Windows. Ablauf: Projekt und ``AppSettings.json`` prüfen → prüfen, dass OBS nicht aufnimmt → Datenordner sichern →
Camera Hub hart beenden (nur der Prozess aus ``[prompter] prozessname``) → Bestand lesen → schreiben → neu starten.
Scheitert das Schreiben mittendrin, wird NICHT neu gestartet; die Sicherung liegt bereit.

F1 · Änderungen verschwinden. Symptom: nach dem nächsten Beenden von Camera Hub sind die neuen Texte weg. Ursache:
Camera Hub schreibt beim ordentlichen Beenden seinen Speicherstand zurück. Gegenmittel: vor dem Schreiben hart beenden
und prüfen, dass der Prozess wirklich weg ist; sonst abbrechen.

F2 · Texte liegen da, die Oberfläche zeigt sie nicht. Ursache: ``AppSettings.json`` ist eine Qt-Einstellungsdatei;
``applogic.prompter.libraryList`` ist EIN flacher Schlüssel (die Punkte gehören zum Namen). Gegenmittel: flach schreiben
und Dateien in ``Texts/`` ohne Bibliothekseintrag wieder eintragen.

F3 · Kameras fallen mitten in der Aufnahme aus. Ursache: Camera Hub steuert die Kameras; ein Beenden während einer
Aufnahme trifft den Dreh. Gegenmittel: vor dem Beenden per obs-websocket prüfen, dass OBS nicht aufnimmt.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from studio_werkzeuge import obs
from studio_werkzeuge.fehler import KonfigFehler, NurWindows, StudioFehler
from studio_werkzeuge.konfig import Konfig, toml_lesen

KUERZEL_MIT_LEERZEICHEN = ("z. B.", "Z. B.", "d. h.", "D. h.", "u. a.", "U. a.")
SCHUTZ = "\x00"
# Kürzel nur mit Wortgrenze davor: „ca.“ ist ein Kürzel, „Mallorca.“ ein Satzende.
KUERZEL_ENDE = re.compile(r"(?<![\w\x00])(?:ca|Nr|Dr|bzw|etc|vgl|Mio|Mrd|[zZ]\.\x00?B|[dD]\.\x00?h|[uU]\.\x00?a)\.$")
GRENZE = re.compile(r"(?<=[.!?])([\"“”»«']?)\s+(?=[A-ZÄÖÜ0-9\[„\"])")
LIBRARY_KEY = "applogic.prompter.libraryList"
MAX_NAME = 80
MIN_PRAEFIX = 3
GUID_MUSTER = re.compile(r"^[0-9A-Fa-f]{8}(-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}$")
PROZESSNAME = re.compile(r"^[\w .-]+\.exe$")
# Diese Prozesse beendet das Werkzeug nie, egal was in der Konfiguration steht.
NIE_BEENDEN = {"obs64.exe", "obs32.exe", "obs.exe", "resolve.exe", "explorer.exe", "svchost.exe", "csrss.exe",
               "wininit.exe", "winlogon.exe", "lsass.exe", "services.exe", "smss.exe", "dwm.exe", "system",
               "python.exe", "pythonw.exe", "cmd.exe", "powershell.exe", "pwsh.exe", "conhost.exe", "taskmgr.exe",
               "ffmpeg.exe", "claude.exe", "node.exe", "code.exe"}


# ── Sätze ────────────────────────────────────────────────────────────────────────────────────────

def saetze(absatz: str) -> list[str]:
    """Teilt einen Absatz in Sätze und lässt Ordnungszahlen und Kürzel ganz."""
    for k in KUERZEL_MIT_LEERZEICHEN:
        absatz = absatz.replace(k, k.replace(" ", SCHUTZ))
    roh = GRENZE.split(absatz)
    teile = [roh[i] + (roh[i + 1] if i + 1 < len(roh) else "") for i in range(0, len(roh), 2)]
    zusammen: list[str] = []
    for t in teile:
        if zusammen and (re.search(r"\b\d+\.$", zusammen[-1]) or KUERZEL_ENDE.search(zusammen[-1])):
            zusammen[-1] = f"{zusammen[-1]} {t}"
        else:
            zusammen.append(t)
    return [s.replace(SCHUTZ, " ").strip() for s in zusammen if s.strip()]


def satzweise(text: str, marken: tuple[str, ...] = ("A", "B")) -> list[str]:
    """Ein Eintrag je Satz, jeweils mit der gerade gültigen Kameramarke vorn."""
    marke_re = re.compile(r"\[(" + "|".join(re.escape(m) for m in marken) + r")\]\s*") if marken else None
    aus: list[str] = []
    marke = None
    for absatz in re.split(r"\n\s*\n+", text.replace("\r\n", "\n").strip()):
        for zeile in absatz.split("\n"):
            zeile = zeile.strip()
            if not zeile:
                continue
            if zeile.startswith("(") and zeile.endswith(")"):
                aus.append(zeile)
                continue
            stuecke = marke_re.split(zeile) if marke_re else [zeile]
            vorne = stuecke[0].strip()
            paare = [(None, vorne)] if vorne else []
            paare += [(stuecke[i], stuecke[i + 1]) for i in range(1, len(stuecke), 2)]
            for neue_marke, stueck in paare:
                if neue_marke:
                    marke = neue_marke
                for s in saetze(stueck.strip()):
                    aus.append(f"[{marke}] {s}" if marke else s)
    return aus


def schreiben_ohne_ueberschreiben(ziel: Path, inhalt: str) -> str:
    """Neu schreiben; ist die Datei schon da und gleich, ist das in Ordnung; ist sie anders, Abbruch."""
    if ziel.exists():
        if ziel.read_text(encoding="utf-8-sig") == inhalt:
            return "schon da und gleich"
        raise StudioFehler(f"{ziel} gibt es schon mit anderem Inhalt. Nie überschreiben: neuen Namen wählen.")
    with open(ziel, "x", encoding="utf-8") as f:
        f.write(inhalt)
    return "geschrieben"


# ── Einspielen ───────────────────────────────────────────────────────────────────────────────────

@dataclass
class Posten:
    name: str
    sektionen: list[str]
    quelle: str


@dataclass
class Projekt:
    posten: list[Posten]
    praefix: str = ""
    fehler: list[str] = field(default_factory=list)


def projekt_laden(datei: Path) -> Projekt:
    """``prompter.toml``: ``praefix`` (Pflicht, mindestens 3 Zeichen; daran erkennt das Werkzeug seine eigenen Einträge)
    und ``[[skript]]`` mit ``name`` und ``datei`` (relativ)."""
    if not datei.is_file():
        raise StudioFehler(f"{datei} fehlt. Vorlage: siehe `studio prompter einspielen --help`.")
    daten = toml_lesen(datei)
    projekt = Projekt([], str(daten.get("praefix", "")))
    if len(projekt.praefix.strip()) < MIN_PRAEFIX:
        projekt.fehler.append(f"praefix fehlt oder ist kürzer als {MIN_PRAEFIX} Zeichen: daran erkennt das Werkzeug "
                              "seine eigenen Einträge (nur die werden aktualisiert oder aufgeräumt).")
    for eintrag in daten.get("skript", []):
        if not isinstance(eintrag, dict):
            projekt.fehler.append(f"[[skript]]-Eintrag ist keine Tabelle: {eintrag!r}")
            continue
        name, quelle = str(eintrag.get("name", "")).strip(), eintrag.get("datei")
        if not name or not isinstance(quelle, str) or not quelle:
            projekt.fehler.append(f"Eintrag ohne name oder datei: {eintrag}")
            continue
        pfad = (datei.parent / quelle).resolve()
        if not pfad.is_file():
            projekt.fehler.append(f"{name}: Datei fehlt ({pfad})")
            continue
        text = pfad.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
        sektionen = [s.strip() for s in re.split(r"\n\s*\n+", text) if s.strip()]
        if not sektionen:
            projekt.fehler.append(f"{name}: leerer Text")
            continue
        if len(name) > MAX_NAME:
            name = name[: MAX_NAME - 1].rstrip(" ,.") + "…"
        projekt.posten.append(Posten(name, sektionen, str(pfad)))
    for doppelt in sorted(n for n, c in Counter(p.name for p in projekt.posten).items() if c > 1):
        projekt.fehler.append(f"Name „{doppelt}“ kommt mehrfach vor")
    if projekt.praefix and any(not p.name.startswith(projekt.praefix) for p in projekt.posten):
        projekt.fehler.append(f"Jeder Name muss mit dem praefix „{projekt.praefix}“ beginnen.")
    return projekt


def prozessname_pruefen(name: str) -> str:
    """Nur ein einfacher Programmname (``Name.exe``), keine Pfade oder Platzhalter, nie ein Prozess der Sperrliste."""
    if not PROZESSNAME.fullmatch(name) or any(z in name for z in "*?/\\:"):
        raise KonfigFehler(f"[prompter] prozessname {name!r}: nur ein Programmname wie „Camera Hub.exe“.")
    if name.lower() in NIE_BEENDEN:
        raise KonfigFehler(f"[prompter] prozessname {name!r} wird nie beendet (Systemprozess oder Aufnahmeprogramm).")
    return name


def tasklist_namen(csv_text: str) -> list[str]:
    """Erste Spalte von ``tasklist /FO CSV /NH`` (exakte Programmnamen)."""
    return [zeile[0] for zeile in csv.reader(io.StringIO(csv_text)) if zeile]


class CameraHub:
    """Die Prozess-Grenze unter Windows. Tests ersetzen sie durch eine Attrappe mit denselben drei Methoden."""

    def __init__(self, prozessname: str, programm: Path | None) -> None:
        if os.name != "nt":
            raise NurWindows("prompter einspielen läuft vorerst nur unter Windows (Camera Hub).")
        self.prozessname, self.programm = prozessname_pruefen(prozessname), programm

    @staticmethod
    def _system32(werkzeug: str) -> str:
        return str(Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32" / werkzeug)

    def laeuft(self) -> bool:
        r = subprocess.run([self._system32("tasklist.exe"), "/FI", f"IMAGENAME eq {self.prozessname}", "/FO", "CSV",
                            "/NH"], capture_output=True, text=True, errors="replace")
        return any(n.lower() == self.prozessname.lower() for n in tasklist_namen(r.stdout or ""))

    def beenden(self) -> tuple[bool, str]:
        """Hart beenden und nachsehen, ob der Prozess wirklich weg ist (der Rückgabewert von taskkill allein taugt
        nicht: „lief nicht“ und „misslungen“ sehen gleich aus)."""
        if not self.laeuft():
            return True, "lief nicht"
        subprocess.run([self._system32("taskkill.exe"), "/IM", self.prozessname, "/F"], capture_output=True)
        for _ in range(12):
            time.sleep(0.5)
            if not self.laeuft():
                return True, "hart beendet"
        return False, "läuft weiter"

    def starten(self) -> bool:
        if self.programm is None or not self.programm.is_file():
            return False
        subprocess.Popen([str(self.programm)], cwd=str(self.programm.parent), close_fds=True,
                         creationflags=0x00000008 | 0x00000200)   # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        return True


def bestand(texts: Path) -> list[tuple[Path, dict]]:
    if not texts.is_dir():
        return []
    raus = []
    for f in sorted(texts.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        if isinstance(d, dict):
            raus.append((f, d))
    return raus


def einstellungen_laden(datei: Path) -> dict:
    if not datei.is_file():
        raise StudioFehler(f"{datei} fehlt: ist [prompter] datenordner richtig?")
    try:
        einstellungen = json.loads(datei.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        raise StudioFehler(f"{datei} ist nicht lesbar ({type(e).__name__}). Nichts verändert.") from e
    if not isinstance(einstellungen, dict):
        raise StudioFehler(f"{datei} ist kein JSON-Objekt. Nichts verändert.")
    return einstellungen


def atomar(pfad: Path, text: str) -> None:
    tmp = pfad.with_suffix(pfad.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(pfad)


def sichern(datenordner: Path) -> Path:
    stempel = datetime.now().strftime("%Y%m%dT%H%M%S")
    ziel = datenordner / f"Sicherung-{stempel}"
    zaehler = 2
    while ziel.exists():
        ziel = datenordner / f"Sicherung-{stempel}-{zaehler}"
        zaehler += 1
    texts = datenordner / "Texts"
    if texts.is_dir():
        shutil.copytree(texts, ziel / "Texts")
    else:
        (ziel / "Texts").mkdir(parents=True)
    shutil.copy2(datenordner / "AppSettings.json", ziel / "AppSettings.json")
    return ziel


def planen(projekt: Projekt, vorher: list[tuple[Path, dict]]) -> tuple[dict, list[tuple[Path, dict]]]:
    """Bestand nach Name und die veralteten eigenen Einträge. Bricht ab bei doppelten Namen im Bestand."""
    namen = Counter(d.get("friendlyName") for _, d in vorher)
    gewollt = {p.name for p in projekt.posten}
    doppelt = sorted(n for n, c in namen.items() if c > 1 and n in gewollt)
    if doppelt:
        raise StudioFehler(f"Im Prompter gibt es mehrere Einträge namens {', '.join(doppelt)}: von Hand bereinigen. "
                           "Nichts verändert.")
    nach_name = {d.get("friendlyName"): (f, d) for f, d in vorher}
    veraltet = [(f, d) for f, d in vorher if str(d.get("friendlyName") or "").startswith(projekt.praefix)
                and d.get("friendlyName") not in gewollt]
    return nach_name, veraltet


def einspielen(projekt: Projekt, datenordner: Path, hub, probe: bool = False, nichts_loeschen: bool = False,
               neustart: bool = True) -> list[str]:
    """Schreibt die Posten in den Camera-Hub-Datenordner. ``hub`` hat ``laeuft``, ``beenden``, ``starten``."""
    texts, einstellungen_datei = datenordner / "Texts", datenordner / "AppSettings.json"
    if projekt.fehler:
        raise StudioFehler("prompter.toml hat Fehler:\n  " + "\n  ".join(projekt.fehler))
    einstellungen_laden(einstellungen_datei)                  # vor dem Beenden: lesbar?
    zeilen = []
    if probe:
        nach_name, veraltet = planen(projekt, bestand(texts))
        for p in projekt.posten:
            zustand = "aktualisiert" if p.name in nach_name else "neu"
            zeilen.append(f"  [{zustand:>12}] {p.name} ({len(p.sektionen)} Abschnitte)")
        was = "bleiben" if nichts_loeschen else "entfernt"
        for _, d in veraltet:
            zeilen.append(f"  [{'veraltet':>12}] {d.get('friendlyName')} (würde {was})")
        zeilen.append(f"Probe: {len(veraltet)} veraltete eigene Einträge würden {was}; nichts verändert.")
        return zeilen

    sicherung = sichern(datenordner)
    zeilen.append(f"Sicherung: {sicherung}")
    weg, wie = hub.beenden()
    if not weg:
        raise StudioFehler("Camera Hub läuft weiter. Wer jetzt schreibt, dessen Arbeit rollt Camera Hub beim nächsten "
                           "Beenden zurück. Nichts verändert.")
    zeilen.append(f"Camera Hub {wie}")
    try:
        nach_name, veraltet = planen(projekt, bestand(texts))   # erst nach dem Beenden: der echte Stand
        einstellungen = einstellungen_laden(einstellungen_datei)
    except StudioFehler:
        if neustart:
            hub.starten()                                    # noch nichts geschrieben: wieder starten ist sicher
        raise
    vorher_indizes = {d.get("index") for _, d in nach_name.values() if isinstance(d.get("index"), int)}
    naechster = (max(vorher_indizes) + 1) if vorher_indizes else 0
    vergeben: set[int] = set()
    guids: list[str] = []
    entfernt: list[str] = []
    try:
        texts.mkdir(parents=True, exist_ok=True)
        for p in projekt.posten:
            treffer = nach_name.get(p.name)
            guid, alter_pfad, index = "", None, None
            if treffer:
                alter_pfad, alt = treffer
                index = alt.get("index")
                guid = str(alt.get("GUID") or "").upper()
                if not GUID_MUSTER.match(guid):
                    # Camera Hub verlangt GUID == Dateiname; nie einen fremden Text als Dateinamen benutzen.
                    guid = alter_pfad.stem.upper() if GUID_MUSTER.match(alter_pfad.stem) else ""
            if not guid:
                guid = str(uuid.uuid4()).upper()
            if not isinstance(index, int) or index in vergeben:
                index, naechster = naechster, naechster + 1
            vergeben.add(index)
            pfad = texts / f"{guid}.json"
            if alter_pfad is not None and alter_pfad != pfad:
                alter_pfad.unlink(missing_ok=True)
            atomar(pfad, json.dumps({"GUID": guid, "chapters": p.sektionen, "friendlyName": p.name, "index": index},
                                    indent=4, ensure_ascii=False))
            guids.append(guid)
        if veraltet and not nichts_loeschen:
            for f, _ in veraltet:
                f.unlink(missing_ok=True)
                entfernt.append(f.stem.upper())
        liste = einstellungen.get(LIBRARY_KEY)
        liste = liste if isinstance(liste, list) else []
        weg_gross = set(entfernt)
        liste = [g for g in liste if not (isinstance(g, str) and g.upper() in weg_gross)]
        schon_da = {g.upper() for g in liste if isinstance(g, str)}
        for g in guids:
            if g not in schon_da:
                liste.append(g)
                schon_da.add(g)
        verwaist = sorted(f.stem for f in texts.glob("*.json") if f.stem.upper() not in schon_da)
        if verwaist:
            zeilen.append(f"  ! {len(verwaist)} Texte lagen als Datei da, fehlten aber in der Bibliothek: wieder "
                          "eingetragen")
            liste.extend(verwaist)
        einstellungen[LIBRARY_KEY] = liste
        atomar(einstellungen_datei, json.dumps(einstellungen, indent=2, ensure_ascii=False))
    except Exception as e:
        # Halber Stand: NICHT neu starten (Camera Hub würde ihn übernehmen); zurückholen entscheidet der Mensch.
        raise StudioFehler(f"Abbruch mitten im Schreiben ({type(e).__name__}: {e}). Camera Hub wurde nicht neu "
                           f"gestartet. Vorzustand: Inhalt von {sicherung} nach {datenordner} kopieren.") from e
    if neustart:
        zeilen.append("Camera Hub neu gestartet" if hub.starten() else "! Camera Hub bitte von Hand starten")
    abschnitte = sum(len(p.sektionen) for p in projekt.posten)
    zeilen.append(f"{len(projekt.posten)} Texte im Prompter, {abschnitte} Abschnitte, "
                  f"{len(entfernt)} veraltete entfernt.")
    return zeilen


# ── CLI ──────────────────────────────────────────────────────────────────────────────────────────

PROMPTER_TOML_BEISPIEL = """\
# prompter.toml (je Projekt) – welche Texte in den Prompter kommen
praefix = "MUSTER "                       # Pflicht (mind. 3 Zeichen): Einträge mit diesem Anfang gehören dem Projekt
[[skript]]
name = "MUSTER M01 · Wie ein Stromnetz atmet"
datei = "F2_prompter.md"                  # relativ zu dieser Datei; Leerzeile = neuer Abschnitt
"""


def einrichten(unter) -> None:
    p = unter.add_parser("prompter", help="Sätze für den Prompter bauen und in Camera Hub einspielen")
    pu = p.add_subparsers(dest="prompter_befehl", required=True, metavar="BEFEHL")
    s = pu.add_parser("saetze", help="ein Satz je Abschnitt, Kameramarken mitführen",
                      description=__doc__.split("\n\n")[1])
    s.add_argument("skript", type=Path, metavar="SKRIPT")
    s.add_argument("--ausgabe", type=Path, metavar="DATEI", help="hierhin schreiben (nie überschreiben)")
    s.add_argument("--marke", action="append", metavar="NAME",
                   help="Kameramarke wie [A]; mehrfach angeben (ohne: A und B)")
    s.set_defaults(ausfuehren=ausfuehren_saetze, braucht_konfig=False)
    e = pu.add_parser("einspielen", help="Texte eines Projekts in den Prompter von Camera Hub legen (Windows)",
                      description=__doc__.split("\n\n")[2] + "\n\n" + PROMPTER_TOML_BEISPIEL,
                      formatter_class=argparse.RawDescriptionHelpFormatter)
    e.add_argument("prompter_toml", nargs="?", type=Path, default=Path("prompter.toml"), metavar="PROMPTER_TOML")
    e.add_argument("--probe", action="store_true", help="nur zeigen, nichts beenden, nichts schreiben")
    e.add_argument("--ohne-obs", action="store_true",
                   help="OBS nicht prüfen (nur, wenn du sicher weißt, dass nichts aufnimmt)")
    e.add_argument("--kein-neustart", action="store_true", help="Camera Hub danach nicht starten")
    e.add_argument("--nichts-loeschen", action="store_true", help="veraltete eigene Einträge stehen lassen")
    e.set_defaults(ausfuehren=ausfuehren_einspielen, braucht_konfig=True)


def ausfuehren_saetze(args, konfig: Konfig) -> int:
    marken = tuple(args.marke) if args.marke else ("A", "B")
    if not args.skript.is_file():
        raise StudioFehler(f"Skript fehlt: {args.skript}")
    liste = satzweise(args.skript.read_text(encoding="utf-8-sig"), marken)
    for satz in liste:
        print(f"  | {satz}")
    print(f"{len(liste)} Abschnitte")
    if args.ausgabe:
        zustand = schreiben_ohne_ueberschreiben(args.ausgabe, "\n\n".join(liste) + "\n")
        print(f"{args.ausgabe}: {zustand}")
    return 0


def obs_frei(konfig: Konfig) -> None:
    """Bricht ab, wenn OBS aufnimmt oder sich nicht prüfen lässt."""
    client = obs.verbinden(konfig)
    try:
        if obs.nimmt_auf(client):
            raise StudioFehler("OBS nimmt gerade auf. Camera Hub jetzt zu beenden, träfe die Kameras. "
                               "Nichts verändert.")
    finally:
        obs.trennen(client)


def ausfuehren_einspielen(args, konfig: Konfig) -> int:
    projekt = projekt_laden(args.prompter_toml)
    datenordner = konfig.pfad_wert("prompter", "datenordner")
    if args.probe:
        for zeile in einspielen(projekt, datenordner, hub=None, probe=True, nichts_loeschen=args.nichts_loeschen):
            print(zeile)
        return 0
    programm = konfig.text("prompter", "programm", "")
    hub = CameraHub(konfig.text("prompter", "prozessname", "Camera Hub.exe"), Path(programm) if programm else None)
    if not args.ohne_obs:
        obs_frei(konfig)
    for zeile in einspielen(projekt, datenordner, hub, nichts_loeschen=args.nichts_loeschen,
                            neustart=not args.kein_neustart):
        print(zeile)
    return 0
