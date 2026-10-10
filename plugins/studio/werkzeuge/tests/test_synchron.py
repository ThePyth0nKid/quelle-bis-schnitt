# SPDX-License-Identifier: MIT
"""Reine Rechenfunktionen des Zwei-Kamera-Paars (übernommen aus der Vorlage, angepasst)."""
from __future__ import annotations

import numpy as np
import pytest
from studio_werkzeuge import synchron as sy
from studio_werkzeuge.fehler import KeinTon, StudioFehler, ZuKurzeUeberlappung
from studio_werkzeuge.synchron import AAC_BLOCK_S, Bewegung, Plan, Zerlegung

SICHER = dict(gipfel=0.6, neben=0.3, bilder=500)
TON7 = Zerlegung(7, 0, 0.0)


# versatz_finden

def test_versatz_finden_bekannte_lage():
    rng = np.random.default_rng(3)
    ref = rng.normal(0, 0.2, 16_000 * 20).astype(np.float32)
    muster = ref[16_000 * 7 + 1234: 16_000 * 13]
    v = sy.versatz_finden(ref, muster, 16_000)
    assert abs(v.lag_s - (7 + 1234 / 16_000)) < 1e-4 and v.konfidenz > 0.99 and v.nebenmaximum < 0.5


def test_versatz_finden_fehlerfaelle():
    with pytest.raises(KeinTon):
        sy.versatz_finden(np.zeros(16_000 * 5), np.ones(16_000 * 4), 16_000)
    with pytest.raises(ZuKurzeUeberlappung):
        sy.versatz_finden(np.ones(16_000 * 5), np.ones(100), 16_000)


# versatz_zerlegen

def test_reiner_bildversatz():
    z = sy.versatz_zerlegen(0.160, 25.0)
    assert (z.bilder, z.bloecke) == (4, 0) and abs(z.rest_s) < 1e-9


def test_aac_bloecke():
    assert (sy.versatz_zerlegen(0.160 + AAC_BLOCK_S, 25.0).bilder, sy.versatz_zerlegen(0.160 + AAC_BLOCK_S,
                                                                                         25.0).bloecke) == (4, 1)
    assert sy.versatz_zerlegen(0.160 - AAC_BLOCK_S, 25.0).bloecke == -1
    z = sy.versatz_zerlegen(0.160 + 2 * AAC_BLOCK_S, 25.0)
    assert (z.bilder, z.bloecke) == (4, 2) and abs(z.rest_s) < 1e-9


def test_30fps_und_negativ():
    z = sy.versatz_zerlegen(0.12131, 30.0)                     # 3 Bilder + 1 AAC-Block
    assert (z.bilder, z.bloecke) == (3, 1) and abs(z.rest_s) < 0.001
    assert sy.versatz_zerlegen(-0.080, 25.0).bilder == -2
    assert (sy.versatz_zerlegen(0.1612, 25.0).bilder, sy.versatz_zerlegen(0.1612, 25.0).bloecke) == (4, 0)


# luecke_entscheiden

def test_eindeutige_bewegung_richtet_aus_kamera_phase():
    e = sy.luecke_entscheiden(TON7, 0.99, 0.0, Bewegung(6.03, **SICHER))
    assert (e.bilder, e.quelle, e.rot) == (6, "bild", False) and any("Kamera-Phase" in h for h in e.hinweise)


def test_bild_und_ton_gleich():
    e = sy.luecke_entscheiden(TON7, 0.99, 0.0, Bewegung(6.86, **SICHER))
    assert (e.bilder, e.quelle, e.rot, e.hinweise) == (7, "bild", False, ())


def test_mehr_als_phase_ist_rot():
    e = sy.luecke_entscheiden(TON7, 0.99, 0.0, Bewegung(3.9, **SICHER))
    assert e.rot and e.bilder == 4 and "gleich eingestellt" in e.warnungen[0]


def test_ohne_eindeutige_bewegung_richtet_der_ton_aus():
    e = sy.luecke_entscheiden(TON7, 0.99, 0.0, Bewegung(-1.8, gipfel=0.14, neben=0.92, bilder=220))
    assert (e.bilder, e.quelle, e.rot) == (7, "ton", False) and "±1 Bild" in e.hinweise[0]


def test_zweifelhafter_ton_ohne_bestaetigung_ist_rot():
    e = sy.luecke_entscheiden(TON7, 0.1, 0.0, Bewegung(None, 0.0, 1.0, 100))
    assert e.rot and "Konfidenz" in e.warnungen[0]


def test_ohne_ton():
    e = sy.luecke_entscheiden(None, 0.0, 0.0, Bewegung(4.2, **SICHER))
    assert (e.bilder, e.quelle, e.rot) == (4, "bild", True)
    with pytest.raises(StudioFehler):
        sy.luecke_entscheiden(None, 0.0, 0.0, Bewegung(None, 0.0, 1.0, 100))


def test_kurzer_take_nach_der_bildzahl():
    e = sy.luecke_entscheiden(None, 0.0, 0.0, Bewegung(None, 0.0, 1.0, 64), bilder_ab=(72, 65))
    assert (e.bilder, e.quelle, e.rot) == (7, "bildzahl", False) and "±1 Bild" in e.hinweise[0]


def test_langer_take_nur_aus_der_bildzahl_ist_rot():
    e = sy.luecke_entscheiden(None, 0.0, 0.0, Bewegung(None, 0.0, 1.0, 500), bilder_ab=(506, 500))
    assert (e.bilder, e.quelle, e.rot) == (6, "bildzahl", True) and "Bildzahl" in e.warnungen[0]


@pytest.mark.parametrize("bilder_ab", [(1500, 100), (80, 40), (60, 66)])
def test_unplausible_bildzahl_ist_rot(bilder_ab):
    e = sy.luecke_entscheiden(None, 0.0, 0.0, Bewegung(None, 0.0, 1.0, 40), bilder_ab=bilder_ab)
    assert (e.quelle, e.rot) == ("bildzahl", True) and "unplausible" in e.warnungen[0]


# plan_bauen, bild_lage, Kleinteile

def test_plan():
    assert sy.plan_bauen(4, 592, 588) == Plan("A", 4, 592, 0)
    assert sy.plan_bauen(4, 593, 588) == Plan("A", 4, 593, 1)
    assert sy.plan_bauen(-3, 500, 510) == Plan("B", -3, 500, 0)
    assert sy.plan_bauen(0, 300, 300) == Plan("A", 0, 300, 0)
    assert sy.plan_bauen(4, 300, 600) == Plan("A", 4, 300, 0)


@pytest.mark.parametrize("k,a,b", [(4, 600, 300), (-400, 300, 300), (4, 0, 10)])
def test_plan_passt_nicht(k, a, b):
    with pytest.raises(StudioFehler):
        sy.plan_bauen(k, a, b)


def test_bild_lage_findet_vier_bilder_eindeutig():
    basis = np.random.default_rng(1).gamma(2.0, 1.0, 3000)
    b = sy.bild_lage(basis[:2000], basis[4:2004], -10, 10)
    assert abs(b.lage - 4) < 0.2 and b.gipfel > 0.5 and b.neben < 0.5 and b.aussagekraeftig


def test_periodische_bewegung_ist_mehrdeutig():
    muster = np.tile([5.0, 5, 5, 5, 5, 0], 400) + np.random.default_rng(2).normal(0, 0.1, 2400)
    b = sy.bild_lage(muster[:2000], muster[4:2004], -12, 12)
    assert b.neben > sy.BEWEGUNG_NEBEN_MAX and not b.aussagekraeftig


def test_bild_lage_ohne_bewegung_und_standbild():
    assert sy.bild_lage(np.zeros(500), np.zeros(500), -5, 5).lage is None
    assert sy.standbild_anteil(np.zeros(100)) == 1.0 and sy.standbild_anteil(np.full(100, 2.0)) == 0.0


def test_ton_wahl():
    assert sy.ton_wahl({"A": 0, "B": 8}, fest="B") == "A"
    assert sy.ton_wahl({"A": 0, "B": 0}, fest="B") == "B"
    assert sy.ton_wahl({"A": 3, "B": 1}, fest="A") == "B"
    assert sy.ton_wahl({"A": 1, "B": 1}, fest="A") == "A"
