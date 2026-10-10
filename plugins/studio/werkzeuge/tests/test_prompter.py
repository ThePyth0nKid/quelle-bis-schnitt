# SPDX-License-Identifier: MIT
"""Prompter: Satztrennung und Einspielen in einen Camera-Hub-Datenordner im Testordner (Prozess als Attrappe)."""
from __future__ import annotations

import json
import os

import pytest
from studio_werkzeuge import prompter as pr
from studio_werkzeuge.cli import main
from studio_werkzeuge.fehler import NurWindows, StudioFehler

# Sätze

def test_saetze_ordnungszahl_und_kuerzel():
    assert pr.saetze("Am 3. Oktober war es so. Das ist z. B. gut! Wirklich?") == [
        "Am 3. Oktober war es so.", "Das ist z. B. gut!", "Wirklich?"]
    assert pr.saetze("Er sagte: „Nein.“ Dann ging er.") == ["Er sagte: „Nein.“", "Dann ging er."]


def test_satzweise_marken_tragen_weiter_und_regie_bleibt():
    text = "[A] Erster Satz. Zweiter Satz.\n\n(Pause)\n\n[B] Dritter. [A] Vierter."
    assert pr.satzweise(text) == ["[A] Erster Satz.", "[A] Zweiter Satz.", "(Pause)", "[B] Dritter.", "[A] Vierter."]
    assert pr.satzweise("[NAH] Eins. Zwei.", marken=("NAH",)) == ["[NAH] Eins.", "[NAH] Zwei."]
    assert pr.satzweise("[NAH] Eins.") == ["[NAH] Eins."]                     # unbekannte Marke bleibt Text


def test_schreiben_ohne_ueberschreiben(tmp_path):
    ziel = tmp_path / "p.md"
    assert pr.schreiben_ohne_ueberschreiben(ziel, "a\n") == "geschrieben"
    assert pr.schreiben_ohne_ueberschreiben(ziel, "a\n") == "schon da und gleich"
    with pytest.raises(StudioFehler, match="Nie überschreiben"):
        pr.schreiben_ohne_ueberschreiben(ziel, "b\n")


def test_cli_saetze(tmp_path, capsys):
    skript = tmp_path / "s.md"
    skript.write_text("[A] Die Freie Stadt Musterhafen misst ihr Netz. Jede Sekunde.\n", encoding="utf-8")
    assert main(["prompter", "saetze", str(skript), "--ausgabe", str(tmp_path / "p.md")]) == 0
    assert (tmp_path / "p.md").read_text(encoding="utf-8") == "[A] Die Freie Stadt Musterhafen misst ihr Netz.\n\n" \
                                                               "[A] Jede Sekunde.\n"


# Einspielen

class FakeHub:
    def __init__(self, geht_weg: bool = True) -> None:
        self.geht_weg, self.beendet, self.gestartet = geht_weg, 0, 0

    def laeuft(self) -> bool:
        return True

    def beenden(self):
        self.beendet += 1
        return (True, "hart beendet") if self.geht_weg else (False, "läuft weiter")

    def starten(self) -> bool:
        self.gestartet += 1
        return True


def _hub_ordner(tmp_path):
    daten = tmp_path / "CameraHub"
    (daten / "Texts").mkdir(parents=True)
    (daten / "AppSettings.json").write_text(json.dumps({pr.LIBRARY_KEY: [], "andere.einstellung": 7}),
                                            encoding="utf-8")
    return daten


def _projekt(tmp_path, namen=("MUSTER M01 · Wie ein Stromnetz atmet", "MUSTER M02 · Was ein Zähler weiß")):
    zeilen = ['praefix = "MUSTER "']
    for i, name in enumerate(namen):
        (tmp_path / f"t{i}.md").write_text(f"[A] Satz {i}.\n\n[B] Noch ein Satz.\n", encoding="utf-8")
        zeilen += ["[[skript]]", f'name = "{name}"', f'datei = "t{i}.md"']
    (tmp_path / "prompter.toml").write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    return pr.projekt_laden(tmp_path / "prompter.toml")


def _stand(daten):
    texte = {}
    for f in (daten / "Texts").glob("*.json"):
        j = json.loads(f.read_text(encoding="utf-8"))
        texte[j["friendlyName"]] = (j.get("GUID"), j["index"], len(j["chapters"]), f.stem)
    return texte, json.loads((daten / "AppSettings.json").read_text(encoding="utf-8"))


def test_erstlauf_und_idempotenz(tmp_path):
    daten, hub = _hub_ordner(tmp_path), FakeHub()
    pr.einspielen(_projekt(tmp_path), daten, hub)
    texte, einst = _stand(daten)
    assert len(texte) == 2 and {t[2] for t in texte.values()} == {2}
    assert sorted(einst[pr.LIBRARY_KEY]) == sorted(t[0] for t in texte.values())
    assert all(t[0] == t[3] for t in texte.values())                          # Dateiname = GUID
    assert einst["andere.einstellung"] == 7 and hub.beendet == 1 and hub.gestartet == 1
    assert len(list(daten.glob("Sicherung-*"))) == 1
    pr.einspielen(_projekt(tmp_path), daten, hub)
    texte2, einst2 = _stand(daten)
    assert texte2 == texte and einst2[pr.LIBRARY_KEY] == einst[pr.LIBRARY_KEY]   # zweiter Lauf: nichts bewegt sich


def test_guid_aus_dateinamen_geheilt_fremdes_bleibt_veraltetes_geht(tmp_path):
    daten, hub = _hub_ordner(tmp_path), FakeHub()
    pr.einspielen(_projekt(tmp_path), daten, hub)
    texte, _ = _stand(daten)
    guid = texte["MUSTER M01 · Wie ein Stromnetz atmet"][0]
    datei = daten / "Texts" / f"{guid}.json"
    j = json.loads(datei.read_text(encoding="utf-8"))
    del j["GUID"]
    datei.write_text(json.dumps(j), encoding="utf-8")
    fremd = "AAAAAAAA-0000-0000-0000-00000000FFFF"
    (daten / "Texts" / f"{fremd}.json").write_text(json.dumps(
        {"GUID": fremd, "chapters": ["x"], "friendlyName": "Mein Handtext", "index": 900}), encoding="utf-8")
    pr.einspielen(_projekt(tmp_path, ("MUSTER M01 · Wie ein Stromnetz atmet",)), daten, hub)
    texte, einst = _stand(daten)
    assert texte["MUSTER M01 · Wie ein Stromnetz atmet"][0] == guid           # GUID aus dem Dateinamen
    assert "Mein Handtext" in texte and fremd in einst[pr.LIBRARY_KEY]          # fremd: unangetastet, eingetragen
    assert "MUSTER M02 · Was ein Zähler weiß" not in texte                     # veraltet eigen: entfernt


def test_nichts_loeschen_und_probe(tmp_path):
    daten, hub = _hub_ordner(tmp_path), FakeHub()
    pr.einspielen(_projekt(tmp_path), daten, hub)
    nur_einer = _projekt(tmp_path, ("MUSTER M01 · Wie ein Stromnetz atmet",))
    zeilen = pr.einspielen(nur_einer, daten, None, probe=True)
    assert "1 veraltete eigene Einträge würden entfernt" in zeilen[-1]
    pr.einspielen(nur_einer, daten, hub, nichts_loeschen=True)
    assert len(_stand(daten)[0]) == 2


def test_hub_geht_nicht_weg_dann_nichts_geschrieben(tmp_path):
    daten = _hub_ordner(tmp_path)
    with pytest.raises(StudioFehler, match="läuft weiter"):
        pr.einspielen(_projekt(tmp_path), daten, FakeHub(geht_weg=False))
    assert list((daten / "Texts").glob("*.json")) == []


def test_projektfehler(tmp_path):
    (tmp_path / "prompter.toml").write_text('praefix = "X "\n[[skript]]\nname = "Y 1"\ndatei = "fehlt.md"\n'
                                            '[[skript]]\nname = "Z"\n', encoding="utf-8")
    p = pr.projekt_laden(tmp_path / "prompter.toml")
    assert any("fehlt" in f for f in p.fehler) and any("ohne name oder datei" in f for f in p.fehler)
    with pytest.raises(StudioFehler, match="prompter.toml hat Fehler"):
        pr.einspielen(p, _hub_ordner(tmp_path), FakeHub())


@pytest.mark.skipif(os.name == "nt", reason="prüft das Verhalten außerhalb von Windows")
def test_camerahub_nur_unter_windows():
    with pytest.raises(NurWindows):
        pr.CameraHub("Camera Hub.exe", None)


def test_cli_einspielen_probe(tmp_path, capsys):
    daten = _hub_ordner(tmp_path)
    _projekt(tmp_path)
    k = tmp_path / "studio.toml"
    k.write_text(f'[prompter]\ndatenordner = "{daten.as_posix()}"\n', encoding="utf-8")
    assert main(["--konfig", str(k), "prompter", "einspielen", str(tmp_path / "prompter.toml"), "--probe"]) == 0
    assert "[         neu] MUSTER M01" in capsys.readouterr().out and list((daten / "Texts").iterdir()) == []
