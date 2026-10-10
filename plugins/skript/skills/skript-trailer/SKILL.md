---
name: skript-trailer
description: 'Der Kanaltrailer (35–60 s), der Fremde zum Folgen bringt: acht Regeln aus der YouTube-Hilfe, Praktikern und einer eigenen Auszählung öffentlicher Trailer; Beat-Tabelle für 40 und 60 Sekunden, Du vor Ich, genau eine Aufforderung bei 77–85 % der Länge. Nutze diesen Skill nach skript für jeden Kanaltrailer, jede Kanalvorstellung, jedes angepinnte Vorstellungsvideo, bei „Trailer“, „Kanalsatz“, „für wen“, „warum es den Kanal gibt“.'
---

# Kanaltrailer: Haken, Beweis, was du bekommst, Haltung, Name spät, eine Aufforderung

## 0. Einordnung

YouTube zeigt den Kanaltrailer Besuchern, die den Kanal noch nicht abonniert haben (YouTube-Hilfe zum Kanaltrailer).
Er ist kein Community-Video, sondern eine Vorstellung für Fremde. Viele große Erklärkanäle legen statt eines eigenen
Trailers ihr stärkstes Video in den Platz; beides ist möglich. Nach 30 Tagen den Trailer gegen das beste Video messen
(Abo-Zuwachs, Abbruch in der Zuschauerbindung).

## 1. Die acht Regeln

| # | Regel | Beleg |
|---|---|---|
| R1 | Für Fremde: nichts voraussetzen, kein Bezug auf frühere Videos | YouTube-Hilfe; YouTube Creator Academy |
| R2 | Die ersten drei Sekunden sind ein Haken, nicht der Name | 5 von 8 starken Trailern nennen den Namen erst bei 38–60 s (eigene Auszählung, n = 12) |
| R3 | Kurz: 30–60 s; YouTube nennt keine feste Länge | eigene Auszählung, n = 12 |
| R4 | Zeigen statt behaupten: echte Ausschnitte oder echte Fragen aus echten Videos | Praktiker-Konsens (Film Booth, Wordstream) |
| R5 | Sagen, was der Zuschauer bekommt und für wen es ist; Du vor Ich | Du-Dichte 2,0–6,8 je 100 Wörter (eigene Auszählung); Film Booth: „a channel is not about you“ |
| R6 | Ein Satz Haltung: warum es den Kanal gibt | Praktiker-Konsens |
| R7 | Genau eine Aufforderung, am Ende, mit Grund oder Rhythmus, bei 77–85 % der Länge | gemessen 76–85 % (eigene Auszählung) |
| R8 | Messen und nachziehen | YouTube Creator Academy |

Eigene Auszählung: n = 12 öffentliche Kanaltrailer großer Wissenskanäle, Methode und Grenzen in
`docs/messungen/skript-auszaehlung.md`.

## 2. Beat-Tabelle

| Beat | 40 s | 60 s | Inhalt | Wörter (40 s) |
|---|---|---|---|---|
| 1 Haken | 0–3 | 0–4 | Frage oder These, stumm lesbar; kein Name, kein Logo | 8 |
| 2 Beweis | 3–12 | 4–18 | zwei bis drei konkrete Fragen oder Ausschnitte aus echten Videos | 23 |
| 3 Was du bekommst | 12–20 | 18–30 | Formate, Nutzen, Rhythmus, in Du-Sätzen | 21 |
| 4 Haltung und Name | 20–28 | 30–42 | ein Satz Warum, dann erst der Name | 21 |
| 5 Für wen | 28–33 | 42–50 | Einladung an den passenden Zuschauer, Abgrenzung erlaubt | 13 |
| 6 Aufforderung | 33–40 | 50–60 | eine, mit Grund oder Rhythmus; die Endkarte übernimmt den Knopf | 18 |

Gemessenes Sprechtempo in Trailern: 2,2 bis 3,0 Wörter je Sekunde (eigene Auszählung). 40 s sind damit rund 95–120
Wörter.

## 3. Hook-Typen für den Trailer

- **Frage:** eine echte Frage aus einem echten Video des Kanals („Warum hält die Straßenbahn schneller als dein Auto?“).
- **These:** ein Satz, der die Haltung des Kanals zeigt.
- **Geständnis:** „Ich weiß, was du denkst: …“, wenn das Warum im selben Satz steckt; besser als Satz 2.

Der Kanalsatz (wer, für wen, was) gehört auf die Endkarte, nicht an den Anfang.

## 4. Abnahme

```bash
python scripts/skript_pruefen.py trailer.md --format trailer     # im Skill skript
```

Relevante Regeln: `aufforderung-trailer` (genau eine bei 70–90 %), `du-vor-ich`, `slots` (sechs Beats ±35 %),
`laenge` (35–60 s). Jeden Fund lesen und entscheiden. Beweise sind echte Ausschnitte oder echte Fragen; Platzhalter
als solche markieren und auflisten, was gedreht werden muss. Name nach der Hälfte.

## 5. Fallen

### F1 · Name in Sekunde 1
**Symptom:** Fremde wischen weg, bevor etwas passiert.
**Ursache:** Der Trailer beginnt mit dem Absender statt mit einem Haken.
**Gegenmittel:** Haken zuerst, Name nach der Hälfte.

### F2 · Behauptung statt Beweis
**Symptom:** „Hier lernst du alles über …“
**Ursache:** Der Trailer beschreibt den Kanal, statt ihn zu zeigen.
**Gegenmittel:** Echte Fragen oder Ausschnitte aus echten Videos.

### F3 · Drei Aufforderungen
**Symptom:** Abonnieren, Glocke, Kommentieren hintereinander.
**Ursache:** Angst, etwas zu vergessen.
**Gegenmittel:** Genau eine, mit Grund.

### F4 · Ein Rhythmus, der nicht gehalten wird
**Symptom:** „Jeden Montag ein neues Video“, und es kommt keins.
**Ursache:** Versprechen ohne Plan.
**Gegenmittel:** Nur nennen, was sicher kommt.

### F5 · Erfundene Beweise
**Symptom:** Ausschnitte, die es im Kanal nicht gibt.
**Ursache:** Der Trailer entstand vor den Videos.
**Gegenmittel:** Nur echte Ausschnitte, sonst Platzhalter mit Drehliste.

### F6 · Musik-Intro vor dem Haken
**Symptom:** Die ersten Sekunden sind nur Logo und Musik.
**Ursache:** Gewohnheit aus Fernsehtrailern.
**Gegenmittel:** Der Haken kommt zuerst; Musik darunter.
