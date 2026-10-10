# SPDX-License-Identifier: MIT
"""Aufnahme-Modus der Source-Record-Filter umschalten, während OBS läuft (`studio obs-modus`).

Die Modi stehen in der Konfiguration (``[obs_modus.modi.<name>]``, z. B. Bitrate für lange Videos, höchste Qualität für
kurze Spezialaufnahmen). Die Filter heißen wie in ``[kameras] quelle_a/filter_a`` und ``quelle_b/filter_b``.

F1 · Encoder lädt nicht neu. Symptom: neue Bitrate steht im Filter, die Datei hat die alte. Ursache:
``SetSourceFilterSettings`` lädt den Encoder des Source-Record-Filters nicht neu. Gegenmittel: Filter entfernen und mit
allen bisherigen Einstellungen plus neuem Modus an derselben Stelle neu anlegen (so macht es dieses Werkzeug).

Sicherheit: Vor jeder Änderung werden alle betroffenen Filter als JSON gesichert (``[obs_modus] sicherung``). Läuft
eine Aufnahme, bricht das Werkzeug ab. ``--probe`` zeigt nur, was sich ändern würde.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from studio_werkzeuge import obs
from studio_werkzeuge.fehler import KonfigFehler, StudioFehler
from studio_werkzeuge.konfig import Konfig


def filterliste(konfig: Konfig) -> list[tuple[str, str]]:
    return [(str(konfig.wert("kameras", f"quelle_{k}")), str(konfig.wert("kameras", f"filter_{k}"))) for k in "ab"]


def modi(konfig: Konfig) -> dict[str, dict]:
    m = konfig.abschnitt("obs_modus.modi")
    if not m:
        raise KonfigFehler("Keine Modi in [obs_modus.modi.<name>] eingetragen.")
    return {name: dict(werte) for name, werte in m.items() if isinstance(werte, dict)}


def neue_einstellungen(alt: dict, modus: dict, alle_modi: dict[str, dict]) -> dict:
    """Bisherige Einstellungen ohne die Schlüssel, die irgendein Modus setzt, plus die des gewählten Modus."""
    modus_schluessel = {k for werte in alle_modi.values() for k in werte}
    neu = {k: v for k, v in alt.items() if k not in modus_schluessel}
    neu.update(modus)
    return neu


def kurz(einst: dict) -> str:
    rc = einst.get("rate_control", "?")
    if rc == "CQP":
        return f"CQP {einst.get('cqp', '?')}"
    return f"{rc} {einst.get('bitrate', '?')} kbit/s (Spitze {einst.get('max_bitrate', '-')})"


def filter_lesen(client: obs.Client, quelle: str, name: str) -> dict:
    f = client.send("GetSourceFilter", {"sourceName": quelle, "filterName": name}, raw=True)
    return {"quelle": quelle, "filter": name, "kind": f["filterKind"], "index": f["filterIndex"],
            "aktiv": f["filterEnabled"], "einstellungen": dict(f.get("filterSettings") or {})}


def sichern(stand: list[dict], ordner: Path) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    ziel = ordner / f"obs-filter-{datetime.now():%Y%m%d-%H%M%S}.json"
    zaehler = 2
    while ziel.exists():
        ziel = ordner / f"obs-filter-{datetime.now():%Y%m%d-%H%M%S}-{zaehler}.json"
        zaehler += 1
    ziel.write_text(json.dumps(stand, ensure_ascii=False, indent=1), encoding="utf-8")
    return ziel


def umschalten(client: obs.Client, filter_: list[tuple[str, str]], modus: str, alle_modi: dict[str, dict],
               sicherungsordner: Path | None, probe: bool = False) -> list[str]:
    """Schaltet alle Filter auf ``modus``; gibt Zeilen für die Ausgabe zurück. Bricht ab, wenn OBS aufnimmt."""
    if modus != "status" and modus not in alle_modi:
        raise StudioFehler(f"Modus {modus!r} unbekannt. Bekannt: status, {', '.join(alle_modi)}.")
    laeuft = modus != "status" and obs.nimmt_auf(client)
    if laeuft and not probe:
        raise StudioFehler("OBS nimmt gerade auf. Erst die Aufnahme stoppen, dann umschalten. Nichts verändert.")
    stand = [filter_lesen(client, q, n) for q, n in filter_]
    zeilen = ["OBS nimmt gerade auf: Umschalten wäre jetzt gesperrt."] if laeuft else []
    if modus == "status":
        return [f"{s['quelle']}: {kurz(s['einstellungen'])} · {s['einstellungen'].get('encoder', '?')} · "
                f"aktiv={s['aktiv']}" for s in stand]
    if probe:
        for s in stand:
            neu = neue_einstellungen(s["einstellungen"], alle_modi[modus], alle_modi)
            zeilen.append(f"{s['quelle']}: {kurz(s['einstellungen'])} → {kurz(neu)} (Probe, nichts verändert)")
        return zeilen
    if sicherungsordner is None:
        raise KonfigFehler("[obs_modus] sicherung fehlt: ohne Sicherung wird nichts verändert.")
    zeilen.append(f"Sicherung: {sichern(stand, sicherungsordner)}")
    for s in stand:
        neu = neue_einstellungen(s["einstellungen"], alle_modi[modus], alle_modi)
        ziel = {"sourceName": s["quelle"], "filterName": s["filter"]}
        client.send("RemoveSourceFilter", ziel, raw=True)
        client.send("CreateSourceFilter", {**ziel, "filterKind": s["kind"], "filterSettings": neu}, raw=True)
        client.send("SetSourceFilterIndex", {**ziel, "filterIndex": s["index"]}, raw=True)
        if not s["aktiv"]:
            client.send("SetSourceFilterEnabled", {**ziel, "filterEnabled": False}, raw=True)
        g = filter_lesen(client, s["quelle"], s["filter"])
        zeilen.append(f"{s['quelle']}: {kurz(s['einstellungen'])} → {kurz(g['einstellungen'])} · Position {g['index']} "
                      f"· aktiv={g['aktiv']}")
        for k in ("record_mode", "path", "encoder"):
            if s["einstellungen"].get(k) != g["einstellungen"].get(k):
                zeilen.append(f"  ! {k} hat sich verändert ({s['einstellungen'].get(k)!r} → "
                              f"{g['einstellungen'].get(k)!r}): im Filter-Dialog prüfen, Sicherung liegt bereit.")
    return zeilen


def einrichten(unter) -> None:
    p = unter.add_parser("obs-modus", help="Aufnahme-Modus der Source-Record-Filter umschalten (sichert vorher)",
                         description=__doc__.split("\n\n")[0])
    p.add_argument("modus", metavar="MODUS", help="status oder ein Name aus [obs_modus.modi]")
    p.add_argument("--probe", action="store_true", help="nur zeigen, was sich ändern würde")
    p.set_defaults(ausfuehren=ausfuehren, braucht_konfig=True)


def ausfuehren(args, konfig: Konfig) -> int:
    alle = modi(konfig) if args.modus != "status" else konfig.abschnitt("obs_modus.modi")
    sicherung = None if args.probe or args.modus == "status" else konfig.pfad_wert("obs_modus", "sicherung")
    client = obs.verbinden(konfig)
    try:
        for zeile in umschalten(client, filterliste(konfig), args.modus, alle, sicherung, args.probe):
            print(zeile)
    finally:
        obs.trennen(client)
    return 0
