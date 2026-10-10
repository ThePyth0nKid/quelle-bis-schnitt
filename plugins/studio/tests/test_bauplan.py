# SPDX-License-Identifier: MIT
"""Tests für bauplan.py: Bildrechnung, Prüfung (Fehler gegen Hinweise), Lage aus einem Fenster, Statistik."""
from __future__ import annotations

import json

import bauplan as bp
import pytest


def _plan(**ueber):
    plan = {
        "projekt": "Probe", "name": "probe", "format": {"breite": 1920, "hoehe": 1080, "fps": 25},
        "spuren": [
            {"art": "video", "name": "Kamera", "lueckenlos": True, "items": [
                {"id": "k1", "quelle": "/medien/a.mp4", "start": 0.0, "dauer": 1.0, "rolle": "A weit"},
                {"id": "k2", "quelle": "/medien/b.mp4", "start": 1.0, "dauer": 2.0, "rolle": "B weit"},
            ]},
            {"art": "audio", "name": "Stimme", "items": [
                {"id": "t1", "quelle": "/medien/stimme.wav", "start": 0.0, "dauer": 3.0, "paar": "k1"},
            ]},
        ],
        "marker": [{"t": 1.0, "farbe": "Blue", "name": "S1"}],
    }
    plan.update(ueber)
    return plan


def test_bild_rundet_kaufmaennisch():
    assert bp.bild(0.02, 25) == 1          # 0,5 Bild → aufwärts
    assert bp.bild(0.0199, 25) == 0
    assert bp.bild(1.0, 25) == 25


def test_kanten_summieren_keinen_rundungsfehler():
    # zehn Stücke à 0,13 s lückenlos: jede Kante wird einzeln gerundet, die Summe bleibt exakt
    stuecke = [{"start": round(i * 0.13, 6), "dauer": 0.13} for i in range(10)]
    kanten = [bp.kanten(s, 25) for s in stuecke]
    assert all(a[1] == b[0] for a, b in zip(kanten, kanten[1:], strict=False))
    assert kanten[-1][1] == bp.bild(1.3, 25)


def test_quellbilder_mit_anderer_bildrate():
    # 1 s in einer 25-fps-Timeline aus einer 30-fps-Quelle: 30 Quellbilder, endFrame exklusiv
    assert bp.quellbilder({"start": 0.0, "dauer": 1.0, "quell_ab": 2.0}, 25, 30) == (60, 90)


def test_lage_aus_fenster_mitte_bewegt_nichts():
    lage = bp.lage_aus_fenster((3840, 2160), (1920, 1080), (0, 0, 3840, 2160))
    assert lage == {"zoom": 1.0, "pan": 0.0, "tilt": 0.0}


def test_lage_aus_fenster_halbes_bild_links_oben():
    lage = bp.lage_aus_fenster((3840, 2160), (1920, 1080), (0, 0, 1920, 1080))
    assert lage["zoom"] == 2.0
    assert lage["pan"] == 960.0     # Bild nach rechts schieben, damit die linke Hälfte in der Mitte steht
    assert lage["tilt"] == -540.0   # nach unten, damit die obere Hälfte sichtbar wird


def test_lage_aus_fenster_ohne_flaeche():
    with pytest.raises(bp.BauplanFehler):
        bp.lage_aus_fenster((3840, 2160), (1920, 1080), (0, 0, 0, 10))


def test_sauberer_plan_ohne_dateien():
    assert bp.pruefen(_plan(), dateien=False) == []


def test_fehler_werden_gesammelt():
    plan = _plan()
    plan["spuren"][0]["items"][1]["start"] = 0.5            # Überlappung
    plan["spuren"][0]["items"].append({"id": "k3", "quelle": "/medien/bild.png", "start": 3.0, "dauer": 1.0})
    plan["spuren"][1]["items"][0]["paar"] = "gibt-es-nicht"
    plan["marker"][0]["farbe"] = "Lila"
    with pytest.raises(bp.BauplanFehler) as fehler:
        bp.pruefen(plan, dateien=False)
    text = str(fehler.value)
    assert "überlappt" in text
    assert "Standbild" in text
    assert "paar" in text
    assert "Farbe Lila" in text


def test_luecke_in_lueckenloser_spur():
    plan = _plan()
    plan["spuren"][0]["items"][1]["start"] = 1.2
    with pytest.raises(bp.BauplanFehler, match="Lücke von 5 Bildern"):
        bp.pruefen(plan, dateien=False)


def test_fehlende_quelle_auf_der_platte(tmp_path):
    plan = _plan()
    for spur in plan["spuren"]:
        for it in spur["items"]:
            it["quelle"] = str(tmp_path / "fehlt.mp4")
    with pytest.raises(bp.BauplanFehler, match="Quelle fehlt"):
        bp.pruefen(plan, dateien=True)


def test_einblendung_ohne_handlung_ist_nur_ein_hinweis():
    plan = _plan()
    plan["spuren"].append({"art": "video", "name": "Einsatz", "items": [
        {"id": "e1", "quelle": "/medien/karte.mov", "start": 0.5, "dauer": 1.0, "rolle": "Karte Zahl"}]})
    hinweise = bp.pruefen(plan, dateien=False)
    assert len(hinweise) == 1 and "e1" in hinweise[0]


def test_lut_ordner_aus_umgebung(tmp_path, monkeypatch):
    monkeypatch.setenv("RESOLVE_LUT_ORDNER", str(tmp_path))
    lut = tmp_path / "look.cube"
    lut.write_text("LUT_3D_SIZE 2", encoding="utf-8")
    fremd = tmp_path.parent / "fremd.cube"
    fremd.write_text("LUT_3D_SIZE 2", encoding="utf-8")
    quelle = tmp_path / "a.mp4"
    quelle.write_bytes(b"x")
    plan = {"projekt": "P", "name": "p", "format": {"breite": 1920, "hoehe": 1080, "fps": 25}, "spuren": [
        {"art": "video", "name": "K", "items": [{"id": "a", "quelle": str(quelle), "start": 0, "dauer": 1,
                                                 "lut": str(lut)}]}]}
    assert bp.pruefen(plan) == []
    plan["spuren"][0]["items"][0]["lut"] = str(fremd)
    with pytest.raises(bp.BauplanFehler, match="LUT-Ordner"):
        bp.pruefen(plan)


def test_statistik_wechsel_je_minute():
    st = bp.statistik(_plan(), "Kamera")
    assert st["einstellungen"] == 2
    assert st["dauer_s"] == 3.0
    assert st["wechsel_je_minute"] == 20.0
    assert st["laengste_id"] == "k2"
    assert bp.statistik(_plan(), "gibt-es-nicht") == {}


def test_dauer_bilder():
    assert bp.dauer_bilder(_plan()) == 75


def test_main_exitcodes(tmp_path, capsys):
    gut = tmp_path / "gut.json"
    gut.write_text(json.dumps(_plan()), encoding="utf-8")
    assert bp.main(["pruefen", str(gut), "--ohne-dateien"]) == 0
    schlecht = _plan()
    del schlecht["format"]
    datei = tmp_path / "schlecht.json"
    datei.write_text(json.dumps(schlecht), encoding="utf-8")
    assert bp.main(["pruefen", str(datei), "--ohne-dateien"]) == 1
    assert bp.main(["pruefen", str(tmp_path / "fehlt.json")]) == 2
    assert bp.main(["statistik", str(gut), "--spur", "Kamera"]) == 0
    assert '"einstellungen": 2' in capsys.readouterr().out
