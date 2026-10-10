---
name: abgabe
description: Macht aus dem fertigen Schnitt die Upload-Datei und das Abgabe-Paket – Master als ProRes 422 HQ aus Resolve, Wandlung nach H.264 (CRF 16, Fast Start) mit Ton auf −14 LUFS, Nachmessung, Sicht- und Hörprobe durch den Menschen, Untertitel, Kapitel, Beschreibung mit Quellen – und prüft, was die Plattform verlangt. Nutze diesen Skill bei „Abgabe“, „Upload-Datei“, „exportieren“, „fertig machen“, „Master“, „Untertitel“, „Kapitel“, „Beschreibung“ und bevor ein Video hochgeladen wird.
---

# Abgabe

Die Abgabe ist der letzte Schritt, an dem ein Fehler noch billig ist. Danach sehen ihn alle.

**Freigabe gibt der Mensch**, nach eigener Sicht- und Hörprobe an genau der Datei, die hochgeladen wird. Kein Agent
erklärt ein Video für fertig.

## 1. Datei bauen

1. **Master aus Resolve** als ProRes 422 HQ (`resolve_rendern.py --format mov --codec ProRes422HQ`, Skill
   `resolve-schnitt`). Der H.264-Render aus Resolve hat keinen Qualitätsregler (Resolve-Falle F12).
2. **Upload-Datei** mit `studio mastern <master.mov> <upload.mp4> [--hoehe 1440]` (erst mit `--probe` messen und
   planen):
   - Video H.264, CRF 16 (Voreinstellung, einstellbar mit `--crf`), `-movflags +faststart` (der Index steht vorn; YouTube empfiehlt das ausdrücklich als
     „Fast Start“, [YouTube-Hilfe](https://support.google.com/youtube/answer/1722171)).
   - Ton auf −14 LUFS, höchstens −1,5 dBTP, mit Nachmessung (Herkunft der Werte: Skill `ton-mastering`).
   - Bricht ab, wenn der Begrenzer mehr als 3 dB greifen müsste: dann die Mischung korrigieren.
3. **Format:** Querformat z. B. 2560×1440 (1440p), Hochformat 1080×1920. YouTube nennt für 1440p bei 24–30 fps 16 Mbit/s
   und für 1080p 8 Mbit/s als empfohlene Bitrate, AAC-LC mit 48 kHz und H.264 High Profile
   ([YouTube-Hilfe](https://support.google.com/youtube/answer/1722171)). Eine höhere Auflösung als die Timeline bringt
   nur etwas, wenn die Quelle sie hergibt (z. B. 4K-Kameras).

## 2. Prüfen vor der Freigabe

- [ ] Nachmessung von `studio mastern`: LUFS und dBTP im Ziel.
- [ ] `studio klick-check <upload.mp4>`: keine neuen Klicks gegenüber der Stimme (Pegel beachten, siehe `ton-mastering`).
- [ ] **Rückcheck Wortlaut:** `studio transkript <upload.mp4>` und mit dem Skript vergleichen: fehlende, doppelte oder
      halbe Sätze, Zahlen. Für kurze Stellen mehrere Whisper-Modelle gegeneinander; nie den erwarteten Text als Vorgabe
      (Prompt) an Whisper geben, sonst hört es, was es hören soll.
- [ ] **Kadrierung:** an einem Kontaktbogen kein Kopf und kein Kinn angeschnitten, Augenlinie ruhig.
- [ ] **Sicht- und Hörprobe durch den Menschen** am Stück, mit Kopfhörer.
- [ ] Länge: Ein YouTube-Konto ohne Bestätigung nimmt standardmäßig höchstens 15 Minuten
      ([YouTube-Hilfe](https://support.google.com/youtube/answer/71673)). Vor einem langen Video prüfen.

## 3. Abgabe-Paket

| Teil | Inhalt |
|---|---|
| Upload-Datei | aus §1, Name mit Fassung (nie eine Datei überschreiben, die noch in einem Schnittprogramm liegt) |
| Untertitel (SRT) | aus dem Transkript der Upload-Datei; nur Groß-/Kleinschreibung, Satzzeichen und Zeilen angleichen. Verhörte Namen und Fachwörter als ausdrückliche Liste korrigieren, nie nach Ähnlichkeit zum Skript |
| Kapitel | Zeitmarken aus den Markern der Timeline; erste Marke bei 0:00 |
| Beschreibung | Was das Video zeigt, Kennzeichnung von Meinung und Werbung, Quellenliste mit Links (aus der Belegtabelle, Plugin `recherche`) |
| Quellen-Kommentar | optional die Quellenliste als angehefteter Kommentar |

Die Beschreibung bekommt Absätze mit Leerzeilen; vor dem Einfügen in das Upload-Formular im Klartext prüfen, ob
Zeilenumbrüche mitten im Satz entstanden sind.

## 4. Offene Lücke: Upload

Hochgeladen wird von Hand im Studio der Plattform. Ein automatischer Upload ist bewusst nicht enthalten: Er braucht
OAuth-Zugang zum Konto und Kontingente der API, und er nimmt dem Menschen den letzten Blick ab. Wer ihn bauen will:
eigenes Werkzeug, eigener Schlüssel, nie im Repo.

## 5. Fallen

### F1 · Datei im Schnittprogramm überschrieben
**Symptom:** Ein neuer Export auf denselben Namen scheitert, oder der Clip steht später auf „Offline“.
**Ursache:** Das Schnittprogramm hält importierte Dateien offen.
**Gegenmittel:** Jede Fassung bekommt einen neuen Namen.

### F2 · Untertitel ändern das Gesagte
**Symptom:** Im Untertitel steht der Skript-Wortlaut statt des Gesprochenen.
**Ursache:** Korrektur nach Ähnlichkeit zum Skript.
**Gegenmittel:** Nur ausdrückliche Verhörer-Liste; alles andere bleibt, wie es gesprochen wurde.

### F3 · Lautheit stimmt, Ton klingt kaputt
**Symptom:** Zahlen im Ziel, aber Knacken oder Pumpen.
**Ursache:** Messung ersetzt nicht das Hören.
**Gegenmittel:** Freigabe nur nach Hörprobe durch den Menschen.

### F4 · Langes Video bricht nach dem Upload ab
**Symptom:** Upload läuft durch, Verarbeitung bricht mit „zu lang“ ab.
**Ursache:** Konto nicht bestätigt (15-Minuten-Grenze).
**Gegenmittel:** Konto vorher bestätigen.
