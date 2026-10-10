---
name: skript-short
description: 'Der Erklär-Short (60–75 s, 160–195 Wörter) nach dem Schema aus dem Skill skript, dazu das Werkzeug Nachgeprüft mit dem Urteil ECHT, FAKE oder OFFEN, wenn eine Behauptung im Raum steht. Das Ding im Hook ist die Behauptung, nie das Quellvideo. Nutze diesen Skill nach skript für jeden Short, bei „Short“, „Nachgeprüft“, „Urteil“, „Faktencheck“, „stimmt das?“.'
---

# Erklär-Short 60–75 Sekunden

Standard sind die sechs Slots aus dem Skill `skript` (§2). Dieser Skill ergänzt, was der Short braucht, wenn eine
Behauptung im Raum steht.

## 1. Nachgeprüft: das Werkzeug fürs Urteil

Nur, wenn eine Behauptung kursiert: ein Video, ein Zitat, eine Schlagzeile. Sonst reines Staunen ohne Urteil.

1. **Das Ding im Hook ist die Behauptung**, wie sie kursiert, nie das Quellvideo mit Konto, Likes oder „dieses Reel“.
   Sonst klingt es nach Reaction. Das Quellvideo kommt frühestens in Slot 3 vor.
2. **Vorher das Quellvideo Bild für Bild ansehen** (Kontaktbogen, Skill `skript` §5). Falsche Aktenzeichen,
   widersprechende Absätze und Quellenangaben stehen oft nur in den Einblendungen, nicht im Transkript.
3. **Slot 5 ist das Urteil:** ECHT, FAKE oder OFFEN mit einem Satz Begründung, als eigenes Urteil markiert („Mein
   Urteil: …“). Die Quelle steht im Bild. Fremdes Bildmaterial nur als Zitat mit Urheberangabe.
4. **Teilurteile sind erlaubt**, wenn die Behauptung aus mehreren Teilen besteht („Der Magnet: ECHT. Strom ab 2030:
   OFFEN.“).
5. **Belegregeln gelten** (Plugin `recherche`, Skill `belegregeln`): Erwähnt ist nicht beteiligt, ein Verfahren ist kein
   Urteil, Privatpersonen ohne Namen.

## 2. Hinweise aus der Messung (keine Pflicht)

Eigene Messung, n = 248 Shorts aus 63 Kanälen blind bzw. 1.374 automatisch, Methode in
`docs/messungen/hook-studie.md`:

- Dass es eine Auszahlung gibt, trennt (blind: Top 92 %, Unten 78 %); wo sie liegt, trennt nicht (47 % gegen 40 % der
  Dauer). Nur eine Tendenz: Schwache Shorts zahlen öfter schon vor einem Viertel aus (35 % gegen 19 %).
- Ein Satz, der eine neue Lücke öffnet („Und jetzt kommt der Teil, den keiner erwartet.“), hält den Mittelteil
  (automatisch: Top 23 %, Unten 17 %). Die Lage ist frei.
- Jede Zeile bewegt die Geschichte über „aber“ und „deshalb“, nie über „und dann“ (Faustregel, nicht gemessen).
- Die Zahl steht als Schrift im laufenden Bild, nicht auf dem Schnitt (Faustregel).

## 3. Abnahme

```bash
python scripts/skript_pruefen.py F<n>_skript.md --format short     # im Skill skript
```

Jeden Fund lesen und entscheiden; das Urteil hat eine Quelle; jede Zahl gegen die Faktenbasis; einmal laut lesen.
Ablage wie im Skill `skript` (§1).

## 4. Fallen

### F1 · Reaction statt Prüfung
**Symptom:** Der Short wirkt wie ein Kommentar zu einem fremden Video.
**Ursache:** Das Quellvideo ist das Ding.
**Gegenmittel:** Die Behauptung ist das Ding; das Video ist Beleg, frühestens in Slot 3.

### F2 · Urteil ohne Quelle
**Symptom:** „FAKE“ steht im Raum, aber niemand kann nachsehen, warum.
**Ursache:** Das Urteil stützt sich auf Eindruck statt Beleg.
**Gegenmittel:** Je Urteil eine Quelle im Bild und im Belegblatt.

### F3 · Übergangsfloskel und Ausklang im Mund
**Symptom:** „Schauen wir mal …“, „Danke fürs Zuschauen“, „Folg mir“.
**Ursache:** Gewohnheit aus Langformaten.
**Gegenmittel:** Übergänge tragen Information; Aufforderungen auf die Endkarte.

### F4 · „gerade“ ohne Neuigkeit
**Symptom:** Zuschauer merken beim nächsten Video, dass es nicht neu war.
**Ursache:** „gerade“ als Spannungswort.
**Gegenmittel:** Nur bei echter Neuigkeit; sonst streichen.

### F5 · Kausalkette im Hook
**Symptom:** Der erste Satz braucht eine Erklärung.
**Ursache:** Zwei Ideen mit „weil“.
**Gegenmittel:** Die Kette in Slot 4 (Skill `skript` §3).
