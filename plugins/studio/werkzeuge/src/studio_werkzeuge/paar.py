# SPDX-License-Identifier: MIT
"""Zwei-Kamera-Paar aus OBS Source Record bildgenau deckungsgleich machen (`studio paar`).

Je Take entsteht ein Ordner, benannt wie die OBS-Aufnahme („2026-03-14 10-15-00“), bei einem roten Befund
„… PRUEFEN“, darin zwei Videos: ``<name> Cam A.mp4`` und ``<name> Cam B.mp4`` (gleiche Bildzahl, gleicher Start,
bytegleiche Tonspur). Kamera A bleibt im Bild unverändert (Stream-Copy) und gibt Zeitachse und Länge vor; Kamera B wird
neu kodiert und dabei auf A gelegt. Gebaut wird in einem Arbeitsordner; erst nach der Prüfung kommen die Dateien an den
Zielort. Liegt dort schon eine ältere Fassung, wandert sie vorher nach ``<Take>/Alt-<zeit>/``; scheitert das Ablegen,
wird zurückgerollt und der Arbeitsordner bleibt als „~Fehler …“ zum Prüfen liegen. Der Bericht liegt in
``<ziel>/synchron/<name>.json``. Ein Bau je Ziel zur selben Zeit (Sperre ``<ziel>/synchron/bau.lock``).

Rohdateien: Voreinstellung ``behalten`` (sie wandern nach ``<Take>/Roh/``). ``papierkorb`` verschiebt sie nach einem
grünen und nachgeprüften Bau nach ``<ziel>/_Papierkorb/<Take>/`` (nie endgültig löschen; leeren entscheidet der
Mensch); ``--roh-lassen`` fasst sie gar nicht an.

Exit: 0 grün · 1 gebaut, aber rot (Ordner „… PRUEFEN“, Gründe im Bericht) · 2 Eingabe- oder Konfigurationsfehler.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path

import numpy as np

from studio_werkzeuge import medien
from studio_werkzeuge.fehler import KeinTon, KonfigFehler, StudioFehler, ZuKurzeUeberlappung
from studio_werkzeuge.klicks import klicks_zaehlen
from studio_werkzeuge.konfig import Konfig
from studio_werkzeuge.sicher import Sperre, umbenennen, verschieben
from studio_werkzeuge.synchron import (
    STANDBILD_ANTEIL,
    Bewegung,
    Plan,
    bild_lage,
    luecke_entscheiden,
    plan_bauen,
    standbild_anteil,
    ton_wahl,
    versatz_finden,
    versatz_zerlegen,
)

ANALYSE_RATE = 16_000
TON_RATE = 48_000
FENSTER_S = 20.0                  # Länge des Ton-Musters aus Kamera B
MIN_FENSTER_S = 4.0
MAX_STEMPEL_ABSTAND_S = 2         # Dateinamen von A und B EINES Takes liegen höchstens so weit auseinander
BEWEGUNG_FENSTER_S = 120.0        # Hauptmessung über die Mitte des Takes
GEGENPROBE_FENSTER_S = 30.0
KANTEN_FENSTER_S = 60.0           # Anfang und Ende langer Takes je so lang vergleichen
KANTEN_MIN_DAUER_S = 150.0
PHASE_SPRUNG_MAX = 0.7            # Bilder: so weit darf der Bild-Versatz zwischen Anfang und Ende wandern
GEGENPROBE_TOLERANZ = 0.6         # Bilder nach dem Bauen (Rundung auf ganze Bilder lässt bis 0,5 übrig)
ABLEGEN_VERSUCHE = 5              # ein Player oder Schnittprogramm hält eine Datei kurz offen
ABLEGEN_PAUSE_S = 1.0
PRUEFEN_ZUSATZ = " PRUEFEN"
ARBEIT_PRAEFIX = "~in Arbeit "
FEHLER_PRAEFIX = "~Fehler "
PAPIERKORB = "_Papierkorb"
DREHUNG_B = {"keine": None, "rechts": "transpose=1", "links": "transpose=2"}
W, H = 128, 72                    # Bewegungsmessung auf kleinen Graubildern
STEMPEL_FORMAT = "%Y%m%d-%H%M%S"


@dataclass(frozen=True)
class Benennung:
    """Wie OBS die Kameradateien nennt: ``<praefix><JJJJMMTT-HHMMSS><endung>``."""

    praefix_a: str = "cam-A-"
    praefix_b: str = "cam-B-"
    endung: str = ".mp4"

    def __post_init__(self) -> None:
        if self.praefix_a.lower() == self.praefix_b.lower():
            raise KonfigFehler("praefix_a und praefix_b müssen sich unterscheiden (auch ohne Groß-/Kleinschreibung).")
        for teil in (self.praefix_a, self.praefix_b, self.endung):
            if any(z in teil for z in "/\\*?:"):
                raise KonfigFehler(f"[kameras] {teil!r}: keine Pfad- oder Platzhalterzeichen erlaubt.")

    @property
    def muster(self) -> re.Pattern[str]:
        return re.compile(rf"^(?:(?P<a>{re.escape(self.praefix_a)})|(?P<b>{re.escape(self.praefix_b)}))"
                          rf"(?P<s>\d{{8}}-\d{{6}}){re.escape(self.endung)}$", re.IGNORECASE)

    def treffer(self, name: str) -> tuple[str, str] | None:
        """(``"A"``/``"B"``, Stempel) oder None."""
        m = self.muster.match(name)
        if not m:
            return None
        return ("A" if m.group("a") else "B"), m.group("s")

    def glob(self, kamera: str = "") -> str:
        praefix = {"A": self.praefix_a, "B": self.praefix_b}.get(kamera, "")
        return f"{praefix}*{self.endung}"


@dataclass(frozen=True)
class Einstellungen:
    encoder: str = "libx264"
    cq: int = 18
    drehung_b: str = "keine"
    rohdateien: str = "behalten"      # behalten | papierkorb
    gegenprobe: bool = True


def benennung_aus(konfig: Konfig) -> Benennung:
    return Benennung(konfig.text("kameras", "praefix_a", "cam-A-"), konfig.text("kameras", "praefix_b", "cam-B-"),
                     konfig.text("kameras", "endung", ".mp4"))


def einstellungen_aus(konfig: Konfig) -> Einstellungen:
    e = Einstellungen(konfig.text("paar", "encoder", "libx264"), konfig.ganzzahl("paar", "cq", 18),
                      konfig.text("paar", "drehung_b", "keine"), konfig.text("paar", "rohdateien", "behalten"),
                      konfig.wahrheit("paar", "gegenprobe", True))
    if e.drehung_b not in DREHUNG_B:
        raise KonfigFehler(f"[paar] drehung_b muss {', '.join(DREHUNG_B)} sein, ist {e.drehung_b!r}.")
    if e.rohdateien not in ("behalten", "papierkorb"):
        raise KonfigFehler(f"[paar] rohdateien muss behalten oder papierkorb sein, ist {e.rohdateien!r}.")
    if e.encoder not in ("libx264", "h264_nvenc"):
        raise KonfigFehler(f"[paar] encoder muss libx264 oder h264_nvenc sein, ist {e.encoder!r}.")
    if not 0 <= e.cq <= 51:
        raise KonfigFehler(f"[paar] cq muss zwischen 0 und 51 liegen, ist {e.cq}.")
    return e


def bau_sperre(ziel: Path) -> Sperre:
    """Ein Bau je Ziel zur selben Zeit (auch Wächter, `--einmal` und Handaufruf untereinander)."""
    return Sperre(ziel / "synchron" / "bau.lock", "Ein anderer Bau")


# ── reine Hilfen ─────────────────────────────────────────────────────────────────────────────────

def abstand_s(s1: str, s2: str) -> float:
    return abs((datetime.strptime(s1, STEMPEL_FORMAT) - datetime.strptime(s2, STEMPEL_FORMAT)).total_seconds())


def ordner_name(stempel: str) -> str:
    """„20260314-101500“ → „2026-03-14 10-15-00“: so benennt OBS die Programm-Aufnahme desselben Takes."""
    try:
        return datetime.strptime(stempel, STEMPEL_FORMAT).strftime("%Y-%m-%d %H-%M-%S")
    except ValueError:
        return stempel


def fps_ausdruck(fps: float | Fraction | str) -> str:
    """Bildrate exakt für ffmpeg-Ausdrücke: 25 → „25“, 29,97 → „(30000/1001)“."""
    bruch = fps if isinstance(fps, Fraction) else Fraction(fps).limit_denominator(100_000)
    return str(bruch.numerator) if bruch.denominator == 1 else f"({bruch.numerator}/{bruch.denominator})"


def encoder_args(encoder: str, cq: int, fps: float) -> list[str]:
    gop = str(max(1, int(round(float(fps) * 2))))
    if encoder == "h264_nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p4", "-tune", "hq", "-rc", "vbr", "-cq", str(cq), "-b:v", "0",
                "-maxrate", "80M", "-bufsize", "160M", "-profile:v", "high", "-g", gop, "-bf", "0"]
    if encoder == "libx264":
        return ["-c:v", "libx264", "-preset", "veryfast", "-crf", str(cq), "-g", gop]
    raise StudioFehler(f"Unbekannter Encoder {encoder!r} (h264_nvenc oder libx264).")


def befehl_ton(quelle: Path, bilder: int, fps: float | Fraction, wav: Path, versatz_s: float = 0.0,
               quelle_s: float | None = None) -> list[str]:
    """Mikrofonspur, exakt ``bilder`` Bilder lang (hinten mit Stille aufgefüllt). ``versatz_s`` > 0 schneidet vorne so
    viel weg, < 0 setzt Stille davor; Übergänge zur Stille werden 5 ms ein-/ausgeblendet (kein Klick an der Naht)."""
    n = int(round(bilder / float(fps) * TON_RATE))
    n0 = int(round(versatz_s * TON_RATE))
    if n0 > 0:
        schub = f"atrim=start_sample={n0},asetpts=PTS-STARTPTS,"
    elif n0 < 0:
        schub = f"adelay={-n0}S:all=1,afade=t=in:st={-n0 / TON_RATE:.6f}:d=0.005,"
    else:
        schub = ""
    ende = None if quelle_s is None else quelle_s - n0 / TON_RATE
    if ende is not None and 0.01 < ende < n / TON_RATE - 0.001:
        schub += f"afade=t=out:st={ende - 0.005:.6f}:d=0.005,"
    return [*medien.FFMPEG, "-v", "error", "-y", "-i", medien.arg(quelle), "-vn", "-map", "0:a:0",
            "-af", f"aresample={TON_RATE},{schub}apad=whole_len={n},atrim=end_sample={n}", "-ac", "2",
            "-c:a", "pcm_s24le", medien.arg(wav)]


def befehl_aac(wav: Path, m4a: Path) -> list[str]:
    return [*medien.FFMPEG, "-v", "error", "-y", "-i", medien.arg(wav), "-c:a", "aac", "-aac_coder", "fast",
            "-b:a", "320k", medien.arg(m4a)]


def befehl_kopie(quelle: Path, ton: Path, ziel: Path) -> list[str]:
    """Bild unverändert übernehmen, Ton ersetzen."""
    return [*medien.FFMPEG, "-v", "error", "-y", "-i", medien.arg(quelle), "-i", medien.arg(ton), "-map", "0:v:0",
            "-map", "1:a:0", "-c", "copy", "-movflags", "+faststart", medien.arg(ziel)]


def befehl_neu(quelle: Path, ton: Path, plan: Plan, fps: float | Fraction, ziel: Path, encoder: str, cq: int,
               drehen: str | None = None) -> list[str]:
    """Kamera B auf A legen: vorne Standbilder davor oder Bilder weg, genau ``plan.bilder`` Bilder, optional drehen."""
    if plan.vorne >= 0:
        vf = f"tpad=start_mode=clone:start={plan.vorne}," if plan.vorne else ""
        vf += f"trim=end_frame={plan.bilder - plan.auffuellen}"
    else:
        vf = f"trim=start_frame={-plan.vorne}:end_frame={-plan.vorne + plan.bilder - plan.auffuellen}"
    if drehen:
        vf += f",{drehen}"
    if plan.auffuellen:
        vf += f",tpad=stop_mode=clone:stop={plan.auffuellen}"
    # Zeitstempel zuletzt neu aus dem Bildindex (exakte Bildrate, auch 30000/1001): tpad am Anfang hinterlässt sonst
    # doppelte oder zu kurze Stempel.
    vf += f",setpts=N/{fps_ausdruck(fps)}/TB"
    return [*medien.FFMPEG, "-v", "error", "-y", "-i", medien.arg(quelle), "-i", medien.arg(ton), "-map", "0:v:0",
            "-map", "1:a:0", "-vf", vf, "-fps_mode", "passthrough", "-frames:v", str(plan.bilder),
            *encoder_args(encoder, cq, float(fps)), "-pix_fmt", "yuv420p", "-color_range", "tv", "-colorspace",
            "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-c:a", "copy", "-movflags", "+faststart",
            medien.arg(ziel)]


# ── Dateien finden und ablegen ───────────────────────────────────────────────────────────────────

def such_orte(inbox: Path, ziel: Path | None = None) -> list[Path]:
    """Wo Rohdateien liegen können: lose in der Inbox, direkt in ``<inbox>/<Take>/``, in ``<ziel>/<Take>/Roh/``."""
    orte = [inbox]
    if inbox.is_dir():
        orte += sorted(p for p in inbox.iterdir() if p.is_dir() and p.name != PAPIERKORB)
    if ziel is not None and ziel.is_dir():
        orte += sorted(p / "Roh" for p in ziel.iterdir() if (p / "Roh").is_dir())
    return orte


def paar_finden(inbox: Path, stempel: str | None = None, ziel: Path | None = None,
                benennung: Benennung | None = None) -> tuple[Path, Path, str]:
    """A und B desselben Takes. Ohne Stempel gilt der neueste Stempel im Dateinamen. B darf höchstens
    ``MAX_STEMPEL_ABSTAND_S`` neben A liegen und muss umgekehrt am nächsten an DIESEM A liegen."""
    benennung = benennung or Benennung()
    a_dateien: dict[str, Path] = {}
    b_dateien: dict[str, Path] = {}
    for ort in such_orte(inbox, ziel):
        for p in sorted(ort.glob(benennung.glob())) if ort.is_dir() else []:
            t = benennung.treffer(p.name)
            if t:   # das erste Vorkommen gewinnt (lose Inbox vor den Unterordnern)
                (a_dateien if t[0] == "A" else b_dateien).setdefault(t[1], p)
    if not a_dateien:
        raise StudioFehler(f"Keine {benennung.glob('A')} in {inbox} (auch nicht in <Take>/ oder <Take>/Roh/).")
    stempel = stempel or max(a_dateien)
    if stempel not in a_dateien:
        raise StudioFehler(f"{benennung.praefix_a}{stempel}{benennung.endung} fehlt in {inbox}")
    naechste = min(b_dateien, key=lambda s: abstand_s(s, stempel), default=None)
    if naechste is None or abstand_s(naechste, stempel) > MAX_STEMPEL_ABSTAND_S:
        raise StudioFehler(f"Zum Take {stempel} gibt es keine B-Datei (±{MAX_STEMPEL_ABSTAND_S} s). Hat Kamera B "
                           "aufgenommen?")
    zurueck = min(a_dateien, key=lambda s: abstand_s(s, naechste))
    if zurueck != stempel:
        raise StudioFehler(f"Die B-Datei {naechste} liegt näher an Take {zurueck}: Paar zu {stempel} nicht eindeutig.")
    return a_dateien[stempel], b_dateien[naechste], stempel


def take_ordner(ziel: Path, name: str) -> Path:
    """Der Take-Ordner, wie er jetzt heißt („<name>“ oder „<name> PRUEFEN“); sonst „<name>“ (noch nicht angelegt)."""
    for kandidat in (ziel / name, ziel / f"{name}{PRUEFEN_ZUSATZ}"):
        if kandidat.is_dir():
            return kandidat
    return ziel / name


def take_ordner_vorbereiten(ziel: Path, name: str, rot: bool) -> tuple[Path, str | None, tuple[Path, Path] | None]:
    """„<name>“ (grün) oder „<name> PRUEFEN“ (rot). Gibt es den Ordner unter dem anderen Namen, wird er samt ``Roh/``
    umbenannt; sind beide Namen belegt, kommt der alte als „… ALT <zeit>“ beiseite. Rückgabe: Ordner, Hinweis,
    Umzug alt→neu (damit Pfade in den umbenannten Ordner nachgeführt werden können)."""
    ordner = ziel / (name + (PRUEFEN_ZUSATZ if rot else ""))
    anderer = ziel / (name if rot else name + PRUEFEN_ZUSATZ)
    hinweis, umzug = None, None
    if anderer.exists():
        if not ordner.exists():
            urteil = "mit neuem Urteil " if (anderer / f"{name} Cam A.mp4").is_file() else ""
            anderer.rename(ordner)
            umzug = (anderer, ordner)
            hinweis = f"Take-Ordner {urteil}umbenannt: „{anderer.name}“ → „{ordner.name}“"
        else:
            alt = ziel / f"{anderer.name} ALT {datetime.now().strftime('%H-%M-%S')}"
            anderer.rename(alt)
            umzug = (anderer, alt)
            hinweis = f"Älteres Ergebnis mit anderem Urteil beiseitegestellt: „{alt.name}“"
    ordner.mkdir(exist_ok=True)
    return ordner, hinweis, umzug


def pfad_nach_umzug(p: Path, umzug: tuple[Path, Path] | None) -> Path:
    if umzug is None:
        return p
    try:
        return umzug[1] / p.relative_to(umzug[0])
    except ValueError:
        return p


def ablegen(dateien: dict[str, Path], ordner: Path, versuche: int = ABLEGEN_VERSUCHE,
            pause_s: float = ABLEGEN_PAUSE_S) -> list[str]:
    """Die fertigen Dateien in ``ordner`` legen, ohne etwas ohne Sicherung zu überschreiben. Liegt schon eine
    Fassung dort, wandert sie vorher nach ``ordner/Alt-<zeit>/``. Scheitert ein Schritt (auch nach Wiederholungen),
    wird alles zurückgerollt: die neuen Dateien zurück an ihren Ort, die alten an ihren Platz. Gibt Hinweise zurück."""
    alt_ordner = ordner / f"Alt-{datetime.now():%Y%m%d-%H%M%S}"
    beiseite: list[tuple[Path, Path]] = []      # (ursprünglich, gesichert)
    abgelegt: list[tuple[Path, Path]] = []      # (Arbeitsdatei, Ziel)
    hinweise: list[str] = []

    def mit_wiederholung(schritt: Callable[[], None], was: str) -> None:
        for versuch in range(versuche):
            try:
                schritt()
                return
            except OSError as e:
                if versuch == versuche - 1:
                    raise StudioFehler(f"{was}: {e}. Ist die Datei gerade in einem Programm geöffnet?") from e
                time.sleep(pause_s)

    try:
        for quelle in dateien.values():
            ziel = ordner / quelle.name
            if ziel.exists():
                alt_ordner.mkdir(exist_ok=True)
                mit_wiederholung(lambda z=ziel: umbenennen(z, alt_ordner / z.name), f"„{ziel.name}“ beiseitelegen")
                beiseite.append((ziel, alt_ordner / ziel.name))
        for quelle in dateien.values():
            ziel = ordner / quelle.name
            mit_wiederholung(lambda q=quelle, z=ziel: umbenennen(q, z), f"„{quelle.name}“ ablegen")
            abgelegt.append((quelle, ziel))
    except StudioFehler:
        for quelle, ziel in reversed(abgelegt):
            try:
                umbenennen(ziel, quelle)
            except OSError:
                pass
        for ursprung, gesichert in reversed(beiseite):
            try:
                umbenennen(gesichert, ursprung)
            except OSError:
                pass
        if alt_ordner.is_dir() and not any(alt_ordner.iterdir()):
            alt_ordner.rmdir()
        raise
    if beiseite:
        hinweise.append(f"Ältere Fassung gesichert in „{alt_ordner.name}“ (löschen entscheidet der Mensch).")
    return hinweise


def roh_mitnehmen(ordner: Path, dateien: tuple[Path, ...]) -> tuple[Path, list[str]]:
    """Die Rohdateien nach ``<ordner>/Roh/`` verschieben. Liegt eine schon dort, bleibt sie."""
    roh = ordner / "Roh"
    roh.mkdir(exist_ok=True)
    hinweise = []
    for p in dateien:
        ziel = roh / p.name
        if ziel.exists():
            continue
        try:
            verschieben(p, ziel)
        except OSError as e:
            hinweise.append(f"Rohdatei {p.name} nicht verschoben ({e}).")
    return roh, hinweise


def papierkorb_ordner(ziel: Path, name: str) -> Path:
    return ziel / PAPIERKORB / name


def in_den_papierkorb(dateien: tuple[Path, ...], korb: Path) -> list[str]:
    """Rohdateien nach ``korb`` verschieben (umbenennen, über Laufwerke mit geprüfter Kopie). Nie löschen."""
    hinweise = []
    korb.mkdir(parents=True, exist_ok=True)
    for p in dateien:
        try:
            verschieben(p, korb / p.name)
        except OSError as e:
            hinweise.append(f"Rohdatei {p.name} nicht in {PAPIERKORB} gelegt ({e}).")
    return hinweise


def bericht_pfad(ziel: Path, name: str) -> Path:
    return ziel / "synchron" / f"{name}.json"


def take_einsortieren(a: Path, b: Path, ziel: Path, stempel: str) -> dict:
    """Gleich nach dem Stop: A und B nach ``<ziel>/<Take>/Roh/``, damit die Videos eines Takes nie lose liegen."""
    ordner = take_ordner(ziel, ordner_name(stempel))
    ordner.mkdir(parents=True, exist_ok=True)
    roh, hinweise = roh_mitnehmen(ordner, (a, b))
    jetzt = {cam: roh / p.name if (roh / p.name).is_file() else p for cam, p in (("A", a), ("B", b))}
    return {"ordner": ordner, "A": jetzt["A"], "B": jetzt["B"], "hinweise": hinweise}


def arbeitsordner_anlegen(ziel: Path, name: str) -> Path:
    """Arbeitsordner mit PID-Datei: so erkennt das Aufräumen, ob der Bau noch lebt."""
    ziel.mkdir(parents=True, exist_ok=True)
    arbeit = Path(tempfile.mkdtemp(dir=ziel, prefix=f"{ARBEIT_PRAEFIX}{name} "))
    (arbeit / "pid.txt").write_text(str(os.getpid()), encoding="ascii")
    return arbeit


def arbeitsordner_behalten(arbeit: Path) -> Path:
    """Nach einem Fehler: Arbeitsordner unter „~Fehler …“ liegen lassen (das Aufräumen fasst ihn nicht an)."""
    neu = arbeit.with_name(FEHLER_PRAEFIX + arbeit.name.removeprefix(ARBEIT_PRAEFIX))
    try:
        arbeit.rename(neu)
        return neu
    except OSError:
        return arbeit


# ── Messen über ffmpeg ───────────────────────────────────────────────────────────────────────────

def bewegung_lesen(aufruf: list[str], was: str) -> np.ndarray:
    """ffmpeg liefert 128×72-NV12-Bilder, stückweise gelesen. stderr wird parallel geleert, sonst blockiert ffmpeg bei
    vielen Warnungen am vollen Puffer und die Schleife hängt."""
    fb = W * H * 3 // 2
    try:
        p = subprocess.Popen(aufruf, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             **medien.OHNE_FENSTER)
    except FileNotFoundError as e:
        raise StudioFehler("ffmpeg nicht gefunden. Ist ffmpeg im PATH?") from e
    fehler_teile: list[bytes] = []
    leser = threading.Thread(target=lambda: fehler_teile.append(p.stderr.read()), daemon=True)
    leser.start()
    werte: list[np.ndarray] = []
    rest, vorher = b"", None
    while stueck := p.stdout.read(fb * 256):
        daten = rest + stueck
        n = len(daten) // fb
        rest = daten[n * fb:]
        if n == 0:
            continue
        y = np.frombuffer(daten[: n * fb], dtype=np.uint8).reshape(n, fb)[:, : W * H].astype(np.float32)
        if vorher is not None:
            y = np.vstack([vorher[None, :], y])
        if len(y) > 1:
            werte.append(np.abs(np.diff(y, axis=0)).mean(axis=1))
        vorher = y[-1]
    rc = p.wait()
    leser.join(timeout=10)
    if rc != 0:
        raise StudioFehler(f"{was} fehlgeschlagen: {b''.join(fehler_teile).decode('utf-8', 'replace').strip()[-400:]}")
    return np.concatenate(werte) if werte else np.zeros(0, dtype=np.float32)


def bewegung(pfad: Path, start_s: float, dauer_s: float, gpu: bool = False) -> np.ndarray:
    """Bewegungsenergie je Bild: mittlere Betragsdifferenz aufeinanderfolgender 128×72-Graubilder."""
    zeit = ["-ss", f"{start_s:.3f}", "-t", f"{dauer_s:.3f}"]
    aus = ["-f", "rawvideo", "-pix_fmt", "nv12", "-"]
    cpu = [*medien.FFMPEG, "-v", "error", *zeit, "-i", medien.arg(pfad), "-vf", f"scale={W}:{H}:flags=area", *aus]
    if gpu:
        gpu_aufruf = [*medien.FFMPEG, "-v", "error", "-hwaccel", "cuda", "-hwaccel_output_format", "cuda", *zeit,
                      "-i", medien.arg(pfad), "-vf", f"scale_cuda={W}:{H},hwdownload,format=nv12", *aus]
        try:
            return bewegung_lesen(gpu_aufruf, "Bewegung (GPU)")
        except StudioFehler:
            pass
    return bewegung_lesen(cpu, f"Bewegung {pfad.name}")


def ton_pruefsumme(pfad: Path) -> str:
    """MD5 der Tonpakete (ohne Dekodieren): gleich = bytegleiche Tonspur."""
    roh = medien.lauf([*medien.FFMPEG, "-v", "error", "-i", medien.arg(pfad), "-map", "0:a:0", "-c", "copy", "-f",
                       "md5", "-"], f"Ton-Prüfsumme {pfad.name}")
    return roh.decode("ascii", "replace").strip().removeprefix("MD5=")


def _ton_versatz(ta: np.ndarray, tb: np.ndarray, start_s: float) -> tuple[float, float]:
    """A-Zeit minus B-Zeit desselben Moments, gemessen an einem B-Fenster ab ``start_s`` (Sekunden, Konfidenz)."""
    rest_s = len(tb) / ANALYSE_RATE - start_s
    fenster = min(FENSTER_S, rest_s)
    if fenster < MIN_FENSTER_S:
        raise ZuKurzeUeberlappung(f"Zu wenig Ton in Kamera B ab {start_s:.1f} s ({rest_s:.1f} s).")
    s0 = int(round(start_s * ANALYSE_RATE))
    v = versatz_finden(ta, tb[s0: s0 + int(round(fenster * ANALYSE_RATE))], ANALYSE_RATE)
    return v.lag_s - start_s, v.konfidenz


def _bewegung_bericht(b: Bewegung) -> dict:
    return {"lage_bilder": None if b.lage is None else round(b.lage, 2), "gipfel": round(b.gipfel, 3),
            "nebenmaximum": round(b.neben, 3), "bilder": b.bilder, "aussagekraeftig": b.aussagekraeftig}


def ergebnis_nachpruefen(dateien: dict[str, Path], soll_bilder: int) -> list[str]:
    """Vor dem Wegräumen der Rohdateien: liegen beide Ergebnisse am Zielort, haben Bild und Ton und so viele Bilder
    wie die Rohdatei von Kamera A? Gibt die Gründe zurück, die dagegen sprechen."""
    gruende = []
    for cam, pfad in dateien.items():
        if not pfad.is_file() or pfad.stat().st_size == 0:
            gruende.append(f"Ergebnis {cam} fehlt oder ist leer")
            continue
        info = medien.video_info(pfad)
        if not info["hat_ton"]:
            gruende.append(f"Ergebnis {cam} hat keinen Ton")
        if info["bilder"] != soll_bilder:
            gruende.append(f"Ergebnis {cam} hat {info['bilder']} statt {soll_bilder} Bilder")
    return gruende


# ── Hauptlauf ────────────────────────────────────────────────────────────────────────────────────

def synchronisieren(a: Path, b: Path, ziel: Path, stempel: str, einst: Einstellungen | None = None,
                    probe: bool = False, roh_lassen: bool = False) -> dict:
    """Misst die Lücke, baut das Paar im Arbeitsordner, prüft es und legt die zwei Videos in den Take-Ordner.
    ``probe``: nur messen, nichts schreiben. Gibt den Bericht zurück (``ok`` = grün)."""
    einst = einst or Einstellungen()
    for pfad, was in ((a, "Kamera A"), (b, "Kamera B")):
        if not pfad.is_file():
            raise StudioFehler(f"{was} nicht gefunden: {pfad}")
    if einst.drehung_b not in DREHUNG_B:
        raise StudioFehler(f"Drehung {einst.drehung_b!r} unbekannt ({', '.join(DREHUNG_B)}).")
    uhr = time.perf_counter()
    zeiten: dict[str, float] = {}

    def stoppuhr(phase: str) -> None:
        nonlocal uhr
        zeiten[phase] = round(time.perf_counter() - uhr, 1)
        uhr = time.perf_counter()

    ia, ib = medien.video_info(a), medien.video_info(b)
    if medien.fps_bruch(ia) != medien.fps_bruch(ib):
        raise StudioFehler(f"Bildraten verschieden: A {ia['fps_bruch']}, B {ib['fps_bruch']}. Kameras und OBS gleich "
                           "einstellen.")
    fps = ia["fps"]
    bruch = medien.fps_bruch(ia)
    gpu = einst.encoder == "h264_nvenc"
    bericht: dict = {"fassung": 2, "erzeugt": datetime.now(UTC).isoformat(timespec="seconds"),
                     "stempel": stempel, "quellen": {"A": str(a), "B": str(b)}, "info": {"A": ia, "B": ib}, "fps": fps}

    # 1. Ton: Versatz im OBS-Takt, dazu die Klicks je Kamera. d0/konfidenz gelten erst nach gelungener Zerlegung.
    zerlegung, konfidenz, drift, d0 = None, 0.0, 0.0, None
    klicks = {"A": 0, "B": 0}
    if ia["hat_ton"] and ib["hat_ton"]:
        try:
            ta, tb = medien.audio_laden(a, ANALYSE_RATE), medien.audio_laden(b, ANALYSE_RATE)
            dauer_b = len(tb) / ANALYSE_RATE
            start = min(1.0, max(0.0, dauer_b - MIN_FENSTER_S - 0.5))
            d_mess, k_mess = _ton_versatz(ta, tb, start)
            ende = dauer_b - FENSTER_S - 1.0
            drift_mess = (_ton_versatz(ta, tb, ende)[0] - d_mess) if ende - start > FENSTER_S else 0.0
            zerlegung = versatz_zerlegen(d_mess, fps)
            d0, konfidenz, drift = d_mess, k_mess, drift_mess
            bericht["ton"] = {"versatz_ms": round(d0 * 1000, 2), "konfidenz": round(konfidenz, 3),
                              "drift_ms": round(drift * 1000, 2),
                              "zerlegung": asdict(zerlegung) | {"rest_ms": round(zerlegung.rest_s * 1000, 2)}}
        except (KeinTon, ZuKurzeUeberlappung) as e:
            zerlegung, konfidenz, drift, d0 = None, 0.0, 0.0, None
            bericht["ton"] = {"fehler": str(e)}
        klicks = {"A": klicks_zaehlen(medien.audio_laden(a, TON_RATE)),
                  "B": klicks_zaehlen(medien.audio_laden(b, TON_RATE))}
    else:
        bericht["ton"] = {"fehler": "Eine Datei hat keinen Tonstrom."}
    bericht["ton"]["klicks"] = klicks
    stoppuhr("ton_messen")

    # 2. Bild: Bewegung über den ganzen Take, Mitte = Messung, Anfang/Ende = Phasensprung
    ma = bewegung(a, 0.0, ia["bilder"] / fps + 1.0, gpu)
    mb = bewegung(b, 0.0, ib["bilder"] / fps + 1.0, gpu)
    n = min(len(ma), len(mb))
    stand = {"A": standbild_anteil(ma), "B": standbild_anteil(mb)}
    mitte = zerlegung.bilder if zerlegung else 0
    w_mitte = min(n, int(BEWEGUNG_FENSTER_S * fps))
    s_mitte = (n - w_mitte) // 2
    bew = bild_lage(ma[s_mitte: s_mitte + w_mitte], mb[s_mitte: s_mitte + w_mitte], mitte - 12, mitte + 12)
    bericht["bild"] = _bewegung_bericht(bew) | {"standbild": {k: round(v, 3) for k, v in stand.items()}}

    entscheidung = luecke_entscheiden(zerlegung, konfidenz, drift, bew, bilder_ab=(ia["bilder"], ib["bilder"]))
    warnungen, hinweise = list(entscheidung.warnungen), list(entscheidung.hinweise)
    if "fehler" in bericht["ton"]:
        hinweise.append(f"Ton: {bericht['ton']['fehler']}")
    rot = entscheidung.rot
    for cam, anteil in stand.items():
        if anteil >= STANDBILD_ANTEIL:
            warnungen.append(f"Kamera {cam} zeigt ein Standbild ({anteil:.0%} unbewegte Bilder): Kamera aus oder kein "
                             "Signal?")
            rot = True
    if n / fps >= KANTEN_MIN_DAUER_S:
        w = int(KANTEN_FENSTER_S * fps)
        s0, s1 = int(fps), n - int(fps) - w
        anfang = bild_lage(ma[s0: s0 + w], mb[s0: s0 + w], entscheidung.bilder - 6, entscheidung.bilder + 6)
        schluss = bild_lage(ma[s1: s1 + w], mb[s1: s1 + w], entscheidung.bilder - 6, entscheidung.bilder + 6)
        bericht["bild"]["anfang"], bericht["bild"]["ende"] = _bewegung_bericht(anfang), _bewegung_bericht(schluss)
        if anfang.aussagekraeftig and schluss.aussagekraeftig and abs(anfang.lage - schluss.lage) > PHASE_SPRUNG_MAX:
            warnungen.append(f"Bild-Versatz wandert im Take von {anfang.lage:.2f} auf {schluss.lage:.2f} Bilder "
                             "(Kamera-Phase gesprungen): das Paar stimmt nur in einem Teil.")
            rot = True
    plan = plan_bauen(entscheidung.bilder, ia["bilder"], ib["bilder"])
    stoppuhr("bild_messen")
    bericht.update(luecke_bilder=entscheidung.bilder, quelle=entscheidung.quelle, plan=asdict(plan),
                   warnungen=warnungen, hinweise=hinweise, zeiten_s=zeiten)
    if probe:
        bericht["ok"] = not rot
        bericht["probe"] = True
        return bericht

    # 3. Bauen im Arbeitsordner. Zeitachse = A (Stream-Copy), B wird darauf gelegt. Ton = Kamera mit den wenigsten
    #    Klicks, um den gemessenen Ton-Versatz auf die A-Zeitachse geschoben.
    fest = "A"
    quellen = {"A": a, "B": b}
    ton_quelle = ton_wahl(klicks, fest) if d0 is not None else fest
    ton_versatz = 0.0 if ton_quelle == fest else -d0
    bericht["ton"]["quelle"] = ton_quelle
    if ton_quelle != fest:
        hinweise.append(f"Ton aus Kamera {ton_quelle} statt {fest} (Klicks A {klicks['A']}, B {klicks['B']}), um "
                        f"{ton_versatz * 1000:+.2f} ms auf die Zeitachse von Kamera {fest} geschoben.")
    if min(klicks.values()) > 0:
        hinweise.append(f"Beide Kameras haben Klicks im Ton (A {klicks['A']}, B {klicks['B']}): Aufnahmeweg prüfen "
                        "(studio klick-check, Prüfreihenfolge in docs/so-filme-ich.md).")
    dauer = plan.bilder / fps
    fenster = max(1.0, min(GEGENPROBE_FENSTER_S, dauer - 0.5))
    t0 = max(0.0, (dauer - fenster) / 2)
    name = ordner_name(stempel)
    arbeit = arbeitsordner_anlegen(ziel, name)
    try:
        teile = {"A": arbeit / f"{name} Cam A.mp4", "B": arbeit / f"{name} Cam B.mp4",
                 "ton": arbeit / f"{name} Ton.wav"}
        m4a = arbeit / "ton.m4a"
        medien.lauf(befehl_ton(quellen[ton_quelle], plan.bilder, bruch, teile["ton"], ton_versatz,
                               (ia if ton_quelle == "A" else ib)["dauer"]), "Tonspur schreiben")
        medien.lauf(befehl_aac(teile["ton"], m4a), "Tonspur kodieren")
        stoppuhr("ton_bauen")
        medien.lauf(befehl_neu(quellen["B"], m4a, plan, bruch, teile["B"], einst.encoder, einst.cq,
                               DREHUNG_B[einst.drehung_b]), "Kamera B auf A legen")
        stoppuhr("cam_b_kodieren")
        medien.lauf(befehl_kopie(quellen["A"], m4a, teile["A"]), "Kamera A übernehmen")
        stoppuhr("cam_a_kopieren")

        # 4. Prüfen, bevor etwas an den Zielort kommt
        oa, ob = medien.video_info(teile["A"]), medien.video_info(teile["B"])
        md5 = {"A": ton_pruefsumme(teile["A"]), "B": ton_pruefsumme(teile["B"])}
        pruef: dict = {"bilder": {"A": oa["bilder"], "B": ob["bilder"], "soll": plan.bilder},
                       "groesse": {"A": f"{oa['breite']}x{oa['hoehe']}", "B": f"{ob['breite']}x{ob['hoehe']}"},
                       "drehung_b": einst.drehung_b, "ton_bytegleich": md5["A"] == md5["B"], "ton_md5": md5["A"],
                       "ton_klicks": klicks_zaehlen(medien.audio_laden(teile["A"], TON_RATE))}
        if oa["bilder"] != plan.bilder or ob["bilder"] != plan.bilder:
            warnungen.append(f"Bildzahl stimmt nicht: A {oa['bilder']}, B {ob['bilder']}, soll {plan.bilder}.")
            rot = True
        if not pruef["ton_bytegleich"]:
            warnungen.append("Die Tonspuren der beiden Videos sind nicht bytegleich.")
            rot = True
        if einst.gegenprobe:
            nach = bild_lage(bewegung(teile["A"], t0, fenster, gpu), bewegung(teile["B"], t0, fenster, gpu), -6, 6)
            pruef["gegenprobe"] = _bewegung_bericht(nach)
            if nach.aussagekraeftig and abs(nach.lage) > GEGENPROBE_TOLERANZ:
                warnungen.append(f"Nach dem Bauen liegen die Bilder {nach.lage:+.2f} Bilder auseinander.")
                rot = True
        stoppuhr("pruefen")
        ordner, umbenannt, umzug = take_ordner_vorbereiten(ziel, name, rot)
        if umbenannt:
            hinweise.append(umbenannt)
        hinweise += ablegen({"A": teile["A"], "B": teile["B"]}, ordner)
    except BaseException as e:
        behalten = arbeitsordner_behalten(arbeit)
        if isinstance(e, StudioFehler):
            raise StudioFehler(f"{e} Arbeitsordner zum Prüfen: {behalten}") from e
        raise
    shutil.rmtree(arbeit, ignore_errors=True)

    ausgaben = {cam: str(ordner / teile[cam].name) for cam in ("A", "B")}
    if not roh_lassen:
        quellen_jetzt = tuple(pfad_nach_umzug(p, umzug) for p in (a, b))
        gruende = [] if rot or einst.rohdateien == "behalten" else ergebnis_nachpruefen(
            {cam: Path(p) for cam, p in ausgaben.items()}, ia["bilder"])
        if rot or einst.rohdateien == "behalten" or gruende:
            if gruende:
                hinweise.append("Rohdateien bleiben (Nachprüfung vor dem Papierkorb): " + "; ".join(gruende))
            roh_ordner, roh_hinweise = roh_mitnehmen(ordner, quellen_jetzt)
            hinweise += roh_hinweise
            ausgaben["roh"] = str(roh_ordner)
        else:
            korb = papierkorb_ordner(ziel, name)
            hinweise += in_den_papierkorb(quellen_jetzt, korb)
            ausgaben["papierkorb"] = str(korb)
        for p in quellen_jetzt:   # ein leer gewordener Roh-Ordner bleibt nicht zurück
            if p.parent.name == "Roh" and p.parent.is_dir() and not any(p.parent.iterdir()):
                p.parent.rmdir()
    stoppuhr("ablegen")
    zeiten["gesamt"] = round(sum(zeiten.values()), 1)
    datei = bericht_pfad(ziel, name)
    datei.parent.mkdir(parents=True, exist_ok=True)
    bericht.update(pruefung=pruef, ok=not rot, ordner=str(ordner), ausgaben=ausgaben, bericht=str(datei))
    teil = datei.with_name(datei.name + ".part")
    teil.write_text(json.dumps(bericht, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(teil, datei)          # der Bericht darf ersetzt werden: er beschreibt immer den letzten Bau
    return bericht


# ── CLI ──────────────────────────────────────────────────────────────────────────────────────────

def einrichten(unter) -> None:
    p = unter.add_parser("paar", help="Zwei Kameradateien eines Takes bildgenau deckungsgleich machen",
                         description=__doc__.split("\n\n")[0])
    p.add_argument("ordner", nargs="?", type=Path, metavar="ORDNER",
                   help="Inbox mit den Rohdateien (ohne: [pfade] inbox aus der Konfiguration)")
    p.add_argument("--stempel", help="JJJJMMTT-HHMMSS aus dem Dateinamen; ohne: das neueste Paar")
    p.add_argument("--a", type=Path, help="Kamera A direkt (mit --b)")
    p.add_argument("--b", type=Path, help="Kamera B direkt (mit --a)")
    p.add_argument("--ziel", type=Path, help="hier entsteht je Take ein Ordner (ohne: [pfade] ziel bzw. die Inbox)")
    p.add_argument("--roh-lassen", action="store_true", help="die Rohdateien gar nicht anfassen")
    p.add_argument("--b-drehung", choices=tuple(DREHUNG_B), help="Kamera B drehen (ohne: [paar] drehung_b)")
    p.add_argument("--encoder", choices=("libx264", "h264_nvenc"), help="ohne: [paar] encoder (libx264)")
    p.add_argument("--cq", type=int, choices=range(0, 52), metavar="0-51",
                   help="Qualität der neu kodierten Kamera B (kleiner = besser)")
    p.add_argument("--ohne-gegenprobe", action="store_true", help="die Bewegungs-Gegenprobe nach dem Bauen weglassen")
    p.add_argument("--probe", action="store_true", help="nur messen und den Plan zeigen, nichts schreiben")
    p.add_argument("--json", action="store_true", help="den Bericht als JSON ausgeben")
    p.set_defaults(ausfuehren=ausfuehren, braucht_konfig=False)


def ausfuehren(args, konfig: Konfig) -> int:
    basis = einstellungen_aus(konfig)
    einst = Einstellungen(args.encoder or basis.encoder, args.cq if args.cq is not None else basis.cq,
                          args.b_drehung or basis.drehung_b, basis.rohdateien,
                          basis.gegenprobe and not args.ohne_gegenprobe)
    benennung = benennung_aus(konfig)
    if args.a or args.b:
        if not (args.a and args.b):
            raise StudioFehler("--a und --b nur zusammen angeben.")
        a, b = args.a, args.b
        t = benennung.treffer(a.name)
        stempel = args.stempel or (t[1] if t else a.stem)
        ziel = args.ziel or konfig.pfad_wert("pfade", "ziel", a.parent)
    else:
        inbox = args.ordner or konfig.pfad_wert("pfade", "inbox")
        ziel = args.ziel or konfig.pfad_wert("pfade", "ziel", inbox)
        a, b, stempel = paar_finden(inbox, args.stempel, ziel, benennung)
    if not args.json:
        print(f"Paar {stempel}: {a.name} + {b.name}")
    if args.probe:
        bericht = synchronisieren(a, b, ziel, stempel, einst, probe=True)
    else:
        with bau_sperre(ziel):
            bericht = synchronisieren(a, b, ziel, stempel, einst, roh_lassen=args.roh_lassen)
    if args.json:
        print(json.dumps(bericht, ensure_ascii=False, indent=1))
        return 0 if bericht["ok"] else 1
    ton, bild = bericht.get("ton") or {}, bericht["bild"]
    print(f"Lücke: {bericht['luecke_bilder']} Bilder nach {bericht['quelle'].upper()} (Ton "
          f"{ton.get('versatz_ms', '–')} ms, Bewegung {bild['lage_bilder']}, "
          f"{'eindeutig' if bild['aussagekraeftig'] else 'nicht eindeutig'})")
    print(f"Ton: Klicks A {ton.get('klicks', {}).get('A', '–')} / B {ton.get('klicks', {}).get('B', '–')}"
          + (f" → Spur aus Kamera {ton['quelle']}" if ton.get("quelle") else ""))
    plan = bericht["plan"]
    was = f"{plan['vorne']} Standbilder davor" if plan["vorne"] >= 0 else f"{-plan['vorne']} Bilder vorne weg"
    print(f"Plan: Kamera A bleibt, Kamera B {was}, beide {plan['bilder']} Bilder")
    if "pruefung" in bericht:
        p = bericht["pruefung"]
        gp = (p.get("gegenprobe") or {}).get("lage_bilder")
        print(f"Prüfung: Bilder A {p['bilder']['A']} / B {p['bilder']['B']}, Ton bytegleich: {p['ton_bytegleich']}, "
              f"Gegenprobe {gp} Bilder")
        print(f"Ordner: {bericht['ordner']} · Bericht: {bericht['bericht']}")
    for w in bericht["warnungen"]:
        print(f"! {w}")
    for h in bericht["hinweise"]:
        print(f"· {h}")
    if bericht.get("probe"):
        print("Probe: nichts geschrieben.")
    print("GRÜN" if bericht["ok"] else "ROT: prüfen")
    return 0 if bericht["ok"] else 1
