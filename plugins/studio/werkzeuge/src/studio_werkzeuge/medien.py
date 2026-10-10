# SPDX-License-Identifier: MIT
"""Datei-Hülle: ffprobe und ffmpeg. Kein Rechnen hier, damit Tests diese Grenze ersetzen können.

Pfade gehen immer absolut an ffmpeg (ein Dateiname mit führendem „-“ würde sonst als Option gelesen), und ffmpeg
läuft mit ``-nostdin`` (sonst kann es auf Tastatureingaben warten oder stdin eines Wächters verschlucken).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from fractions import Fraction
from pathlib import Path

import numpy as np

from studio_werkzeuge.fehler import StudioFehler

# Unter pythonw (Wächter im Hintergrund) öffnet sonst jeder ffmpeg-Aufruf kurz ein Konsolenfenster.
OHNE_FENSTER: dict = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
FFMPEG = ["ffmpeg", "-nostdin"]


def arg(pfad: Path | str) -> str:
    """Pfad als absoluter Text für die Befehlszeile."""
    return str(Path(pfad).absolute())


def lauf(aufruf: list[str], was: str, timeout: float | None = None) -> bytes:
    """Prozess ausführen, stdout als Bytes. Fehlt das Programm oder scheitert es, kommt ein ``StudioFehler``."""
    try:
        return subprocess.run(aufruf, capture_output=True, check=True, timeout=timeout, **OHNE_FENSTER).stdout
    except FileNotFoundError as e:
        raise StudioFehler(f"{aufruf[0]} nicht gefunden. Ist ffmpeg installiert und im PATH?") from e
    except subprocess.TimeoutExpired as e:
        raise StudioFehler(f"{was}: nach {timeout:.0f} s abgebrochen.") from e
    except subprocess.CalledProcessError as e:
        raise StudioFehler(f"{was} fehlgeschlagen: {e.stderr.decode('utf-8', 'replace').strip()[-400:]}") from e


def _ganz(wert, was: str) -> int:
    try:
        return int(wert)
    except (TypeError, ValueError) as e:
        raise StudioFehler(f"ffprobe liefert keine Zahl für {was} ({wert!r}).") from e


def medien_info(pfad: Path) -> dict:
    """Dauer (s) und ob ein Ton- bzw. Bildstrom da ist."""
    roh = lauf(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type:format=duration", "-of", "json",
                arg(pfad)], f"ffprobe {Path(pfad).name}")
    try:
        daten = json.loads(roh.decode("utf-8", "replace"))
        dauer = float((daten.get("format") or {}).get("duration") or 0.0)
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        raise StudioFehler(f"ffprobe liefert keine brauchbare Dauer für {pfad}") from e
    stroeme = daten.get("streams") or []
    return {"dauer_s": dauer, "hat_ton": any(s.get("codec_type") == "audio" for s in stroeme),
            "hat_bild": any(s.get("codec_type") == "video" for s in stroeme)}


def video_info(pfad: Path) -> dict:
    """Breite, Höhe, Bildrate (``fps`` als Zahl, ``fps_bruch`` exakt), Bildzahl (gezählte Pakete), Dauer, Ton?"""
    roh = lauf(["ffprobe", "-v", "error", "-count_packets", "-show_entries",
                "stream=codec_type,width,height,r_frame_rate,nb_read_packets:format=duration", "-of", "json",
                arg(pfad)], f"ffprobe {Path(pfad).name}")
    try:
        daten = json.loads(roh.decode("utf-8", "replace"))
    except json.JSONDecodeError as e:
        raise StudioFehler(f"ffprobe liefert kein JSON für {pfad}") from e
    stroeme = daten.get("streams") or []
    bild = next((s for s in stroeme if s.get("codec_type") == "video"), None)
    if bild is None:
        raise StudioFehler(f"{Path(pfad).name} hat keinen Bildstrom (leere Aufnahme?).")
    teile = str(bild.get("r_frame_rate", "0/1")).split("/")
    zaehler, nenner = _ganz(teile[0], "die Bildrate"), _ganz(teile[1] if len(teile) > 1 else 1, "die Bildrate")
    bilder = _ganz(bild.get("nb_read_packets") or 0, "die Bildzahl")
    if bilder <= 0 or zaehler <= 0 or nenner <= 0:
        raise StudioFehler(f"{Path(pfad).name} enthält keine lesbaren Bilder.")
    try:
        dauer = float((daten.get("format") or {}).get("duration") or 0.0)
    except ValueError:
        dauer = 0.0
    return {"breite": bild.get("width"), "hoehe": bild.get("height"), "fps": zaehler / nenner,
            "fps_bruch": f"{zaehler}/{nenner}", "bilder": bilder, "dauer": dauer,
            "hat_ton": any(s.get("codec_type") == "audio" for s in stroeme)}


def fps_bruch(info: dict) -> Fraction:
    return Fraction(info.get("fps_bruch") or info["fps"]).limit_denominator(100_000)


def audio_laden(pfad: Path, rate_hz: int) -> np.ndarray:
    """Mono-Ton als float32 (−1..1) per ffmpeg-Pipe. Eine fehlende oder unlesbare Datei ist ein Fehler, nie
    „kein Ton“ (sonst sähe ein kaputter Aufruf wie eine grüne Ampel aus)."""
    if not Path(pfad).is_file():
        raise StudioFehler(f"Datei fehlt: {pfad}")
    roh = lauf([*FFMPEG, "-v", "error", "-i", arg(pfad), "-vn", "-ac", "1", "-ar", str(rate_hz), "-f", "f32le", "-"],
               f"Ton lesen ({Path(pfad).name})")
    return np.frombuffer(roh, dtype=np.float32)


def bilder_zaehlen(pfad: Path) -> int:
    roh = lauf(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                "stream=nb_read_packets", "-of", "csv=p=0", arg(pfad)], f"ffprobe {Path(pfad).name}")
    return _ganz(roh.decode("ascii", "replace").strip().split(",")[0], f"die Bildzahl von {Path(pfad).name}")


def lautheit_messen(pfad: Path, vorfilter: str = "") -> dict:
    """Integrierte Lautheit (LUFS), Lautheitsumfang (LU) und True Peak (dBTP) nach EBU R 128 / ITU-R BS.1770.
    True Peak wird bei 192 kHz gemessen (vierfache Überabtastung bei 48 kHz, wie BS.1770 Anhang 2 empfiehlt).
    Stille kommt als sehr kleiner Wert (−70) oder ``-inf`` zurück; der Aufrufer muss sie abfangen."""
    kette = ",".join(x for x in (vorfilter, "aresample=192000", "ebur128=peak=true:framelog=quiet") if x)
    try:
        r = subprocess.run([*FFMPEG, "-hide_banner", "-nostats", "-i", arg(pfad), "-vn", "-af", kette, "-f", "null",
                            "-"], capture_output=True, **OHNE_FENSTER)
    except FileNotFoundError as e:
        raise StudioFehler("ffmpeg nicht gefunden. Ist ffmpeg installiert und im PATH?") from e
    text = r.stderr.decode("utf-8", "replace")
    if r.returncode != 0:
        raise StudioFehler(f"Messung von {pfad} gescheitert: {text.strip()[-300:]}")
    return ebur128_lesen(text)


def ebur128_lesen(text: str) -> dict:
    """Die Zusammenfassung von ffmpeg ``ebur128`` lesen."""
    if "Summary:" not in text:
        raise StudioFehler("ebur128 liefert keine Zusammenfassung (Datei ohne Ton?).")
    t = text[text.rfind("Summary:"):]

    def zahl(muster: str) -> float:
        m = re.search(muster, t)
        if not m:
            raise StudioFehler(f"ebur128: {muster} fehlt in der Zusammenfassung")
        return float(m.group(1))

    # Leerraum als "[ \t]" statt Backslash-s: so sieht kein Muster wie ein Laufwerkspfad aus (Leck-Prüfung im Repo).
    return {"lufs": zahl(r"I:[ \t]+(-?[\d.]+|-inf) LUFS"), "lra": zahl(r"LRA:[ \t]+(-?[\d.]+) LU"),
            "dbtp": zahl(r"Peak:[ \t]+(-?[\d.]+|-inf) dBFS")}
