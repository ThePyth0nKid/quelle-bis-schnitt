# SPDX-License-Identifier: MIT
"""Wächter der Zwei-Kamera-Aufnahme (`studio waechter`): hört auf OBS und macht aus jedem Take ein Paar.

Bei Rec, nach einigen Sekunden: Liefern beide Kameras ein lebendes Bild (nicht schwarz, kein Standbild)? Wachsen beide
Dateien? Hat das Mikrofon Pegel? Wenn nicht: Hinweis (unter Windows als stille Benachrichtigung, sonst im Protokoll).
Bei Stop: A und B des Takes kommen sofort nach ``<ziel>/<Take>/Roh/``, dann baut ``studio paar --stempel <Take>`` als
eigener Prozess das Paar. Startet währenddessen eine neue Aufnahme, wird der Bau abgebrochen und danach wiederholt.
Beim Start holt der Wächter Takes nach, die noch kein Paar haben, und Stempel aus ``<ziel>/synchron/neu_bauen.txt``.

``--einmal`` braucht kein OBS: holt alle offenen Takes nach und endet. ``--probe`` zeigt nur, was zu tun wäre.
Protokoll: ``<ziel>/synchron/waechter.log``. Der Logger von obsws-python steht auf WARNING (sonst steht das Passwort im
Protokoll). Schwellen der Startprüfung: einstellbare Voreinstellungen, nicht gemessen.
"""
from __future__ import annotations

import base64
import json
import logging
import logging.handlers
import math
import os
import queue
import shutil
import signal
import struct
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np

from studio_werkzeuge import medien, obs
from studio_werkzeuge.fehler import StudioFehler
from studio_werkzeuge.konfig import Konfig
from studio_werkzeuge.paar import (
    PRUEFEN_ZUSATZ,
    STEMPEL_FORMAT,
    Benennung,
    benennung_aus,
    bericht_pfad,
    einstellungen_aus,
    ordner_name,
    paar_finden,
    powershell,
    synchronisieren,
    take_einsortieren,
)

START_PRUEFUNG_S = 4.0
MIKRO_FENSTER_S = 5.0
STUMM_DB = -70.0                  # Spitzenpegel darunter = Mikrofon liefert nichts
SCHWARZ_HELL = 4.0                # mittlere Helligkeit (0..255) darunter = schwarzes Bild
STANDBILD_DIFF = 0.02             # drei Bilder ohne Unterschied = Standbild (eine lebende Kamera rauscht)
MAX_STEMPEL_ABSTAND_S = 3         # Rec-Ereignis ↔ Dateiname (OBS stempelt beim Start der Ausgabe)
NACH_STOP_S = 4.0
EINSORTIEREN_VERSUCHE = 10        # OBS gibt die Dateien erst kurz nach dem Stop frei
EINSORTIEREN_PAUSE_S = 2.0
HERZSCHLAG_S = 5.0
NEUVERBINDEN_S = 10.0

log = logging.getLogger("studio.waechter")


# ── reine Funktionen ─────────────────────────────────────────────────────────────────────────────

def stempel_aus_zeit(t: datetime) -> str:
    return t.strftime(STEMPEL_FORMAT)


def stempel_naechster(kandidaten, ziel: str, max_s: float = MAX_STEMPEL_ABSTAND_S) -> str | None:
    """Der Stempel aus ``kandidaten``, der ``ziel`` am nächsten liegt (höchstens ``max_s`` Sekunden)."""
    t0 = datetime.strptime(ziel, STEMPEL_FORMAT)
    best: tuple[float, str] | None = None
    for s in kandidaten:
        try:
            d = abs((datetime.strptime(s, STEMPEL_FORMAT) - t0).total_seconds())
        except ValueError:
            continue
        if d <= max_s and (best is None or d < best[0]):
            best = (d, s)
    return best[1] if best else None


def bild_urteil(bilder: list[np.ndarray]) -> str | None:
    """None = die Kamera lebt; sonst der Grund."""
    if not bilder:
        return "kein Bild"
    if float(np.mean([b.mean() for b in bilder])) < SCHWARZ_HELL:
        return "Bild schwarz"
    unterschiede = [float(np.abs(a - b).mean()) for a, b in zip(bilder, bilder[1:], strict=False)]
    if unterschiede and max(unterschiede) < STANDBILD_DIFF:
        return "Standbild (kein Signal? Kamera aus?)"
    return None


def mikro_urteil(spitze_mul: float | None) -> str | None:
    if spitze_mul is None:
        return "kein Pegel gemeldet"
    db = 20 * math.log10(spitze_mul) if spitze_mul > 0 else -math.inf
    return None if db > STUMM_DB else f"stumm ({db:.0f} dBFS)"


def datei_urteil(vorher: dict[str, int], nachher: dict[str, int]) -> list[str]:
    probleme = []
    for cam in ("A", "B"):
        if cam not in nachher:
            probleme.append(f"Kamera {cam}: keine Datei")
        elif nachher[cam] <= vorher.get(cam, 0):
            probleme.append(f"Kamera {cam}: Datei wächst nicht")
    return probleme


def bmp_grau(daten: bytes) -> np.ndarray:
    """Ein unkomprimiertes 24- oder 32-Bit-BMP als Graubild (float32, 0..255). OBS liefert Screenshots auf Wunsch als
    BMP; so braucht der Wächter keine Bildbibliothek."""
    if daten[:2] != b"BM":
        raise ValueError("kein BMP")
    versatz = struct.unpack_from("<I", daten, 10)[0]
    breite, hoehe = struct.unpack_from("<ii", daten, 18)
    bits = struct.unpack_from("<H", daten, 28)[0]
    if bits not in (24, 32):
        raise ValueError(f"BMP mit {bits} Bit wird nicht gelesen")
    kanaele = bits // 8
    zeile = (breite * kanaele + 3) // 4 * 4
    roh = np.frombuffer(daten, dtype=np.uint8, count=zeile * abs(hoehe), offset=versatz).reshape(abs(hoehe), zeile)
    pixel = roh[:, : breite * kanaele].reshape(abs(hoehe), breite, kanaele)[:, :, :3].astype(np.float32)
    grau = pixel.mean(axis=2)
    return grau[::-1] if hoehe > 0 else grau   # positive Höhe: unterste Zeile zuerst


def toast_xml(titel: str, text: str) -> str:
    return ('<toast><visual><binding template="ToastGeneric">'
            f"<text>{escape(titel)}</text><text>{escape(text)}</text>"
            '</binding></visual><audio silent="true"/></toast>')


def ergebnis_text(stempel: str, rc: int, bericht: dict | None, fehler: str, ziel: Path) -> tuple[str, str]:
    uhr = f"{stempel[9:11]}:{stempel[11:13]}:{stempel[13:15]}"
    if rc == 0 and bericht:
        wie = {"bild": "nach dem Bild", "bildzahl": "nach der Bildzahl, ±1 Bild"}.get(bericht.get("quelle"),
                                                                                  "nach dem Ton, ±1 Bild")
        ton = bericht.get("ton") or {}
        klicks = ton.get("klicks") or {}
        ton_text = (f" · Ton aus Kamera {ton['quelle']} (Klicks A {klicks.get('A', '?')} / B {klicks.get('B', '?')})"
                    if ton.get("quelle") else "")
        return (f"Take {uhr} synchron",
                f"{ziel / ordner_name(stempel)} · Lücke {bericht['luecke_bilder']} Bilder ({wie}) · Ton bytegleich"
                f"{ton_text}")
    if rc == 1 and bericht:
        grund = (bericht.get("warnungen") or ["siehe Bericht"])[0]
        return f"Take {uhr}: prüfen", f"Ordner „{ordner_name(stempel)}{PRUEFEN_ZUSATZ}“ · {grund}"
    return f"Take {uhr}: Paar nicht gebaut", fehler or f"Exit {rc}"


def bericht_lesen(ziel: Path, stempel: str) -> dict | None:
    datei = bericht_pfad(ziel, ordner_name(stempel))
    return json.loads(datei.read_text(encoding="utf-8")) if datei.is_file() else None


def neu_bauen_lesen(datei: Path, benennung: Benennung | None = None) -> list[str]:
    """Stempel aus ``neu_bauen.txt`` (eine Zeile je Take, ``#`` = Kommentar). Die Datei wird danach geleert."""
    benennung = benennung or Benennung()
    if not datei.is_file():
        return []
    stempel = []
    for zeile in datei.read_text(encoding="utf-8").splitlines():
        zeile = zeile.split("#", 1)[0].strip()
        if zeile and benennung.treffer(f"{benennung.praefix_a}{zeile}{benennung.endung}"):
            stempel.append(zeile)
    datei.write_text("", encoding="utf-8")
    return sorted(set(stempel))


def offene_takes(inbox: Path, ziel: Path, benennung: Benennung | None = None, laufend: str | None = None) -> list[str]:
    """Stempel der Takes ohne Paar: A lose in der Inbox, oder Take-Ordner mit ``Roh/``, aber ohne fertiges Paar.
    Der laufende Take und „… ALT …“-Ordner bleiben außen vor."""
    benennung = benennung or Benennung()
    offen: set[str] = set()
    for p in inbox.glob(benennung.glob("A")) if inbox.is_dir() else []:
        t = benennung.treffer(p.name)
        if t and t[0] == "A" and not (laufend and stempel_naechster([t[1]], laufend)):
            offen.add(t[1])
    for take in ziel.iterdir() if ziel.is_dir() else []:
        name = take.name.removesuffix(PRUEFEN_ZUSATZ)
        fertig = (take / f"{name} Cam A.mp4").is_file() and (take / f"{name} Cam B.mp4").is_file()
        if not (take / "Roh").is_dir() or fertig or " ALT " in take.name:
            continue
        for p in (take / "Roh").glob(benennung.glob("A")):
            t = benennung.treffer(p.name)
            if t and t[0] == "A":
                offen.add(t[1])
    return sorted(offen)


def arbeitsordner_aufraeumen(ziel: Path, stempel: str | None = None) -> list[Path]:
    """Liegengebliebene „~in Arbeit …“-Ordner eines abgebrochenen Baus entfernen: die des Takes, ohne Stempel alle."""
    weg = []
    muster = f"~in Arbeit {ordner_name(stempel)} *" if stempel else "~in Arbeit *"
    for p in ziel.glob(muster) if ziel.is_dir() else []:
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
            weg.append(p)
    return weg


# ── Prozess- und System-Grenze ───────────────────────────────────────────────────────────────────

def hinweis(titel: str, text: str, windows: bool = True) -> None:
    """Stiller Windows-Hinweis (ohne Ton, ohne Fokus); sonst nur Protokoll."""
    log.info("Hinweis: %s · %s", titel, text)
    if not windows or os.name != "nt":
        return
    xml = toast_xml(titel, text).replace("'", "''")
    app = r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"
    skript = (
        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]"
        " | Out-Null;"
        "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null;"
        "$x = New-Object Windows.Data.Xml.Dom.XmlDocument;"
        f"$x.LoadXml('{xml}');"
        "$t = New-Object Windows.UI.Notifications.ToastNotification $x;"
        f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{app}').Show($t)")
    kodiert = base64.b64encode(skript.encode("utf-16-le")).decode("ascii")
    try:
        subprocess.run([powershell(), "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-EncodedCommand",
                        kodiert], capture_output=True, timeout=20, check=True, **medien.OHNE_FENSTER)
    except (OSError, subprocess.SubprocessError) as e:
        log.warning("Hinweis nicht gezeigt (%s)", e)


def baum_beenden(p: subprocess.Popen) -> None:
    """Den Bau-Prozess samt Kindern (ffmpeg) beenden; nur diesen eigenen Prozessbaum."""
    if os.name == "nt":
        taskkill = str(Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32" / "taskkill.exe")
        subprocess.run([taskkill, "/T", "/F", "/PID", str(p.pid)], capture_output=True, **medien.OHNE_FENSTER)
    else:
        try:
            os.killpg(p.pid, signal.SIGTERM)
        except OSError:
            p.terminate()


def einzige_instanz(pfad: Path):
    """Sperrdatei halten; None, wenn schon ein Wächter läuft."""
    f = open(pfad, "a+b")  # noqa: SIM115 - bleibt offen, solange der Wächter lebt
    f.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return None
    return f


def protokoll_einrichten(ordner: Path, vordergrund: bool) -> None:
    ordner.mkdir(parents=True, exist_ok=True)
    handler: list[logging.Handler] = [logging.handlers.RotatingFileHandler(
        ordner / "waechter.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")]
    if vordergrund and sys.stdout is not None:
        handler.append(logging.StreamHandler(sys.stdout))
    logging.getLogger("obsws_python").setLevel(logging.WARNING)
    log.setLevel(logging.INFO)
    log.propagate = False
    for h in handler:
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        log.addHandler(h)


# ── Ohne OBS: einmal nachholen ───────────────────────────────────────────────────────────────────

def einmal(konfig: Konfig, probe: bool = False) -> list[str]:
    """Alle offenen Takes einsortieren und bauen (im selben Prozess). Gibt Zeilen für die Ausgabe zurück."""
    inbox = konfig.pfad_wert("pfade", "inbox")
    ziel = konfig.pfad_wert("pfade", "ziel", inbox)
    benennung, einst = benennung_aus(konfig), einstellungen_aus(konfig)
    neu = [] if probe else neu_bauen_lesen(ziel / "synchron" / "neu_bauen.txt", benennung)
    zeilen = []
    for s in sorted(set(offene_takes(inbox, ziel, benennung)) | set(neu)):
        try:
            a, b, _ = paar_finden(inbox, s, ziel, benennung)
        except StudioFehler as e:
            zeilen.append(f"Take {s}: nicht nachgeholt ({e})")
            continue
        if probe:
            zeilen.append(f"Take {s}: würde einsortiert und gebaut ({a.name} + {b.name})")
            continue
        arbeitsordner_aufraeumen(ziel, s)
        aus = take_einsortieren(a, b, ziel, s)
        try:
            bericht = synchronisieren(aus["A"], aus["B"], ziel, s, einst)
            zeilen.append(f"Take {s}: {'GRÜN' if bericht['ok'] else 'ROT, prüfen'} → {bericht['ordner']}")
        except StudioFehler as e:
            zeilen.append(f"Take {s}: Paar nicht gebaut ({e})")
    return zeilen or ["Keine offenen Takes."]


# ── Mit OBS ──────────────────────────────────────────────────────────────────────────────────────

class Waechter:
    """Lauscht auf Rec/Stop. ``req_fabrik``/``ereignis_fabrik`` liefern die OBS-Clients (in Tests Attrappen)."""

    def __init__(self, konfig: Konfig, req_fabrik=None, ereignis_fabrik=None) -> None:
        self.konfig = konfig
        self.inbox = konfig.pfad_wert("pfade", "inbox")
        self.ziel = konfig.pfad_wert("pfade", "ziel", self.inbox)
        self.benennung = benennung_aus(konfig)
        self.quellen = {k.upper(): str(konfig.wert("kameras", f"quelle_{k}", "")) for k in "ab"}
        self.filter_a = str(konfig.wert("kameras", "filter_a", ""))
        self.windows_hinweis = bool(konfig.wert("waechter", "windows_hinweis", True))
        self.startpruefung = bool(konfig.wert("waechter", "startpruefung", True))
        self.bau_max_s = float(konfig.wert("waechter", "bau_max_min", 60)) * 60
        self.req_fabrik = req_fabrik or (lambda: obs.verbinden(konfig))
        self.ereignis_fabrik = ereignis_fabrik or (lambda **kw: obs.ereignis_client(konfig, **kw))
        self.nimmt_auf = threading.Event()
        self.auftraege: queue.Queue[str] = queue.Queue()
        self.vorgemerkt: set[str] = set()
        self.merk_lock = threading.Lock()
        self.req_lock = threading.RLock()
        self.start_zeit: datetime | None = None
        self.req = None
        self.ev = None
        self.mikro_name: str | None = None
        self.nachgeholt = False

    def melde(self, titel: str, text: str) -> None:
        hinweis(titel, text, self.windows_hinweis)

    def anfrage(self, art: str, daten: dict | None = None) -> dict:
        with self.req_lock:
            if self.req is None:
                raise ConnectionError("OBS nicht verbunden")
            return self.req.send(art, daten, raw=True) or {}

    def verbinden(self) -> None:
        with self.req_lock:
            self.req = self.req_fabrik()
            if self.quellen["A"]:
                for f in self.anfrage("GetSourceFilterList", {"sourceName": self.quellen["A"]}).get("filters", []):
                    if f.get("filterName") == self.filter_a or f.get("filterKind") == "source_record_filter":
                        self.mikro_name = (f.get("filterSettings") or {}).get("audio_source") or self.mikro_name
            status = self.anfrage("GetRecordStatus")
            if status.get("outputActive"):
                self.start_zeit = datetime.now() - timedelta(milliseconds=status.get("outputDuration") or 0)
                self.nimmt_auf.set()
            else:
                self.nimmt_auf.clear()
            self.ev = self.ereignis_fabrik()
            self.ev.callback.register(self.on_record_state_changed)
        log.info("mit OBS verbunden (Mikrofon der Filter: %s, Aufnahme läuft: %s)", self.mikro_name,
                 self.nimmt_auf.is_set())

    def trennen(self) -> None:
        with self.req_lock:
            for c in (self.ev, self.req):
                if c is not None:
                    obs.trennen(c)
            self.ev = self.req = None

    def on_record_state_changed(self, data) -> None:
        zustand = getattr(data, "output_state", "")
        if zustand == "OBS_WEBSOCKET_OUTPUT_STARTED":
            self.start_zeit = datetime.now()
            self.nimmt_auf.set()
            log.info("Rec gestartet %s", stempel_aus_zeit(self.start_zeit))
            if self.startpruefung:
                threading.Thread(target=self.start_pruefen, args=(self.start_zeit,), daemon=True).start()
        elif zustand == "OBS_WEBSOCKET_OUTPUT_STOPPED":
            self.nimmt_auf.clear()
            log.info("Rec gestoppt")
            if self.start_zeit is not None:
                threading.Thread(target=self.nach_stop, args=(self.start_zeit,), daemon=True).start()

    def _gilt_noch(self, start: datetime) -> bool:
        return self.start_zeit == start and self.nimmt_auf.is_set()

    def groessen(self, start: datetime) -> dict[str, int]:
        ziel = stempel_aus_zeit(start)
        aus = {}
        for cam in ("A", "B"):
            kandidaten = {}
            for p in self.inbox.glob(self.benennung.glob(cam)):
                t = self.benennung.treffer(p.name)
                if t and t[0] == cam:
                    kandidaten[t[1]] = p
            s = stempel_naechster(kandidaten, ziel)
            if s is not None:
                aus[cam] = kandidaten[s].stat().st_size
        return aus

    def bild(self, quelle: str) -> np.ndarray:
        daten = self.anfrage("GetSourceScreenshot", {"sourceName": quelle, "imageFormat": "bmp",
                                                     "imageWidth": 160})["imageData"]
        return bmp_grau(base64.b64decode(daten.split(",", 1)[-1]))

    def mikro_spitze(self, dauer_s: float) -> float | None:
        spitze: dict[str, float | None] = {"wert": None}

        def on_input_volume_meters(data) -> None:
            for eingang in getattr(data, "inputs", []) or []:
                pegel = eingang.get("inputLevelsMul") or []
                if eingang.get("inputName") == self.mikro_name and pegel:
                    spitze["wert"] = max(spitze["wert"] or 0.0, max(kanal[1] for kanal in pegel))

        ev = self.ereignis_fabrik(subs=1 << 16)   # InputVolumeMeters (obs-websocket EventSubscription)
        ev.callback.register(on_input_volume_meters)
        time.sleep(dauer_s)
        obs.trennen(ev)
        return spitze["wert"]

    def start_pruefen(self, start: datetime) -> None:
        time.sleep(START_PRUEFUNG_S)
        if not self._gilt_noch(start):
            return
        probleme: list[str] = []
        try:
            g1 = self.groessen(start)
            time.sleep(1.0)
            probleme += datei_urteil(g1, self.groessen(start))
            for cam, quelle in self.quellen.items():
                if not quelle:
                    continue
                bilder = []
                for _ in range(3):
                    bilder.append(self.bild(quelle))
                    time.sleep(0.4)
                if (urteil := bild_urteil(bilder)) is not None:
                    probleme.append(f"Kamera {cam} ({quelle}): {urteil}")
            if self.mikro_name and (urteil := mikro_urteil(self.mikro_spitze(MIKRO_FENSTER_S))) is not None:
                probleme.append(f"Mikrofon: {urteil}")
        except Exception as e:  # noqa: BLE001 - die Prüfung darf die Aufnahme nie stören
            log.exception("Startprüfung abgebrochen")
            probleme.append(f"Prüfung unvollständig ({e})")
        if not self._gilt_noch(start):
            return
        if probleme:
            log.warning("Startprüfung: %s", " · ".join(probleme))
            self.melde("Aufnahme prüfen", " · ".join(probleme))
        else:
            log.info("Startprüfung ok: beide Kameras leben, beide Dateien wachsen, Mikrofon hat Pegel")

    def nach_stop(self, start: datetime) -> None:
        try:
            time.sleep(NACH_STOP_S)
            s = None
            for versuch in range(EINSORTIEREN_VERSUCHE):
                if versuch:
                    time.sleep(EINSORTIEREN_PAUSE_S)
                kandidaten = [t[1] for p in self.inbox.glob(self.benennung.glob("A"))
                              if (t := self.benennung.treffer(p.name)) and t[0] == "A"]
                if (s := stempel_naechster(kandidaten, stempel_aus_zeit(start))) is not None:
                    break
            if s is None:
                self.melde("Take ohne Kamera A", f"Zum Take {stempel_aus_zeit(start)} gibt es keine A-Datei in "
                           f"{self.inbox}.")
                return
            self.einsortieren(s)
            self.vormerken(s)
        except Exception:  # noqa: BLE001 - ein kaputter Take darf den Wächter nicht still beenden
            log.exception("Nach dem Stop %s gescheitert", stempel_aus_zeit(start))
            self.melde("Take nicht einsortiert", f"Take {stempel_aus_zeit(start)}: siehe waechter.log; ein Neustart "
                       "des Wächters holt ihn nach.")

    def vormerken(self, stempel: str) -> None:
        with self.merk_lock:
            if stempel in self.vorgemerkt:
                return
            self.vorgemerkt.add(stempel)
        log.info("Paar %s vorgemerkt", stempel)
        self.auftraege.put(stempel)

    def einsortieren(self, stempel: str) -> None:
        aus: dict = {"hinweise": []}
        for versuch in range(EINSORTIEREN_VERSUCHE):
            if versuch:
                time.sleep(EINSORTIEREN_PAUSE_S)
            try:
                a, b, _ = paar_finden(self.inbox, stempel, self.ziel, self.benennung)
            except StudioFehler as e:
                log.warning("Take %s nicht einsortiert: %s", stempel, e)
                return
            aus = take_einsortieren(a, b, self.ziel, stempel)
            if not aus["hinweise"]:
                log.info("Take %s einsortiert: %s", stempel, aus["ordner"])
                return
        log.warning("Take %s nur zum Teil einsortiert: %s", stempel, " · ".join(aus["hinweise"]))

    def nachholen(self) -> None:
        for p in arbeitsordner_aufraeumen(self.ziel):
            log.info("Arbeitsordner eines abgebrochenen Baus entfernt: %s", p.name)
        laufend = stempel_aus_zeit(self.start_zeit) if self.nimmt_auf.is_set() and self.start_zeit else None
        neu = neu_bauen_lesen(self.ziel / "synchron" / "neu_bauen.txt", self.benennung)
        for s in sorted(set(offene_takes(self.inbox, self.ziel, self.benennung, laufend)) | set(neu)):
            try:
                paar_finden(self.inbox, s, self.ziel, self.benennung)
            except StudioFehler as e:
                log.warning("Take %s nicht nachgeholt: %s", s, e)
                continue
            self.einsortieren(s)
            self.vormerken(s)

    def bauen(self, stempel: str) -> tuple[int, bool]:
        """(Exit-Code, fertig). fertig=False: abgebrochen, weil eine Aufnahme begann."""
        synchron = self.ziel / "synchron"
        synchron.mkdir(parents=True, exist_ok=True)
        arbeitsordner_aufraeumen(self.ziel, stempel)
        umgebung = dict(os.environ, PYTHONUTF8="1")
        if self.konfig.pfad is not None:
            umgebung["STUDIO_KONFIG"] = str(self.konfig.pfad)
        aufruf = [sys.executable, "-m", "studio_werkzeuge", "paar", "--stempel", stempel]
        extra = {} if os.name == "nt" else {"start_new_session": True}
        with open(synchron / f"waechter-{stempel}.log", "wb") as aus:
            p = subprocess.Popen(aufruf, stdout=aus, stderr=subprocess.STDOUT, env=umgebung, **medien.OHNE_FENSTER,
                                 **extra)
            beginn = time.monotonic()
            while p.poll() is None:
                if self.nimmt_auf.is_set():
                    baum_beenden(p)
                    p.wait()
                    log.info("Bau %s abgebrochen (Aufnahme läuft), wird wiederholt", stempel)
                    return p.returncode, False
                if time.monotonic() - beginn > self.bau_max_s:
                    baum_beenden(p)
                    p.wait()
                    aus.write(f"\nFEHLER: Zeitüberschreitung nach {self.bau_max_s / 60:.0f} min\n".encode())
                    return 2, True
                time.sleep(0.5)
        return p.returncode, True

    def melden(self, stempel: str, rc: int) -> None:
        bericht = bericht_lesen(self.ziel, stempel) if rc in (0, 1) else None
        datei = self.ziel / "synchron" / f"waechter-{stempel}.log"
        zeilen = datei.read_text(encoding="utf-8", errors="replace").strip().splitlines() if datei.is_file() else []
        fehler = next((z for z in reversed(zeilen) if z.startswith("FEHLER")), zeilen[-1] if zeilen else "")
        titel, text = ergebnis_text(stempel, rc, bericht, fehler, self.ziel)
        (log.info if rc == 0 else log.warning)("%s: %s", titel, text)
        self.melde(titel, text)

    def arbeiten(self) -> None:
        while True:
            stempel = self.auftraege.get()
            try:
                while True:
                    while self.nimmt_auf.is_set():
                        time.sleep(1.0)
                    rc, fertig = self.bauen(stempel)
                    if fertig:
                        break
                self.melden(stempel, rc)
            except Exception:  # noqa: BLE001 - ein kaputter Take darf den Wächter nicht beenden
                log.exception("Bau %s gescheitert", stempel)
            finally:
                with self.merk_lock:
                    self.vorgemerkt.discard(stempel)

    def laufen(self) -> None:
        threading.Thread(target=self.arbeiten, daemon=True).start()
        wartet_seit: float | None = None
        while True:
            try:
                self.verbinden()
                if wartet_seit is not None:
                    log.info("OBS nach %.0f s wieder da", time.monotonic() - wartet_seit)
                    wartet_seit = None
                if not self.nachgeholt:
                    self.nachgeholt = True
                    threading.Thread(target=self.nachholen, daemon=True).start()
                while True:
                    time.sleep(HERZSCHLAG_S)
                    self.anfrage("GetVersion")
            except Exception as e:  # noqa: BLE001 - OBS zu, Neustart, Passwort: immer neu verbinden
                if wartet_seit is None:
                    wartet_seit = time.monotonic()
                    log.info("OBS nicht erreichbar (%s); neuer Versuch alle %.0f s", type(e).__name__, NEUVERBINDEN_S)
                self.trennen()
                self.nimmt_auf.clear()
                time.sleep(NEUVERBINDEN_S)


# ── CLI ──────────────────────────────────────────────────────────────────────────────────────────

def einrichten(unter) -> None:
    p = unter.add_parser("waechter", help="OBS beobachten und nach jedem Take das Paar bauen",
                         description=__doc__.split("\n\n")[0])
    p.add_argument("--einmal", action="store_true", help="ohne OBS: offene Takes nachholen und enden")
    p.add_argument("--probe", action="store_true", help="nur zeigen, was zu tun wäre")
    p.add_argument("--vordergrund", action="store_true", help="Protokoll zusätzlich in der Konsole")
    p.set_defaults(ausfuehren=ausfuehren, braucht_konfig=True)


def ausfuehren(args, konfig: Konfig) -> int:
    if args.einmal or args.probe:
        for zeile in einmal(konfig, probe=args.probe):
            print(zeile)
        if args.probe and not args.einmal:
            print("Probe: ohne --einmal liefe der Wächter dauerhaft mit OBS.")
        return 0
    inbox = konfig.pfad_wert("pfade", "inbox")
    synchron = konfig.pfad_wert("pfade", "ziel", inbox) / "synchron"
    protokoll_einrichten(synchron, args.vordergrund)
    sperre = einzige_instanz(synchron / "waechter.lock")
    if sperre is None:
        print("Ein Wächter läuft schon; dieser endet.")
        return 0
    log.info("Wächter gestartet (PID %s)", os.getpid())
    Waechter(konfig).laufen()
    return 0
