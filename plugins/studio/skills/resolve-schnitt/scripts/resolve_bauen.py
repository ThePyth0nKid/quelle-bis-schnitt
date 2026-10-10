#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Baut aus einem Bauplan (bauplan.py) eine NEUE Timeline in DaVinci Resolve Studio.

    <resolve-python> -u resolve_bauen.py <bauplan.json> [--sicherung <ordner>] [--bericht <datei.json>]
        [--ohne-sicherung]

Was geschieht: Projekt laden oder anlegen · .drp-Sicherung (die API hat kein Undo) · Quellen in den Media-Pool-Ordner
<name> (nur was fehlt) · neue Timeline „<name>-HHMM“ mit eigener Auflösung und Bildrate · Spuren anlegen und benennen ·
Items bildgenau setzen (jede Platzierung wird zurückgelesen) · Bildlage, Deckkraft, LUT, Pegel, Blenden · Bild-Ton-Paare
verknüpfen · Übergänge · Fusion-Fahrten (Keyframe-Zoom, Subpixel) · Marker · Bericht.
Eine vorhandene Timeline wird nie angefasst. Exit 0 alles gesetzt, 1 mindestens ein Item oder Schritt fehlgeschlagen,
2 Eingabefehler oder Resolve nicht erreichbar.
"""
from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

# Das Python von Resolve läuft isoliert: der Skriptordner steht nicht im Suchpfad (referenz/api-fakten.md, F3)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bauplan as bp  # noqa: E402
import resolve_api as ra  # noqa: E402

STAPEL = 40


def p(*a) -> None:
    print(*a, flush=True)


def lebt(item) -> bool:
    """Ein Fehlschlag sieht aus wie ein Erfolg: nur ein Item mit Startbild ist wirklich gesetzt (F9)."""
    return item is not None and item.GetStart() is not None


def _auf_platz(item, info: dict) -> bool:
    return lebt(item) and item.GetStart() == info["recordFrame"]


def setzen(mp, tl, art: str, infos: list[dict]) -> list:
    """AppendToTimeline im Stapel; Rückgabe in Reihenfolge der infos (None = nicht gesetzt).

    Kommt ein Stapel nicht vollständig und in Reihenfolge an, wird die Rückgabeliste NICHT Position für Position
    verglichen (sie kann kürzer sein oder tote Objekte enthalten, F9). Stattdessen wird die Spur mit
    ``GetItemListInTrack`` neu eingelesen; nur was dort am geplanten Startbild fehlt, wird einzeln nachgesetzt."""
    aus: list = []
    for a in range(0, len(infos), STAPEL):
        teil = infos[a:a + STAPEL]
        res = list(mp.AppendToTimeline(teil) or [])
        if len(res) == len(teil) and all(_auf_platz(x, i) for x, i in zip(res, teil, strict=True)):
            aus.extend(res)
            continue
        spuren = {i["trackIndex"] for i in teil}
        vorhanden = {}
        for idx in spuren:
            for item in tl.GetItemListInTrack(art, idx) or []:
                if lebt(item):
                    vorhanden[(idx, item.GetStart())] = item
        for info in teil:
            obj = vorhanden.get((info["trackIndex"], info["recordFrame"]))
            if obj is None:
                neu = (mp.AppendToTimeline([info]) or [None])[0]
                obj = neu if _auf_platz(neu, info) else None
            aus.append(obj)
    return aus


def lage_setzen(item, lage: dict) -> bool:
    d: dict = {}
    if "zoom" in lage:
        d["ZoomX"] = d["ZoomY"] = float(lage["zoom"])
    if "pan" in lage:
        d["Pan"] = float(lage["pan"])
    if "tilt" in lage:
        d["Tilt"] = float(lage["tilt"])
    c = lage.get("crop") or {}
    for k, ziel in (("l", "CropLeft"), ("r", "CropRight"), ("o", "CropTop"), ("u", "CropBottom")):
        if k in c:
            d[ziel] = float(c[k])
    if "deckkraft" in lage:
        d["Opacity"] = float(lage["deckkraft"])
    return bool(item.SetProperties(d)) if d else True


def lut_setzen(item, pfad: str) -> tuple[bool, str]:
    """3D-LUT auf Knoten 1 des Items (Knoten-Graph-API). Zurückgelesen über GetLUT; Resolve meldet den Pfad teils
    relativ zum LUT-Ordner, darum zählt das Ende des Pfades."""
    graph = item.GetNodeGraph() if hasattr(item, "GetNodeGraph") else None
    if graph is None:
        return False, "kein Knoten-Graph"
    if not graph.SetLUT(1, str(pfad)):
        return False, "SetLUT abgelehnt (Datei nicht in Resolves LUT-Liste?)"
    gelesen = str(graph.GetLUT(1) or "").replace("\\", "/")
    if Path(gelesen).is_absolute():
        stimmt = Path(gelesen).resolve() == Path(pfad).resolve()
    else:
        stimmt = (Path(pfad).as_posix().lower().endswith(gelesen.lower())
                  and Path(gelesen).name.lower() == Path(pfad).name.lower())
    if not stimmt:
        return False, f"zurückgelesen „{gelesen}“"
    return True, ""


def fahrt_setzen(item, fahrt: dict, n: int) -> bool:
    """Keyframe-Zoom über eine Fusion-Komposition (Subpixel, kein Stufen-Wackeln). Verdrahten per Zuweisung, ohne
    Lock/ConnectInput (F8)."""
    comp = item.AddFusionComp()
    if comp is None:
        return False
    mi, mo = comp.FindTool("MediaIn1"), comp.FindTool("MediaOut1")
    xf = comp.AddTool("Transform", -32768, -32768)
    if not (mi and mo and xf):
        return False
    xf.Input = mi.Output
    mo.Input = xf.Output
    if "pivot" in fahrt:
        xf.Pivot = {1: float(fahrt["pivot"][0]), 2: float(fahrt["pivot"][1])}
    xf.Size = comp.BezierSpline()
    xf.Size[0] = float(fahrt.get("von", 1.0))
    xf.Size[max(1, n - 1)] = float(fahrt.get("bis", 1.0))
    return abs(float(xf.GetInput("Size", max(1, n - 1))) - float(fahrt.get("bis", 1.0))) < 1e-3


def _projekt_einstellen(r, proj, fps, breite: int, hoehe: int, sicherung: Path | None) -> None:
    neu = int(proj.GetTimelineCount() or 0) == 0
    if neu:
        proj.SetSetting("timelineFrameRate", str(fps))
        proj.SetSetting("timelineResolutionWidth", str(breite))
        proj.SetSetting("timelineResolutionHeight", str(hoehe))
        return
    if sicherung is not None:
        p("Sicherung:", ra.sichern(r, proj, sicherung))
    # Projekt-Bildrate und -Auflösung müssen zur Timeline passen, auch wenn schon eine Timeline da ist: sonst kommen
    # Ton-Clips ein Bild zu kurz an (referenz/api-fakten.md, F18)
    soll = {"timelineFrameRate": str(fps), "timelineResolutionWidth": str(breite),
            "timelineResolutionHeight": str(hoehe)}
    for k, v in soll.items():
        ist = proj.GetSetting(k)
        if str(ist) not in (v, f"{float(v):.1f}"):
            p(f"Projekt-Einstellung {k}: {ist} → {v}: {bool(proj.SetSetting(k, v))}")


def _spur_anlegen(tl, art: str, idx: int, name: str, fehler: list[str]) -> None:
    while int(tl.GetTrackCount(art) or 0) < idx:
        # Tonspuren ausdrücklich stereo: eine Mono-Spur gibt jeden Clip 3 dB leiser aus (F13)
        if not (tl.AddTrack(art, "stereo") if art == "audio" else tl.AddTrack(art)):
            fehler.append(f"Spur {art} {idx} lässt sich nicht anlegen")
            break
    tl.SetTrackName(art, idx, name)


def _item_einrichten(obj, it: dict, art: str, fps, fehler: list[str], zaehler: dict) -> None:
    if art == "video" and it.get("lage") and not lage_setzen(obj, it["lage"]):
        fehler.append(f"{it.get('id')}: Lage abgelehnt {it['lage']}")
    if art == "video" and it.get("lut"):
        ok_lut, warum = lut_setzen(obj, it["lut"])
        if ok_lut:
            zaehler["lut"] = zaehler.get("lut", 0) + 1
        else:
            fehler.append(f"{it.get('id')}: LUT {Path(it['lut']).name}: {warum}")
    if art == "audio" and "pegel_db" in it and not obj.SetProperties({"AudioVolume": float(it["pegel_db"])}):
        fehler.append(f"{it.get('id')}: Pegel abgelehnt")
    if it.get("blende"):
        ein, aus = it["blende"]
        if not obj.SetFades({"FadeIn": float(ein) * fps, "FadeOut": float(aus) * fps}):
            fehler.append(f"{it.get('id')}: Blende abgelehnt")


def bauen(plan: dict, sicherung: Path | None, bericht_pfad: Path | None, r=None) -> int:
    f = plan["format"]
    fps, breite, hoehe = f["fps"], int(f["breite"]), int(f["hoehe"])
    r = r or ra.verbinden()
    proj = ra.projekt_holen(r, plan["projekt"])
    ra.darf_schreiben(proj)
    _projekt_einstellen(r, proj, fps, breite, hoehe, sicherung)
    mp = proj.GetMediaPool()
    if any(i.get("lut") for s in plan["spuren"] for i in s.get("items", [])):
        proj.RefreshLUTList()                        # neue .cube-Dateien sonst unbekannt: SetLUT lehnt ab
    ordner = ra.ordner_holen(mp, plan["name"])
    quellen = list(dict.fromkeys(i["quelle"] for s in plan["spuren"] for i in s.get("items", [])))
    pool = ra.importieren(mp, ordner, quellen)
    qfps = {k: float(v.GetClipProperty("FPS") or fps) for k, v in pool.items()}
    p(f"Media Pool: {len(pool)} Quellen")

    tl = ra.neue_timeline(proj, mp, plan["name"], breite, hoehe, fps)
    s0 = tl.GetStartFrame()
    p(f"Timeline „{tl.GetName()}“ {breite}×{hoehe} @ {tl.GetSetting('timelineFrameRate')}")
    fehler: list[str] = []
    eintraege: list[dict] = []
    nach_id: dict[str, object] = {}
    zaehler: dict[str, int] = {"video": 0, "audio": 0}
    for spur in plan["spuren"]:
        art = spur["art"]
        zaehler[art] += 1
        idx = zaehler[art]
        _spur_anlegen(tl, art, idx, spur.get("name", f"{art} {idx}"), fehler)
        items = sorted(spur.get("items", []), key=lambda x: x["start"])
        infos = []
        for it in items:
            k = ra.norm(it["quelle"])
            ab, _bis = bp.kanten(it, fps)
            q_ab, q_bis = bp.quellbilder(it, fps, qfps[k])
            # mediaType 1 = nur Bild, 2 = nur Ton; sonst landet der Kamera-Ton auf der Spur der Stimme (F16)
            infos.append({"mediaPoolItem": pool[k], "startFrame": q_ab, "endFrame": q_bis, "trackIndex": idx,
                          "recordFrame": s0 + ab, "mediaType": 1 if art == "video" else 2})
        gesetzt = setzen(mp, tl, art, infos)
        ok_n = 0
        for it, obj in zip(items, gesetzt, strict=True):
            ab, bis = bp.kanten(it, fps)
            e = {"id": it.get("id"), "spur": spur.get("name"), "ab": ab, "bilder": bis - ab, "ok": False}
            eintraege.append(e)
            if not lebt(obj):
                fehler.append(f"{spur.get('name')}: {it.get('id') or it['quelle']} @ Bild {ab} nicht gesetzt")
                continue
            ist_ab, ist_n = obj.GetStart() - s0, obj.GetDuration()
            if ist_ab != ab or ist_n != bis - ab:
                fehler.append(f"{spur.get('name')}: {it.get('id')} liegt bei {ist_ab}+{ist_n} statt {ab}+{bis - ab}")
            e.update(ok=True, ist_ab=ist_ab, ist_bilder=ist_n)
            ok_n += 1
            if it.get("id"):
                nach_id[it["id"]] = obj
            _item_einrichten(obj, it, art, fps, fehler, zaehler)
        if spur.get("aus"):
            tl.SetTrackEnable(art, idx, False)
        p(f"  {art[0].upper()}{idx} {spur.get('name')}: {ok_n} von {len(items)} gesetzt")

    # Paare verknüpfen (Bild und zugehöriger Ton wandern beim Handschnitt gemeinsam)
    paare = 0
    for it in (i for s in plan["spuren"] for i in s.get("items", [])):
        if it.get("paar") and it.get("id") in nach_id and it["paar"] in nach_id:
            if tl.SetClipsLinked([nach_id[it["id"]], nach_id[it["paar"]]], True):
                paare += 1
            else:
                fehler.append(f"{it['id']}: Verknüpfen mit {it['paar']} abgelehnt")
    # Fahrten, dann Übergänge (AddTransition verbindet nur Nachbarn derselben Spur, F15)
    fahrten = uebergaenge = 0
    for it in (i for s in plan["spuren"] if s["art"] == "video" for i in s.get("items", [])):
        obj = nach_id.get(it.get("id"))
        if obj is None:
            continue
        if it.get("fahrt"):
            ab, bis = bp.kanten(it, fps)
            if fahrt_setzen(obj, it["fahrt"], bis - ab):
                fahrten += 1
            else:
                fehler.append(f"{it['id']}: Fahrt nicht gesetzt")
        ue = it.get("uebergang")
        if ue:
            t = obj.AddTransition({"type": ue["typ"], "category": ue.get("kategorie", "simple"), "position": "end",
                                   "alignment": ue.get("lage", "center"),
                                   "duration": max(2, bp.bild(ue["dauer"], fps))})
            if t:
                uebergaenge += 1
            else:
                fehler.append(f"{it['id']}: Übergang {ue['typ']} abgelehnt (Name, Fleisch oder schon einer da)")
    marker = 0
    for m in plan.get("marker", []):
        # frameId zählt relativ zum Timeline-Start, nicht absolut (referenz/api-fakten.md, Marker)
        if tl.AddMarker(bp.bild(m["t"], fps), m.get("farbe", "Blue"), str(m.get("name", ""))[:60],
                        str(m.get("notiz", "")), max(1, bp.bild(m.get("dauer", 0), fps)), str(m.get("data", ""))):
            marker += 1
        else:
            fehler.append(f"Marker {m.get('name')} @ {m['t']} s abgelehnt")
    r.GetProjectManager().SaveProject()
    soll = bp.dauer_bilder(plan)
    ist = tl.GetEndFrame() - s0
    p(f"Paare {paare} · Fahrten {fahrten} · Übergänge {uebergaenge} · Marker {marker} · LUT {zaehler.get('lut', 0)} · "
      f"Länge {ist} Bilder (Plan {soll})")
    if ist != soll:
        fehler.append(f"Timeline-Länge {ist} Bilder, Plan {soll}")
    if bericht_pfad:
        ra.json_schreiben(bericht_pfad, {"timeline": tl.GetName(), "projekt": proj.GetName(),
                                         "gebaut": f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}",
                                         "bilder": ist, "fps": fps, "fehler": fehler, "items": eintraege})
    if fehler:
        p(f"FEHLER ({len(fehler)}):\n  " + "\n  ".join(fehler[:30]))
        return 1
    p(f"OK: „{tl.GetName()}“ im Projekt „{proj.GetName()}“")
    return 0


def main(argv: list[str] | None = None) -> int:
    ra.utf8()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("bauplan")
    ap.add_argument("--sicherung", help="Ordner für die .drp-Sicherung (Vorgabe: <bauplan-ordner>/sicherung)")
    ap.add_argument("--ohne-sicherung", action="store_true")
    ap.add_argument("--bericht", help="Bericht als JSON (Vorgabe: <bauplan>.bau.json)")
    a = ap.parse_args(argv)
    try:
        plan = bp.laden(a.bauplan)
    except (bp.BauplanFehler, OSError, ValueError) as e:
        p(str(e))
        return 2
    plan_ordner = Path(a.bauplan).resolve().parent
    sicherung = None if a.ohne_sicherung else Path(a.sicherung) if a.sicherung else plan_ordner / "sicherung"
    bericht = Path(a.bericht) if a.bericht else Path(a.bauplan).with_suffix(".bau.json")
    try:
        return bauen(plan, sicherung, bericht)
    except ra.ResolveFehler as e:
        p(f"Resolve: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
