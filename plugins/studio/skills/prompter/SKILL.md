---
name: prompter
description: Bringt ein fertiges Skript in den Teleprompter – ein Satz je Abschnitt, Kameramarken je Satz, Satzgrenzen ohne Fehler bei Ordnungszahlen und Kürzeln – und lädt es sicher in die Prompter-Software (Elgato Camera Hub, vorerst Windows), ohne eine laufende Aufnahme zu stören. Mit studio prompter saetze und studio prompter einspielen. Nutze diesen Skill bei „Prompter“, „Teleprompter bestücken“, „Skript ins Glas“, „Sätze für den Prompter“, „Prompter lädt nicht“ und vor jedem Dreh mit Prompter.
---

# Prompter: ein Satz je Abschnitt

Im Prompter blättert man Abschnitt für Abschnitt (Pfeiltasten, Fußpedal oder Fernbedienung). Steht **ein Satz je
Abschnitt** im Glas, gilt:
- Jeder Satz ist ein eigener Anlauf. Verspricht man sich, wiederholt man nur diesen Satz, und der Schnitt findet den
  letzten vollständigen Anlauf leicht.
- Der Blick bleibt nah an der Linse, weil nur wenig Text im Glas steht.
- Kameramarken (`[A]`, `[B]` …) stehen vor jedem Satz, auch wenn sie im Skript nur am Absatzanfang standen.

## 1. Ablauf

1. Skript fertig und freigegeben (Plugin `skript`). Im Prompter wird nicht mehr umgeschrieben.
2. `studio prompter saetze <skript.md> --ausgabe <prompter.md>`: teilt in Sätze, ein Satz je Absatz (überschreibt
   nie). Regiezeilen in Klammern bleiben eigene Abschnitte; eigene Kameramarken mit `--marke NAME`. **Die Ausgabe
   lesen**, bevor sie ins Glas geht.
3. Projekt-Datei `prompter.toml` im Projektordner: welche Texte in welcher Reihenfolge in den Prompter kommen. Beispiel
   (vollständig in `studio prompter einspielen --help`):
   ```toml
   praefix = "MUSTER "                         # Einträge mit diesem Anfang gehören dem Projekt
   [[skript]]
   name = "MUSTER M01 · Wie ein Stromnetz atmet"
   datei = "F2_prompter.md"                    # relativ zu dieser Datei; Leerzeile = neuer Abschnitt
   ```
4. `studio prompter einspielen [prompter.toml] --probe`: zeigt, was angelegt, ersetzt oder entfernt würde. Dann ohne
   `--probe`. Weitere Schalter: `--kein-neustart`, `--nichts-loeschen` (veraltete eigene Einträge stehen lassen),
   `--ohne-obs` (OBS nicht prüfen; nur wenn sicher nichts aufnimmt). Das Werkzeug
   - prüft per obs-websocket, dass OBS **nicht aufnimmt** (sonst Abbruch),
   - sichert den Datenordner der Prompter-Software,
   - beendet nur den in `[prompter] prozessname` genannten Prozess und bricht ab, wenn er nicht endet,
   - schreibt die Texte und startet die Software neu.
5. Im Glas kontrollieren: erster und letzter Satz, Umlaute, Zahlen.

## 2. Satzgrenzen

Getrennt wird nach `.`, `!`, `?` (auch mit schließendem Anführungszeichen), wenn danach Leerraum und ein Großbuchstabe,
eine Ziffer oder eine Kameramarke folgt. Nicht getrennt wird:
- nach Ordnungszahlen („am 3. Oktober“),
- nach üblichen Kürzeln („z. B.“, „d. h.“, „bzw.“, „ca.“, „Nr.“, „Mio.“, „Mrd.“ …).

Fehlt ein Kürzel in der Liste, entsteht ein halber Satz im Glas. Deshalb Schritt 2: die Ausgabe lesen.

## 3. Sprechen am Prompter

- Zahlen so ins Skript schreiben, wie man sie spricht, wenn sie schwer zu lesen sind („zweitausendsechsundzwanzig“
  statt „2026“ nur dort, wo man sonst stolpert).
- Pro Satz: Pedal drücken, kurz atmen, dann sprechen. Das Pedal ist im Ton als dumpfer Stoß hörbar; der Schnitt setzt
  die Kante an den Beginn der Sprache, nicht an das Pedal (Skill `ton-mastering`, F3).
- Lieber den ganzen Satz neu als ab der Mitte.

## 4. Fallen

### F1 · Neue Texte verschwinden wieder
**Symptom:** Nach dem nächsten Beenden der Prompter-Software sind die eingespielten Texte weg.
**Ursache:** Die Software schreibt beim ordentlichen Beenden ihren Speicherstand zurück und überschreibt die Änderung.
**Gegenmittel:** Vor dem Schreiben hart beenden und prüfen, dass der Prozess wirklich weg ist (das Werkzeug tut das).

### F2 · Texte liegen auf der Platte, die Oberfläche zeigt sie nicht
**Symptom:** Dateien sind geschrieben, die Liste im Prompter bleibt leer.
**Ursache:** Die Bibliotheksliste ist ein flacher Schlüssel mit Punkten im Namen (Qt-Einstellungsdatei); verschachtelt
geschrieben wird er still ignoriert.
**Gegenmittel:** Flach schreiben; das Werkzeug trägt verwaiste Texte wieder in die Liste ein.

### F3 · Kameras fallen während der Aufnahme aus
**Symptom:** Mitten im Take bricht ein Kamerabild ab.
**Ursache:** Die Prompter-Software steuert auch Kameras; sie wurde während einer Aufnahme beendet.
**Gegenmittel:** Nie während einer Aufnahme einspielen; das Werkzeug prüft OBS vorher.

### F4 · Satz im Glas zerrissen
**Symptom:** Ein Abschnitt endet mitten im Satz („… am 3.“).
**Ursache:** Ordnungszahl oder unbekanntes Kürzel als Satzende erkannt.
**Gegenmittel:** Ausgabe von `prompter saetze` lesen, Kürzel ergänzen oder den Satz im Skript umstellen.
