---
name: dreh-setup
description: Richtet den Aufnahmeweg für Sprechvideos ein und prüft ihn vor dem Dreh – Kameras per HDMI-Capture, Mikrofon über ein Audio-Interface mit 48 kHz, Rauschunterdrückung, OBS mit Source Record für getrennte Kameradateien, Speicherort, Bitrate-Modi und Probeaufnahme mit Klick-Messung. Nutze diesen Skill bei „Dreh vorbereiten“, „Aufnahme einrichten“, „OBS einrichten“, „Source Record“, „Bitrate umstellen“, „Probeaufnahme“, „warum knackt die Aufnahme“, „neue Kamera“, „neues Mikro“ und bevor ein langer Take aufgenommen wird.
---

# Dreh-Setup: der Aufnahmeweg

Ziel: Jede Kamera landet als eigene Datei auf der Platte, alle mit derselben Bildrate und mit sauberem Ton. Was hier
nicht stimmt, lässt sich im Schnitt nicht mehr reparieren.

Das konkrete Setup ist **ein Beispiel**. Die ausführliche Anleitung mit dem Beispiel-Setup und der Liste der Werte, die
du für dein eigenes Setup eintragen solltest, steht in `docs/so-filme-ich.md` im Repo.

## 1. Der Weg im Überblick

```
Kamera A ─HDMI─▶ Capture A ─┐
Kamera B ─HDMI─▶ Capture B ─┼─▶ OBS ─▶ Source Record (je Kamera eine Datei) ─▶ <inbox> (interne SSD)
Mikrofon ─▶ Audio-Interface (48 kHz) ─▶ Rauschunterdrückung ─┘        └─▶ Programm-Aufnahme (Gegenprobe)
```

- **Source Record** ist ein freies OBS-Plugin ([exeldro/obs-source-record](https://github.com/exeldro/obs-source-record),
  GPL-2.0): Es hängt als Filter an einer Quelle und schreibt sie als eigene Datei.
- Die **Programm-Aufnahme** von OBS läuft mit. Sie ist die Gegenprobe, wenn eine Kameradatei Fehler hat.

## 2. Regeln für OBS

1. **Source-Record-Filter in der Oberfläche anlegen**, Aufnahme-Modus „Recording“ (im Plugin-Code `record_mode = 3`,
   [Quelle](https://github.com/exeldro/obs-source-record/blob/master/source-record.c)). Wert 2 heißt „Streaming“: Dann
   schreibt der Filter bei einer Aufnahme nichts.
2. **Encoder oder Bitrate nur durch Löschen und Neuanlegen des Filters ändern.** Geänderte Einstellungen laden den
   Encoder nicht neu. `studio obs-modus <modus>` macht genau das und sichert die alten Einstellungen vorher als JSON.
3. **Keine eigenen Audiogeräte an den Kameraquellen.** Der Ton kommt aus einer Quelle (Mikrofon); ein zweites
   Audiogerät an einer Kameraquelle erzeugt Nachlauf und Knacken in der Kameradatei.
4. **Eine Bildrate überall:** Kameras, Capture-Geräte und OBS-Profil gleich (z. B. alle 25 fps). Sonst liegen die
   Kameras nach dem Ausrichten Bilder daneben, und einzelne Bilder doppeln sich.
5. **Aufnahme auf eine interne SSD**, nicht auf ein USB-Laufwerk mit exFAT. Erst danach ins Archiv verschieben.
6. **obs-websocket:** Passwort nur aus einer Umgebungsvariable oder der Konfiguration lesen. Das Python-Paket
   `obsws-python` schreibt beim Verbinden auf Log-Stufe INFO das Passwort ins Protokoll: Logger auf WARNING stellen
   (das Werkzeug `studio` tut das).
7. **Nichts per WebSocket ändern, während OBS aufnimmt.** `studio obs-modus` und `studio prompter einspielen` brechen
   dann ab.

## 3. Vor jedem Dreh (Checkliste)

- [ ] Beide Kameras liefern Bild (kein „No Signal“-Standbild des Capture-Geräts), Akku oder Netzteil, Hitze-Abschaltung aus.
- [ ] Bildrate von Kamera, Capture und OBS gleich.
- [ ] Mikrofonpegel: Spitzen deutlich unter 0 dBFS, Sprache gut über dem Rauschen.
- [ ] Audio-Interface und OBS auf derselben Abtastrate (48 kHz). Nach einer Umstellung prüfen, ob OBS noch auf das
      richtige Gerät zeigt: manche Systeme legen dabei ein neues Gerät an.
- [ ] Freier Platz auf dem Ziellaufwerk für den längsten Take (Bitrate × Dauer × Kameras, siehe §4).
- [ ] **Probeaufnahme** (Faustregel: etwa eine halbe Minute) mit Sprechen und Pausen, dann `studio klick-check <dateien>` auf beide Kameradateien
      und die Programm-Aufnahme. Rot = nicht drehen, erst die Prüfreihenfolge in Skill `ton-mastering`.
- [ ] Prompter geladen (Skill `prompter`), Fußpedal oder Fernbedienung geprüft.

## 4. Bitrate-Modi

Die Modi stehen in `studio.toml` unter `[obs_modus.modi.<name>]` und werden mit `studio obs-modus <name>` gesetzt;
`studio obs-modus status` zeigt den aktuellen Stand, `--probe` nur die geplante Änderung. Die Vorlage bringt `lang` und
`max` mit, weitere legst du selbst an. Speicherbedarf: Bitrate in Mbit/s × 3600 / 8 = MB je Stunde und Kamera, z. B.
20 Mbit/s ≈ 9 GB je Stunde. Beispielwerte aus einem Setup, nicht gemessen:

| Modus | Einstellung | Wofür |
|---|---|---|
| lang | VBR 20 Mbit/s, Spitze 30 | lange Videos, Platz sparen |
| hoch | VBR 50 Mbit/s, Spitze 70 | Takes, aus denen später stark vergrößert wird |
| max | CQP 18 | nur kurze Spezialaufnahmen (sehr große Dateien) |

## 5. Fallen

### F1 · Filter schreibt nichts
**Symptom:** Nach der Aufnahme liegt keine Kameradatei im Ordner.
**Ursache:** Aufnahme-Modus des Source-Record-Filters steht auf „Streaming“, oft nach Anlegen per WebSocket.
**Gegenmittel:** Filter in der Oberfläche löschen und neu anlegen, Modus „Recording“; im OBS-Protokoll beim
Aufnahmestart nach einem Encoder-Eintrag für den Filter suchen.

### F2 · Neue Bitrate wirkt nicht
**Symptom:** Im Filter steht die neue Bitrate, die Datei hat die alte.
**Ursache:** Geänderte Filtereinstellungen laden den Encoder nicht neu.
**Gegenmittel:** `studio obs-modus` (löscht und legt neu an, an derselben Stelle der Filterliste).

### F3 · Knacken nur in einer Kameradatei
**Symptom:** Kamera B knackt, Kamera A und Programm-Aufnahme nicht.
**Ursache:** häufig ein eigenes Audiogerät an der Kameraquelle oder ein langsames Ziellaufwerk.
**Gegenmittel:** Prüfreihenfolge in Skill `ton-mastering`; bis zur Klärung den Ton der sauberen Datei nehmen und das dem
Menschen melden, nicht still umschwenken.

### F4 · Stumme Takes nach Umstellung der Abtastrate
**Symptom:** Nach dem Umstellen des Interfaces auf 48 kHz sind die nächsten Takes stumm.
**Ursache:** Das System hat ein neues Audiogerät angelegt, OBS zeigt noch auf das alte.
**Gegenmittel:** Nach jeder Umstellung das Mikrofon in OBS neu wählen und eine Probeaufnahme machen.

### F5 · Kamera nimmt nur ein Standbild auf
**Symptom:** Eine Kameradatei zeigt die ganze Zeit dasselbe Bild oder „No Signal“.
**Ursache:** Kamera aus, im Ruhemodus oder HDMI-Ausgabe abgeschaltet.
**Gegenmittel:** Vor jedem Take Live-Bild beider Kameras ansehen; `studio waechter` prüft das beim Aufnahmestart.
