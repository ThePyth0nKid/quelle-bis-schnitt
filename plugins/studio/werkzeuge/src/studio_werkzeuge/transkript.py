# SPDX-License-Identifier: MIT
"""Transkript mit Zeitmarken (`studio transkript`): lokal mit faster-whisper oder über einen Fern-Befehl.

Lokal: ``geraet=auto`` nimmt CUDA, wenn eine NVIDIA-Karte da ist, sonst die CPU. Fehlt das Extra, kommt eine klare
Meldung (``pip install "studio-werkzeuge[whisper]"``).

Fern (nur per Konfiguration): ``[transkript.fern] befehl`` ist eine Befehlsliste, die ohne Shell gestartet wird, z. B.
ein ``ssh``-Aufruf auf einen eigenen Rechner. Der Befehl bekommt den Ton als WAV (16 kHz, mono) auf stdin und muss JSON
auf stdout liefern: ``{"segmente": [{"start": 0.0, "end": 1.2, "text": "…"}]}``.
Es gibt keinen fest eingetragenen Rechner.

F1 · Das Transkript bestätigt, was man hören wollte. Ursache: ein erwarteter Text als ``initial_prompt`` lenkt Whisper
auf diesen Wortlaut. Gegenmittel: nie einen erwarteten Text übergeben; zum Gegenprüfen mehrere Modelle vergleichen.
"""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

from studio_werkzeuge import medien
from studio_werkzeuge.fehler import KonfigFehler, StudioFehler
from studio_werkzeuge.konfig import Konfig, ist_platzhalter

MODELL = "large-v3"
SPRACHE = "de"


def geraet_waehlen(geraet: str) -> tuple[str, str]:
    """(device, compute_type) für faster-whisper."""
    if geraet == "auto":
        try:
            import ctranslate2
            geraet = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
        except Exception:  # noqa: BLE001 - ohne CUDA-Laufzeit einfach CPU
            geraet = "cpu"
    if geraet == "cuda":
        return "cuda", "float16"
    if geraet == "cpu":
        return "cpu", "int8"
    raise StudioFehler(f"Gerät {geraet!r} unbekannt (auto, cuda, cpu).")


def lokal(datei: Path, modell: str = MODELL, sprache: str = SPRACHE, geraet: str = "auto") -> list[dict]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise StudioFehler('faster-whisper fehlt. Installieren: pip install "studio-werkzeuge[whisper]"') from e
    device, compute = geraet_waehlen(geraet)
    model = WhisperModel(modell, device=device, compute_type=compute)
    # Bewusst ohne initial_prompt (F1).
    segmente, _info = model.transcribe(str(datei), language=sprache or None, word_timestamps=True)
    return [{"start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip(),
             "woerter": [{"start": round(w.start, 3), "end": round(w.end, 3), "wort": w.word.strip()}
                         for w in (s.words or [])]} for s in segmente]


def fern_befehl(konfig: Konfig) -> list[str]:
    befehl = konfig.abschnitt("transkript.fern").get("befehl") or []
    if not isinstance(befehl, list) or not befehl or not all(isinstance(t, str) and t for t in befehl):
        raise KonfigFehler("[transkript.fern] befehl muss eine nicht leere Liste von Texten sein.")
    if any(ist_platzhalter(t) for t in befehl):
        raise KonfigFehler("[transkript.fern] befehl enthält noch <Platzhalter>.")
    return befehl


def zeitlimit_pruefen(zeitlimit_s: float) -> float:
    if isinstance(zeitlimit_s, bool) or not isinstance(zeitlimit_s, (int, float)) or not math.isfinite(zeitlimit_s) \
            or zeitlimit_s <= 0:
        raise KonfigFehler(f"[transkript.fern] zeitlimit_s muss eine Zahl über 0 sein, ist {zeitlimit_s!r}.")
    return float(zeitlimit_s)


def _segment(s: object) -> dict:
    if not isinstance(s, dict):
        raise StudioFehler("Fern-Befehl: jedes Segment muss ein Objekt sein.")
    try:
        start, ende = float(s.get("start")), float(s.get("end"))
    except (TypeError, ValueError) as e:
        raise StudioFehler(f"Fern-Befehl: Segment ohne gültige Zeiten ({s.get('start')!r}, {s.get('end')!r}).") from e
    woerter = s.get("woerter", [])
    return {"start": start, "end": ende, "text": str(s.get("text", "")).strip(),
            "woerter": woerter if isinstance(woerter, list) else []}


def fern(datei: Path, befehl: list[str], zeitlimit_s: float = 3600.0) -> list[dict]:
    """Ton als WAV über stdin an den Fern-Befehl, JSON zurück. Keine Shell, Zeitlimit für beide Schritte."""
    zeitlimit_s = zeitlimit_pruefen(zeitlimit_s)
    wav = medien.lauf([*medien.FFMPEG, "-v", "error", "-i", medien.arg(datei), "-vn", "-ac", "1", "-ar", "16000",
                       "-f", "wav", "-"], f"Ton lesen ({datei.name})", timeout=zeitlimit_s)
    try:
        r = subprocess.run(befehl, input=wav, capture_output=True, timeout=zeitlimit_s, **medien.OHNE_FENSTER)
    except FileNotFoundError as e:
        raise StudioFehler(f"Fern-Befehl {befehl[0]!r} nicht gefunden.") from e
    except subprocess.TimeoutExpired as e:
        raise StudioFehler(f"Fern-Transkript nach {zeitlimit_s:.0f} s abgebrochen.") from e
    if r.returncode != 0:
        raise StudioFehler(f"Fern-Befehl endete mit {r.returncode}: {r.stderr.decode('utf-8', 'replace')[-300:]}")
    try:
        daten = json.loads(r.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise StudioFehler("Fern-Befehl lieferte kein JSON.") from e
    segmente = daten.get("segmente") if isinstance(daten, dict) else daten
    if not isinstance(segmente, list):
        raise StudioFehler('Fern-Befehl: erwartet {"segmente": [...]}.')
    return [_segment(s) for s in segmente]


def zeit_srt(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3_600_000:02d}:{ms // 60_000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def als_text(segmente: list[dict], art: str) -> str:
    if art == ".json":
        return json.dumps({"segmente": segmente}, ensure_ascii=False, indent=1)
    if art == ".srt":
        return "\n".join(f"{i}\n{zeit_srt(s['start'])} --> {zeit_srt(s['end'])}\n{s['text']}\n"
                         for i, s in enumerate(segmente, start=1))
    return "\n".join(f"[{s['start']:8.2f} – {s['end']:8.2f}] {s['text']}" for s in segmente) + "\n"


def einrichten(unter) -> None:
    p = unter.add_parser("transkript", help="Transkript mit Zeitmarken (faster-whisper lokal oder Fern-Befehl)",
                         description=__doc__.split("\n\n")[0])
    p.add_argument("datei", type=Path, metavar="DATEI")
    p.add_argument("--modell", help=f"Whisper-Modell (ohne: [transkript] modell, sonst {MODELL})")
    p.add_argument("--sprache", help=f"Sprachcode (ohne: [transkript] sprache, sonst {SPRACHE})")
    p.add_argument("--geraet", choices=("auto", "cuda", "cpu"), help="ohne: [transkript] geraet, sonst auto")
    p.add_argument("--ausgabe", type=Path, help="Datei .json, .srt oder .txt (nie überschreiben); ohne: Bildschirm")
    p.set_defaults(ausfuehren=ausfuehren, braucht_konfig=False)


def ausfuehren(args, konfig: Konfig) -> int:
    if not args.datei.is_file():
        raise StudioFehler(f"Datei fehlt: {args.datei}")
    if args.ausgabe and args.ausgabe.exists():
        raise StudioFehler(f"{args.ausgabe} gibt es schon. Nie überschreiben: anderen Namen wählen.")
    backend = konfig.text("transkript", "backend", "lokal")
    if backend == "fern":
        segmente = fern(args.datei, fern_befehl(konfig), konfig.zahl("transkript.fern", "zeitlimit_s", 3600))
    elif backend == "lokal":
        segmente = lokal(args.datei, args.modell or konfig.text("transkript", "modell", MODELL),
                         args.sprache or konfig.text("transkript", "sprache", SPRACHE),
                         args.geraet or konfig.text("transkript", "geraet", "auto"))
    else:
        raise KonfigFehler(f"[transkript] backend muss lokal oder fern sein, ist {backend!r}.")
    if args.ausgabe:
        with open(args.ausgabe, "x", encoding="utf-8") as f:     # nie überschreiben, auch nicht in letzter Sekunde
            f.write(als_text(segmente, args.ausgabe.suffix.lower()))
        print(f"{len(segmente)} Abschnitte → {args.ausgabe}")
    else:
        print(als_text(segmente, ".txt"), end="")
    return 0
