# SPDX-License-Identifier: MIT
"""Datei-Hülle: ffprobe und ffmpeg. Kein Rechnen hier, damit Tests diese Grenze ersetzen können."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import numpy as np

from studio_werkzeuge.fehler import StudioFehler

# Unter pythonw (Wächter im Hintergrund) öffnet sonst jeder ffmpeg-Aufruf kurz ein Konsolenfenster.
OHNE_FENSTER: dict = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


def lauf(aufruf: list[str], was: str) -> bytes:
    """Prozess ausführen, stdout als Bytes. Fehlt das Programm oder scheitert es, kommt ein ``StudioFehler``."""
    try:
        return subprocess.run(aufruf, capture_output=True, check=True, **OHNE_FENSTER).stdout
    except FileNotFoundError as e:
        raise StudioFehler(f"{aufruf[0]} nicht gefunden. Ist ffmpeg installiert und im PATH?") from e
    except subprocess.CalledProcessError as e:
        raise StudioFehler(f"{was} fehlgeschlagen: {e.stderr.decode('utf-8', 'replace').strip()[-400:]}") from e


def medien_info(pfad: Path) -> dict:
    """Dauer (s) und ob ein Tonstrom da ist."""
    roh = lauf(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type:format=duration", "-of", "json",
                str(pfad)], f"ffprobe {pfad.name}")
    try:
        daten = json.loads(roh.decode("utf-8", "replace"))
        dauer = float((daten.get("format") or {}).get("duration") or 0.0)
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        raise StudioFehler(f"ffprobe liefert keine brauchbare Dauer für {pfad}") from e
    hat_ton = any(s.get("codec_type") == "audio" for s in daten.get("streams") or [])
    hat_bild = any(s.get("codec_type") == "video" for s in daten.get("streams") or [])
    return {"dauer_s": dauer, "hat_ton": hat_ton, "hat_bild": hat_bild}


def video_info(pfad: Path) -> dict:
    """Breite, Höhe, Bildrate, Bildzahl (gezählte Pakete), Dauer, ob ein Tonstrom da ist."""
    roh = lauf(["ffprobe", "-v", "error", "-count_packets", "-show_entries",
                "stream=codec_type,width,height,r_frame_rate,nb_read_packets:format=duration", "-of", "json",
                str(pfad)], f"ffprobe {pfad.name}")
    daten = json.loads(roh.decode("utf-8", "replace"))
    stroeme = daten.get("streams") or []
    bild = next((s for s in stroeme if s.get("codec_type") == "video"), None)
    if bild is None:
        raise StudioFehler(f"{pfad.name} hat keinen Bildstrom (leere Aufnahme?).")
    zaehler, nenner = (int(x) for x in str(bild.get("r_frame_rate", "0/1")).split("/"))
    bilder = int(bild.get("nb_read_packets") or 0)
    if bilder <= 0 or zaehler <= 0 or nenner <= 0:
        raise StudioFehler(f"{pfad.name} enthält keine lesbaren Bilder.")
    return {"breite": bild.get("width"), "hoehe": bild.get("height"), "fps": zaehler / nenner, "bilder": bilder,
            "dauer": float((daten.get("format") or {}).get("duration") or 0.0),
            "hat_ton": any(s.get("codec_type") == "audio" for s in stroeme)}


def audio_laden(pfad: Path, rate_hz: int) -> np.ndarray:
    """Mono-Ton als float32 (−1..1) per ffmpeg-Pipe. Eine fehlende oder unlesbare Datei ist ein Fehler, nie
    „kein Ton“ (sonst sähe ein kaputter Aufruf wie eine grüne Ampel aus)."""
    if not Path(pfad).is_file():
        raise StudioFehler(f"Datei fehlt: {pfad}")
    roh = lauf(["ffmpeg", "-v", "error", "-i", str(pfad), "-vn", "-ac", "1", "-ar", str(rate_hz), "-f", "f32le", "-"],
               f"Ton lesen ({Path(pfad).name})")
    return np.frombuffer(roh, dtype=np.float32)


def bilder_zaehlen(pfad: Path) -> int:
    roh = lauf(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                "stream=nb_read_packets", "-of", "csv=p=0", str(pfad)], f"ffprobe {pfad.name}")
    return int(roh.decode("ascii", "replace").strip().split(",")[0])


def lautheit_messen(pfad: Path, vorfilter: str = "") -> dict:
    """Integrierte Lautheit (LUFS), Lautheitsumfang (LU) und True Peak (dBTP) nach EBU R 128 / ITU-R BS.1770.
    True Peak wird bei 192 kHz gemessen (vierfache Überabtastung bei 48 kHz, wie BS.1770 Anhang 2 empfiehlt).
    Stille kommt als ``lufs = -inf`` zurück; der Aufrufer muss sie abfangen."""
    kette = ",".join(x for x in (vorfilter, "aresample=192000", "ebur128=peak=true:framelog=quiet") if x)
    try:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(pfad), "-vn", "-af", kette, "-f", "null",
                            "-"],
                           capture_output=True, **OHNE_FENSTER)
    except FileNotFoundError as e:
        raise StudioFehler("ffmpeg nicht gefunden. Ist ffmpeg installiert und im PATH?") from e
    text = r.stderr.decode("utf-8", "replace")
    if r.returncode != 0:
        raise StudioFehler(f"Messung von {pfad} gescheitert: {text.strip()[-300:]}")
    return ebur128_lesen(text)


def ebur128_lesen(text: str) -> dict:
    """Die Zusammenfassung von ffmpeg ``ebur128`` lesen."""
    t = text[text.rfind("Summary:"):]
    if "Summary:" not in text:
        raise StudioFehler("ebur128 liefert keine Zusammenfassung (Datei ohne Ton?).")

    def zahl(muster: str) -> float:
        m = re.search(muster, t)
        if not m:
            raise StudioFehler(f"ebur128: {muster} fehlt in der Zusammenfassung")
        return float(m.group(1))

    # Leerraum als "[ \t]" statt Backslash-s: so sieht kein Muster wie ein Laufwerkspfad aus (Leck-Prüfung im Repo).
    return {"lufs": zahl(r"I:[ \t]+(-?[\d.]+|-inf) LUFS"), "lra": zahl(r"LRA:[ \t]+(-?[\d.]+) LU"),
            "dbtp": zahl(r"Peak:[ \t]+(-?[\d.]+|-inf) dBFS")}
