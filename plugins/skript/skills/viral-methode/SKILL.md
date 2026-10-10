---
name: viral-methode
description: 'Die Methode hinter viralen Erklär-Shorts, aus einer eigenen, blind gegengeprüften Messung (Top- gegen schwache Shorts desselben Kanals, 63 Kanäle): was trennt, was nicht, der Bauplan in sieben Sätzen, zwei Stufen mit Freigabe durch den Menschen (erst Skript, dann Bau), der Takt im Schnitt, Nachfrage messen, Rückkanal. Nutze diesen Skill bei „viral“, „Short aus einem Link oder Thema“, „was trennt gute von schwachen Shorts“, „Takt“, „wie oft schneiden“, „Themenwahl“, zusammen mit skript und hook.'
---

# Viral-Methode: messen, was trennt, und den Rest dem Menschen lassen

Kein Skript und kein Agent garantiert Reichweite. Diese Methode trifft jedes Merkmal, das gemessen virale von schwachen
Shorts trennt, sagt, welches fehlt, und macht den Rest messbar. Regeln mit eigenem Skill werden hier nur aufgerufen:
Schema und Slots im Skill `skript`, Hook-Regel im Skill `hook`, Sprechstil im Skill `sprechtext`, Urteil
ECHT/FAKE/OFFEN im Skill `skript-short`, Belege im Plugin `recherche`.

## 1. Die zwei Stufen

| Stufe | Was entsteht | Wer sagt Ja |
|---|---|---|
| **1 Skript** | drei Winkel, drei Hooks, Bild-1-Text, Sprechtext nach den sechs Slots, Belegblatt, Prüfung, blinde Nacherzählung; `F<n>_skript.md`, `F<n>_prompter.md`, `F<n>_belege.md` | der Mensch liest und gibt frei oder sagt, was nicht passt (dann F<n+1>) |
| **2 Bau** | Schnittplan je Satz, Drehplan, Liste der Bilder und Einspieler, Karten, Rohschnitt | erst nach dem Ja zu Stufe 1 |

Ohne Freigabe keine Stufe 2, kein Dreh, keine bezahlten Werkzeuge, keine Veröffentlichung. Ein Agent kann Stufe 2 als
Entwurf vorbereiten, gekennzeichnet „gilt erst nach Freigabe“; freigeben kann er nicht.

## 2. Einordnen (eine Minute, ohne Rückfrage)

| Eingang | wird | Rahmen |
|---|---|---|
| Link mit Behauptung | Nachgeprüft-Short | Die Behauptung ist das Ding, das Urteil in Slot 5 |
| Thema | Erklär-Short | sechs Slots, z. B. Mensch gegen Technik |
| Thema, das man selbst nachbauen kann | Nachgebaut | eigene Messung als Beleg |
| ein Wissensding, eine Zahl | Snack 30–45 s | Skill `skript-snack` |

Ein Link, der im eigenen Kanal unter dem Median liegt (Aufrufe geteilt durch den Median des Kanals unter 1), ist ein
Thema, kein Vorbild.

## 3. Der Wissenskern

Eigene Messung: 1.378 Shorts, 63 Kanäle, davon 248 blind gegengeprüft; Top sind die 10 meistgesehenen Shorts eines
Kanals, Unten die 6 am wenigsten gesehenen, die 15 neuesten gestrichen. Methode und Grenzen in
`docs/messungen/hook-studie.md`. Zusammenhänge, keine Ursachen.

### 3.1 Was trennt (jedes Skript sollte jede Zeile treffen)

| Merkmal | Top | Unten | Stand | Was das Skript daraus macht |
|---|---|---|---|---|
| beim ersten Hören verständlich (1–3) | 2,5 | 2,2 | blind gesichert | ein Fremder (Agent `hook-blind`) erzählt Bild-1-Text und die ersten zwei Sätze nach, Note mindestens 2 |
| erkennbarer Hook-Typ | 95 % | 84 % | blind gesichert | Frage mit Ding, Widerspruch, Zeigen, Ding und Tat, Szene |
| Versprechen vorhanden | 92 % | 80 % | blind gesichert | die Frage nach dem Ding-Satz, spätestens bei Sekunde 6 |
| Wendung vorhanden | 65 % | 51 % | blind gesichert | eine Stelle, an der die Erwartung kippt |
| Auszahlung vorhanden | 92 % | 78 % | blind gesichert | der Schluss beantwortet genau die Frage aus dem Hook |
| Sprechbeginn im Median | 0,00 s | 0,04 s | automatisch gesichert | Ton ab Bild 1, kein Vorlauf im Schnitt |
| Kontra-Wort in den ersten 5 s | 18 % | 14 % | automatisch gesichert | aber, doch, nicht, falsch: früh |
| Satz, der eine neue Lücke öffnet | 23 % | 17 % | automatisch gesichert | um die Mitte ein Satz, der eine neue Frage aufmacht |
| kein Ding im ersten Satz | 28 % | 41 % | Tendenz, p = 0,10 | bleibt Regel, weil das Ding den Hook verständlich macht |

**Der Bauplan in sieben Sätzen:**
1. Der erste Satz nennt ein Ding, das man sich vorstellen kann, und was es tut.
2. Der zweite Satz stellt die Frage, die sich jetzt jeder stellt; sie ist das Versprechen.
3. Kontext und erster Beleg folgen bis etwa zu einem Drittel.
4. Eine Wendung kippt die Erwartung.
5. Um die Mitte öffnet ein Satz eine neue Lücke, dann kommt die nächste Stufe.
6. Die Antwort kommt, gern mit einer Alltags-Analogie.
7. Am Ende steht eine Pointe, die Antwort oder eine Frage, kein Abbruch; die Aufforderung steht auf der Endkarte.

### 3.2 Was nicht trennt: nicht darauf optimieren

Zahl im Hook (20 % gegen 20 %) · Du-Ansprache in den ersten 5 s (38 % gegen 37 %) · Sprechtempo (3,26 gegen 3,24
Wörter je Sekunde) · Kausalwort · „Ich“ vorn · Alltags-Analogie (16 % gegen 14 %, bleibt fürs Verstehen) · Frage-Hook
mit Ding (16 % gegen 10 %, nicht schwächer) · Text auf Bild 1 (89 % gegen 86 %: Standard, kein Vorteil). **Eher
schwächer:** Aufforderung am Ende (27 % gegen 39 %, nicht gesichert) · Auszahlung vor einem Viertel der Dauer (Tendenz)
· Frage ohne Ding · Namens-Bauchbinde als Bild 1 (zu wenige Fälle für einen Test). Wo die Beats liegen, trennt nicht;
dass es sie gibt, trennt.

## 4. Stufe 1: vom Link oder Thema zum Skript

1. **Einordnen** (§2), Stoppuhr starten.
2. **Link lesen:** Video laden (nur öffentliche Links, Plattformregeln beachten), transkribieren, Kontaktbogen bauen
   (`ffmpeg -i quelle.mp4 -vf "fps=1,scale=320:-1,tile=6x4" -frames:v 1 bogen.jpg`), Faktor gegen den Kanal-Median
   ausrechnen. Einblendungen tragen oft Fakten, die im Transkript fehlen.
3. **Faktenbasis mit Belegen** (Plugin `recherche`): jede Quelle im Original, Wortlaut übernehmen, aktuelle Zahlen zuerst.
4. **Vorbilder suchen:** drei bis fünf Top-Shorts mit ähnlichem Ding oder Hook-Typ, dazu je Kanal den schwächsten als
   Gegenbeispiel. Das Muster übernehmen, nie die Worte (F4).
5. **Drei Winkel:** je Winkel Rahmen, die eine Frage im Kopf des Zuschauers, die Auszahlung, und zwei Prüffragen: Trifft
   es den Zuschauer selbst? Kann der Sprecher es glaubwürdig sagen? Einer gewinnt, mit Begründung.
6. **Drei Hooks**, jeder nacherzählt; `hook_pruefen.py` (Skill `hook`). Bild-1-Text getrennt: 4–7 Wörter, stumm lesbar.
7. **Sprechtext nach den sechs Slots** (Skill `skript`), drei Lacher-Vorschläge darunter, keiner im Text.
8. **Belegblatt** (Skill `skript` §7).
9. **Prüfen:** `skript_pruefen.py`, `pruefe_sprechtext.py`; jede Zahl gegen das Belegblatt. Fehlt ein gesichertes Merkmal
   aus §3.1, nachbessern oder bewusst verwerfen.
10. **Blinde Nacherzählung:** Agent `hook-blind` bekommt nur den Bild-1-Text und die ersten zwei Sätze. Note unter 2:
    neuer Hook.
11. **Ablegen und zeigen.** Der Mensch gibt frei.

## 5. Der Takt (für Stufe 2)

Faustregeln, abgeleitet aus einer kleinen eigenen Messung (Methode und Grenzen in `docs/messungen/skript-takt.md`):

- **Sprecher-Shorts:** erster Bildwechsel spätestens bei 3 s, danach 20 bis 40 Bildwechsel je Minute; der Sprecher
  alle 4 bis 8 s wieder im Bild. Gemessen waren 12 bis 46 Wechsel je Minute bei zwei Tech-Erklärkanälen (n = 6 Shorts);
  das Band ist eine Ableitung, keine gemessene Grenze.
- **Kamerawechsel nur an Satz- oder Phrasengrenzen**, der Ton aus einer durchgehenden Quelle (Plugin `studio`, Skill
  `zwei-kamera`).
- **Erklär-Reels auf einer Grafikbühne:** Harte Schnitte sind dort das falsche Maß. Gezählt wird der Inhaltswechsel
  (neue Karte, neue große Zahl, neues Diagramm): 16 bis 29 je Minute bei den fünf meistgesehenen Reels eines
  Erklärkanals (n = 5). Keine Strecke über 4 s ohne neues Bild, außer einer gesetzten Pause.
- **Stillstand verteilt messen:** je Kapitel, nicht nur für das ganze Video.

## 6. Nachfrage messen, bevor ein Thema gewählt wird

- **Suchvorschläge** zeigen, was Leute eintippen:
  `https://suggestqueries.google.com/complete/search?client=firefox&hl=de&gl=de&ds=yt&q=<Begriff>`
- **Aufrufe je Thema:** `yt-dlp --flat-playlist --dump-json "ytsearch40:<Begriff>"`, nach `view_count` sortieren.
  Titel kommen teils automatisch übersetzt.
- Das Ergebnis als `recherche/00_nachfrage_<datum>.md` in den Skriptordner, damit das Skript darauf aufbaut.

Suchbegriffe gehen dabei an die jeweiligen Anbieter.

## 7. Rückkanal

Je veröffentlichtem Short eine Zeile: Datum, Plattform, Link, Hook, Prüfergebnis, Aufrufe nach 48 Stunden und nach
7 Tagen, Faktor gegen den eigenen Kanal-Median. Ab etwa 20 eigenen Shorts lohnt dieselbe Methode wie in der
Hook-Studie (Top gegen Unten im eigenen Kanal, blind annotiert). So lernt die Methode aus den eigenen Zahlen.

## 8. Fallen

### F1 · Grüner Test als Alibi
**Symptom:** Alle Prüfungen bestanden, der Mensch lehnt das Skript ab.
**Ursache:** Prüfungen messen Form.
**Gegenmittel:** Ob der Text trägt, entscheidet der Mensch beim Lesen und blind der Agent `hook-blind`.

### F2 · Das Quellvideo als Ding
**Symptom:** Aus Nachgeprüft wird eine Reaction.
**Ursache:** Konto, Likes oder „dieses Video“ im ersten Satz.
**Gegenmittel:** Die Behauptung ist das Ding.

### F3 · Stufe 2 ohne Ja
**Symptom:** Drehzeit für ein Skript, das nicht gewollt ist.
**Ursache:** Bau vor Freigabe.
**Gegenmittel:** Erst Freigabe von Stufe 1, dann Bau.

### F4 · Vorbilder: Muster, nie Worte
**Symptom:** Ein Satz aus einem fremden Short klingt im eigenen Mund nach Kopie.
**Ursache:** Formulierungen statt Muster übernommen.
**Gegenmittel:** Nur Aufbau und Hook-Typ übernehmen. Wortgetreues Übersetzen und Nachsprechen fremder Texte ist eine
Bearbeitung und braucht die Erlaubnis des Urhebers (in Deutschland §§ 3, 23 UrhG).

### F5 · Clean Room reicht nicht
**Symptom:** Ein eigenes Skript im Format eines fremden Kanals landet trotzdem nah am Vorbild.
**Ursache:** Wer dasselbe Thema in derselben Länge erklärt, greift zu denselben Gattungssätzen und Bildmitteln, auch
ohne das Vorbild gesehen zu haben.
**Gegenmittel:** Nach Stufe 1 ein frischer Abstand-Prüfer mit dem Transkript des Vorbilds und dem eigenen Prompter samt
Bildplan; der Schreib-Agent bekommt nur dessen Ersatzsätze, nie die fremden Zitate.

### F6 · Das Beispiel wird zur Formel
**Symptom:** Mehrere Schreib-Agenten benutzen dieselbe Wendung, die in einer Tabelle als Beispiel stand.
**Ursache:** Agenten übernehmen Beispiele wörtlich.
**Gegenmittel:** Beispiele variieren und gesperrte Formeln ausdrücklich nennen; vor der Abgabe nach ihnen suchen.

### F7 · Ein Beat fehlt
**Symptom:** Guter Hook, schwacher Short.
**Ursache:** Versprechen oder Auszahlung fehlen (blind: ohne Versprechen 20 % der schwachen gegen 8 % der Top-Shorts).
**Gegenmittel:** Jede Zeile aus §3.1 prüfen.

### F8 · Zwei Sitzungen im selben Ordner
**Symptom:** Dateien überschreiben sich, Fassungsnummern springen.
**Ursache:** Zwei Agenten arbeiten parallel am selben Video.
**Gegenmittel:** Vor dem Start prüfen, wer noch arbeitet; je Video ein Ordner und eine schreibende Sitzung.
