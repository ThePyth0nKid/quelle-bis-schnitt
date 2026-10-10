# SPDX-License-Identifier: MIT
"""`studio inbox-ordnen`: Paarbildung, Probe, Lauf mit Protokoll und Rücklauf (übernommen und angepasst)."""
from __future__ import annotations

from studio_werkzeuge import inbox as io_
from studio_werkzeuge.cli import main


def test_plan_ordnen_paart_a_und_b_und_uebernimmt_den_stempel_von_a():
    zuordnung, fremd = io_.plan_ordnen(["cam-A-20260314-101703.mp4", "cam-B-20260314-101704.mp4",
                                        "cam-A-20260314-110828.mp4", "cam-B-20260314-110828.mp4",
                                        "cam-B-20260314-120000.mp4", "_geordnet-x.tsv"])
    assert zuordnung["cam-B-20260314-101704.mp4"] == "20260314-101703"
    assert zuordnung["cam-B-20260314-110828.mp4"] == "20260314-110828"
    assert zuordnung["cam-B-20260314-120000.mp4"] == "20260314-120000"       # B ohne A: eigener Ordner
    assert fremd == ["_geordnet-x.tsv"]


def test_zielordner_nutzt_vorhandenen_pruefen_ordner(tmp_path):
    assert io_.zielordner("20260314-103051", tmp_path) == tmp_path / "2026-03-14 10-30-51" / "Roh"
    (tmp_path / "2026-03-14 10-30-51 PRUEFEN").mkdir()
    assert io_.zielordner("20260314-103051", tmp_path) == tmp_path / "2026-03-14 10-30-51 PRUEFEN" / "Roh"


def test_probe_lauf_und_ruecklauf(tmp_path, capsys):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for n in ("cam-A-20260314-101703.mp4", "cam-B-20260314-101704.mp4", "notiz.txt"):
        (inbox / n).write_bytes(b"x")
    args = ["inbox-ordnen", str(inbox), "--min-alter", "0"]
    assert main([*args, "--probe"]) == 0
    assert "Probe: nichts verschoben." in capsys.readouterr().out and (inbox / "cam-A-20260314-101703.mp4").is_file()
    assert main(args) == 0
    roh = inbox / "2026-03-14 10-17-03" / "Roh"
    assert sorted(p.name for p in roh.iterdir()) == ["cam-A-20260314-101703.mp4", "cam-B-20260314-101704.mp4"]
    protokoll = next(inbox.glob("_geordnet-*.tsv"))
    assert main(["inbox-ordnen", "--zurueck", str(protokoll)]) == 0
    assert (inbox / "cam-B-20260314-101704.mp4").is_file() and not (inbox / "2026-03-14 10-17-03").exists()


def test_zu_junge_dateien_bleiben_liegen(tmp_path, capsys):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "cam-A-20260314-101703.mp4").write_bytes(b"x")
    assert main(["inbox-ordnen", str(inbox)]) == 0                           # Voreinstellung: 1 h Mindestalter
    assert "1 zu jung" in capsys.readouterr().out and (inbox / "cam-A-20260314-101703.mp4").is_file()


def test_ruecklauf_uebersteht_eine_fehlende_datei(tmp_path, capsys):
    inbox = tmp_path / "inbox"
    take = inbox / "2026-03-14 10-30-51"
    take.mkdir(parents=True)
    (take / "cam-A-20260314-103051.mp4").write_bytes(b"a")
    tsv = inbox / "_geordnet.tsv"
    tsv.write_text(f"{inbox / 'cam-A-20260314-103051.mp4'}\t{take / 'cam-A-20260314-103051.mp4'}\n"
                   f"{inbox / 'cam-B-20260314-103051.mp4'}\t{take / 'cam-B-20260314-103051.mp4'}\n", encoding="utf-8")
    assert main(["inbox-ordnen", "--zurueck", str(tsv)]) == 1
    aus = capsys.readouterr().out
    assert "1/2 Dateien zurückgelegt" in aus and "nicht zurückgelegt" in aus and not take.exists()
