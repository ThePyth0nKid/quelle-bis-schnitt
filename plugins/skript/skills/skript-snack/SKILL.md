---
name: skript-snack
description: 'Der Wissens-Snack (30–45 s, 80–115 Wörter) nach dem Schema aus dem Skill skript, verkürzt auf ein Ding, eine verblüffende Zahl, eine Alltags-Analogie oder Vergleichsleiter und die Auszahlung. Nutze diesen Skill nach skript für jeden Snack, bei „Snack“, „Fakt“, „Schätzfrage“, „kurzes Wissensvideo“, „eine Zahl erklären“.'
---

# Wissens-Snack 30–45 Sekunden

Dasselbe Schema wie der Short (Skill `skript` §2), nur kürzer.

| Slot | bei 35 s | bei 45 s | Wörter bei 35 s |
|---|---|---|---|
| 1 Hook: ein Ding und was es tut, beim ersten Hören klar; die Zahl nur, wenn sie das Ding größer macht | 0–3 | 0–3 | 8 |
| 2 Absender und Versprechen | 3–6 | 3–7 | 8 |
| 3 Bekanntes: Körper oder vertraute Referenz | 6–14 | 7–17 | 20 |
| 4 Das Ding, zusammenhängend erklärt | 14–26 | 17–33 | 32 |
| 5 Auszahlung | 26–32 | 33–40 | 15 |
| 6 Schluss | 32–35 | 40–45 | 8 |

Die Wortzahlen gelten bei 2,6 Wörtern je Sekunde (Faustwert, eigenes Tempo messen).

## 1. Hinweise (keine Pflicht)

- **Anfang:** 13 von 21 erfolgreichen Snacks beginnen mit Zeigewort oder Szene („Das hier“, „Schau dir“, „Stell dir
  vor“); die erste Zahl fällt bis Sekunde 5 (eigene Messung, n = 21 Snacks aus 10 Kanälen, Methode in
  `docs/messungen/skript-auszaehlung.md`). Ob ein Zeigewort vorn mehr Reichweite bringt, ist nur eine Tendenz (Skill
  `hook`).
- **Vergleichsleiter:** Bei riesigen Zahlen hilft eine Leiter von bekannt nach unbekannt, zwei bis fünf Stufen, jede ein
  ganzer Satz (Kühlschrankmagnet → Lautsprecher → Kernspintomograph → das Ding). Zahlen in einen vertrauten Vergleich
  zu übersetzen verbessert das Verständnis und das Erinnern (Barrio, Goldstein & Hofman, „Improving Comprehension of
  Numbers in the News“, CHI 2016). Ob die Leiter auch beim bloßen Zuschauen trägt, ohne dass man selbst schätzt, ist
  offen; ein Satz wie „Jetzt schätz mal …“ löst die Schätzung aus.
- **Wendung:** 17 von 21 Snacks haben eine („Jetzt denkst du vielleicht … Aber …“). Dass es eine gibt, trennt auch in
  der Hook-Studie; wo sie liegt, nicht (blind 65 % gegen 51 %, Methode in `docs/messungen/hook-studie.md`).
- **Vergleichsformen** in den 21 Snacks: Alltagsmaß 7, Zeit 6, Geld 5 (nur bei Geldthemen), Körper 4, Anteile 3,
  Temperatur 2, Steigerungsleiter 2. Geld nur bei Geldthemen.
- **Analogie:** Eine Alltags-Analogie macht die Zahl greifbar. Für die Reichweite ist sie nicht gesichert (blind 16 %
  gegen 14 %); sie bleibt, weil sie das Verstehen trägt.

## 2. Umrechnungen: Werkzeug, wenn es passt

Eine feste Umrechnung (Laufstrecke, Badewannen, Fußballfelder) als Markenzeichen nutzt sich schnell ab. In den 21
gezählten Snacks kam keine Sport-Umrechnung vor. Umrechnen nur, wenn es eine Zahl wirklich greifbar macht, und jeden
Umrechnungsfaktor mit Quelle auf die Karte.

## 3. Abnahme

```bash
python scripts/skript_pruefen.py F<n>_skript.md --format snack     # im Skill skript
```

Jeden Fund lesen und entscheiden; Zahlen gegen die Quelle; einmal laut lesen. Ablage wie im Skill `skript` (§1).

## 4. Fallen

### F1 · „Wusstest du“
**Symptom:** Der Einstieg klingt nach Quiz-Kalender.
**Ursache:** Abgenutzte Formel (Stilentscheidung, nicht gemessen; es gibt erfolgreiche Shorts, die so beginnen).
**Gegenmittel:** Das Ding direkt nennen.

### F2 · Rückfrage als letzter gesprochener Satz
**Symptom:** „Was meinst du?“ als Ende.
**Ursache:** Die Aufforderung ist in den Mund gerutscht.
**Gegenmittel:** Fragen an die Zuschauer gehören auf die Endkarte.

### F3 · Geld als Referenz für Nicht-Geld
**Symptom:** „So viel wie ein Kleinwagen“ für eine Temperatur.
**Ursache:** Bequemer Vergleich.
**Gegenmittel:** Eine Referenz aus derselben Welt (Körper, Alltag, Zeit).

### F4 · Zahl als Etikett, zwei Lacher
**Symptom:** „5 Tonnen. Musterhafen. Rekord.“ und zwei Pointen auf 35 Sekunden.
**Ursache:** Zu viel auf zu wenig Zeit.
**Gegenmittel:** Zahl im ganzen Satz; höchstens ein Lacher, am Ende.
