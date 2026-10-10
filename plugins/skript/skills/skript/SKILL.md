---
name: skript
description: 'Das Schema für gesprochene Erklärvideos: sechs Slots auf einer Seite, eine Hook-Regel (ein Ding, beim ersten Hören verständlich), die Klammer aus Frage und Antwort, die erste Fassung in höchstens 15 Minuten, jede Fassung als eigene Datei mit Belegblatt. Dazu das Prüfskript scripts/skript_pruefen.py, dessen Regeln einzeln auf aus, hinweis oder sperrt stehen; der Mensch entscheidet je Fund. Nutze diesen Skill, wenn ein Sprechtext, Skript, Short, Snack, Trailer oder Langvideo geschrieben oder umgeschrieben wird, bei „Skript“, „Sprechtext“, „Prompter-Text“, „neue Fassung“. Unter-Skills je Format: skript-snack, skript-short, skript-trailer, skript-lang.'
---

# Skript: ein Schema, schnell statt perfekt

Dieser Skill beschreibt, wie ein gesprochenes Erklärvideo entsteht: ein Schema mit sechs Slots, eine Hook-Regel, ein
Belegblatt und eine schnelle erste Fassung, die ein Mensch liest und beurteilt. Das Prüfskript berät. Ob der Text
trägt, entscheidet der Mensch beim Lesen und beim lauten Sprechen.

Verwandt: `hook` (erster Satz, Bild 1), `sprechtext` (ganze, sprechbare Sätze), `anti-slop-writing` (Vokabular),
`viral-methode` (was messbar trennt), die Format-Skills `skript-snack`, `skript-short`, `skript-trailer`, `skript-lang`
und aus dem Plugin `recherche` die Skills `belegregeln` und `recherche-runde`.

## 1. Ablage: jede Fassung eine Datei

Jede Fassung kommt, sobald sie existiert, als eigene Datei in einen Ordner je Video:

```
<skriptordner>/<JJJJ-MM-TT>_<format>-<kurzname>/
  F1_skript.md      ganzes Skript (Vorlage §7)
  F1_prompter.md    nur der Sprechtext, Slot für Slot mit Leerzeile
  F1_belege.md      Belegblatt (Vorlage §7)
  LIESMICH.md       eine Zeile je Fassung: Datum, was sich geändert hat, Prüfstand, Status
```

Nie eine vorhandene F-Datei überschreiben; jede Änderung ist F<n+1>. So bleibt nachvollziehbar, welche Fassung der
Mensch gesehen und freigegeben hat. Die erste Zeile des Skripts ist der Name im Prompter und bleibt über alle
Fassungen gleich (Skill `prompter` im Plugin `studio`).

## 2. Das Schema: sechs Slots

Standard ist der Short mit 60–75 Sekunden, also 160–195 Wörter bei 2,6 Wörtern je Sekunde. Das Tempo ist ein
Faustwert; miss dein eigenes (Wörter des Prompters geteilt durch die Sekunden einer Aufnahme).

| Slot | Sekunde | Wörter | Inhalt |
|---|---|---|---|
| 1 Hook | 0–5 | ~15 | Ein Ding, das man sich vorstellen kann, und was es tut; beim ersten Hören verständlich (§3). Dann die Frage, die sich jetzt jeder stellt. |
| 2 Absender | 5–7 | ~5 | Wer spricht und warum er es weiß („Ich hab's nachgerechnet.“). Die Frage aus dem Hook ist schon das Versprechen. |
| 3 Bekanntes | 10–25 | ~35 | Der Staun-Fakt aus dem Alltag des Zuschauers: Zahl, Quelle im Satz, eine Alltags-Analogie. |
| 4 Das Ding | 25–50 | ~60 | Was ist es, warum ist es so, wie funktioniert es. Drei bis fünf zusammenhängende Sätze mit „deshalb“ und „aber“, ein oder zwei Analogien. Hier sitzen meist die Wendung und der Satz, der eine neue Lücke öffnet. |
| 5 Auszahlung | 50–62 | ~30 | Der Satz, der beides zusammenbringt. Steht eine Behauptung im Raum: ein Urteil mit Begründung (Skill `skript-short`). |
| 6 Schluss | 55–70 | ~30 | Die Frage aus dem Hook noch einmal, jetzt mit der klaren Antwort. Der letzte Satz ist Auszahlung oder Pointe, keine Aufforderung. |

**Beispiel für Slot 1 und 2** (erfunden): „Diese Straßenbahn in Musterhafen hält aus 50 Kilometern pro Stunde nach
20 Metern. Doch bremst dein Fuß im Auto wirklich schneller als sie? Ich hab's nachgerechnet.“

**Die Klammer:** Der Hook stellt eine Frage, der Schluss stellt sie noch einmal und beantwortet sie. Der Zuschauer geht
schlauer heraus, als er hereingekommen ist.

**Zusammenhänge statt Regeln:** Das Bekannte ist das Vorwissen, das Ding ist die Lücke, die Analogie ist die Brücke.
Bekanntes zuerst, wenn der Zuschauer über sich selbst staunen soll; das Ding zuerst, wenn es selbst der Schock ist.

**Rahmen:** Ein bewährter Rahmen ist „Mensch gegen Technik“ (der eigene Körper gegen ein Technik-Ding). Er ist bei
großen Kanälen selten (eigene Messung: 10 von 249 Top-Shorts, Methode in `docs/messungen/hook-studie.md`), also frei;
ob er besser läuft, ist ungetestet. Andere Rahmen gehen genauso, etwa Nachgeprüft (eine Behauptung prüfen) oder
Nachgebaut (selbst ausprobieren). Die Slots 1, 2, 5 und 6 bleiben in jedem Rahmen.

**Was gemessen ist:** Die sechs Slots decken jeden Beat ab, der in einer blinden Gegenprobe virale von schwachen Shorts
desselben Kanals trennt: Versprechen (Top 92 % gegen Unten 80 %), Wendung (65 % gegen 51 %) und Auszahlung (92 % gegen
78 %). Wo die Beats liegen, trennt nicht. Automatisch gemessen kommen dazu: Sprechen ab dem ersten Bild, ein
Kontra-Wort vorn, ein Satz mit neuer Lücke um die Mitte (eigene Messung, n = 248 Shorts aus 63 Kanälen blind bzw.
1.374 automatisch, Methode in `docs/messungen/hook-studie.md`). Das sind Zusammenhänge, keine Ursachen.

## 3. Die Hook-Regel

1. **Beim ersten Hören verständlich, eine Idee.** Test: Ein Fremder erzählt den Hook in einem Satz einem Freund nach,
   und es ergibt Sinn. Blind gemessen sind Top-Hooks verständlicher (2,5 gegen 2,2 auf einer Skala bis 3), und schwache
   Shorts haben dreimal so oft gar keinen erkennbaren Hook (16 % gegen 5 %).
2. **Ein Ding im ersten Satz, und was es tut.** Blind ist das eine Tendenz: Ohne Ding beginnen 41 % der schwachen und
   28 % der Top-Shorts (p = 0,10). Es bleibt Regel, weil das Ding den Hook verständlich macht. Kein Gruß, kein Anlauf,
   kein Name, den man erst kennen muss.
3. **Keine Kausalkette im ersten Satz.** Zwei Ideen, mit „weil“ verbunden, brauchen Zwischenschritte. Die Kette gehört
   in Slot 4. Das ist eine Verständnis-Regel, kein Reichweiten-Befund (Kausalwort vorn: 7 % gegen 8 %).
4. **Das Ding ist das Phänomen:** die Zahl, das Urteil oder die Behauptung, wie sie kursiert. Nie das Quellvideo mit
   Konto und Likes, sonst klingt es nach Reaction.
5. **Die Frage kommt nach dem Satz mit dem Ding,** nicht an seiner Stelle. Eine Frage ohne Ding fällt durch.
6. **Zahl, Zeigewort, Ich sind Werkzeuge.** Die Zahl hilft, wenn sie das Ding größer macht, trennt aber nicht (20 %
   gegen 20 %). „Ich“ vorn nur mit Tat und Ding im selben Satz. „gerade“ nur bei echter Neuigkeit.
7. **Drei Kandidaten, jeder einmal nacherzählt, der verständlichste gewinnt.** Keine zehn. Werkzeug: Skill `hook` und
   der Agent `hook-blind`.

Alle Zahlen in §3: eigene Messung, n = 248 Shorts aus 63 Kanälen, blind, Methode in `docs/messungen/hook-studie.md`.

## 4. Was immer gilt

- **Belege, die du verteidigen kannst.** Jede Fassung bekommt ein Belegblatt (§7). Je Behauptung: was gesagt wird, wer
  es sagt, wo (vollständiger Link), wann, der wörtliche Satz aus der Quelle, die Rechnung, wie sicher, und ein Satz
  „Wenn dich jemand fragt“. Zitate aus Filmen und Videos am Ton prüfen, nicht an Fan-Transkripten. Was sich nicht
  belegen lässt, fliegt raus oder heißt im Text ausdrücklich Schätzung oder Meinung (Skill `belegregeln`).
- **Aktuelle Zahlen.** Erst den neuesten Stand suchen. Zahlen zu Technik, Markt und Plattformen sollten höchstens
  12 Monate alt sein; Grundlagen dürfen älter sein, dann mit aktueller Bestätigung daneben.
- **Du-Ansprache**, der Absender in Satz 2 oder 3. Das ist Stil, kein Reichweiten-Hebel (Du in den ersten 5 s: 38 %
  gegen 37 %, eigene Messung wie oben).
- **Analogien aus dem Alltag**, die jeder richtig einschätzt (Kühlschrankmagnet, Glühbirne, Linienbus). Sie tragen das
  Verstehen; für die Reichweite ist ihr Effekt nicht gesichert (16 % gegen 14 %).
- **Lacher optional:** drei Vorschläge unter dem Skript, der Mensch nimmt einen, keinen oder improvisiert.
- **Sprache:** kein Gedankenstrich, keine Floskel, keine Wörter der Bann-Liste (Skill `anti-slop-writing`).
- **Die Aufforderung steht auf der Endkarte, nicht im Mund.** Blind gemessen enden schwache Shorts öfter mit einer
  Aufforderung (39 % gegen 27 %, nicht gesichert).

## 5. Der Ablauf: erste Fassung in höchstens 15 Minuten

1. **Faktenbasis mit Belegen:** vorhandene lesen oder kurz recherchieren (Plugin `recherche`). Jede Quelle im Original
   öffnen, den wörtlichen Satz kopieren. Offene Zahlen heißen „[prüfen]“ und gehen nicht in den Dreh.
2. **Quellvideo, falls es eins gibt,** Bild für Bild ansehen, bevor der Hook entsteht. Einblendungen tragen oft Fakten,
   die im Transkript fehlen: `ffmpeg -i quelle.mp4 -vf "fps=1,scale=320:-1,tile=6x4" -frames:v 1 bogen.jpg`
3. **Drei Hooks**, Nacherzähl-Test, einer gewinnt.
4. **Skript nach den sechs Slots**, direkt in der Hauptsitzung. Ein eigener Schreib-Agent lohnt nur, wenn mehrere Skripte
   parallel entstehen.
5. **Selbstcheck, zwei Minuten** (Pfade relativ zum jeweiligen Skill-Ordner):
   ```bash
   python scripts/skript_pruefen.py F1_skript.md --format short          # Skill skript
   python scripts/pruefe_sprechtext.py F1_prompter.md --ziel 75          # Skill sprechtext
   ```
   Dann jede Zahl gegen die Faktenbasis und einmal laut lesen.
6. **Ablegen und zeigen:** `F<n>_skript.md`, `F<n>_prompter.md`, `F<n>_belege.md` in den Ordner (§1), dann dem Menschen
   zeigen. Er sagt, was nicht passt; die nächste Fassung ist F<n+1>. Lieber schnell zeigen als lange prüfen.
7. **Kritiker** (Agent `skript-kritiker`) nur, wenn der Mensch einen will.

## 6. Das Prüfskript: Regeln, Stufen, Entscheidung

```bash
python scripts/skript_pruefen.py F1_skript.md --format snack|short|trailer|lang
python scripts/skript_pruefen.py F1_skript.md --format short --streng           # die fünf harten Punkte sperren
python scripts/skript_pruefen.py F1_skript.md --format short --regel du-dichte=aus --regel laenge=sperrt
python scripts/skript_pruefen.py F1_skript.md --format short --regeln meine-regeln.toml --json
python scripts/skript_pruefen.py --liste                                          # alle Regeln mit Stufe
```

Jede Regel steht auf `aus` (nicht prüfen), `hinweis` (melden, **Standard**) oder `sperrt` (melden, Exit-Code 1).
Das Skript gibt nichts frei und verwirft nichts. Für jeden Fund entscheidet der Mensch: **übernehmen, verwerfen oder
anders**. Wer eine Regel dauerhaft anders will, legt eine Regeldatei an:

```toml
# meine-regeln.toml (gilt auch für hook_pruefen.py und pruefe_sprechtext.py)
[regeln]
bannwort = "sperrt"
du-dichte = "aus"        # z. B. bei einem Sie-Format

[bann]
zusaetzlich = ["Gamechanger"]
erlaubt = ["spannend"]
```

**Die fünf harten Punkte** (mit `--streng` sperrend, sonst Hinweis):

| Punkt | Regeln |
|---|---|
| 1 Erster Satz | `anlauf-vorn` (kein Gruß, kein „Heute zeige ich …“), `quellvideo-vorn` (kein Reel, Video, Likes …) |
| 2 Belege | `zahlentabelle` (Zahlen brauchen „## Zahlen“), `zahlen-quelle` (jede Zeile mit Quelle), `belegblatt` (F<n>_belege.md daneben) |
| 3 Sprache | `floskel`, `du-dichte` (mindestens 2 je 100 Wörter, Trailer und Lang 3), `bannwort`, `gedankenstrich` |
| 4 Länge | `laenge` (Snack 30–45 s, Short 60–75 s, Trailer 35–60 s, Lang 300–840 s gesprochen; `--band` ändert das) |
| 5 Schluss | `letzter-satz` (keine Aufforderung, kein Fazit); im Trailer `aufforderung-trailer` (genau eine bei 70–90 %) |

**Hinweis-Regeln:** `kausal-vorn`, `ichwir-vorn`, `ding-vorn`, `erster-satz-lang`, `frage-vorn`, `quelle-im-satz`,
`versprechen`, `klammer`, `wendung`, `neue-luecke` (im Langvideo im Takt, `--takt`), `zahlenleiter`, `analogie`,
`lacher-lage` (mit `--lacher`), `auszahlung-frueh` (mit `--auszahlung`), `slots`, `du-vor-ich`, `letzter-satz-also`,
`schlussfrage-lang`.

`--fremdton <s>` zählt Sekunden fremder O-Töne zur Länge, weil der Zuschauer sie hört; ihre Wörter stehen nicht im
Sprechtext. Regie-Marken in eckigen Klammern am Zeilenanfang (`[A]`, `[B]`) zählen nicht als Wort.

## 7. Die Dateien

```
# <Titel>, <Format>, <Datum>, F<n>
Stoppuhr: <Start> bis <Ende> = <Minuten>

## Bild 1
**<4–7 Wörter, stumm lesbar>**

## Hook-Kandidaten
1. … (nacherzählt: …)  2. …  3. …  gewählt: <n>, weil …

## Sprechtext
<Slot 1>

<Slot 2>
…

## Lacher-Vorschläge (optional)
1. …  2. …  3. …

## Zahlen
| im Text | Wert | Quelle |

## Endkarte
<Aufforderung, Kanalsatz>
```

Belegblatt `F<n>_belege.md`, in zwei Minuten lesbar:

```
# Belege zu F<n>: <Titel>, Stand <Datum>
<n> Behauptungen, davon <k> mit Primärquelle ★

## Die drei Fragen, die am ehesten kommen
1. <Frage> · <Antwort in einem Satz, mit Quelle>

## Satz für Satz
### „<was gesagt wird>“
- Quelle: <wer>, „<Titel>“, <vollständiger Link>, veröffentlicht <Datum>, abgerufen <Datum>
- Wörtlich: „<Satz aus der Quelle>“ (deutsch: „…“)
- Rechnung: <Schritt für Schritt, falls umgerechnet>
- Sicherheit: ★ Primärquelle oder ☆ Presse · belegt, Schätzung oder Annahme
- Wenn dich jemand fragt: „<ein bis zwei gesprochene Sätze>“

## Was nicht belegt ist
```

## 8. Fallen

### F1 · Grüner Test als Alibi
**Symptom:** Das Skript besteht alle Prüfungen, der Mensch versteht den Hook trotzdem nicht.
**Ursache:** Prüfskripte messen Form, nicht Verständnis.
**Gegenmittel:** Den Text einem Menschen zeigen und laut lesen lassen; den Hook blind nacherzählen lassen (`hook-blind`).

### F2 · Kausal-Hook
**Symptom:** „Dieser Magnet wiegt 500 Tonnen, weil …“ und der Fremde fragt „Warum?“.
**Ursache:** Zwei Ideen mit „weil“ verbunden; die Kette braucht Zwischenschritte.
**Gegenmittel:** Eine Idee in den Hook, die Kette in Slot 4.

### F3 · Pflicht-Signaturen
**Symptom:** Derselbe Vergleich oder Witz in jedem Video wird zur Masche und zündet nicht mehr.
**Ursache:** Ein Werkzeug wurde zur Pflicht.
**Gegenmittel:** Signaturen nur, wenn sie das Ding wirklich greifbar machen.

### F4 · Quellvideo als Ding
**Symptom:** Aus einer Prüfung wird eine Reaction („Dieses Reel hat 7.000 Likes …“).
**Ursache:** Das Video statt der Behauptung steht im ersten Satz.
**Gegenmittel:** Die Behauptung ist das Ding; das Quellvideo frühestens in Slot 3.

### F5 · Die lange Kette
**Symptom:** Schreiber und mehrere Kritiker-Läufe brauchen Stunden für einen kurzen Text.
**Ursache:** Prüfschleifen ersetzen das Lesen durch den Menschen.
**Gegenmittel:** Erste Fassung in 15 Minuten, dann zeigen. Kritiker nur auf Wunsch.

### F6 · Lacher als Fremdverweis
**Symptom:** Der Witz zündet nicht.
**Ursache:** Er bezieht sich auf ein anderes Video, das der Zuschauer nicht kennt.
**Gegenmittel:** Der Lacher steht im Bild dieses Videos.

### F7 · Ein Beat fehlt
**Symptom:** Starker Hook, trotzdem schwach.
**Ursache:** Versprechen oder Auszahlung fehlen; schwache Shorts haben blind öfter kein Versprechen (20 % gegen 8 %) und
keine Auszahlung (22 % gegen 8 %) (eigene Messung, n = 248, Methode in `docs/messungen/hook-studie.md`).
**Gegenmittel:** Jeden Slot prüfen; ein guter Hook rettet keinen fehlenden Beat.

### F8 · Eine Studie ohne Blindprobe
**Symptom:** Regeln, die sich später nicht halten.
**Ursache:** Wer weiß, welches Video viral war, sieht mehr Unterschiede, als da sind.
**Gegenmittel:** Zahlen nur aus blinder Gegenprobe oder automatischer Messung übernehmen.

### F9 · Regie und Notizen im Sprechtext
**Symptom:** Falsche Länge, falscher erster Satz.
**Ursache:** Regie-Marken oder Prüfnotizen (z. B. mit ⚠) stehen im Text und zählen mit.
**Gegenmittel:** Marken in eckigen Klammern am Zeilenanfang setzt das Skript ab; Prüfnotizen vor der Längenmessung
entfernen.
