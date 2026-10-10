# SPDX-License-Identifier: MIT
"""Ton auf Ziel-Lautheit bringen, mit stetigem True-Peak-Begrenzer, gemessen vorher und nachher.

Ablauf: Lautheit und True Peak messen (EBU R 128 über ffmpeg ``ebur128``, True Peak bei 192 kHz) → Verstärkung
berechnen → abbrechen, wenn der Begrenzer mehr als ``max_begrenzer_db`` greifen müsste (dann stimmt die Mischung nicht)
→ schreiben (in eine ``.part``-Datei) → nachmessen → erst bei Erfolg an den Zielnamen. Eine vorhandene Ausgabe wird nie
überschrieben.

Voreinstellungen (alle einstellbar, ``[mastern]`` oder Optionen):
* −14 LUFS: verbreiteter Zielwert der Lautheitsnormalisierung von Streamingdiensten, z. B. Spotify
  (https://support.spotify.com/artists/article/loudness-normalization/). YouTube veröffentlicht keinen festen Wert.
* −1,5 dBTP: Reserve unter der Höchstgrenze −1 dBTP aus EBU R 128 (https://tech.ebu.ch/publications/r128).
* 3 dB Begrenzer, 0,2 dB Reserve für die AAC-Wandlung: einstellbare Voreinstellungen, nicht gemessen.
* Video: H.264 (libx264) CRF 16, ``+faststart``; CRF 16 ist eine einstellbare Voreinstellung, nicht gemessen.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from studio_werkzeuge import medien
from studio_werkzeuge.fehler import StudioFehler
from studio_werkzeuge.konfig import Konfig

ZIEL_LUFS = -14.0
ZIEL_TRUE_PEAK = -1.5
MAX_BEGRENZER_DB = 3.0
CRF = 16
AAC_RESERVE_DB = 0.2
TOLERANZ_LU = 0.5
# Absolutes Gate nach ITU-R BS.1770 (https://www.itu.int/rec/R-REC-BS.1770): darunter gilt der Ton als still.
STILLE_LUFS = -70.0
AUDIO_CODECS = {".wav": ["-c:a", "pcm_s24le"], ".flac": ["-c:a", "flac"],
                ".m4a": ["-c:a", "aac", "-b:a", "320k"], ".aac": ["-c:a", "aac", "-b:a", "320k"]}
VIDEO_ENDUNGEN = {".mp4", ".mov", ".m4v", ".mkv"}


def begrenzer_bedarf(gemessen: dict, gain_db: float, ziel_tp: float) -> float:
    """Um wie viel dB der Begrenzer die höchste Spitze nach der Anhebung drücken muss (0, wenn gar nicht)."""
    return max(0.0, round(gemessen["dbtp"] + gain_db - ziel_tp, 2))


def kette(gain_db: float, ziel_tp: float, reserve_db: float = 0.0) -> str:
    """Verstärkung, dann stetiger Begrenzer mit vierfacher Überabtastung (kein hartes Kappen mit Knick)."""
    grenze = 10 ** ((ziel_tp - reserve_db) / 20.0)
    return (f"volume={gain_db:.2f}dB,aresample=192000,"
            f"alimiter=limit={grenze:.4f}:attack=5:release=80:level=false,aresample=48000")


def ist_video(ausgang: Path, hat_bild: bool) -> bool:
    return hat_bild and ausgang.suffix.lower() in VIDEO_ENDUNGEN


def ffmpeg_befehl(eingang: Path, ausgang: Path, filter_ton: str, video: bool, crf: int, hoehe: int | None) -> list[str]:
    befehl = ["ffmpeg", "-v", "error", "-y", "-i", str(eingang)]
    if video:
        vf = [f"scale=-2:{hoehe}:flags=lanczos"] if hoehe else []
        vf.append("format=yuv420p")
        befehl += ["-map", "0:v:0", "-map", "0:a:0", "-vf", ",".join(vf), "-c:v", "libx264", "-preset", "slow",
                   "-crf", str(crf), "-profile:v", "high", "-colorspace", "bt709", "-color_primaries", "bt709",
                   "-color_trc", "bt709", "-color_range", "tv", "-af", filter_ton, "-c:a", "aac", "-b:a", "320k",
                   "-ar", "48000", "-movflags", "+faststart"]
    else:
        codec = AUDIO_CODECS.get(ausgang.suffix.lower())
        if codec is None:
            raise StudioFehler(f"Endung {ausgang.suffix!r} unbekannt. Ton: {', '.join(AUDIO_CODECS)}; "
                               f"Video: {', '.join(sorted(VIDEO_ENDUNGEN))}.")
        befehl += ["-map", "0:a:0", "-vn", "-af", filter_ton, *codec, "-ar", "48000"]
    return befehl + [str(ausgang)]


def verstaerkung_finden(eingang: Path, gain: float, ziel: float, ziel_tp: float, reserve: float,
                        runden: int = 3) -> tuple[float, dict]:
    """Der Begrenzer schluckt etwas Lautheit; darum die Kette messen und die Verstärkung nachführen."""
    gemessen = medien.lautheit_messen(eingang, kette(gain, ziel_tp, reserve))
    for _ in range(runden - 1):
        if abs(gemessen["lufs"] - ziel) <= 0.15:
            break
        gain += ziel - gemessen["lufs"]
        gemessen = medien.lautheit_messen(eingang, kette(gain, ziel_tp, reserve))
    return round(gain, 2), gemessen


def mastern(eingang: Path, ausgang: Path, ziel: float = ZIEL_LUFS, ziel_tp: float = ZIEL_TRUE_PEAK,
            max_begrenzer: float = MAX_BEGRENZER_DB, crf: int = CRF, hoehe: int | None = None,
            probe: bool = False) -> dict:
    """Misst, plant, schreibt und prüft. Gibt einen Bericht zurück; ``bericht["ok"]`` sagt, ob das Ziel sitzt."""
    if not eingang.is_file():
        raise StudioFehler(f"Eingang fehlt: {eingang}")
    if ausgang.exists():
        raise StudioFehler(f"{ausgang} gibt es schon. Nie überschreiben: anderen Namen wählen.")
    if ausgang.resolve() == eingang.resolve():
        raise StudioFehler("Eingang und Ausgang sind dieselbe Datei.")
    info = medien.medien_info(eingang)
    if not info["hat_ton"]:
        raise StudioFehler(f"{eingang.name} hat keinen Tonstrom.")
    video = ist_video(ausgang, info["hat_bild"])
    reserve = AAC_RESERVE_DB if (video or ausgang.suffix.lower() in (".m4a", ".aac")) else 0.0
    vor = medien.lautheit_messen(eingang)
    if vor["lufs"] <= STILLE_LUFS:
        raise StudioFehler(f"{eingang.name} ist stumm (Lautheit {vor['lufs']} LUFS, unter dem absoluten Gate).")
    gain = round(ziel - vor["lufs"], 2)
    bedarf = begrenzer_bedarf(vor, gain, ziel_tp)
    bericht: dict = {"eingang": str(eingang), "ausgang": str(ausgang), "ziel_lufs": ziel, "ziel_true_peak": ziel_tp,
                     "vorher": vor, "anhebung_db": gain, "begrenzer_db": bedarf, "video": video, "ok": False}
    if bedarf > max_begrenzer:
        bericht["abbruch"] = (f"Der Begrenzer müsste {bedarf:.1f} dB greifen (erlaubt {max_begrenzer:.1f} dB). "
                              "Mischung prüfen: zu laute Klänge, O-Töne oder Spitzen? Nichts geschrieben.")
        return bericht
    gain, plan = verstaerkung_finden(eingang, gain, ziel, ziel_tp, reserve)
    bericht.update(anhebung_db=gain, plan_messung=plan, kette=kette(gain, ziel_tp, reserve))
    if probe:
        bericht["probe"] = True
        bericht["ok"] = abs(plan["lufs"] - ziel) <= TOLERANZ_LU and plan["dbtp"] <= ziel_tp
        return bericht

    teil = ausgang.with_name(f"{ausgang.stem}.part{ausgang.suffix}")
    teil.unlink(missing_ok=True)
    try:
        medien.lauf(ffmpeg_befehl(eingang, teil, kette(gain, ziel_tp, reserve), video, crf, hoehe), "Mastern")
        nach = medien.lautheit_messen(teil)
        bericht["nachher"] = nach
        fehler = []
        if abs(nach["lufs"] - ziel) > TOLERANZ_LU:
            fehler.append(f"Lautheit {nach['lufs']:.2f} LUFS verfehlt {ziel:.1f} ± {TOLERANZ_LU} LU")
        if nach["dbtp"] > ziel_tp:
            fehler.append(f"True Peak {nach['dbtp']:.2f} dBTP über {ziel_tp:.1f} dBTP")
        if video and medien.bilder_zaehlen(teil) != medien.bilder_zaehlen(eingang):
            fehler.append("Bildzahl der Ausgabe weicht vom Eingang ab")
        if fehler:
            bericht["abbruch"] = "; ".join(fehler) + ". Nichts an den Zielnamen gelegt."
            return bericht
        os.replace(teil, ausgang)
    finally:
        teil.unlink(missing_ok=True)
    bericht["ok"] = True
    ausgang.with_name(ausgang.name + ".json").write_text(json.dumps(bericht, ensure_ascii=False, indent=1),
                                                        encoding="utf-8")
    return bericht


def einrichten(unter) -> None:
    p = unter.add_parser("mastern", help="Ton auf −14 LUFS / −1,5 dBTP bringen (gemessen, mit Nachmessung)",
                         description=__doc__.split("\n\n")[0])
    p.add_argument("eingang", type=Path, metavar="EINGANG")
    p.add_argument("ausgang", type=Path, metavar="AUSGANG",
                   help="Endung bestimmt die Ausgabe: .mp4/.mov/.mkv = Video (H.264), .wav/.flac/.m4a = nur Ton")
    p.add_argument("--ziel-lufs", type=float, help=f"Ziel-Lautheit (Voreinstellung {ZIEL_LUFS})")
    p.add_argument("--ziel-true-peak", type=float, help=f"Höchster True Peak in dBTP (Voreinstellung {ZIEL_TRUE_PEAK})")
    p.add_argument("--max-begrenzer-db", type=float, help=f"Abbruch darüber (Voreinstellung {MAX_BEGRENZER_DB})")
    p.add_argument("--crf", type=int, help=f"Videoqualität H.264 (Voreinstellung {CRF}, kleiner = besser)")
    p.add_argument("--hoehe", type=int, help="Video auf diese Höhe skalieren (z. B. 1440); ohne: Größe bleibt")
    p.add_argument("--probe", action="store_true", help="nur messen und planen, nichts schreiben")
    p.set_defaults(ausfuehren=ausfuehren, braucht_konfig=False)


def ausfuehren(args, konfig: Konfig) -> int:
    ziel = args.ziel_lufs if args.ziel_lufs is not None else float(konfig.wert("mastern", "ziel_lufs", ZIEL_LUFS))
    tp = args.ziel_true_peak if args.ziel_true_peak is not None else float(
        konfig.wert("mastern", "ziel_true_peak", ZIEL_TRUE_PEAK))
    grenze = args.max_begrenzer_db if args.max_begrenzer_db is not None else float(
        konfig.wert("mastern", "max_begrenzer_db", MAX_BEGRENZER_DB))
    crf = args.crf if args.crf is not None else int(konfig.wert("mastern", "crf", CRF))
    b = mastern(args.eingang, args.ausgang, ziel, tp, grenze, crf, args.hoehe, args.probe)
    v = b["vorher"]
    print(f"Vorher: {v['lufs']:.1f} LUFS, LRA {v['lra']:.1f} LU, True Peak {v['dbtp']:.1f} dBTP")
    print(f"Plan: Anhebung {b['anhebung_db']:+.2f} dB, Begrenzer greift höchstens {b['begrenzer_db']:.1f} dB")
    if "plan_messung" in b:
        m = b["plan_messung"]
        print(f"Kette gemessen: {m['lufs']:.2f} LUFS, True Peak {m['dbtp']:.2f} dBTP")
    if "nachher" in b:
        n = b["nachher"]
        print(f"Nachher: {n['lufs']:.2f} LUFS, LRA {n['lra']:.1f} LU, True Peak {n['dbtp']:.2f} dBTP")
    if b.get("abbruch"):
        print(f"ABBRUCH: {b['abbruch']}")
        return 1
    if b.get("probe"):
        print("Probe: nichts geschrieben.")
        return 0 if b["ok"] else 1
    print(f"Fertig: {b['ausgang']} (Messwerte in {b['ausgang']}.json)")
    return 0
