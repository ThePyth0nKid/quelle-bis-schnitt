---
name: sprechtext
description: 'Schreibt gesprochene deutsche Sätze für Shorts, Erklärvideos, Prompter-Texte und Voice-over: ganze Sätze mit Verb, Anschlusswörter, Einwand und Antwort, Frage und Antwort, Zeigen statt Behaupten, kein Telegrammstil, kein vergessenes Wort. Enthält die Vollständigkeitsprobe scripts/pruefe_sprechtext.py (Sätze ohne Verb, Doppelpunkt-Telegramme, Beat-Häufung, Zeitbudget je Kapitel) mit einstellbaren Regeln. Nutze diesen Skill, wenn Text in einen Teleprompter, ein Sprechskript, eine Sprechregie oder ein Voice-over geht, zusammen mit anti-slop-writing (Vokabular).'
---

# Sprechtext: Sätze, die ein Mensch sagt

**Der Fehler, den dieser Skill verhindert:** Ein Skript, das nach Schreibregeln gekürzt wurde, rutscht ins Telegramm.
„Gemessen 1997.“ „Masse unter null.“ „Die Menge: eine Bergmasse. Negativ.“ Beim Vorlesen fehlen die Wörter, und der
Sprecher ergänzt sie selbst („also ein Tunnel“, „doch die Physik“). Gesprochen braucht jeder Satz ein Verb.

`anti-slop-writing` bleibt für das Vokabular (keine Floskeln, keine Bedeutungs-Behaupter). Zwei Schreibregeln von dort
gelten gesprochen umgekehrt: Fragmente sind die Ausnahme, und Antithesen-Staccato („Kein Abo. Keine Werbung.“) ist
kein Stil.

## 1. Das gemessene Muster

Wie ein erfolgreicher englischsprachiger Tech-Erklärer seine Sätze baut (eigene Messung, n = 5 Shorts, rund 1.350
Wörter, Methode in `docs/messungen/skript-sprechmuster.md`):

| Wert | gemessen | Was das heißt |
|---|---|---|
| Wörter je Satz | Mittel 9, Standardabweichung 6,6, von 1 bis 40 | kurze und lange Sätze wechseln |
| Sätze mit höchstens 3 Wörtern | etwa 1 von 6 | Beats, immer nach einem ganzen Satz |
| Satzanfang mit Anschlusswort | etwa 1 von 4,5 | Und, Aber, Also, Jetzt tragen den Zuhörer |
| Fragen | etwa 1 von 10 Sätzen | jede wird im nächsten Satz beantwortet |
| Anrede „du“ | etwa alle 12 Wörter | der Zuschauer ist die Hauptperson |
| „ich“ | etwa alle 15 Wörter | der Sprecher ist die zweite Person, mit Meinung |

Ein Kanal, fünf Videos: Das beschreibt einen Stil, keine Norm.

## 2. Acht Bausteine

1. **Behauptung mit Verb.** „Das Schloss im Browser verrät trotzdem, welche Seiten du besuchst.“
2. **Einwand, dann Antwort.** „Jetzt denkst du vielleicht: Und was ist mit dem sicheren Modus? Guter Gedanke, aber guck
   dir das Protokoll an.“
3. **Frage, sofort beantwortet.** „Was kannst du also tun? Ein Kabel ziehen.“
4. **Zeigen statt behaupten.** „Guck dir den Ring an.“ „Hier siehst du …“ (nur, wenn dazu ein Bild läuft).
5. **Meinung als Einschub.** „Das finde ich beunruhigend.“
6. **Kleine Geschichte im Präsens.** „Heute früh stehe ich an der Haltestelle, und die Anzeige springt auf null.“
7. **Kontrast als ganzer Satz.** „Viele glauben, die Bahn bremst langsamer als ein Auto. Aber sie hat einen Trick.“
8. **Der Beat.** Ein bis drei Wörter, nur als Reaktion auf den Satz davor: „Weg.“ „Nicht diese.“ Höchstens einer je
   fünf Sätze.

## 3. Zehn Regeln

1. **Jeder Satz hat ein Subjekt und ein gebeugtes Verb.** „Gemessen 1997.“ → „Das hat das Wetteramt 1997 gemessen.“
2. **Kein Doppelpunkt-Telegramm.** „Die Menge: eine Bergmasse.“ → „Dafür brauchst du eine ganze Bergmasse.“
3. **Anschlusswörter am Satzanfang sind erwünscht:** Und, Aber, Also, Jetzt, Dann, Denn, Dafür, Trotzdem. Geschrieben
   wären sie Füllstoff, gesprochen sind sie Rhythmus.
4. **Du und ich.** „Du brauchst dafür …“, „Ich hab's nachgeprüft.“ Nie „man“, nie „die Nutzer“.
5. **Ein Einwand je Video:** „Jetzt denkst du vielleicht: …“ und die Antwort im nächsten Satz.
6. **Höchstens eine Frage je Kapitel,** und der nächste Satz beantwortet sie.
7. **Zeigen:** „Guck dir … an“, „Hier siehst du …“, wenn ein Bild dazu läuft. Nicht als Formel in jedem Absatz.
8. **Beats sparsam:** höchstens einer je fünf Sätze, nie zwei hintereinander, nie als Kapitelanfang.
9. **Zahlen im Satz, nicht als Etikett.** „1988 halten zwei Physiker den Tunnel offen“, nicht „Physiker 1988“. Große
   Zahlen als Vergleich: „so viel, wie in einen ganzen Stausee passt“.
10. **Laut lesen.** Wo die Zunge stolpert (Konsonantenhaufen, drei Nebensätze), umbauen. Die Wörter, die der Sprecher
    beim Lesen selbst einfügt, gehören ins Skript; die Wörter, die er verschluckt, fliegen raus.

## 4. Vorher und nachher

| Telegramm (falsch) | Gesprochen (richtig) |
|---|---|
| 1935 rechnen zwei Physiker aus: Die Raumzeit darf ABKÜRZUNGEN haben. · Ein Tunnel zwischen zwei Orten. | 1935 rechnen zwei Physiker aus, dass die Raumzeit Abkürzungen haben darf, also einen Tunnel zwischen zwei Orten. |
| Dafür braucht die Röhre eine Füllung mit NEGATIVER Energie. · Masse unter NULL. | Dafür brauchst du eine Füllung aus negativer Energie. Das ist Masse, die weniger wiegt als gar nichts. |
| Zwei Metallplatten, ein tausendstel MILLIMETER Abstand, dazwischen zieht das Vakuum. | Nimm zwei Metallplatten, ein tausendstel Millimeter auseinander, und das Vakuum zieht sie zusammen. |

## 5. Ablauf

1. **Kapitel = Take.** Gibt es Zeitmarken für die Bilder (z. B. aus einem Schnittplan), ist das Wortbudget je Kapitel
   `(Marke des nächsten Kapitels − Marke dieses Kapitels) × Tempo`.
2. **Schreiben** nach den zehn Regeln und acht Bausteinen.
3. **Vollständigkeitsprobe** (Pfad relativ zu diesem Skill-Ordner):
   ```bash
   python scripts/pruefe_sprechtext.py prompter.md --ziel 75 [--tempo 2.6] [--budget kapitel.json]
   python scripts/pruefe_sprechtext.py prompter.md --regel ohne-verb=sperrt
   python scripts/pruefe_sprechtext.py --liste
   ```
   Regeln: `ohne-verb`, `doppelpunkt-ende`, `beats-hintereinander`, `kapitel-beginnt-mit-beat`, `beat-haeufung`,
   `ueber-budget`, `gesamtlaenge`. Jede steht auf `aus`, `hinweis` (Standard) oder `sperrt`; eine gemeinsame
   Regeldatei wie im Skill `skript` (§6) geht auch. Für einen Short `--ziel 75`, für einen Snack `--ziel 45`.
   Die Verb-Erkennung arbeitet mit Wortstämmen, nicht mit einem Wörterbuch: Sie ist eine Warnlampe. Großgeschriebene
   Wörter mitten im Satz gelten als Substantiv („Die Kosten.“ wird gemeldet), „'s“ fällt weg („Wie läuft's?“ nicht).
   Zeilen mit `#`, `⏱` oder `▶` zählen nicht, und ein Block nur aus solchen Zeilen ist kein Kapitel; das Budget hängt
   an der Kapitelnummer. Eine leere Datei ist ein Fehler (Exit-Code 2). Jede Meldung von Hand lesen und entscheiden.
4. **Laut lesen** (Regel 10), dann `anti-slop-writing` fürs Vokabular.
5. **In den Prompter nur den Sprechtext.** Regie gehört auf eine eigene Seite (Skill `prompter` im Plugin `studio`).

## 6. Fallen

### F1 · Schreibregeln zerlegen Sprechtext
**Symptom:** Der Sprecher stolpert und ergänzt beim Lesen Wörter.
**Ursache:** „Fragmente sind erlaubt“ aus Schreib-Regelwerken wurde auf gesprochenen Text angewandt.
**Gegenmittel:** Gesprochen gilt Regel 1; Fragmente nur als Beat (Regel 8).

### F2 · Großbuchstaben als Betonung
**Symptom:** Der Sprecher bricht an den groß geschriebenen Wörtern ab.
**Ursache:** Zu viele Betonungen in einem Satz.
**Gegenmittel:** Höchstens zwei betonte Wörter je Satz.

### F3 · Der Mittelpunkt
**Symptom:** „ · “ wird als Satzende gelesen, obwohl der Satz weitergeht.
**Ursache:** Der Punkt in der Mitte ist eine Pause.
**Gegenmittel:** Vor und nach „ · “ steht je ein ganzer Satz.

### F4 · Namen im Bild, aber nicht im Ton
**Symptom:** Auf einer Tafel stehen Namen, die nie gesagt werden.
**Ursache:** Bild und Text getrennt geschrieben.
**Gegenmittel:** Was im Bild steht, kommt im Ton vor, und umgekehrt.

### F5 · Software heißt nicht „Maschine“
**Symptom:** Zuschauer stellen sich ein physisches Gerät vor, wo ein Rechenverfahren gemeint ist.
**Ursache:** „Maschine“ klingt nach Metall.
**Gegenmittel:** Für Rechenverfahren „Algorithmus“, „Programm“ oder „Software“ sagen und die Grammatik mitziehen. Eine
Kamera oder ein Roboter bleibt ein Ding.

### F6 · Vager Abo-Aufruf
**Symptom:** „Wenn dir das hilft, abonnier …“ verpufft.
**Ursache:** Der Satz nennt keinen Nutzen.
**Gegenmittel:** Sagen, was man davon hat: „Wenn du solche Zahlen künftig selbst prüfen willst, abonnier den Kanal.“

### F7 · Satzzeichen im Eigennamen
**Symptom:** Der Prompter zerlegt einen Satz in zwei Abschnitte.
**Ursache:** Ein „!“ oder „?“ im Namen eines Vereins oder Produkts gilt als Satzende.
**Gegenmittel:** Im Sprechtext den Namen ohne das Zeichen schreiben, im Bild mit. Die Probe meldet so eine Stelle oft als
Satz ohne Verb.
