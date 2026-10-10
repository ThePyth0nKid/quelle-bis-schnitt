---
name: hook
description: 'Schreibt und prüft den Hook, also den ersten gesprochenen Satz und den Text auf Bild 1, für Shorts, Snacks, Trailer und Langvideos. Erste Regel: beim ersten Hören verständlich, mit einem Ding, das man sich vorstellen kann, und was es tut; das Ding ist das Phänomen, nie das Quellvideo. Gestützt auf eine eigene, blind gegengeprüfte Messung an 63 Kanälen. Prüfskript scripts/hook_pruefen.py mit einstellbaren Regeln statt Punktwert. Nutze diesen Skill bei „Hook“, „erster Satz“, „Titel“, „Bild 1“, „Thumbnail-Text“, „Anfang“.'
---

# Hook: ein Ding, beim ersten Hören verstanden

Verwandt: `skript` (Schema, Klammer), `sprechtext` (ganze Sätze), `anti-slop-writing` (Vokabular), Agent `hook-blind`
(blinde Nacherzählung).

Alle Prozentzahlen hier: eigene Messung, Top-Shorts gegen schwache Shorts desselben Kanals, n = 248 Shorts aus 63
Kanälen blind bzw. 1.374 automatisch, Methode und Grenzen in `docs/messungen/hook-studie.md`. Es sind Zusammenhänge,
keine Ursachen.

## 1. Die Regel, die zählt

1. **Beim ersten Hören klar.** Blind bestätigt: Top-Hooks sind verständlicher (2,5 gegen 2,2 auf einer Skala bis 3,
   30 : 11 Kanäle), schwache Shorts haben dreimal so oft gar keinen erkennbaren Hook (16 % gegen 5 %). Test: Ein
   Fremder erzählt den Hook in einem Satz einem Freund nach, und es ergibt Sinn. „Eine Idee“ ist der Weg dahin; als
   eigener Messwert hielt sie blind nicht (96 % gegen 93 %).
2. **Ein Ding im ersten Satz, das man sich vorstellen kann, und was es tut.** Blind eine Tendenz: Ohne Ding beginnen
   41 % der schwachen und 28 % der Top-Shorts (24 : 13 Kanäle, p = 0,10). Es bleibt Regel, weil das Ding den Hook
   verständlich macht.
3. **Keine Kausalkette.** Zwei Ideen mit „weil“ verbunden brauchen Zwischenschritte. Das ist eine Verständnis-Regel,
   kein Reichweiten-Befund (Kausalwort in den ersten 3 s: 7 % gegen 8 %). Ob es noch eine Idee ist, entscheidet der
   Nacherzähl-Test.
4. **Das Ding ist das Phänomen:** die Zahl, das Urteil oder die Behauptung, wie sie kursiert. Nie das Quellvideo mit
   Konto und Likes.
5. **Eine Frage trägt, wenn ein Ding darin steckt.** Frage-Hooks mit Ding sind blind nicht schwächer (16 % gegen 10 %,
   nicht gesichert). Gute Form: erst der Satz mit dem Ding, dann die Frage, die sich jeder stellt; der Schluss
   beantwortet sie (Skill `skript`, die Klammer).
6. **Drei Kandidaten, jeder einmal nacherzählt, der verständlichste gewinnt.**

## 2. Was hilft, was nicht

| Merkmal im Hook | Top gegen Unten | Umgang |
|---|---|---|
| Ding im ersten Satz, mit Tat | blind: ohne Ding 28 % gegen 41 %, p = 0,10 | Regel; blind eine Tendenz |
| kein Anlauf, Sprechen ab Bild 1 | automatisch: Sprechbeginn Median 0,00 s gegen 0,04 s | Pflicht |
| Kontra-Wort in den ersten 5 s (aber, doch, nicht, falsch) | automatisch: 18 % gegen 14 %, gesichert | früh einbauen |
| Frage mit Ding | blind: 16 % gegen 10 %, nicht gesichert | erlaubt |
| „Dieses“ oder „Das hier“ vorn | automatisch: 12 % gegen 8 %, p = 0,09 | Tendenz |
| Zahl in den ersten 3 s | 20 % gegen 20 % | Werkzeug, kein Muss |
| Du in den ersten 5 s | 38 % gegen 37 % | Stil, kein Hebel |
| Ich oder Wir als erstes Wort | 10 % gegen 7 % | nur mit Tat und Ding im selben Satz |
| Kausalwort | 7 % gegen 8 %; echte Kette blind 2 % gegen 2 % | Hinweis; der Nacherzähl-Test entscheidet |
| „gerade“ oder „neu“ | 20 % gegen 18 % | nur bei echter Neuigkeit |

> **[Ding] + [Tat]**, ohne Anlauf und beim ersten Hören klar; dazu ein Widerspruch oder eine Frage mit Ding; die Zahl,
> wenn sie das Ding größer macht.

**Paare aus der Messung** (bester gegen schwächsten Short im selben Kanal, als Beispiel, nicht als Beweis):

| Oben | Unten | Was unten fehlt |
|---|---|---|
| „Das Pantheon ist einfach mal die größte unverstärkte Betonkuppel, die je gebaut wurde.“ (BreakingLab) | „Okay, diese fünf Bücher, die machen dich garantiert schlauer.“ | Liste statt Ding |
| „What would happen if you dug a hole straight through the Earth and then jumped in?“ (Cleo Abram) | „Okay, I just found another amazing patent …“ | Anlauf vor dem Ding |
| „USB-C was supposed to save us from the every-device-uses-a-different-cable problem.“ (Johnny Harris) | „Shut up, it is not.“ | kein Ding |

## 3. Bild 1

Text steht auf fast jedem ersten Bild (89 % oben, 86 % unten, nicht blind): ohne Text fällt man auf, mit Text gewinnt
man nichts. Das Ding in Aktion auf Bild 1 ist nicht gesichert (19 % gegen 13 %). Bild, Text und erster Satz sagen
dasselbe. Bild-1-Text: 4–7 Wörter, stumm lesbar, als Frage oder Widerspruch, kein Logo, keine Namens-Bauchbinde.

## 4. Prüfskript

```bash
python scripts/hook_pruefen.py "<Satz 1> <Satz 2>" [--titel "<Bild 1>"] [--neu]
python scripts/hook_pruefen.py "<…>" --streng                   # harte Punkte sperren
python scripts/hook_pruefen.py "<…>" --regel du-vorn=aus --json
python scripts/hook_pruefen.py --liste
```

Kein Punktwert. Harte Punkte (mit `--streng` sperrend, sonst Hinweis): `anlauf-vorn`, `quellvideo-vorn`, `bannwort`,
`gerade-ohne-neuigkeit` (ohne `--neu`). Hinweise: `ichwir-vorn`, `kausal-vorn`, `ding-vorn`, `erster-satz-lang`,
`frage-vorn`, `du-vorn`, `bild1-text`. Stufen und Regeldatei wie im Skill `skript` (§6). Den Nacherzähl-Test macht
kein Skript: dafür der Agent `hook-blind`. Der Mensch entscheidet je Fund.

## 5. Fallen

### F1 · Kein Ding
**Symptom:** Der Fremde kann nicht sagen, worum es geht.
**Ursache:** Anweisung ohne Ziel („Halt die Hände eng zusammen“), Stimmung, Fachjargon, Eigenwerbung.
**Gegenmittel:** Den Gegenstand beim Namen nennen und sagen, was er tut.

### F2 · Vorwissen nötig
**Symptom:** Einstieg mitten im Gespräch, unbekannte Namen, Schulbuch-Anfang („Wir befinden uns im Jahr 1964 …“).
**Ursache:** Der Hook setzt voraus, was erst das Video erklärt.
**Gegenmittel:** So schreiben, dass ein Fremder ohne Titel und ohne Kanal versteht.

### F3 · Die Zahl als Etikett
**Symptom:** „5,8 TB. Musterhafen. Datenleck.“
**Ursache:** Zahl und Ding stehen ohne Satz nebeneinander.
**Gegenmittel:** Die Zahl in einen ganzen Satz mit Verb.

### F4 · Die Angst-Frage statt der Szene
**Symptom:** „Nimmt uns die KI die Jobs weg?“ erzeugt kein Bild im Kopf.
**Ursache:** Gesellschaftsthemen verführen zum abstrakten Hook ohne Ding.
**Gegenmittel:** Den Hook mit einer Szene beginnen (eine Baustelle, ein Hafen, ein Brief), in der etwas passiert; die
Gesellschaftsfrage kommt als Wendung. Ein beobachtetes Muster in Einzelfällen, nicht blind geprüft und ohne Zahl.

### F5 · Wörter ohne Bezug
**Symptom:** Der Fremde fragt „was ist es?“, „welcher Plan?“.
**Ursache:** „es“, „dieser Plan“, „dagegen“, „die von damals“ zeigen auf etwas, das er nicht kennt; dazu Sätze, die man
umdrehen muss.
**Gegenmittel:** Das Ding beim Namen nennen, Menge und Zeitraum sagen, die Auswahl in den Satz holen.

### F6 · Nachbessern verschiebt die Zählung
**Symptom:** Nach dem Präzisieren rutscht das Versprechen hinter Sekunde 6, der Bild-1-Text hat 8 statt 7 Wörter.
**Ursache:** Jeder geschärfte Hook wird länger.
**Gegenmittel:** Nach jeder Änderung neu zählen und neu prüfen.

### F7 · Ein Zitat in Ich-Form auf Bild 1
**Symptom:** Der Fremde hält das Zitat für die Aussage des Sprechers.
**Ursache:** „ICH HABE KEINE ZEIT“ auf Bild 1 ohne Urheber.
**Gegenmittel:** Zitate auf Bild 1 mit Urheber („Bürgermeisterin 2016: …“) oder in der dritten Person.

### F8 · Doppeldeutige Wörter
**Symptom:** „Ihre Stimme für 150 Euro“ klingt nach Wahlstimme statt nach Stimmklon.
**Ursache:** Ein Wort mit zwei Bedeutungen im Hook.
**Gegenmittel:** Eindeutig benennen („KI-Kopie ihrer Stimme“).

### F9 · Die Behauptung im Hook muss für jeden genannten Fall stimmen
**Symptom:** Ein Hook nennt zwei Beispiele, der Beleg trägt nur eines.
**Ursache:** Beim Zuspitzen wird verallgemeinert.
**Gegenmittel:** Nur den belegten Fall in den Hook. Verspricht der Hook ein Dokument, muss es genau diesen Satz tragen.

### F10 · Bild-1-Text und erster Satz widersprechen sich
**Symptom:** „Der Satz, den keiner kennt“ steht über dem bekanntesten Satz des Themas.
**Ursache:** Bild und Ton wurden getrennt geschrieben.
**Gegenmittel:** Beide zusammen blind prüfen lassen (`hook-blind` bekommt beides).

### F11 · Grüner Test als Alibi
**Symptom:** Das Skript meldet nichts, der Hook ist trotzdem unverständlich.
**Ursache:** Das Skript sieht nur Wörter, kein Verständnis.
**Gegenmittel:** Immer den Nacherzähl-Test; Note unter 2 heißt: neuer Hook.
