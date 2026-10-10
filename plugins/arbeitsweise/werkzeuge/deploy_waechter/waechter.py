#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Deploy-Wächter: ein Strang je Projekt deployt, und kein Deploy wirft Ausgeliefertes zurück.

Befehle (Exit-Codes in Klammern):
  acquire    Lock für ein Projekt holen              (0 = gehört dir, 1 = belegt, 2 = Fehler)
  release    Lock freigeben und Ergebnis loggen      (0 = frei, 1 = fremder Lock oder nicht bestätigt)
  status     Lock des Projekts zeigen                (0 = frei, 1 = belegt); mit --alle: alle Projekte
  log        freien Text ins Log schreiben           (0)
  obermenge  jeder ausgelieferte Stand ist Vorfahre des Ziels, Arbeitskopie sauber
                                                     (0 = deployen erlaubt, 1 = NICHT deployen)

NIE PIPEN. ``waechter.py acquire … | tail -1`` liefert den Exit-Code von ``tail``, nicht den des
Wächters. Ein belegter Lock sähe dann aus wie ein freier. Ausgabe direkt lesen, Exit-Code sofort prüfen.

Exit-Code 2 heißt immer: Aufruf-, Konfigurations- oder Dateifehler. Nie „belegt“.

Übersteuern (``--erzwingen``, ``--trotzdem``, ``--bewusst-draussen``) geht nur interaktiv an einem Terminal,
mit Rückfrage und einem ``--grund`` von mindestens 10 Zeichen. Ein Agent ohne Terminal bekommt Exit 1.

Konfiguration ``.deploy-waechter.toml``, gesucht in: ``--konfig`` → Git-Wurzel des Arbeitsordners →
Benutzer-Konfigordner. Ohne Konfiguration gelten Voreinstellungen (Lock und Log im Benutzer-Zustandsordner).
Nur Standardbibliothek, Python ≥ 3.11.
"""
from __future__ import annotations

import argparse
import getpass
import json
import math
import os
import re
import subprocess
import sys
import time
import tomllib
import uuid
from dataclasses import dataclass, field
from pathlib import Path

KONFIG_NAME = ".deploy-waechter.toml"
# Voreinstellung, nicht gemessen: so lange darf ein Deploy dauern, bevor sein Lock als verwaist gilt.
VERWAIST_MINUTEN = 90
# Voreinstellung: so viele Tage zurück zählen Log-Einträge und aktive Branches.
TAGE = 10
# Mindestlänge einer Begründung beim Übersteuern (Voreinstellung).
GRUND_MIN_ZEICHEN = 10
HEX = r"[0-9a-f]{7,40}"
# Unter Windows nicht als Dateiname nutzbar.
RESERVIERT = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}


class WaechterFehler(Exception):
    """Aufruf- oder Konfigurationsfehler (Exit-Code 2)."""


class Verweigert(Exception):
    """Übersteuern abgelehnt: kein Terminal oder nicht bestätigt (Exit-Code 1)."""


# ── Konfiguration ──────────────────────────────────────────────────────────


def benutzer_konfig() -> Path:
    if os.name == "nt" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / "deploy-waechter" / "deploy-waechter.toml"
    basis = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(basis) / "deploy-waechter" / "deploy-waechter.toml"


def zustand_ordner() -> Path:
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "deploy-waechter"
    basis = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(basis) / "deploy-waechter"


@dataclass
class Konfig:
    quelle: Path | None
    projekt: str | None = None
    lock_ordner: Path = field(default_factory=lambda: zustand_ordner() / "locks")
    log_datei: Path = field(default_factory=lambda: zustand_ordner() / "deploy-log.md")
    verwaist_minuten: float = VERWAIST_MINUTEN
    ausgeliefert_refs: list[str] = field(default_factory=list)
    log_als_quelle: bool = True
    tage: int = TAGE
    arten: dict[str, list[str]] = field(default_factory=dict)


def _pfad(wert: object, basis: Path, schluessel: str, aus_repo: bool) -> Path:
    if not isinstance(wert, str) or not wert.strip():
        raise WaechterFehler(f"{schluessel} muss ein Pfad (Text) sein")
    if aus_repo:
        # Eine Konfiguration aus einem (womöglich fremden) Repo darf nur unterhalb des Zustandsordners schreiben.
        roh = Path(wert)
        if wert.startswith("~") or "$" in wert or "%" in wert or roh.is_absolute() or roh.drive or roh.root:
            raise WaechterFehler(f"{schluessel}: in einer Repo-Konfiguration nur relative Pfade unterhalb des "
                                 "Zustandsordners (kein ~, $, %, kein absoluter Pfad). Andere Orte gehören in die "
                                 "Benutzer-Konfiguration oder nach --konfig.")
        wurzel = zustand_ordner().resolve()
        pfad = (wurzel / roh).resolve()
        if not pfad.is_relative_to(wurzel):
            raise WaechterFehler(f"{schluessel}: {wert!r} verlässt den Zustandsordner {wurzel}")
        return pfad
    pfad = Path(os.path.expandvars(wert)).expanduser()
    return pfad if pfad.is_absolute() else (basis / pfad).resolve()


def _tabelle(wert: object, schluessel: str) -> dict:
    if not isinstance(wert, dict):
        raise WaechterFehler(f"[{schluessel}] muss eine Tabelle sein")
    return wert


def _liste(wert: object, schluessel: str) -> list[str]:
    if not isinstance(wert, list) or not all(isinstance(x, str) for x in wert):
        raise WaechterFehler(f"{schluessel} muss eine Liste von Texten sein")
    return wert


def konfig_laden(explizit: Path | None, repo: Path) -> Konfig:
    aus_repo = False
    if explizit is not None:
        if not explizit.is_file():
            raise WaechterFehler(f"Konfiguration {explizit} nicht gefunden")
        datei = explizit
    else:
        datei = None
        wurzel = git_wurzel(repo)
        if wurzel and (wurzel / KONFIG_NAME).is_file():
            datei, aus_repo = wurzel / KONFIG_NAME, True
        elif benutzer_konfig().is_file():
            datei = benutzer_konfig()
    if datei is None:
        return Konfig(quelle=None)
    if aus_repo:
        print(f"Hinweis: Konfiguration aus dem Repo geladen: {datei}", file=sys.stderr)
    try:
        roh = tomllib.loads(datei.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as fehler:
        raise WaechterFehler(f"{datei}: nicht lesbar ({fehler})") from None

    basis = datei.parent
    k = Konfig(quelle=datei)
    for unbekannt in sorted(set(roh) - {"projekt", "lock", "log", "obermenge"}):
        print(f"Hinweis: {datei}: unbekannter Schlüssel {unbekannt!r} wird ignoriert", file=sys.stderr)
    if "projekt" in roh:
        if not isinstance(roh["projekt"], str):
            raise WaechterFehler("projekt muss ein Text sein")
        k.projekt = roh["projekt"]

    lock = _tabelle(roh.get("lock", {}), "lock")
    if "ordner" in lock:
        k.lock_ordner = _pfad(lock["ordner"], basis, "lock.ordner", aus_repo)
    if "verwaist_nach_minuten" in lock:
        wert = lock["verwaist_nach_minuten"]
        if isinstance(wert, bool) or not isinstance(wert, int | float) or not math.isfinite(wert) or wert < 0:
            raise WaechterFehler("lock.verwaist_nach_minuten muss eine Zahl ≥ 0 sein (0 = nie verwaist)")
        k.verwaist_minuten = float(wert)

    log = _tabelle(roh.get("log", {}), "log")
    if "datei" in log:
        k.log_datei = _pfad(log["datei"], basis, "log.datei", aus_repo)

    ober = _tabelle(roh.get("obermenge", {}), "obermenge")
    if "ausgeliefert_refs" in ober:
        k.ausgeliefert_refs = _liste(ober["ausgeliefert_refs"], "obermenge.ausgeliefert_refs")
    if "log_als_quelle" in ober:
        if not isinstance(ober["log_als_quelle"], bool):
            raise WaechterFehler("obermenge.log_als_quelle muss true oder false sein (ohne Anführungszeichen)")
        k.log_als_quelle = ober["log_als_quelle"]
    if "tage" in ober:
        if isinstance(ober["tage"], bool) or not isinstance(ober["tage"], int) or ober["tage"] < 1:
            raise WaechterFehler("obermenge.tage muss eine ganze Zahl ≥ 1 sein")
        k.tage = ober["tage"]
    for name, art in _tabelle(ober.get("arten", {}), "obermenge.arten").items():
        art = _tabelle(art, f"obermenge.arten.{name}")
        k.arten[name] = _liste(art.get("pfade", []), f"obermenge.arten.{name}.pfade")
    return k


# ── Git ────────────────────────────────────────────────────────────────────


def git(repo: Path, *args: str, pruefen: bool = False) -> subprocess.CompletedProcess[str]:
    ergebnis = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    if pruefen and ergebnis.returncode != 0:
        raise WaechterFehler(f"git {' '.join(args)} scheiterte: {ergebnis.stderr.strip()}")
    return ergebnis


def git_wurzel(repo: Path) -> Path | None:
    try:
        ergebnis = git(repo, "rev-parse", "--show-toplevel")
    except OSError:
        return None
    return Path(ergebnis.stdout.strip()) if ergebnis.returncode == 0 and ergebnis.stdout.strip() else None


def commit_von(repo: Path, ref: str) -> str | None:
    ergebnis = git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    return ergebnis.stdout.strip() if ergebnis.returncode == 0 else None


def ist_vorfahre(repo: Path, commit: str, ziel: str) -> bool:
    return git(repo, "merge-base", "--is-ancestor", commit, ziel).returncode == 0


# ── Projekt, Mensch, Log ───────────────────────────────────────────────────


def normalisieren(name: str) -> str:
    """Projektname → dateisystemtauglicher, vergleichbarer Schlüssel."""
    schluessel = re.sub(r"[^a-z0-9._-]+", "-", (name or "").strip().lower()).strip("-.") or "unbekannt"
    if schluessel.split(".")[0] in RESERVIERT:
        schluessel = f"p-{schluessel}"
    return schluessel


def projekt_bestimmen(explizit: str | None, konfig: Konfig, repo: Path) -> str:
    for kandidat in (explizit, os.environ.get("DEPLOY_PROJEKT"), konfig.projekt):
        if kandidat:
            return normalisieren(kandidat)
    wurzel = git_wurzel(repo)
    return normalisieren((wurzel or repo.resolve()).name)


def benutzer() -> str:
    try:
        return getpass.getuser()
    except (OSError, KeyError, ImportError):
        return "unbekannt"


def mensch_bestaetigt(aktion: str, grund: str) -> str:
    """Nur ein Mensch am Terminal darf übersteuern. Gibt den Benutzernamen für das Log zurück."""
    if len(grund.strip()) < GRUND_MIN_ZEICHEN:
        raise WaechterFehler(f"--grund braucht mindestens {GRUND_MIN_ZEICHEN} Zeichen (kommt ins Log)")
    if sys.stdin is None or not sys.stdin.isatty():
        raise Verweigert("Übersteuern nur interaktiv durch einen Menschen (kein Terminal). "
                         "Ein Agent zeigt dem Menschen den Befund und fragt.")
    try:
        antwort = input(f"{aktion}\nGrund: {grund}\nWirklich übersteuern? Tippe 'ja': ")
    except EOFError:
        antwort = ""
    if antwort.strip().lower() != "ja":
        raise Verweigert("nicht bestätigt, nichts übersteuert")
    return benutzer()


def _text(wert: object) -> str:
    """Freitext für eine Log-Zeile: eine Zeile, keine eingeschleusten Marker."""
    text = " ".join(str(wert or "").split())
    return re.sub(r"(ausgeliefert|bewusst-draussen)=", r"\1:", text, flags=re.IGNORECASE)


def jetzt_text(jetzt: float | None = None) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(jetzt if jetzt is not None else time.time()))


def log_schreiben(konfig: Konfig, projekt: str, zeile: str) -> None:
    """Hängt eine Zeile an (UTF-8). Das Log wird nie umgeschrieben."""
    konfig.log_datei.parent.mkdir(parents=True, exist_ok=True)
    with konfig.log_datei.open("a", encoding="utf-8") as f:
        f.write(f"- {jetzt_text()} · [{projekt}] {zeile}\n")


def log_zeilen(konfig: Konfig, projekt: str) -> list[tuple[float | None, str]]:
    """Alle Log-Zeilen eines Projekts als (Zeitpunkt, Zeile)."""
    if not konfig.log_datei.is_file():
        return []
    muster = re.compile(r"^- (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) · \[([^\]]+)\] (.*)$")
    zeilen = []
    for roh in konfig.log_datei.read_text(encoding="utf-8", errors="replace").splitlines():
        m = muster.match(roh)
        if not m or m.group(2) != projekt:
            continue
        try:
            zeitpunkt = time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"))
        except (ValueError, OverflowError):
            zeitpunkt = None
        zeilen.append((zeitpunkt, m.group(3)))
    return zeilen


# ── Lock ───────────────────────────────────────────────────────────────────


@dataclass
class LockZustand:
    # frei | gueltig | verwaist | defekt (unlesbar, noch jung) | defekt_alt (unlesbar, älter als die Verwaisung)
    art: str
    daten: dict | None = None
    alter: float = 0.0


def lock_pfad(konfig: Konfig, projekt: str) -> Path:
    return konfig.lock_ordner / f"{projekt}.lock"


def _epoch(daten: dict | None) -> float | None:
    wert = (daten or {}).get("epoch")
    if isinstance(wert, bool) or not isinstance(wert, int | float) or not math.isfinite(wert):
        return None
    return float(wert)


def lock_zustand(pfad: Path, verwaist_minuten: float, jetzt: float) -> LockZustand:
    try:
        stat = pfad.stat()
        roh = pfad.read_text(encoding="utf-8")
    except FileNotFoundError:
        return LockZustand("frei")
    except (OSError, UnicodeDecodeError):
        return LockZustand("defekt")  # unlesbar (z. B. gerade geöffnet): sicherheitshalber belegt
    try:
        daten = json.loads(roh)
    except ValueError:
        daten = None
    daten = daten if isinstance(daten, dict) else None
    grenze = verwaist_minuten * 60
    epoch = _epoch(daten)
    if epoch is None:
        # Leer, kaputt oder ohne gültigen Zeitpunkt: belegt, bis die Datei selbst älter als die Verwaisung ist.
        alter = jetzt - stat.st_mtime
        return LockZustand("defekt_alt" if grenze and alter > grenze else "defekt", daten, alter)
    alter = jetzt - epoch
    return LockZustand("verwaist" if grenze and alter > grenze else "gueltig", daten, alter)


def _beschreibung(z: LockZustand) -> str:
    if z.daten is None or z.art.startswith("defekt"):
        return f"Lock-Datei unlesbar oder defekt (seit {int(z.alter // 60)} min)"
    teile = [str(z.daten.get("halter")), str(z.daten.get("bereich")), f"seit {int(z.alter // 60)} min"]
    if z.daten.get("notiz"):
        teile.append(str(z.daten["notiz"]))
    if z.art == "verwaist":
        teile.append("verwaist")
    return " · ".join(teile)


def _loeschen(pfad: Path) -> None:
    """Datei löschen; unter Windows kurz wiederholen, falls sie gerade geöffnet ist."""
    for versuch in range(5):
        try:
            pfad.unlink(missing_ok=True)
            return
        except PermissionError:
            if versuch == 4:
                raise
            time.sleep(0.1)


def _zuruecklegen(weg: Path, pfad: Path) -> bool:
    """Einen versehentlich weggezogenen, gültigen Lock zurücklegen, ohne einen neuen zu überschreiben."""
    try:
        os.link(weg, pfad)  # atomar, scheitert, wenn pfad schon existiert
    except FileExistsError:
        return False
    except OSError:
        try:
            if os.name != "nt":
                return False  # ohne Hardlinks gibt es unter POSIX kein sicheres Zurücklegen
            os.rename(weg, pfad)  # Windows: scheitert, wenn pfad schon existiert
            return True
        except OSError:
            return False
    _loeschen(weg)
    return True


def _belegt(projekt: str, z: LockZustand) -> int:
    print(f"LOCK-BELEGT: dasselbe Projekt '{projekt}' wird gerade deployt ({_beschreibung(z)}). "
          "NICHT parallel deployen: warten oder den Menschen fragen.")
    return 1


def _uebernehmen(konfig: Konfig, projekt: str, pfad: Path, halter: str, jetzt: float) -> int:
    """Verwaisten oder defekten Lock atomar wegziehen. Nur wer das Wegziehen schafft, macht weiter."""
    weg = pfad.with_name(f"{pfad.name}.stale.{os.getpid()}.{uuid.uuid4().hex}")
    try:
        os.replace(pfad, weg)
    except (FileNotFoundError, PermissionError):
        print(f"LOCK-BELEGT: ein anderer Strang übernimmt den Lock von '{projekt}' gerade. NICHT deployen.")
        return 1
    z = lock_zustand(weg, konfig.verwaist_minuten, jetzt)
    if z.art not in ("verwaist", "defekt_alt"):
        # Zwischen Lesen und Wegziehen hat ein anderer Strang einen frischen Lock angelegt.
        if not _zuruecklegen(weg, pfad):
            print(f"Hinweis: frischen Lock nicht zurücklegen können, er liegt unter {weg}.", file=sys.stderr)
        return _belegt(projekt, z)
    if z.art == "verwaist":
        zeile = f"VERWAISTER LOCK übernommen (war: {_text(_beschreibung(z))}) durch {_text(halter)}"
        print(f"Hinweis: verwaisten Lock von {(z.daten or {}).get('halter')} übernommen "
              f"(älter als {konfig.verwaist_minuten:g} min).")
    else:
        zeile = f"DEFEKTER LOCK entfernt (älter als {konfig.verwaist_minuten:g} min) durch {_text(halter)}"
    log_schreiben(konfig, projekt, zeile)
    _loeschen(weg)
    return 0


def lock_holen(konfig: Konfig, projekt: str, halter: str, bereich: str, notiz: str = "",
               jetzt: float | None = None) -> int:
    konfig.lock_ordner.mkdir(parents=True, exist_ok=True)
    pfad = lock_pfad(konfig, projekt)
    for _ in range(5):
        zeitpunkt = time.time() if jetzt is None else jetzt
        try:
            # O_EXCL: Anlegen ist atomar, zwei Stränge können nicht beide gewinnen.
            fd = os.open(pfad, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            z = lock_zustand(pfad, konfig.verwaist_minuten, zeitpunkt)
            if z.art == "frei":
                continue  # inzwischen freigegeben
            if z.art in ("gueltig", "defekt"):
                return _belegt(projekt, z)
            ergebnis = _uebernehmen(konfig, projekt, pfad, halter, zeitpunkt)
            if ergebnis:
                return ergebnis
            continue
        return _anlegen_abschliessen(konfig, projekt, pfad, fd, halter, bereich, notiz, zeitpunkt)
    print(f"LOCK-FEHLER: Lock-Datei {pfad} ließ sich nicht anlegen.")
    return 2


def _anlegen_abschliessen(konfig: Konfig, projekt: str, pfad: Path, fd: int, halter: str, bereich: str,
                          notiz: str, zeitpunkt: float) -> int:
    marke = uuid.uuid4().hex
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"halter": halter, "bereich": bereich, "notiz": notiz, "projekt": projekt,
                       "start": jetzt_text(zeitpunkt), "epoch": zeitpunkt, "marke": marke}, f, ensure_ascii=False)
    except OSError as fehler:
        _loeschen(pfad)
        print(f"LOCK-FEHLER: Lock-Datei nicht schreibbar ({fehler}); wieder entfernt.")
        return 2
    # Liegt unsere Datei noch an ihrem Platz? Sonst hat ein Übernehmer sie weggezogen.
    if (lock_zustand(pfad, 0, zeitpunkt).daten or {}).get("marke") != marke:
        print(f"LOCK-BELEGT: der Lock von '{projekt}' wurde beim Anlegen übernommen. NICHT deployen.")
        return 1
    try:
        log_schreiben(konfig, projekt, " · ".join(x for x in ("LOCK", _text(halter), _text(bereich), _text(notiz))
                                                   if x))
    except OSError as fehler:
        _loeschen(pfad)
        print(f"LOCK-FEHLER: Log {konfig.log_datei} nicht schreibbar ({fehler}); Lock wieder entfernt.")
        return 2
    print(f"LOCK-OK: {projekt}/{bereich} gehört jetzt {halter}")
    andere = [(p, z) for p, z in aktive_locks(konfig) if p != projekt]
    if andere:
        liste = ", ".join(f"{p}: {(z.daten or {}).get('halter', 'unlesbar')}" for p, z in andere)
        print(f"Hinweis: parallel deployen andere Projekte ({liste}), kein Konflikt.")
    return 0


def lock_freigeben(konfig: Konfig, projekt: str, halter: str, ergebnis: str = "", ausgeliefert: str | None = None,
                   erzwingen: bool = False, grund: str = "") -> int:
    pfad = lock_pfad(konfig, projekt)
    z = lock_zustand(pfad, konfig.verwaist_minuten, time.time())
    if z.art == "frei":
        print(f"LOCK-FREI ({projekt}): nichts freizugeben")
        if ausgeliefert:
            log_schreiben(konfig, projekt, f"AUSGELIEFERT ohne Lock · {_text(halter)} · ausgeliefert={ausgeliefert}")
        return 0
    # Unlesbare Lock-Dateien gelten als fremd: nie still löschen.
    fremd = z.daten is None or z.daten.get("halter") != halter
    teile = ["FREI", _text((z.daten or {}).get("halter") or "unlesbar"), _text((z.daten or {}).get("bereich")),
             _text(ergebnis) or "ohne Ergebnis-Angabe"]
    if fremd:
        if not erzwingen:
            print(f"LOCK-FREMD: {projekt}: {_beschreibung(z)}. Nur ein Mensch gibt einen fremden Lock frei: "
                  "--erzwingen --grund \"…\" an einem Terminal.")
            return 1
        wer = mensch_bestaetigt(f"Fremden Lock von '{projekt}' freigeben ({_beschreibung(z)}).", grund)
        teile.append(f"ERZWUNGEN durch {_text(halter)} (Benutzer {_text(wer)}): {_text(grund)}")
    if ausgeliefert:
        teile.append(f"ausgeliefert={ausgeliefert}")
    # Erst loggen, dann löschen: scheitert das Log, bleibt der Lock stehen (Exit 2 über OSError).
    log_schreiben(konfig, projekt, " · ".join(t for t in teile if t))
    _loeschen(pfad)
    print(f"LOCK-FREIGEGEBEN ({projekt}): {ergebnis or 'ohne Ergebnis-Angabe'}")
    return 0


def aktive_locks(konfig: Konfig) -> list[tuple[str, LockZustand]]:
    if not konfig.lock_ordner.is_dir():
        return []
    gefunden = []
    for pfad in sorted(konfig.lock_ordner.glob("*.lock")):
        z = lock_zustand(pfad, konfig.verwaist_minuten, time.time())
        if z.art != "frei":
            gefunden.append((pfad.stem, z))
    return gefunden


def lock_status(konfig: Konfig, projekt: str, alle: bool) -> int:
    if alle:
        gehalten = aktive_locks(konfig)
        if not gehalten:
            print("LOCK-FREI: kein Projekt deployt gerade")
            return 0
        print(f"{len(gehalten)} Projekt(e) deployen gerade:")
        for name, z in gehalten:
            print(f"  {name}: {_beschreibung(z)}")
        return 1
    z = lock_zustand(lock_pfad(konfig, projekt), konfig.verwaist_minuten, time.time())
    if z.art == "frei":
        print(f"LOCK-FREI ({projekt})")
        return 0
    print(f"LOCK-BELEGT ({projekt}): {_beschreibung(z)}")
    return 1


# ── Obermenge ──────────────────────────────────────────────────────────────


@dataclass
class Obermenge:
    ziel: str
    ok: list[str] = field(default_factory=list)
    hart: list[tuple[str, str]] = field(default_factory=list)       # (Commit, Grund)
    ohne_wirkung: list[str] = field(default_factory=list)           # fehlt, betrifft dieses Ziel nicht
    ausgenommen: list[str] = field(default_factory=list)            # bewusst draußen
    weich: list[tuple[str, int]] = field(default_factory=list)      # (Branch, Commits nicht im Ziel)
    schmutzig: list[str] = field(default_factory=list)
    ohne_basis: bool = False

    @property
    def blockiert(self) -> bool:
        return bool(self.hart or self.schmutzig or self.ohne_basis)


def ausgelieferte_staende(repo: Path, konfig: Konfig, projekt: str, jetzt: float) -> tuple[list[str], set[str]]:
    """Ausgelieferte Commits (aus Git-Referenzen und Log) und bewusst ausgenommene Commits."""
    staende: list[str] = []
    if konfig.ausgeliefert_refs:
        refs = git(repo, "for-each-ref", "--format=%(refname)", *konfig.ausgeliefert_refs, pruefen=True)
        for ref in refs.stdout.split():
            commit = commit_von(repo, ref)
            staende.append(commit or ref)
    draussen: set[str] = set()
    if konfig.log_als_quelle:
        grenze = jetzt - konfig.tage * 86400
        for zeitpunkt, zeile in log_zeilen(konfig, projekt):
            for h in re.findall(rf"\bbewusst-draussen=({HEX})\b", zeile):
                draussen.add(commit_von(repo, h) or h)
            if zeitpunkt is not None and zeitpunkt < grenze:
                continue
            staende += re.findall(rf"\bausgeliefert=({HEX})\b", zeile)
    eindeutig = list(dict.fromkeys(staende))
    return eindeutig, draussen


def aktive_branches(repo: Path, tage: int, jetzt: float) -> list[str]:
    roh = git(repo, "for-each-ref", "--format=%(committerdate:unix)\t%(refname:short)", "refs/heads", "refs/remotes")
    namen = []
    for zeile in roh.stdout.splitlines():
        datum, _, name = zeile.partition("\t")
        if not name or name.endswith("/HEAD") or not datum.isdigit():
            continue
        if jetzt - int(datum) <= tage * 86400:
            namen.append(name)
    return namen


def obermenge_pruefen(repo: Path, konfig: Konfig, projekt: str, ziel: str = "HEAD", art: str | None = None,
                      arbeitskopie: bool = True, jetzt: float | None = None) -> Obermenge:
    zeitpunkt = time.time() if jetzt is None else jetzt
    if git_wurzel(repo) is None:
        raise WaechterFehler(f"{repo} ist kein Git-Repo")
    ziel_commit = commit_von(repo, ziel)
    if ziel_commit is None:
        raise WaechterFehler(f"Ziel {ziel!r} ist kein Commit")
    pfade: list[str] = []
    if art is not None:
        if art not in konfig.arten:
            raise WaechterFehler(f"Art {art!r} ist nicht konfiguriert (bekannt: {', '.join(konfig.arten) or 'keine'})")
        pfade = konfig.arten[art]

    befund = Obermenge(ziel=ziel)
    staende, draussen = ausgelieferte_staende(repo, konfig, projekt, zeitpunkt)
    befund.ohne_basis = not staende
    for stand in staende:
        commit = commit_von(repo, stand)
        if commit is None:
            befund.hart.append((stand, "im Repo unbekannt (git fetch?) – Obermenge nicht beweisbar"))
            continue
        if commit in draussen or any(commit.startswith(d) for d in draussen):
            befund.ausgenommen.append(commit)
            continue
        if ist_vorfahre(repo, commit, ziel_commit):
            befund.ok.append(commit)
            continue
        if pfade:
            # ziel...commit = Arbeit auf der Seite von commit seit dem gemeinsamen Vorfahren
            mit = git(repo, "diff", "--name-only", f"{ziel_commit}...{commit}", "--", *pfade).stdout.split()
            if not mit:
                befund.ohne_wirkung.append(commit)
                continue
            befund.hart.append((commit, f"fehlt im Ziel, {len(mit)} Datei(en) in {', '.join(pfade)}"))
        else:
            befund.hart.append((commit, "fehlt im Ziel"))

    for name in aktive_branches(repo, konfig.tage, zeitpunkt):
        if not ist_vorfahre(repo, name, ziel_commit):
            anzahl = git(repo, "rev-list", "--count", f"{ziel_commit}..{name}").stdout.strip()
            befund.weich.append((name, int(anzahl or 0)))

    if arbeitskopie and ziel_commit == commit_von(repo, "HEAD"):
        status = git(repo, "status", "--porcelain", "--", *(pfade or ["."]), pruefen=True)
        befund.schmutzig = [z for z in status.stdout.splitlines() if z.strip()]
    return befund


def kurz(commit: str) -> str:
    return commit[:12]


def obermenge_ausgeben(b: Obermenge, art: str | None) -> None:
    print(f"ZIEL: {b.ziel}" + (f" · Art {art}" if art else ""))
    print("HART · ausgelieferte Stände müssen Vorfahren des Ziels sein")
    if b.ohne_basis:
        print("  Keine ausgelieferten Stände bekannt (weder Referenzen noch Log). Obermenge nicht beweisbar.")
    for c in b.ok:
        print(f"  OK     {kurz(c)}")
    for c in b.ausgenommen:
        print(f"  DRAUSSEN (bewusst) {kurz(c)}")
    for c in b.ohne_wirkung:
        print(f"  fehlt, betrifft diese Art nicht {kurz(c)}")
    for c, grund in b.hart:
        print(f"  FEHLT  {kurz(c)}  {grund}")
    print("WEICH · Branches mit frischer Arbeit, die nicht im Ziel stecken (nur Bericht)")
    if not b.weich:
        print("  (keiner)")
    for name, anzahl in b.weich:
        print(f"  {anzahl:>4} Commits  {name}")
    if b.schmutzig:
        print("ARBEITSKOPIE · uncommittet (fährt beim Hochladen der Arbeitskopie mit)")
        for zeile in b.schmutzig[:15]:
            print(f"  {zeile}")
        if len(b.schmutzig) > 15:
            print(f"  … und {len(b.schmutzig) - 15} weitere")


# ── Kommandozeile ──────────────────────────────────────────────────────────


def _parser() -> argparse.ArgumentParser:
    # Gemeinsame Optionen gelten vor UND nach dem Unterbefehl (SUPPRESS: nur gesetzt, wenn angegeben).
    gemeinsam = argparse.ArgumentParser(add_help=False)
    gemeinsam.add_argument("--konfig", type=Path, default=argparse.SUPPRESS,
                           help=f"Pfad zur Konfiguration (sonst {KONFIG_NAME} in der Git-Wurzel)")
    gemeinsam.add_argument("--repo", type=Path, default=argparse.SUPPRESS,
                           help="Arbeitsordner (Standard: aktueller Ordner)")
    gemeinsam.add_argument("--projekt", default=argparse.SUPPRESS,
                           help="Projektname (sonst $DEPLOY_PROJEKT, Konfiguration oder Name der Git-Wurzel)")
    p = argparse.ArgumentParser(prog="waechter.py", description=__doc__, parents=[gemeinsam],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="befehl", required=True)

    def befehl(name: str, hilfe: str) -> argparse.ArgumentParser:
        return sub.add_parser(name, help=hilfe, parents=[gemeinsam])

    a = befehl("acquire", "Lock holen (0 = gehört dir, 1 = belegt)")
    a.add_argument("--halter", required=True, help="wer deployt (Strang, Sitzung, Kürzel)")
    a.add_argument("--bereich", required=True, help="was deployt wird, z. B. backend, app-ios, migration")
    a.add_argument("--notiz", default="")

    r = befehl("release", "Lock freigeben und Ergebnis loggen")
    r.add_argument("--halter", required=True)
    r.add_argument("--ergebnis", default="", help="z. B. 'Build 142 ok' oder 'abgebrochen'")
    r.add_argument("--ausgeliefert", help="ausgelieferter Commit (wird für obermenge gemerkt)")
    r.add_argument("--erzwingen", action="store_true",
                   help="fremden Lock freigeben (nur ein Mensch am Terminal, mit --grund und Rückfrage)")
    r.add_argument("--grund", default="", help=f"Begründung fürs Log, mindestens {GRUND_MIN_ZEICHEN} Zeichen")

    s = befehl("status", "Lock zeigen (0 = frei, 1 = belegt)")
    s.add_argument("--alle", action="store_true", help="alle Projekte")

    lg = befehl("log", "freien Text ins Log schreiben")
    lg.add_argument("text")

    o = befehl("obermenge", "vor dem Deploy: nichts Ausgeliefertes fällt heraus (0 = ok, 1 = nicht deployen)")
    o.add_argument("--ziel", default="HEAD", help="was gebaut wird (Branch oder Commit)")
    o.add_argument("--art", help="Deploy-Art aus [obermenge.arten.*]; zählt nur Rückwürfe in deren Pfaden")
    o.add_argument("--fetch", action="store_true", help="vorher 'git fetch --all' ausführen")
    o.add_argument("--ohne-arbeitskopie", action="store_true",
                   help="Arbeitskopie nicht prüfen (nur, wenn aus dem Commit gebaut wird, nicht aus dem Ordner)")
    o.add_argument("--bewusst-draussen", metavar="COMMIT",
                   help="einen ausgelieferten Stand bewusst ausnehmen (nur ein Mensch am Terminal, mit --grund)")
    o.add_argument("--trotzdem", action="store_true",
                   help="Sperre übersteuern (nur ein Mensch am Terminal, mit --grund und Rückfrage)")
    o.add_argument("--grund", default="", help=f"Begründung fürs Log, mindestens {GRUND_MIN_ZEICHEN} Zeichen")
    return p


def _utf8_ausgabe() -> None:
    """Windows-Konsolen schreiben sonst in einer Codepage und scheitern an Umlauten oder Pfeilen."""
    for strom in (sys.stdout, sys.stderr):
        try:
            strom.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def main(argv: list[str] | None = None) -> int:
    _utf8_ausgabe()
    a = _parser().parse_args(argv)
    a.repo = getattr(a, "repo", None) or Path.cwd()
    a.konfig = getattr(a, "konfig", None)
    a.projekt = getattr(a, "projekt", None)
    try:
        konfig = konfig_laden(a.konfig, a.repo)
        projekt = projekt_bestimmen(a.projekt, konfig, a.repo)
        if a.befehl == "acquire":
            return lock_holen(konfig, projekt, a.halter, a.bereich, a.notiz)
        if a.befehl == "release":
            return _release_befehl(a, konfig, projekt)
        if a.befehl == "status":
            return lock_status(konfig, projekt, a.alle)
        if a.befehl == "log":
            log_schreiben(konfig, projekt, _text(a.text))
            print("geloggt")
            return 0
        return _obermenge_befehl(a, konfig, projekt)
    except Verweigert as grund:
        print(f"NICHT ÜBERSTEUERT: {grund}")
        return 1
    except WaechterFehler as fehler:
        print(f"FEHLER: {fehler}", file=sys.stderr)
        return 2
    except OSError as fehler:
        print(f"FEHLER: Datei- oder Systemfehler: {fehler}", file=sys.stderr)
        return 2


def _release_befehl(a: argparse.Namespace, konfig: Konfig, projekt: str) -> int:
    ausgeliefert = None
    if a.ausgeliefert:
        ausgeliefert = commit_von(a.repo, a.ausgeliefert) if git_wurzel(a.repo) else None
        if ausgeliefert is None:
            if not re.fullmatch(HEX, a.ausgeliefert):
                raise WaechterFehler(f"--ausgeliefert {a.ausgeliefert!r} ist kein bekannter Commit")
            ausgeliefert = a.ausgeliefert
    if a.erzwingen and len(a.grund.strip()) < GRUND_MIN_ZEICHEN:
        raise WaechterFehler(f"--erzwingen braucht --grund mit mindestens {GRUND_MIN_ZEICHEN} Zeichen")
    return lock_freigeben(konfig, projekt, a.halter, a.ergebnis, ausgeliefert, a.erzwingen, a.grund)


def _obermenge_befehl(a: argparse.Namespace, konfig: Konfig, projekt: str) -> int:
    if (a.trotzdem or a.bewusst_draussen) and len(a.grund.strip()) < GRUND_MIN_ZEICHEN:
        raise WaechterFehler(f"--trotzdem und --bewusst-draussen brauchen --grund mit mindestens "
                             f"{GRUND_MIN_ZEICHEN} Zeichen (kommt ins Log)")
    if a.bewusst_draussen:
        commit = commit_von(a.repo, a.bewusst_draussen)
        if commit is None:
            raise WaechterFehler(f"{a.bewusst_draussen!r} ist kein bekannter Commit")
        wer = mensch_bestaetigt(f"Ausgelieferten Stand {commit[:12]} dauerhaft von der Obermenge ausnehmen.", a.grund)
        log_schreiben(konfig, projekt, f"BEWUSST DRAUSSEN · bewusst-draussen={commit} · Benutzer {_text(wer)} · "
                                       f"{_text(a.grund)}")
        print(f"vermerkt: {commit[:12]} ist bewusst nicht im Ziel ({a.grund})")
        return 0
    if a.fetch:
        git(a.repo, "fetch", "--all", "--quiet", pruefen=True)
    befund = obermenge_pruefen(a.repo, konfig, projekt, a.ziel, a.art, not a.ohne_arbeitskopie)
    obermenge_ausgeben(befund, a.art)
    if not befund.blockiert:
        print("OK: Obermenge bewiesen. Jeder ausgelieferte Stand ist ein Vorfahre des Ziels.")
        if befund.weich:
            print("    Die WEICH-Liste ist kein Fehler, aber sie muss eine Entscheidung sein.")
        return 0
    if befund.schmutzig:
        print("NICHT AUS DIESEM ORDNER DEPLOYEN: uncommittete Arbeit würde mit hochgeladen.")
        print("    Aus einem sauberen Stand bauen, z. B. 'git clone --local' oder 'git worktree add --detach'.")
    if befund.hart:
        print("NICHT DEPLOYEN: dieser Stand würde Ausgeliefertes zurückwerfen.")
        print("    Die fehlende Arbeit HEREIN mergen (in einer sauberen Kopie, nie umgekehrt), dann neu prüfen.")
    if befund.ohne_basis:
        print("NICHT DEPLOYEN ohne bekannte Basis. Beim allerersten Deploy übersteuert ein Mensch am Terminal:")
        print("    --trotzdem --grund \"erster Deploy dieses Projekts\".")
    if not a.trotzdem:
        return 1
    wer = mensch_bestaetigt(f"Obermenge-Sperre für Ziel {a.ziel} übersteuern.", a.grund)
    fehlend = ",".join(kurz(c) for c, _ in befund.hart) or "-"
    log_schreiben(konfig, projekt, f"OBERMENGE ÜBERSTEUERT · Ziel {_text(a.ziel)} · fehlend {fehlend} · "
                                   f"uncommittet {len(befund.schmutzig)} · Benutzer {_text(wer)} · "
                                   f"Grund: {_text(a.grund)}")
    print(f"ÜBERSTEUERT von {wer} (im Log vermerkt): {a.grund}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
