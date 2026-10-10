# SPDX-License-Identifier: MIT
"""`studio paar`: Datei-Ablage und Ende-zu-Ende mit künstlichen Videos (übernommen aus der Vorlage, angepasst).

Das künstliche Paar entsteht aus EINEM verlustfreien Master: ein helles Quadrat springt zufällig über dunklen Grund,
dazu Rauschen als Ton. Kamera A beginnt bei Bild 0; Bild und Ton von B beginnen getrennt einstellbar später. Nach dem
Bauen muss Bild i von A dasselbe zeigen wie Bild i von B, und beide Tonspuren müssen bytegleich sein.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import threading
from pathlib import Path

import numpy as np
import pytest
from studio_werkzeuge import medien
from studio_werkzeuge import paar as ps
from studio_werkzeuge.cli import main
from studio_werkzeuge.fehler import KonfigFehler, StudioFehler
from studio_werkzeuge.synchron import Plan, versatz_finden

FPS = 25
W_T, H_T = 320, 180
FFMPEG_DA = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
braucht_ffmpeg = pytest.mark.skipif(not FFMPEG_DA, reason="ffmpeg fehlt")
STEMPEL = "20260314-101500"
NAME = "2026-03-14 10-15-00"


def _dateien(ordner: Path, *namen: str) -> None:
    ordner.mkdir(parents=True, exist_ok=True)
    for n in namen:
        (ordner / n).write_bytes(b"x")


# ── Benennung, Befehle ───────────────────────────────────────────────────────────────────────────

def test_benennung_aus_konfiguration(tmp_path, hilfe):
    k = hilfe.konfig_aus(tmp_path, '[kameras]\npraefix_a = "front-"\npraefix_b = "seite-"\nendung = ".mkv"\n')
    b = ps.benennung_aus(k)
    assert b.treffer("front-20260314-101500.mkv") == ("A", STEMPEL)
    assert b.treffer("SEITE-20260314-101500.MKV") == ("B", STEMPEL)
    assert b.treffer("front-20260314-101500.mp4") is None and b.glob("B") == "seite-*.mkv"
    with pytest.raises(KonfigFehler):
        ps.Benennung("cam-", "CAM-")


def test_einstellungen_werden_geprueft(tmp_path, hilfe):
    assert ps.einstellungen_aus(hilfe.konfig_aus(tmp_path, "")).rohdateien == "behalten"   # Voreinstellung: behalten
    for falsch in ('[paar]\ndrehung_b = "schief"\n', '[paar]\nrohdateien = "loeschen"\n', '[paar]\nencoder = "x"\n'):
        with pytest.raises(KonfigFehler):
            ps.einstellungen_aus(hilfe.konfig_aus(tmp_path, falsch))


def test_befehle_bildgenau_und_ton_exakt_lang():
    cmd = ps.befehl_neu(Path("b.mp4"), Path("t.m4a"), Plan("A", 4, 592, 1), 25.0, Path("z.mp4"), "libx264", 18)
    erwartet = "tpad=start_mode=clone:start=4,trim=end_frame=591,tpad=stop_mode=clone:stop=1,setpts=N/25/TB"
    assert cmd[cmd.index("-vf") + 1] == erwartet
    assert cmd[cmd.index("-frames:v") + 1] == "592"
    frueher = ps.befehl_neu(Path("b.mp4"), Path("t.m4a"), Plan("B", -3, 500, 0), 25.0, Path("z.mp4"), "libx264", 18,
                            "transpose=2")
    assert frueher[frueher.index("-vf") + 1] == "trim=start_frame=3:end_frame=503,transpose=2,setpts=N/25/TB"
    af = (t := ps.befehl_ton(Path("b.mp4"), 588, 25.0, Path("t.wav")))[t.index("-af") + 1]
    assert "apad=whole_len=1128960" in af and "atrim=end_sample=1128960" in af
    nvenc = ps.encoder_args("h264_nvenc", 18, 25.0)
    assert "-bf" in nvenc and nvenc[nvenc.index("-preset") + 1] == "p4"


def test_befehl_ton_schiebt_die_andere_spur():
    af = (t := ps.befehl_ton(Path("a.mp4"), 500, 25.0, Path("t.wav"), 0.28))[t.index("-af") + 1]
    assert af.startswith("aresample=48000,atrim=start_sample=13440,asetpts=PTS-STARTPTS,apad=whole_len=960000")
    af = (t := ps.befehl_ton(Path("b.mp4"), 500, 25.0, Path("t.wav"), -0.28, quelle_s=19.0))[t.index("-af") + 1]
    assert "adelay=13440S:all=1,afade=t=in:st=0.280000:d=0.005," in af and "afade=t=out:st=19.275000:d=0.005,apad" in af


def test_ordner_name():
    assert ps.ordner_name(STEMPEL) == NAME and ps.ordner_name("freier-name") == "freier-name"


# ── Paare finden und ablegen ─────────────────────────────────────────────────────────────────────

def test_paar_finden_neuester_stempel_b_eine_sekunde_daneben(tmp_path):
    _dateien(tmp_path, "cam-A-20260314-091546.mp4", "cam-B-20260314-091546.mp4",
             "cam-A-20260314-101703.mp4", "cam-B-20260314-101704.mp4", "cam-A-kaputt.mp4")
    a, b, stempel = ps.paar_finden(tmp_path)
    assert stempel == "20260314-101703" and b.name == "cam-B-20260314-101704.mp4"
    assert ps.paar_finden(tmp_path, "20260314-091546")[1].name == "cam-B-20260314-091546.mp4"


def test_paar_finden_fehlerfaelle(tmp_path):
    _dateien(tmp_path / "x", "cam-A-20260314-101703.mp4", "cam-B-20260314-101710.mp4")
    with pytest.raises(StudioFehler, match="keine B-Datei"):
        ps.paar_finden(tmp_path / "x")
    _dateien(tmp_path / "y", "cam-A-20260314-120000.mp4", "cam-A-20260314-120001.mp4", "cam-B-20260314-120001.mp4")
    with pytest.raises(StudioFehler, match="nicht eindeutig"):
        ps.paar_finden(tmp_path / "y", "20260314-120000")
    with pytest.raises(StudioFehler):
        ps.paar_finden(tmp_path / "gibt-es-nicht")


def test_paar_finden_an_allen_orten(tmp_path):
    inbox, ziel = tmp_path / "inbox", tmp_path / "ziel"
    _dateien(inbox / "2026-03-06 12-12-59", "cam-A-20260306-121259.mp4", "cam-B-20260306-121259.mp4")
    _dateien(ziel / NAME / "Roh", f"cam-A-{STEMPEL}.mp4", f"cam-B-{STEMPEL}.mp4")
    a, b, _ = ps.paar_finden(inbox, "20260306-121259")
    assert a.parent.name == "2026-03-06 12-12-59"
    a, b, s = ps.paar_finden(inbox, None, ziel)
    assert s == STEMPEL and a.parent.name == "Roh"


def test_take_ordner_vorbereiten(tmp_path):
    ordner, hinweis, umzug = ps.take_ordner_vorbereiten(tmp_path, NAME, rot=False)
    assert ordner == tmp_path / NAME and ordner.is_dir() and hinweis is None and umzug is None
    roh_a = ordner / "Roh" / f"cam-A-{STEMPEL}.mp4"
    _dateien(roh_a.parent, roh_a.name)
    rot, hinweis, umzug = ps.take_ordner_vorbereiten(tmp_path, NAME, rot=True)
    assert rot.name == f"{NAME} PRUEFEN" and (rot / "Roh" / roh_a.name).is_file() and "umbenannt" in hinweis
    assert ps.pfad_nach_umzug(roh_a, umzug) == rot / "Roh" / roh_a.name
    (tmp_path / NAME).mkdir()
    ok, hinweis, umzug = ps.take_ordner_vorbereiten(tmp_path, NAME, rot=False)
    assert ok.is_dir() and umzug[1].name.startswith(f"{NAME} PRUEFEN ALT ")


def test_take_einsortieren_und_roh(tmp_path):
    inbox = tmp_path / "inbox"
    a, b = inbox / f"cam-A-{STEMPEL}.mp4", inbox / f"cam-B-{STEMPEL}.mp4"
    _dateien(inbox, a.name, b.name)
    aus = ps.take_einsortieren(a, b, inbox, STEMPEL)
    assert aus["hinweise"] == [] and aus["A"] == inbox / NAME / "Roh" / a.name and aus["B"].is_file()
    assert [p.name for p in inbox.iterdir()] == [NAME]
    assert ps.take_einsortieren(aus["A"], aus["B"], inbox, STEMPEL) == aus          # nochmal: nichts passiert
    assert ps.paar_finden(inbox, STEMPEL, inbox)[:2] == (aus["A"], aus["B"])


def test_roh_entsorgen_meldet_was_nicht_geht(tmp_path):
    a = tmp_path / "cam-A.mp4"
    a.write_bytes(b"a")
    hinweise = ps.roh_entsorgen((a, tmp_path / "fehlt.mp4"), lambda p: p.unlink())
    assert len(hinweise) == 1 and "fehlt.mp4" in hinweise[0] and not a.exists()


@pytest.mark.skipif(sys.platform == "win32", reason="außerhalb von Windows")
def test_papierkorb_nur_unter_windows(tmp_path):
    a = tmp_path / "x.mp4"
    a.write_bytes(b"a")
    with pytest.raises(OSError, match="nur unter Windows"):
        ps.papierkorb(a)
    assert a.exists()                                                         # nie endgültig löschen


def test_bewegung_lesen_haengt_nicht_an_vollem_stderr():
    fb = ps.W * ps.H * 3 // 2
    kind = ("import sys\n"
            f"fb = {fb}\n"
            "for i in range(5):\n"
            "    sys.stderr.write('W' * 200000); sys.stderr.flush()\n"
            "    sys.stdout.buffer.write(bytes([i * 10]) * fb); sys.stdout.flush()\n")
    ergebnis: dict = {}
    t = threading.Thread(target=lambda: ergebnis.setdefault("m", ps.bewegung_lesen([sys.executable, "-c", kind], "P")),
                         daemon=True)
    t.start()
    t.join(timeout=30)
    assert not t.is_alive(), "Lese-Schleife hängt (stderr-Puffer voll)"
    assert len(ergebnis["m"]) == 4 and np.allclose(ergebnis["m"], 10.0)


# ── Ende zu Ende ─────────────────────────────────────────────────────────────────────────────────

def _ff(*args: str, eingabe: bytes | None = None) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], input=eingabe, check=True)


def _master(pfad: Path, ton: str, bilder: int = 350, seed: int = 3) -> None:
    rng = np.random.default_rng(seed)
    x, y = 100.0, 60.0
    folge = np.full((bilder, H_T, W_T), 40, dtype=np.uint8)
    for i in range(bilder):
        schritt = rng.choice([0, 6, 12, 24, 36])
        x = (x + rng.uniform(-1, 1) * schritt) % (W_T - 60)
        y = (y + rng.uniform(-1, 1) * schritt) % (H_T - 60)
        folge[i, int(y): int(y) + 60, int(x): int(x) + 60] = 230
    _ff("-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W_T}x{H_T}", "-r", str(FPS), "-i", "-",
        "-f", "lavfi", "-i", ton, "-shortest", "-c:v", "ffv1", "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", str(pfad),
        eingabe=folge.tobytes())


ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-bf", "2", "-g", "250", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "128k"]
SPRACHE = ("anoisesrc=d=15:c=pink:r=48000:a=0.08:seed=7[n];sine=f=110:r=48000:d=15,volume=2.5[s];"
           "[n][s]amix=inputs=2:normalize=0")
AUSSETZER = ("volume=enable='between(t,3,3.03)+between(t,4.6,4.63)+between(t,6.5,6.53)+between(t,7.8,7.83)"
             "+between(t,9,9.03)+between(t,10.7,10.73)':volume=0")


def _paar(ordner: Path, ton: str = "anoisesrc=d=15:c=pink:r=48000:a=0.3:seed=7", b_bild_s: float = 0.16,
          b_ton_s: float = 0.16, b_filter: str | None = None, a_ton_filter: str | None = None,
          b_ton_filter: str | None = None) -> tuple[Path, Path]:
    master = ordner.parent / f"{ordner.name}-master.mkv"
    _master(master, ton)
    a, b = ordner / f"cam-A-{STEMPEL}.mp4", ordner / f"cam-B-{STEMPEL}.mp4"
    _ff("-i", str(master), "-t", "13.6", *(["-af", a_ton_filter] if a_ton_filter else []), *ENC, str(a))
    extra = (["-vf", b_filter] if b_filter else []) + (["-af", b_ton_filter] if b_ton_filter else [])
    _ff("-ss", f"{b_bild_s}", "-i", str(master), "-ss", f"{b_ton_s}", "-i", str(master), "-map", "0:v:0", "-map",
        "1:a:0", "-t", "13.36", *extra, *ENC, str(b))
    return a, b


def _graubilder(pfad: Path, vorher: str | None = None) -> np.ndarray:
    vf = (f"{vorher}," if vorher else "") + "scale=160:90,format=gray"
    roh = subprocess.run(["ffmpeg", "-v", "error", "-i", str(pfad), "-vf", vf, "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(roh, dtype=np.uint8).reshape(-1, 90, 160).astype(np.float32)


ZURUECKDREHEN = {"links": "transpose=1", "rechts": "transpose=2", "keine": None}


def _deckungsgleich(bericht: dict) -> None:
    fa = _graubilder(Path(bericht["ausgaben"]["A"]))
    fb = _graubilder(Path(bericht["ausgaben"]["B"]), ZURUECKDREHEN[bericht["pruefung"]["drehung_b"]])
    n = min(len(fa), len(fb)) - 4
    abw = {lag: float(np.abs(fa[2 + lag: 2 + lag + n] - fb[2: 2 + n]).mean()) for lag in (-2, -1, 0, 1, 2)}
    assert min(abw, key=abw.get) == 0, abw
    assert abw[0] < 0.5 * min(abw[-1], abw[1]), abw


@braucht_ffmpeg
def test_ende_zu_ende_zwei_videos_und_rohdateien_behalten(tmp_path):
    """Voreinstellung: grün, genau zwei deckungsgleiche Videos im Take-Ordner, die Rohdateien bleiben in Roh/."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    a, b = _paar(inbox)
    aus = ps.take_einsortieren(a, b, inbox, STEMPEL)
    bericht = ps.synchronisieren(aus["A"], aus["B"], inbox, STEMPEL, ps.Einstellungen(cq=14))
    assert (bericht["luecke_bilder"], bericht["quelle"]) == (4, "bild") and bericht["ok"], bericht["warnungen"]
    p = bericht["pruefung"]
    assert p["bilder"]["A"] == p["bilder"]["B"] == 340 and p["ton_bytegleich"]
    assert bericht["plan"] == {"frueh": "A", "vorne": 4, "bilder": 340, "auffuellen": 2}
    _deckungsgleich(bericht)
    ordner = inbox / NAME
    assert sorted(q.name for q in ordner.iterdir()) == [f"{NAME} Cam A.mp4", f"{NAME} Cam B.mp4", "Roh"]
    assert (ordner / "Roh" / a.name).is_file() and (ordner / "Roh" / b.name).is_file()
    assert Path(bericht["bericht"]) == inbox / "synchron" / f"{NAME}.json"
    assert sorted(q.name for q in inbox.iterdir()) == [NAME, "synchron"]          # kein ~in Arbeit, nichts lose


@braucht_ffmpeg
def test_papierkorb_modus_nach_gruenem_bau(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    a, b = _paar(inbox)
    aus = ps.take_einsortieren(a, b, inbox, STEMPEL)
    weg: list[Path] = []
    bericht = ps.synchronisieren(aus["A"], aus["B"], inbox, STEMPEL, ps.Einstellungen(rohdateien="papierkorb"),
                                 entsorgen=lambda q: (weg.append(q), q.unlink()))
    assert bericht["ok"] and weg == [aus["A"], aus["B"]] and not (inbox / NAME / "Roh").exists()


@braucht_ffmpeg
def test_ton_kommt_aus_der_kamera_ohne_aussetzer(tmp_path):
    """B hat Aussetzer, A nicht → Ton aus A; Ergebnis ohne Klicks, deckungsgleich, bytegleich; Drehung geprüft."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    a, b = _paar(inbox, ton=SPRACHE, b_ton_filter=AUSSETZER)
    ta = medien.audio_laden(a, 16_000)
    bericht = ps.synchronisieren(a, b, inbox, STEMPEL, ps.Einstellungen(cq=14, drehung_b="links"), roh_lassen=True)
    assert bericht["ok"], bericht["warnungen"]
    assert bericht["pruefung"]["groesse"]["B"] == "180x320"
    ton = bericht["ton"]
    assert ton["klicks"]["B"] >= 3 and ton["klicks"]["A"] == 0 and ton["quelle"] == "A", ton
    assert bericht["pruefung"]["ton_klicks"] == 0 and bericht["pruefung"]["ton_bytegleich"]
    _deckungsgleich(bericht)
    tx = medien.audio_laden(Path(bericht["ausgaben"]["A"]), 16_000)
    v = versatz_finden(ta, tx[16_000 * 2: 16_000 * 8], 16_000)
    assert abs(v.lag_s - 2.0) < 0.002, v
    assert a.is_file() and b.is_file()                                         # --roh-lassen: unangetastet


@braucht_ffmpeg
def test_ton_aus_b_wird_auf_die_a_zeitachse_geschoben(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    a, b = _paar(inbox, ton=SPRACHE, a_ton_filter=AUSSETZER)
    tb = medien.audio_laden(b, 16_000)
    bericht = ps.synchronisieren(a, b, inbox, STEMPEL, ps.Einstellungen(cq=14), roh_lassen=True)
    assert bericht["ok"] and bericht["ton"]["quelle"] == "B", bericht
    assert any(h.startswith("Ton aus Kamera B") and "-160.00 ms" in h for h in bericht["hinweise"])
    tx = medien.audio_laden(Path(bericht["ausgaben"]["A"]), 16_000)
    v = versatz_finden(tb, tx[16_000 * 2: 16_000 * 8], 16_000)
    assert abs((v.lag_s - 2.0) + 0.16) < 0.002, v


@braucht_ffmpeg
def test_kamera_phase_ein_bild_neben_dem_ton(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    a, b = _paar(inbox, b_bild_s=0.20, b_ton_s=0.16)
    bericht = ps.synchronisieren(a, b, tmp_path / "ziel", STEMPEL, ps.Einstellungen(cq=14), roh_lassen=True)
    assert (bericht["luecke_bilder"], bericht["quelle"], bericht["ok"]) == (5, "bild", True), bericht["warnungen"]
    assert any("Kamera-Phase" in h for h in bericht["hinweise"])
    _deckungsgleich(bericht)


@braucht_ffmpeg
def test_widerspruch_landet_im_pruefen_ordner(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    a, b = _paar(inbox, b_bild_s=0.28, b_ton_s=0.16)
    aus = ps.take_einsortieren(a, b, inbox, STEMPEL)
    bericht = ps.synchronisieren(aus["A"], aus["B"], inbox, STEMPEL, ps.Einstellungen(cq=14))
    assert not bericht["ok"] and bericht["luecke_bilder"] == 7
    ordner = inbox / f"{NAME} PRUEFEN"
    assert Path(bericht["ordner"]) == ordner and not (inbox / NAME).exists()
    assert sorted(q.name for q in ordner.iterdir()) == [f"{NAME} Cam A.mp4", f"{NAME} Cam B.mp4", "Roh"]
    _deckungsgleich(bericht)


@braucht_ffmpeg
def test_phasensprung_im_take_ist_rot(tmp_path, monkeypatch):
    import studio_werkzeuge.synchron as sy
    monkeypatch.setattr(ps, "KANTEN_MIN_DAUER_S", 12.0)
    monkeypatch.setattr(ps, "KANTEN_FENSTER_S", 5.0)
    monkeypatch.setattr(sy, "BEWEGUNG_MIN_BILDER", 100)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    a, b = _paar(inbox, b_filter="select='not(eq(n\\,165))',setpts=N/25/TB")
    bericht = ps.synchronisieren(a, b, tmp_path / "ziel", STEMPEL, probe=True)
    assert not bericht["ok"] and any("wandert" in w for w in bericht["warnungen"]), bericht


@braucht_ffmpeg
def test_stummer_ton_luecke_aus_dem_bild(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    a, b = _paar(inbox, ton="anullsrc=r=48000:cl=stereo")
    bericht = ps.synchronisieren(a, b, tmp_path / "ziel", STEMPEL, probe=True)
    assert (bericht["luecke_bilder"], bericht["quelle"], bericht["ok"]) == (4, "bild", False)
    assert any("Kein brauchbarer Ton" in w for w in bericht["warnungen"])
    assert not (tmp_path / "ziel").exists()                                    # Probe schreibt nichts


@braucht_ffmpeg
def test_kurzer_take_nach_der_bildzahl(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    master = tmp_path / "master.mkv"
    _master(master, "anoisesrc=d=15:c=pink:r=48000:a=0.3:seed=7", bilder=75)
    a, b = inbox / "cam-A-20260314-112917.mp4", inbox / "cam-B-20260314-112917.mp4"
    _ff("-i", str(master), "-t", "2.0", *ENC, str(a))
    _ff("-ss", "0.16", "-i", str(master), "-t", "1.84", *ENC, str(b))
    bericht = ps.synchronisieren(a, b, inbox, "20260314-112917", ps.Einstellungen(cq=14), roh_lassen=True)
    assert (bericht["luecke_bilder"], bericht["quelle"], bericht["ok"]) == (4, "bildzahl", True), bericht["warnungen"]
    p = bericht["pruefung"]
    assert p["bilder"]["A"] == p["bilder"]["B"] == 50 and p["ton_bytegleich"]
    _deckungsgleich(bericht)


@braucht_ffmpeg
def test_cli_paar_probe_mit_konfiguration(tmp_path, hilfe, capsys):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    _paar(inbox)
    k = tmp_path / "studio.toml"
    k.write_text(f'[pfade]\ninbox = "{inbox.as_posix()}"\n', encoding="utf-8")
    assert main(["--konfig", str(k), "paar", "--probe"]) == 0
    aus = capsys.readouterr().out
    assert "Lücke: 4 Bilder nach BILD" in aus and "Probe: nichts geschrieben." in aus
    assert sorted(q.name for q in inbox.iterdir()) == [f"cam-A-{STEMPEL}.mp4", f"cam-B-{STEMPEL}.mp4"]
