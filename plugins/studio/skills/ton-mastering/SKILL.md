---
name: ton-mastering
description: Sorgt dafür, dass der Ton eines Sprechvideos brauchbar ist, bevor geschnitten wird, und dass er bei der Abgabe auf Ziel liegt – Klicks messen (studio klick-check), Prüfreihenfolge bei Knacken, Schnittkanten am Sprachkern, Hörprobe durch den Menschen, Mastern auf −14 LUFS und höchstens −1,5 dBTP mit Nachmessung (studio mastern). Nutze diesen Skill bei „Ton prüfen“, „es knackt“, „Klicks“, „Lautheit“, „LUFS“, „mastern“, „Stimme zu leise“, „Pegel“ und vor dem ersten Schnittschritt.
---

# Ton: erst messen, dann schneiden, zuletzt mastern

Ein Bild lässt sich im Schnitt retten, ein kaputter Ton nicht. Deshalb läuft die Tonprüfung **vor** dem ersten
Schnittschritt, und abgenommen wird der Ton von einem Menschen mit den Ohren, nicht von einem Zähler.

## 1. Klicks messen, bevor geschnitten wird

```
studio klick-check <kamera-a> <kamera-b> <programm-aufnahme> [--json]
```

- Gemessen wird **jede** Tonquelle des Takes, nicht nur die, die man schneiden will.
- Ein Klick ist ein Sprung von Abtastwert zu Abtastwert, der den lokalen Pegel um ein Vielfaches übersteigt. Treffer
  dicht hintereinander zählen als einer.
- Ampel je Minute: unter 5 grün, 5–15 gelb, über 15 rot. Die Schwellen sind einstellbar; woher sie kommen, steht in
  `docs/messungen/studio-klicks.md` (eigene Messung an wenigen Takes, also ein Richtwert).
- **Rot heißt: nicht schneiden**, sondern dem Menschen den Befund zeigen. Ist eine Quelle rot und eine andere desselben
  Takes grün, das melden und fragen, nicht still auf die andere umschwenken.
- Der Zähler hängt am Pegel: Lauter gemachtes Material zählt mehr Konsonanten als Klicks. Deshalb Rohdateien messen und
  ernst nehmen, was das Werkzeug zum Pegel sagt.
- Weichen zwei Messungen um Größenordnungen ab, gilt die geeichte. Ein neuer Zähler wird erst an bekannt sauberem und
  bekannt kaputtem Material geeicht, bevor er Entwarnung geben darf.

## 2. Prüfreihenfolge bei Knacken

In dieser Reihenfolge, nach jedem Schritt eine kurze Probeaufnahme und `studio klick-check`:

1. **Abtastrate überall gleich (48 kHz):** Audio-Interface im System, OBS, Rauschunterdrückung. Dauerndes Umrechnen
   zwischen 44,1 und 48 kHz ist eine häufige Ursache.
2. **Audiogerät an den Kameraquellen:** Hat eine Kameraquelle in OBS ein eigenes Audiogerät, abschalten. Der Ton kommt
   aus genau einer Mikrofonquelle.
3. **Kanten der Rauschunterdrückung in Pausen:** Geht die Rauschunterdrückung in Sprechpausen auf digitale Stille, zählt
   der Zähler die Kanten als Klicks. Erkennbar: Treffer liegen in Pausen, ringsum exakte Nullwerte. Das ist kein Defekt
   im Aufnahmeweg; abhören und entscheiden.
4. **Ziellaufwerk:** Aufnahme auf ein langsames Laufwerk (USB 2, exFAT) kann ganze Tonblöcke beschädigen. Hinweis darauf:
   viele Klick-Abstände im Raster eines AAC-Blocks (1024 Abtastwerte, bei 48 kHz 21,33 ms). Auf die interne SSD
   aufnehmen.
5. **Pegel:** zu leise aufgenommen und später stark angehoben, werden kleine Störungen hörbar. Gain am Interface so,
   dass Sprache kräftig ist und Spitzen Abstand zu 0 dBFS halten.

## 3. Stimme schneiden

- **Kanten an den Sprachkern**, nicht an den ersten Pegel-Einsatz: Davor liegen oft Atem oder das Fußpedal des
  Prompters (dumpfer Stoß kurz vor dem ersten Wort).
- **Wortenden nicht abschneiden:** Nach einem Schluss-„t“ oder „ch“ kommt nach kurzer Stille noch ein heller Knall.
  Die Endkante nimmt ein kurzes, helles Ereignis kurz nach dem Wort mit.
- **Kein Loch an der Naht:** Raumton zwischen zwei Stücken nicht von der leisesten Stelle, sondern von der
  gleichmäßigsten ruhigen Stelle des Takes nehmen; Nähte gleich laut überblenden. Ein harter Abfall in Stille an jeder
  Naht ist als Pumpen hörbar.
- **Wortzeiten aus Whisper nicht für Kanten verwenden:** Das erste Wort nach einer Pause wird oft zu früh angesetzt.
  Kanten aus dem Pegel, Whisper nur zum Finden.

## 4. Hörprobe durch den Menschen

Vor dem ersten Bild bekommt ein Mensch ein kurzes Stück gemasterte Stimme zu hören (Faustregel: etwa 20 Sekunden mit
mindestens zwei Nähten). Lautheit auf Ziel und eine saubere Rücktranskription beweisen nicht, dass der Ton gut klingt:
Whisper hört kein Knacken.

## 5. Mastern

```
studio mastern <eingang> <ausgang> [--ziel-lufs -14] [--ziel-true-peak -1.5] [--max-begrenzer-db 3] [--probe]
```

- **Messung** nach ITU-R BS.1770 ([ITU](https://www.itu.int/rec/R-REC-BS.1770)): integrierte Lautheit in LUFS und True
  Peak in dBTP; für True Peak wird überabgetastet (das Werkzeug misst bei 192 kHz).
- **Ziel −14 LUFS integriert, höchstens −1,5 dBTP** als Voreinstellung. Grundlage: Spotify normalisiert auf −14 LUFS und
  empfiehlt True Peak unter −1 dBTP, bei lauteren Mischungen unter −2 dBTP
  ([Spotify](https://support.spotify.com/us/artists/article/loudness-normalization/)); −1,5 dBTP liegt dazwischen.
  YouTube veröffentlicht keinen festen Zielwert; prüfe den Upload selbst (Statistiken für Interessierte, „content
  loudness“). Fernsehen arbeitet nach EBU R 128 mit −23 LUFS ([EBU](https://tech.ebu.ch/publications/r128)).
- **Abbruch statt Quetschen:** Müsste der Begrenzer mehr als 3 dB wegnehmen, stimmt die Mischung nicht (einzelne Spitzen
  von Klängen, O-Tönen oder Musik). Dann die Mischung korrigieren, nicht lauter begrenzen. Der Wert ist einstellbar.
- **Nachmessung:** Das Werkzeug misst die fertige Datei erneut und berichtet LUFS und dBTP. Liegt sie nicht im Ziel, ist
  die Datei nicht abgabefertig.
- Einzelne fremde Tonausschnitte (Interviews, Podcasts) vorher als eigenes Stück auf Stimmlautstärke bringen, nicht nur
  in der Timeline anheben: Ihre eigenen Spitzen treiben sonst die Summe an 0 dBFS.

## 6. Fallen

### F1 · Entwarnung mit dem eigenen Zähler
**Symptom:** Ein Bericht meldet viele Klicks, ein schnell gebauter zweiter Zähler findet kaum welche; geschnitten wird,
und im fertigen Video knackt es durchgehend.
**Ursache:** Der zweite Zähler war nicht geeicht.
**Gegenmittel:** Die geeichte Messung gilt; bei Widerspruch dem Menschen beide Zahlen zeigen und abhören lassen.

### F2 · Anheben macht Knacken hörbar
**Symptom:** Nach dem Anheben der Stimme um viele dB knackt sie dauernd.
**Ursache:** Beschädigte Tonblöcke in der Rohdatei; leise waren sie kaum hörbar.
**Gegenmittel:** Vor dem Anheben messen; eine andere, saubere Quelle desselben Takes vorschlagen oder neu aufnehmen.

### F3 · Das Erste, was man hört, ist das Pedal
**Symptom:** Vor jedem Satz ein dumpfer Stoß, Pausen werden länger.
**Ursache:** Kante am ersten Pegel-Einsatz statt am Sprachkern; das Prompter-Pedal liegt kurz vor dem ersten Wort.
**Gegenmittel:** Kante an den Sprachkern; Stöße außerhalb der Sprache durch Raumton ersetzen, nie innerhalb der Sprache.

### F4 · Pumpen an jeder Naht
**Symptom:** An jedem Schnitt fällt der Hintergrund kurz ab.
**Ursache:** Raumton aus der leisesten Stelle, in den Pausen der Sätze liegen aber Atem und Nachhall deutlich lauter.
**Gegenmittel:** Ausklang des vorigen Stücks bis in den Vorlauf des nächsten laufen lassen und gleich laut überblenden.

### F5 · Abgabe zu laut gequetscht
**Symptom:** Lautheit stimmt, die Stimme klingt platt, Klänge verzerren.
**Ursache:** Der Begrenzer musste viele dB wegnehmen.
**Gegenmittel:** `studio mastern` bricht oberhalb von `--max-begrenzer-db` ab; Mischung korrigieren.
