#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Rendert eine Timeline über die Render-Queue und zieht auf Wunsch Standbilder.

    <resolve-python> -u resolve_rendern.py --ziel <ordner> [--projekt <Name>] [--timeline <Name>]
        [--name <datei ohne Endung>] [--format mp4|mov] [--codec H264|H264_NVIDIA|H265|ProRes422HQ …]
        [--stills 0.5,12.0,…] [--nur-stills] [--von <s> --bis <s>]

Ohne --timeline wird die aktuelle Timeline gerendert. Auflösung und Bildrate kommen aus der Timeline.
Die Bitrate lässt sich über die API nicht setzen (F12): für die Abgabe den Master als ProRes 422 HQ rendern
(--format mov --codec ProRes422HQ) und danach mit ``studio mastern`` nach H.264 wandeln; der H.264-Render von hier ist
die schnelle Sichtfassung.

Eine vorhandene Datei wird nie überschrieben: Resolve hält importierte Dateien offen, ein Render auf denselben Pfad
scheitert oder trifft eine Datei, die noch in einer Timeline liegt (F14). Der Name bekommt dann -2, -3 …
Der Auftrag wird nach dem Lauf wieder aus der Queue entfernt. Exit 0 fertig, 1 Render fehlgeschlagen, 2 Eingabe/Resolve.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # F3
import resolve_api as ra  # noqa: E402

ENDUNGEN = {"mp4": ".mp4", "mov": ".mov"}


def p(*a) -> None:
    print(*a, flush=True)


def tc(bild: int, fps: float | str, drop: bool = False) -> str:
    """Bildnummer → Timecode (Nennwert-Zählung, Drop-Frame mit „;“); siehe resolve_api.bild_zu_tc."""
    return ra.bild_zu_tc(bild, fps, drop)


VERBOTEN = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')


def sicherer_stamm(name: str) -> str:
    """Dateinamen-Stamm aus einem Timeline-Namen oder --name: kein Ordneranteil, keine Trenner, keine Doppelpunkte."""
    stamm = VERBOTEN.sub("_", Path(str(name).replace("\\", "/")).name).strip(" .")
    return stamm or "timeline"


def freier_name(ziel: Path, stamm: str, endung: str) -> str:
    """Erster Name „stamm“, „stamm-2“ … ohne vorhandene Datei im Zielordner."""
    name, n = stamm, 2
    while (ziel / f"{name}{endung}").exists():
        name, n = f"{stamm}-{n}", n + 1
    return name


def timeline_holen(proj, name: str | None):
    if not name:
        tl = proj.GetCurrentTimeline()
        if tl is None:
            raise ra.ResolveFehler("keine Timeline offen und keine mit --timeline genannt")
        return tl
    for i in range(1, int(proj.GetTimelineCount() or 0) + 1):
        t = proj.GetTimelineByIndex(i)
        if t.GetName() == name:
            proj.SetCurrentTimeline(t)
            return t
    raise ra.ResolveFehler(f"Timeline „{name}“ gibt es im Projekt nicht")


def _sha(pfad: Path) -> str:
    return hashlib.sha256(pfad.read_bytes()).hexdigest()


def stills(proj, tl, zeiten: list[float], ziel: Path, stamm: str, warte_s: float = 0.5) -> list[str]:
    """Standbilder ohne Render. Das erste Bild nach dem Laden ist unzuverlässig (F19): ein Aufwärmbild wird geschrieben
    und gelöscht; ein Bild, das byte-gleich zum vorigen ist (andere Stelle), wird einmal neu geholt.

    Bildnummern bei der echten Bildrate (23,976 / 29,97 …), Timecodes mit Nennwert-Zählung und Drop-Frame, wie die
    Timeline sie zeigt. Vorhandene Dateien werden nie überschrieben; gelöscht wird nur, was dieser Lauf selbst
    schrieb."""
    stamm = sicherer_stamm(stamm)
    fps = str(tl.GetSetting("timelineFrameRate"))
    drop = ra.timeline_drop_frame(tl)
    s0 = tl.GetStartFrame()
    aufwaermen = ziel / f"{freier_name(ziel, f'{stamm}_aufwaermen', '.png')}.png"
    tl.SetCurrentTimecode(tc(s0, fps, drop))
    time.sleep(warte_s)
    vorige, vorige_bild = None, 0
    if proj.ExportCurrentFrameAsStill(str(aufwaermen)) and aufwaermen.exists():
        vorige = _sha(aufwaermen)
        aufwaermen.unlink()                  # vorher frei gewählt, also sicher eine eigene Datei
    aus: list[str] = []
    for t in zeiten:
        b = ra.frames(t, fps)
        pfad = ziel / f"{freier_name(ziel, f'{stamm}_bild{b:06d}', '.png')}.png"
        for _versuch in range(2):
            tl.SetCurrentTimecode(tc(s0 + b, fps, drop))
            time.sleep(warte_s)
            ok = proj.ExportCurrentFrameAsStill(str(pfad)) is True and pfad.exists()
            # gleich dem vorigen Bild bei anderer Stelle = Resolve hinkt hinterher
            if ok and (vorige is None or b == vorige_bild or _sha(pfad) != vorige):
                break
        else:
            if pfad.exists():
                pfad.unlink()                    # eigene, unzuverlässige Datei nicht als Beleg liegen lassen
            p(f"  Standbild bei {t:.2f} s unzuverlässig (abgelehnt oder gleich dem vorigen): bitte von Hand prüfen")
            continue
        vorige, vorige_bild = _sha(pfad), b
        aus.append(str(pfad))
    return aus


def render_einstellungen(tl, ziel: Path, name: str, fmt: str, codec: str, von: float | None,
                         bis: float | None) -> dict:
    fps = str(tl.GetSetting("timelineFrameRate"))
    s0 = tl.GetStartFrame()
    einst = {"SelectAllFrames": von is None and bis is None, "TargetDir": str(ziel), "CustomName": name,
             "ExportVideo": True, "ExportAudio": True,
             "FormatWidth": int(tl.GetSetting("timelineResolutionWidth")),
             "FormatHeight": int(tl.GetSetting("timelineResolutionHeight")),
             "AudioCodec": "aac", "AudioSampleRate": 48000}
    if not einst["SelectAllFrames"]:
        einst["MarkIn"] = s0 + ra.frames(von or 0.0, fps)
        einst["MarkOut"] = (s0 + ra.frames(bis, fps) - 1) if bis is not None else tl.GetEndFrame() - 1
    if fmt == "mov" and codec.startswith("ProRes"):
        einst["AudioCodec"] = "lpcm"
    return einst


def rendern(proj, tl, ziel: Path, name: str, fmt: str, codec: str, von: float | None = None,
            bis: float | None = None, takt_s: float = 1.0) -> int:
    ra.darf_schreiben(proj)
    if not proj.SetCurrentRenderFormatAndCodec(fmt, codec):
        p(f"Format/Codec {fmt}/{codec} abgelehnt; möglich: {proj.GetRenderCodecs(fmt)}")
        return 2
    einst = render_einstellungen(tl, ziel, name, fmt, codec, von, bis)
    if not proj.SetRenderSettings(einst):
        p(f"Render-Einstellungen abgelehnt: {einst}")
        return 2
    job = proj.AddRenderJob()
    if not job:
        p("Render-Auftrag lässt sich nicht anlegen")
        return 1
    t0 = time.time()
    if not proj.StartRendering([job], False):
        p("Render startet nicht")
        proj.DeleteRenderJob(job)
        return 1
    letzte = -1
    while proj.IsRenderingInProgress():
        st = proj.GetRenderJobStatus(job) or {}
        proz = int(st.get("CompletionPercentage") or 0)
        if proz >= letzte + 10:
            p(f"  {proz} %")
            letzte = proz
        time.sleep(takt_s)
    st = proj.GetRenderJobStatus(job) or {}
    datei = next((Path(j["TargetDir"]) / j["OutputFilename"] for j in (proj.GetRenderJobList() or [])
                  if j.get("JobId") == job), None)
    proj.DeleteRenderJob(job)
    if st.get("JobStatus") != "Complete":
        p(f"Render nicht fertig: {st}")
        return 1
    p(f"Render fertig in {time.time() - t0:.1f} s: {datei}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ra.utf8()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--projekt")
    ap.add_argument("--timeline")
    ap.add_argument("--ziel", required=True)
    ap.add_argument("--name")
    ap.add_argument("--format", default="mp4", choices=sorted(ENDUNGEN))
    ap.add_argument("--codec", default="H264")
    ap.add_argument("--stills", default="")
    ap.add_argument("--nur-stills", action="store_true")
    ap.add_argument("--von", type=float)
    ap.add_argument("--bis", type=float)
    a = ap.parse_args(argv)
    try:
        r = ra.verbinden()
        proj = ra.projekt_holen(r, a.projekt, anlegen=False) if a.projekt else \
            r.GetProjectManager().GetCurrentProject()
        tl = timeline_holen(proj, a.timeline)
    except ra.ResolveFehler as e:
        p(f"Resolve: {e}")
        return 2
    ziel = Path(a.ziel)
    ziel.mkdir(parents=True, exist_ok=True)
    stamm = sicherer_stamm(a.name or tl.GetName())
    if a.stills:
        r.OpenPage("edit")
        for s in stills(proj, tl, [float(x) for x in a.stills.split(",") if x.strip()], ziel, stamm):
            p("Standbild:", s)
    if a.nur_stills:
        return 0
    name = freier_name(ziel, stamm, ENDUNGEN[a.format])
    if name != stamm:
        p(f"„{stamm}{ENDUNGEN[a.format]}“ gibt es schon, neuer Name: „{name}{ENDUNGEN[a.format]}“")
    try:
        return rendern(proj, tl, ziel, name, a.format, a.codec, a.von, a.bis)
    except ra.ResolveFehler as e:
        p(f"Resolve: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
