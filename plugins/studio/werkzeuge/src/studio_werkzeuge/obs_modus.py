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
import os
import re
from datetime import datetime
from pathlib import Path

from studio_werkzeuge import obs
from studio_werkzeuge.fehler import KonfigFehler, StudioFehler
from studio_werkzeuge.konfig import Konfig

# Source Record kann auch streamen: Server und Schlüssel stehen dann in den Filtereinstellungen.
GEHEIM = re.compile(r"(key|token|pass|secret|auth|server|kennwort|schluessel)", re.IGNORECASE)


def filterliste(konfig: Konfig) -> list[tuple[str, str]]:
    return [(konfig.text("kameras", f"quelle_{k}"), konfig.text("kameras", f"filter_{k}")) for k in "ab"]


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


def geheime_schluessel(stand: list[dict]) -> list[str]:
    """Schlüssel, die nach Zugangsdaten aussehen und einen Wert haben (z. B. Stream-Server und -Schlüssel)."""
    return sorted({k for s in stand for k, v in s["einstellungen"].items() if GEHEIM.search(k) and v not in ("", None)})


def sichern(stand: list[dict], ordner: Path) -> Path:
    """Vollständige Sicherung (sie muss sich zurückspielen lassen). Unter POSIX nur für den Besitzer lesbar (0600)."""
    ordner.mkdir(parents=True, exist_ok=True)
    ziel = ordner / f"obs-filter-{datetime.now():%Y%m%d-%H%M%S}.json"
    zaehler = 2
    while ziel.exists():
        ziel = ordner / f"obs-filter-{datetime.now():%Y%m%d-%H%M%S}-{zaehler}.json"
        zaehler += 1
    fd = os.open(ziel, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(stand, ensure_ascii=False, indent=1))
    return ziel


def zurueckspielen(client: obs.Client, s: dict) -> None:
    """Den Filter mit den gesicherten Einstellungen an alter Stelle wieder anlegen."""
    ziel = {"sourceName": s["quelle"], "filterName": s["filter"]}
    client.send("CreateSourceFilter", {**ziel, "filterKind": s["kind"], "filterSettings": s["einstellungen"]},
                raw=True)
    client.send("SetSourceFilterIndex", {**ziel, "filterIndex": s["index"]}, raw=True)
    if not s["aktiv"]:
        client.send("SetSourceFilterEnabled", {**ziel, "filterEnabled": False}, raw=True)


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
    sicherung = sichern(stand, sicherungsordner)
    zeilen.append(f"Sicherung: {sicherung}")
    if geheim := geheime_schluessel(stand):
        zeilen.append(f"  ! Die Sicherung enthält Zugangsdaten ({', '.join(geheim)}): Datei geschützt aufbewahren, "
                      "nicht weitergeben.")
    for s in stand:
        neu = neue_einstellungen(s["einstellungen"], alle_modi[modus], alle_modi)
        ziel = {"sourceName": s["quelle"], "filterName": s["filter"]}
        client.send("RemoveSourceFilter", ziel, raw=True)
        try:
            client.send("CreateSourceFilter", {**ziel, "filterKind": s["kind"], "filterSettings": neu}, raw=True)
            client.send("SetSourceFilterIndex", {**ziel, "filterIndex": s["index"]}, raw=True)
            if not s["aktiv"]:
                client.send("SetSourceFilterEnabled", {**ziel, "filterEnabled": False}, raw=True)
        except Exception as e:  # noqa: BLE001 - jede Störung beim Neuanlegen: alten Filter zurück
            try:
                zurueckspielen(client, s)
                wieder = "der alte Filter ist wieder angelegt"
            except Exception:  # noqa: BLE001
                wieder = f"der alte Filter ließ sich NICHT zurückspielen, Einstellungen stehen in {sicherung}"
            raise StudioFehler(f"{s['quelle']}: Neuanlegen gescheitert ({type(e).__name__}); {wieder}.") from e
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
