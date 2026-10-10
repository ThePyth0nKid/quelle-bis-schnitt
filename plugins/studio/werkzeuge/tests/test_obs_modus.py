# SPDX-License-Identifier: MIT
"""`studio obs-modus` mit einer OBS-Attrappe: sichern, umschalten durch Neuanlegen, Abbruch bei Aufnahme."""
from __future__ import annotations

import json

import pytest
from studio_werkzeuge import obs_modus as om
from studio_werkzeuge.fehler import KonfigFehler, StudioFehler

MODI = {"lang": {"rate_control": "VBR", "bitrate": 20000, "max_bitrate": 30000},
        "max": {"rate_control": "CQP", "cqp": 18}}
FILTER = [("Kamera vorn", "Aufnahme A"), ("Kamera seite", "Aufnahme B")]


class FakeObs:
    """Hält Filter je Quelle als Liste; kennt die Anfragen, die das Werkzeug stellt."""

    def __init__(self, aufnahme: bool = False) -> None:
        self.aufnahme = aufnahme
        self.anfragen: list[str] = []
        einst = {"rate_control": "CQP", "cqp": 18, "record_mode": 3, "path": "<inbox>", "encoder": "x264"}
        self.filter = {q: [{"name": "Farbe", "kind": "color_filter", "einst": {}, "aktiv": True},
                           {"name": n, "kind": "source_record_filter", "einst": dict(einst),
                            "aktiv": q == "Kamera vorn"}]
                       for q, n in FILTER}

    def _suche(self, quelle, name):
        return next(i for i, f in enumerate(self.filter[quelle]) if f["name"] == name)

    def send(self, art, d=None, raw=False):
        self.anfragen.append(art)
        if art == "GetRecordStatus":
            return {"outputActive": self.aufnahme}
        q, n = (d or {}).get("sourceName"), (d or {}).get("filterName")
        if art == "GetSourceFilter":
            i = self._suche(q, n)
            f = self.filter[q][i]
            return {"filterKind": f["kind"], "filterIndex": i, "filterEnabled": f["aktiv"],
                    "filterSettings": dict(f["einst"])}
        if art == "RemoveSourceFilter":
            self.filter[q].pop(self._suche(q, n))
        elif art == "CreateSourceFilter":
            self.filter[q].append({"name": n, "kind": d["filterKind"], "einst": dict(d["filterSettings"]),
                                   "aktiv": True})
        elif art == "SetSourceFilterIndex":
            f = self.filter[q].pop(self._suche(q, n))
            self.filter[q].insert(d["filterIndex"], f)
        elif art == "SetSourceFilterEnabled":
            self.filter[q][self._suche(q, n)]["aktiv"] = d["filterEnabled"]
        return {}


def test_neue_einstellungen_behalten_den_rest():
    alt = {"rate_control": "CQP", "cqp": 18, "record_mode": 3, "path": "x"}
    assert om.neue_einstellungen(alt, MODI["lang"], MODI) == {"record_mode": 3, "path": "x", "rate_control": "VBR",
                                                              "bitrate": 20000, "max_bitrate": 30000}


def test_umschalten_sichert_und_legt_an_derselben_stelle_neu_an(tmp_path):
    obs = FakeObs()
    zeilen = om.umschalten(obs, FILTER, "lang", MODI, tmp_path / "sicherung")
    sicherung = json.loads(next((tmp_path / "sicherung").glob("obs-filter-*.json")).read_text(encoding="utf-8"))
    assert [s["einstellungen"]["rate_control"] for s in sicherung] == ["CQP", "CQP"]     # Vorher-Zustand gesichert
    for quelle, name in FILTER:
        f = obs.filter[quelle][1]
        assert f["name"] == name and f["einst"]["bitrate"] == 20000 and "cqp" not in f["einst"]
        assert f["einst"]["record_mode"] == 3                                 # übrige Einstellungen bleiben
    assert obs.filter["Kamera seite"][1]["aktiv"] is False                   # war aus, bleibt aus
    assert "RemoveSourceFilter" in obs.anfragen and "SetSourceFilterSettings" not in obs.anfragen
    assert not any("! " in z for z in zeilen)


def test_probe_und_status_veraendern_nichts(tmp_path):
    obs = FakeObs(aufnahme=True)
    zeilen = om.umschalten(obs, FILTER, "max", MODI, None, probe=True)
    assert zeilen[0].startswith("OBS nimmt gerade auf") and all("Probe" in z for z in zeilen[1:])
    assert om.umschalten(obs, FILTER, "status", MODI, None)[0].startswith("Kamera vorn: CQP 18")
    assert not {"RemoveSourceFilter", "CreateSourceFilter"} & set(obs.anfragen)


def test_abbruch_bei_aufnahme_und_ohne_sicherung(tmp_path):
    with pytest.raises(StudioFehler, match="nimmt gerade auf"):
        om.umschalten(FakeObs(aufnahme=True), FILTER, "lang", MODI, tmp_path)
    with pytest.raises(KonfigFehler, match="sicherung"):
        om.umschalten(FakeObs(), FILTER, "lang", MODI, None)
    with pytest.raises(StudioFehler, match="unbekannt"):
        om.umschalten(FakeObs(), FILTER, "turbo", MODI, tmp_path)


def test_modi_aus_konfiguration(tmp_path, hilfe):
    k = hilfe.konfig_aus(tmp_path, '[obs_modus.modi.lang]\nbitrate = 20000\n[kameras]\n'
                                   'quelle_a = "a"\nfilter_a = "fa"\nquelle_b = "b"\nfilter_b = "fb"\n')
    assert om.modi(k) == {"lang": {"bitrate": 20000}} and om.filterliste(k) == [("a", "fa"), ("b", "fb")]
    with pytest.raises(KonfigFehler):
        om.modi(hilfe.konfig_aus(tmp_path, ""))
