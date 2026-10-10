---
name: skript-lang
description: 'Das Langvideo (5–8, 8–12 und 12–16 Minuten) als Skript: mit der Fehlvorstellung anfangen (Muller et al. 2008), das Versprechen in Minute 1 bekräftigen, eine Frage als Motor, ein Key Visual, Re-Hooks im Takt, Spaltenskript aus Wort, Bild und Quelle, hart kürzen, Auszahlung und abruptes Ende; dazu Fallen zu Belegen, Kennzeichnung, laufenden Verfahren und Kürzen. Nutze diesen Skill nach skript für jedes Video über drei Minuten, bei „Langvideo“, „Untersuchung“, „Dossier“, „Kapitel“, „Erklärfilm“.'
---

# Langvideo 5–16 Minuten

Belege für die Regeln: Studien und öffentlich zugängliche Interviews mit Praktikern; Quellen in der Tabelle. Was davon
Ableitung ist, steht in §6.

## 1. Die zehn Regeln

| # | Regel | Beleg | Art |
|---|---|---|---|
| L1 | **Mit der falschen Vorstellung anfangen, nicht mit der richtigen Erklärung.** Ein klarer Erklärfilm ändert Überzeugungen kaum; ein Film, der die verbreitete Fehlvorstellung ausspricht und auflöst, schon. | Muller, Bewes, Sharma & Reimann 2008, Journal of Computer Assisted Learning 24; 364 Studierende, Effektstärke d 0,79–0,83 | Studie |
| L2 | **Die erste Minute bekräftigt das Versprechen aus Titel und Thumbnail, sie beantwortet es nicht.** | Johnny Harris im Gespräch mit David Perell (2025); MrBeast-Produktionsmemo (2024); YouTube-Hilfe: die ersten 30 Sekunden als Intro | Praktiker, Plattform |
| L3 | **Zeigen statt ankündigen: ein Key Visual, das man sehen muss, um es zu verstehen.** | Cleo Abram im Gespräch mit Jay Youshaei (2024) | Praktiker |
| L4 | **Eine Frage ist der Motor; jede weitere erhöht den Einsatz; der Zuschauer entdeckt mit.** | Loewenstein 1994 (The Psychology of Curiosity, Psychological Bulletin 116); Harris | Theorie, Praktiker |
| L5 | **Re-Hooks: um Minute 3 und 6 ein neues sichtbares Ereignis, dazu kleine Auszahlungen unterwegs.** | MrBeast-Produktionsmemo (Re-Engagement bei 3 und 6 Minuten) | Praktiker |
| L6 | **Jeder Punkt bekommt seine eigene Spannung: erst Problem, dann Lektion; „aber“ und „deshalb“.** | Ed Lawrence (Creator Science); Randy Olson, And-But-Therefore | Praktiker |
| L7 | **Wort und Bild gleichzeitig schreiben, im Spaltenskript.** Ohne Bildspalte ist es ein Essay. | Harris; Abram (drei Spalten: Wort, Bild, Quellen) | Praktiker |
| L8 | **Hart kürzen.** Rund 20 % aus jedem Skript. | Ed Lawrence (kürzt zwei Minuten aus jedem Skript) | Praktiker |
| L9 | **Auszahlung, dann abrupt aus oder Schleife zum Anfang.** Eine kurze Frage an die Zuschauer ist erlaubt. | MrBeast-Memo; Lawrence | Praktiker |
| L10 | **Quellen sichtbar, Meinung als Meinung markiert, Unsicherheit benannt.** | Kurzgesagt, öffentliche Quellenpraxis seit 2019 | Konvention |

## 2. Beat-Tabellen

| 5–8 min | 8–12 min | Beat |
|---|---|---|
| 0:00–0:08 | 0:00–0:10 | Hook: Bild oder Behauptung, kein Kontext |
| 0:08–0:30 | 0:10–0:30 | Einsatz und Versprechen: warum es dich betrifft, was du am Ende weißt |
| 0:30–1:00 | 0:30–1:00 | Fahrplan in einem Satz und **die verbreitete Fehlvorstellung aussprechen** |
| 1:00–2:30 | 1:00–3:00 | Block 1: Frage aufmachen, erster Beweis, **Key Visual** einführen |
| ~2:30 | ~3:00 | **Re-Hook 1**: neues Ereignis, Wendung |
| 2:30–4:30 | 3:00–6:00 | Block 2: Mechanismus, jeder Punkt mit eigenem Problem und Lösung |
| ~4:30 | ~6:00 | **Re-Hook 2**: Gegenbeweis, Zahl, eigene Messung |
| 4:30–6:00 | 6:00–9:30 | Block 3: Folgen, Einordnung, Meinung markiert, Quellen im Bild |
| 6:00–6:45 | 9:30–10:30 | Auszahlung: Antwort auf die Titelfrage, Schleife zum Anfang |
| 6:45–7:00 | 10:30–11:00 | Abrupt aus oder eine Frage, dann Endbildschirm |

**12–16 Minuten fertig** (gesprochen bis etwa 840 s, siehe Längenplanung unten):

| gesprochen | Beat |
|---|---|
| 0:00–0:10 | Hook mit Ding und Beleg („… und gleich zeig ich dir das Dokument“), Bild 1 aus dem Beleg |
| 0:10–0:45 | Titel-Satz (L2), Absender höchstens als Halbsatz |
| 0:45–1:30 | **Fehlvorstellung** (L1) |
| 1:30–3:00 | Block 1 und Key Visual; erste Auszahlung |
| ~3:00 | **Re-Hook 1**, danach höchstens ein kurzer Abo-Satz mit konkretem Nutzen |
| 3:00–6:00 | Block 2 (Mechanismus, je Punkt Problem und Lösung) |
| ~6:00 | **Re-Hook 2** |
| 6:00–9:00 | Block 3 (wer beteiligt ist, Gegenprobe: was NICHT stimmt) |
| ~9:00 | **Re-Hook 3** (neue Seite des Themas) |
| 9:00–11:00 | Block 4, Meinung markiert |
| 11:00–13:00 | Handlung in Schritten statt Appell, Schleife zum Hook |

**Längenplanung:** Das fertige Video ist länger als der Sprechtext, weil Belege, Karten und Pausen dazukommen. Gemessen
war es 1,14- bis 1,33-mal so lang (eigene Messung, n = 2, Methode in `docs/messungen/skript-langvideo-laenge.md`).
Deshalb prüft `skript_pruefen.py --format lang` das Band 300–840 s gesprochen; mit `--band` an den eigenen Faktor
anpassen. Wortzahl je Minute: 150 als Faustwert (nicht gemessen); besser das eigene Tempo messen.
Ein Kanaljingle, falls es einen gibt, kommt erst nach Hook und Fahrplan (eigene Auszählung, Methode in
`docs/messungen/skript-auszaehlung.md`).

## 3. Neun Eröffnungsmuster (erste 30 Sekunden)

1. **Fehlvorstellung:** „Ich hatte das Gefühl, dass … das geringere Übel ist. Was wir herausgefunden haben, hat mich
   überrascht.“
2. **Superlativ mit Zahl:** „Drei Erfindungen, die Millionen Leben gekostet haben.“
3. **Kalter Einstieg in eine Szene** mit Person und Uhrzeit: „Erika ist gerade aufgewacht. Es ist 4 Uhr morgens.“
4. **Bild-Anker:** „Mitten in der Heide wird dieses Schachbrettmuster ausgelegt. Warum?“
5. **Frage und Fahrplan.**
6. **Persönliches Bekenntnis.**
7. **„Kennst du das?“-Analogie.**
8. **Der Hinweis von innen:** jemand hat etwas zugespielt.
9. **Die Leerstelle:** „Sie taucht in keiner Nachricht auf. Sie wird an keiner Börse gehandelt.“

## 4. Das Spaltenskript

| Wort (links) | Bild (Mitte) | Quelle (rechts) | Stempel |
|---|---|---|---|
| jeder Satz oder jedes Satzpaar eine Zeile | was läuft: Karte, Foto, Dokument, Einspieler | Quelle mit Datum und Fundstelle | BELEGT, MEINUNG oder UNBESTÄTIGT (F15) |

## 5. Abnahme

```bash
python scripts/skript_pruefen.py F<n>_skript.md --format lang [--takt 180] [--band 300-840]   # im Skill skript
```

Dazu: L1 Fehlvorstellung vor Minute 1 · L3 Key Visual benannt · L7 Spaltenskript vollständig · L8 Kürzungslauf gemacht
(Ziel: 20 % raus) · Quellen im Bild · ein Kritiker liest bei 0:30, 1:00, 3:00, 6:00 und am Ende. Jeden Fund lesen und
entscheiden.

## 6. Was nicht belegt ist

Mullers Effekte gelten für Lernerfolg, nicht für Zuschauerbindung · die Minuten aus dem MrBeast-Memo gelten für
Challenge-Formate, die Übertragung ist Ableitung · „33 % steigen in 30 s aus“ steht nur in Blogs · die Wirkung von
And-But-Therefore ist nicht durch eine Studie belegt · Wortzahl je Minute ist ein Faustwert.

## 7. Fallen

### F1 · Die Du-Dichte fällt bei Themen über Institutionen
**Symptom:** Der Entwurf hat unter 2 Du je 100 Wörter.
**Ursache:** Wer über Behörden oder Konzerne schreibt, vergisst den Zuschauer.
**Gegenmittel:** Gleich beim Schreiben Brücken setzen: „stell dir vor“, „deine Stadt“, „Jetzt denkst du …“. Nachträglich
kostet jede Brücke Wörter, die woanders fehlen.

### F2 · Ungenaue Namen und zwei Jahreszahlen im Hook
**Symptom:** „eine große Bank“ hört der Fremde als irgendeine Bank; „fünf Jahre nach …, bis 2019“ muss er umrechnen.
**Ursache:** Zu allgemein, zu viel Rechnen.
**Gegenmittel:** Institutionen genau benennen; der zweiten Zahl ein Ereignis geben.

### F3 · Das Versprechen wird nicht erkannt
**Symptom:** Das Prüfskript meldet `versprechen`, obwohl Satz 3 stark ist.
**Ursache:** Es sucht nach Wörtern wie „gleich“, „zeig dir“, „am Ende“ oder einer Frage.
**Gegenmittel:** Entweder den Satz verlängern („…, und gleich zeig ich dir, was intern darüber steht“) oder den Fund
bewusst verwerfen. Der Mensch entscheidet.

### F4 · Länge nach dem Faktencheck
**Symptom:** Nach der Prüfung ist das Skript 15–20 % länger.
**Ursache:** Die Nachprüfung bringt neue Funde und Einschränkungen.
**Gegenmittel:** Erst kürzen (L8), dann Du-Brücken setzen, dann neu zählen. Länge auf das fertige Video planen (§2).

### F5 · KI-Klang
**Symptom:** Zuschauer schreiben, der Text klinge maschinell.
**Ursache:** Schablonen im Bau, nicht einzelne Wörter (Skill `anti-slop-writing`, F1).
**Gegenmittel:** Blinder Klang-Prüfer; eigene gesprochene Wendungen des Sprechers einbauen.

### F6 · Kommentare lesen, bevor du schreibst
**Symptom:** Dieselbe Kritik kommt unter jedem Video wieder.
**Ursache:** Die Kommentare des letzten Videos wurden nicht ausgewertet.
**Gegenmittel:** Kommentare abrufen, nichts auf die Platte, die Fragen auszählen. Antworten hängen auch an Antworten:
für jede Antwort bis zur Wurzel hochlaufen, sonst fehlen die Debatten. Schlagwörter mit Wortgrenzen zählen und
Stichproben lesen. Namen der Kommentierenden nie veröffentlichen; Pseudonyme nur lokal zuordnen.

### F7 · Zukunft ohne Stand
**Symptom:** Ein Gedankenspiel klingt wie ein beschlossener Plan.
**Ursache:** Szenario, Ziel und Gesetz werden gleich erzählt.
**Gegenmittel:** Jede Aussage über die Zukunft bekommt ihren Stand, im Bild und im Satz: SZENARIO (Text oder Studie),
ZIEL (beschlossenes Ziel), GESETZ (gilt oder kommt).

### F8 · Freie Rede an der falschen Stelle
**Symptom:** Frei gesprochene Halbsätze werden zu Prüf-Funden.
**Ursache:** Unklar, wo der Sprecher frei reden darf.
**Gegenmittel:** Im Skript markieren, wo frei gesprochen werden darf (Meinung, eigene Erfahrung) und wo nicht (Namen,
Vorwürfe, Zahlen). Eine Stolperliste „vor dem Dreh einmal laut lesen“ mit allen heiklen Zahlen.

### F9 · Satzzeichen zerschneiden den Prompter
**Symptom:** Ein Satz landet in zwei Prompter-Abschnitten oder zwei Sätze kleben zusammen.
**Ursache:** „!“ in einem Eigennamen gilt als Satzende; „seit 2012.“ gilt als Ordnungszahl.
**Gegenmittel:** Eigennamen im Sprechtext ohne Satzzeichen; Ordnungszahl-Schutz nur für ein- und zweistellige Zahlen
(Skill `prompter` im Plugin `studio`). Immer zuerst mit `--probe` einspielen.

### F10 · Die erste Minute mit Meta füllen
**Symptom:** Die Zuschauerbindung fällt in den ersten 60 Sekunden steil ab.
**Ursache:** Vorstellung, Kanal-Erklärung, Allgemeines ohne neues Ding.
**Gegenmittel:** Bis Sekunde 60 nur Inhalt (Hook, Beleg, zweiter Beleg, Versprechen); Absender höchstens als Halbsatz,
Abo-Satz und Serienbezug erst nach der ersten Auszahlung. An einem eigenen Video beobachtet (n = 1), keine Studie.

### F11 · Kürzen verliert Korrekturen
**Symptom:** Einschränkungen und Korrekturen früherer Fassungen sind nach dem Kürzen wieder weg.
**Ursache:** Beim Kürzen und beim Klang-Umbau fallen Nebensätze, die eine Aussage erst richtig machten.
**Gegenmittel:** Nach jeder Fassung prüft ein Faktenprüfer gegen das alte Belegblatt und die Liste aller früheren Funde,
mit dem Auftrag „Was ist beim Kürzen verloren gegangen?“. Fakten haben das letzte Wort vor dem Klang.

### F12 · Eine Fälschung zur Demonstration
**Symptom:** Ein Ausschnitt mit geklonter Stimme oder erzeugtem Bild wird ohne Kennzeichnung geteilt.
**Ursache:** Die Kennzeichnung stand nur im Sprechtext.
**Gegenmittel:** Kennzeichnung ab dem ersten Bild bis zum Ende des Ausschnitts im Bild (z. B. „KI-FÄLSCHUNG · DEMO“),
dazu in Beschreibung und Plattform-Angabe. Rechtlicher Rahmen in der EU: Transparenzpflichten nach Art. 50 der
KI-Verordnung (Verordnung (EU) 2024/1689). Die Fälschung nennt keinen Dritten und sagt nichts zu einer Wahl.

### F13 · Shorts-Hooks gehören in denselben Dreh
**Symptom:** Für die Hooks der Shorts braucht es eine eigene Sitzung.
**Ursache:** Sie standen nicht im Skript.
**Gegenmittel:** Hinter das Videoende im selben Prompter-Eintrag: „Ende des Videos. Ab hier kommen die Shorts.“, dann je
Short Titel und Hook. Die Prüfung (Länge, Regeln) läuft nur über den Haupttext.

### F14 · Wagnis ohne Beleg
**Symptom:** Ein mutiger Satz kippt im Faktencheck.
**Ursache:** Mut in der Behauptung statt in der Frage.
**Gegenmittel:** Gewagt heißt mutig in der Frage, nie locker bei den Belegen: die Frage, die sich keiner traut, ein
Live-Experiment, das stärkste Gegenargument im Bild. Ein Mythos-Check zitiert die These mit Herkunft, sagt, was stimmt
und was nicht, und vergibt einen Stempel: STIMMT, HALB, UNBELEGT oder FALSCH; das Urteil braucht selbst Belege.
Leugnung von Völkermord, antisemitische Codes, Gewaltaufrufe und Privatpersonen kommen nie vor, auch nicht zum
Entkräften.

### F15 · Unbelegtes ohne Etikett
**Symptom:** Eine Vermutung klingt wie eine Tatsache.
**Ursache:** Es gibt nur „belegt“ oder „weg“.
**Gegenmittel:** Drei Stufen im Spaltenskript: **BELEGT** (Quelle, ggf. Zweitquelle mit „laut …“), **MEINUNG**
(gesprochen als eigene Sicht), **UNBESTÄTIGT** (gesprochen offen: „Es gibt Berichte, dass … Bestätigt habe ich das nicht
gefunden.“). Grenze: Vorwürfe gegen erkennbare Personen bleiben unter den Verdachtsregeln; ein Etikett schützt nicht
vor dem Weiterverbreiten eines Gerüchts (Skill `belegregeln`).

### F16 · Gremien und Gutachten unkritisch übernehmen
**Symptom:** Ein Gremium stützt eine These, und niemand fragt, wer dahintersteht.
**Ursache:** Expertenurteil gilt als neutral.
**Gegenmittel:** Erst lesen, was das Gremium wirklich empfiehlt. Wer es finanziert oder besetzt, nur mit Beleg nennen.
Ein Beispiel aus der Fachliteratur für gelenkte „unabhängige“ Forschung: der Einfluss der Tabakindustrie auf die
Wissenschaft (Grüning, Gilmore & McKee, American Journal of Public Health 96(1), 2006). Dieselbe Prüfung gilt, wenn ein
Gremium die eigene Meinung stützt.

### F17 · Belegte Einzelsätze, unbelegte Gesamtaussage
**Symptom:** Jeder Satz hat eine Quelle, trotzdem hört der Zuschauer einen Vorwurf, den niemand belegt hat.
**Ursache:** Die Reihenfolge der Sätze ergibt eine verdeckte Aussage, besonders rund um ein laufendes Verfahren. Bei
mehrdeutigen Äußerungen zählt auch die naheliegende Deutung (BVerfG, Beschluss vom 25.10.2005, 1 BvR 1696/98).
**Gegenmittel:** Nach jeder Fassung mit einem laufenden Verfahren prüft ein eigener Durchgang die **Gesamtschau**, nicht
nur Einzelsätze. Allgemeine Regel vor den Absatz über die Person; der Absatz endet mit einem Trennsatz („Ein Vorwurf
ist das nicht …“). Keine Zitate der Person gegen genau die Pflicht, um die es im Verfahren geht.

### F18 · Die Anhörung von Hand gebaut
**Symptom:** Der Brief an die betroffene Seite vergisst Sätze, die sie betreffen.
**Ursache:** Die Zitate wurden von Hand aus dem Skript gesucht.
**Gegenmittel:** Zitate per Skript wörtlich aus `F<n>_prompter.md` ziehen; jeder Absatz, der die Person nennt oder
erkennbar meint, kommt ganz hinein, dazu Bild-1-Text, Titel und Stempel. Frist mindestens fünf Werktage. Ein frischer
Gegenleser vergleicht Brief und Prompter Satz für Satz.

### F19 · Kommentare als Ansage
**Symptom:** „Unter meinem letzten Video hat jemand geschrieben …“, „Fairer Punkt“, Dank an einzelne Zuschauer.
**Ursache:** Die Antwort auf Kommentare wird angesagt statt gegeben.
**Gegenmittel:** Die Frage aus dem Kommentar wird zur Frage des Kapitels, die Überleitung trägt Inhalt. Den Bezug auf
frühere Videos in Beschreibung oder Infokarte.

### F20 · Neue Überleitungen sind Behauptungen
**Symptom:** Ein zugespitzter Brückensatz kippt im Faktencheck.
**Ursache:** Überleitungen gelten als Stil, nicht als Aussage.
**Gegenmittel:** Jede neue Überleitung geht wie ein Faktensatz durch den Faktenprüfer. Eigene Preise mit Monat nennen,
wenn sich der Marktpreis bewegt. Regiezeilen nennen die Marke, nicht eine Zahl von Sätzen („alles mit [LIVE]
überspringen“), weil der Prompter Satz für Satz zerlegt.
