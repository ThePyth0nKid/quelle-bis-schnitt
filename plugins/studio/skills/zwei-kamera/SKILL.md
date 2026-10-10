---
name: zwei-kamera
description: Legt zwei gleichzeitig laufende Kameras bildgenau übereinander – Start-Versatz messen (Ton-Kreuzkorrelation, Bewegung, Bildzahl), Paar je Take bauen, Ergebnis prüfen, Rohdateien behalten. Mit den Befehlen studio paar und studio waechter. Nutze diesen Skill bei „zwei Kameras synchronisieren“, „Kamera B liegt daneben“, „Paar bauen“, „Takes ordnen“, „Wächter starten“, „Versatz“, „Multicam“ und bevor ein Zwei-Kamera-Take geschnitten wird.
---

# Zwei Kameras, ein Paar

OBS startet die Ausgaben der Source-Record-Filter nacheinander. Kamera B beginnt deshalb ein paar Bilder nach Kamera A,
je Take anders. Im Beispiel-Setup lag der Versatz zwischen 3 und 18 Bildern bei 25 fps (eigene Messung, Stichprobe und
Methode in `docs/messungen/studio-zwei-kamera.md`). Ohne Ausgleich spricht Kamera B neben ihrem Ton.

## 1. Voraussetzungen

- Beide Kameras, beide Capture-Geräte und OBS mit **derselben Bildrate**. Sonst bleibt nach dem Ausgleich ein Rest von
  mehreren Bildern, und einzelne Bilder doppeln sich.
- Beide Kameradateien tragen denselben Mikrofonton (Source Record nimmt die Tonspur des Filters).
- Dateinamen mit Zeitstempel, damit Paare zusammenfinden: `<praefix><JJJJMMTT-HHMMSS><endung>`. In OBS im
  Source-Record-Filter z. B. `cam-A-%CCYY%MM%DD-%hh%mm%ss` bzw. `cam-B-…` eintragen; Präfixe und Endung stehen in
  `studio.toml` unter `[kameras]`.

## 2. Wie der Versatz gemessen wird

1. **Ton:** Kreuzkorrelation (FFT) der beiden Tonspuren ergibt den Start-Versatz im Takt von OBS, zerlegt in ganze
   Bilder plus Rest.
2. **Bewegung:** Die Kameras laufen frei (kein gemeinsamer Takt), ihre Phase zum OBS-Takt wandert. Dieselbe echte
   Bewegung kann deshalb 0 oder 1 Bild neben dem Ton-Versatz liegen. Ist im Take eine **eindeutige Bewegung**, richtet
   sie aus; der Ton ist die Gegenprobe. Weichen beide deutlich ab, ist das Paar rot.
3. **Bildzahl:** Bei sehr kurzen Takes reicht weder Ton noch Bewegung. OBS stoppt beide Ausgaben gleichzeitig, also gilt
   dann: Versatz = Bilder A − Bilder B, mit Hinweis „±1 Bild“.

Ein Bild bei 25 fps sind 40 ms. Ob das für den Schnitt stört, entscheidet der Mensch am Kontaktbogen (Mund, Hände).

## 3. Werkzeuge

| Befehl | Was |
|---|---|
| `studio paar [ORDNER] [--stempel JJJJMMTT-HHMMSS] [--probe] [--json]` | sucht ein Paar (A/B nach Zeitstempel im Dateinamen) im Ordner oder in `[pfade] inbox`, ohne `--stempel` das neueste; misst, baut je Take einen Ordner mit genau den zwei ausgerichteten Dateien und schreibt einen Bericht. `--probe` zeigt nur den Plan; `--a`/`--b` nimmt zwei Dateien direkt; `--roh-lassen` fasst die Rohdateien nicht an |
| `studio waechter [--einmal] [--probe]` | hält eine Verbindung zu OBS: beim Aufnahmestart Kameras, Dateien und Mikrofonpegel prüfen, nach dem Stopp das Paar bauen; `--einmal` holt ohne OBS nur offene Takes nach |
| `studio inbox-ordnen [INBOX] [--probe]` | legt alte lose Rohdateien paarweise in Take-Ordner; schreibt ein Protokoll, `--zurueck <tsv>` stellt alles wieder an den alten Platz |

Einstellungen in `studio.toml` unter `[kameras]` (Dateipräfixe, Namen der OBS-Quellen und Filter) und `[paar]`
(Encoder, Qualität, Drehung von Kamera B, Umgang mit Rohdateien, Gegenprobe).

**Rohdateien bleiben standardmäßig liegen** (`[paar] rohdateien = "behalten"`, sie wandern in `<Take>/Roh/`). Ob sie
nach einem grünen, nachgeprüften Bau nach `<ziel>/_Papierkorb/<Take>/` wandern dürfen (`rohdateien = "papierkorb"`;
verschoben, nie gelöscht), entscheidet der Mensch in der Konfiguration, nicht das Werkzeug.

Rote Paare landen in einem Ordner mit Kennzeichnung (z. B. „… PRUEFEN“), nie unter dem normalen Namen. Gründe stehen im
Bericht (`warnungen`).

## 4. Prüfen

- Bericht lesen: Quelle des Versatzes (Bewegung, Ton, Bildzahl), Abstand Ton zu Bewegung, Bildzahlen, Klicks je Spur.
- Kontaktbogen an zwei, drei Stellen mit deutlicher Bewegung (Klatschen, Handbewegung): beide Kameras nebeneinander.
- Bei langen Takes Anfang und Ende vergleichen: ein Phasensprung im Take ist ein Grund für Rot.

## 5. Fallen

### F1 · Hardlinks scheitern
**Symptom:** Verlinken der Take-Dateien in einen Projektordner bricht ab.
**Ursache:** exFAT kennt keine Hardlinks, und zwischen zwei Laufwerken gehen sie nie; Symlinks brauchen unter Windows
Zusatzrechte.
**Gegenmittel:** Dateien dort lesen, wo sie liegen, oder kopieren. Verschieben nur durch Umbenennen auf derselben Platte.

### F2 · Halb kopierte Datei
**Symptom:** Eine Kameradatei im Take-Ordner ist abgeschnitten.
**Ursache:** Verschoben wurde, während OBS die Datei noch offen hatte (Kopieren statt Umbenennen).
**Gegenmittel:** Nach dem Stopp einige Sekunden warten und mehrfach versuchen; nur umbenennen, nie kopieren und löschen.

### F3 · Falsche Kamera als Tonquelle
**Symptom:** Das Paar knackt, obwohl eine der beiden Rohdateien sauber ist.
**Ursache:** Der Bau nahm den Ton der Kamera mit Klicks.
**Gegenmittel:** Klicks beider Spuren zählen und die sauberere nehmen; im Bericht steht, welche genommen wurde. Haben
beide Klicks, liegt die Ursache im Aufnahmeweg (Skill `ton-mastering`).

### F4 · Wächter trifft den falschen Prozess
**Symptom:** „Beenden“ stoppt ein anderes Programm mit ähnlichem Namen.
**Ursache:** Prozesse nur am Dateinamen gesucht.
**Gegenmittel:** Prozesse am vollen Pfad oder an einer Sperrdatei erkennen.

### F5 · Keyframes verhindern bildgenaues Kürzen
**Symptom:** Nach dem Kürzen ohne Neukodieren springt der Anfang.
**Ursache:** Kameradateien haben Keyframes nur in großen Abständen.
**Gegenmittel:** Die Kamera, die verschoben wird, neu kodieren; die andere unverändert kopieren.
