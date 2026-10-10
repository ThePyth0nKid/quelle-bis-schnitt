# Anti-Slop-Forschung: KI-Klang aus Texten entfernen

> Recherche-Stand Juli 2026, bereinigt für die Veröffentlichung im Oktober 2026. Grundlage des Skills
> `anti-slop-writing`. Gilt für gesprochene Skripte (deutsch), Storyboards, Beschreibungstexte, Übergaben und Anleitungen.
> Kernbefund vorweg: Menschen, die viel mit Sprachmodellen arbeiten, erkennen KI-Text im Mehrheitsvotum zu 99,3 %
> (Russell, Karpinska & Iyyer, ACL 2025, Quelle 2). Der Hauptverräter ist das Vokabular, danach die Symmetrie im
> Satzbau. Beides lässt sich wegschreiben.
>
> Alle Beispielsätze in diesem Dokument sind erfunden, auch ihre Zahlen.

---

## 1. Zehn Kernregeln (priorisiert)

1. **Konkretes Detail schlägt alles.** Jede Behauptung braucht eine Zahl, einen Namen, ein Gerät, einen Ort oder ein
   Datum. Fehlende Spezifik ist in den Marker-Katalogen der stärkste Slop-Hinweis (Quellen 6, 11).
2. **Meta-Kommentar streichen.** Was ankündigt statt sagt, fliegt raus: „Es ist wichtig zu beachten“, „Tauchen wir
   ein“, „Lass uns einen Blick werfen“. Der Satz danach ist der eigentliche Anfang.
3. **„Nicht X, sondern Y“ meiden.** Die Negations-Parallele ist das meistgenannte Struktur-Merkmal (Quellen 4, 9; bei
   Russell et al. nennen 35,9 % der Begründungen den Satzbau). Direkt und bejahend formulieren.
4. **Dreierlisten brechen.** Sprachmodelle bilden reflexhaft symmetrische Dreier („schnell, sicher und effizient“).
   Zwei nennen oder einen ausführen; drei nur, wenn es sachlich genau drei sind.
5. **Satzlängen streuen.** KI-Deutsch liegt laut Quelle 12 bei 18–24 Wörtern je Satz mit einer Standardabweichung unter
   3, Menschen bei 6–12. Auf einen langen Satz folgt ein kurzer.
6. **Haltung beziehen.** Keine Pro-und-Contra-Nebelwand, kein „einerseits, andererseits“-Fazit, kein „die Zukunft wird
   zeigen“.
7. **Bedeutung zeigen, nicht behaupten.** „Entscheidend“, „von zentraler Bedeutung“ sind Behauptungs-Vokabeln. Wenn
   etwas wichtig ist, beweist das ein Fakt.
8. **Bann-Liste mit Synonym-Verbot.** Wörter allein zu verbieten reicht nicht: Das Modell ersetzt „überragend“ durch
   „herausragend“. Immer dazuschreiben: „auch keine Synonyme und keine Umschreibungen desselben Musters“ (Quelle 15).
9. **Hedges und leere Verstärker löschen.** „möglicherweise“, „unter Umständen“, „wirklich“, „absolut“. Entweder stimmt
   der Satz ohne sie, oder er stimmt gar nicht.
10. **Laut-Lese-Test als letzte Prüfung.** Würde ein Mensch den Satz so in die Kamera sprechen? Nominalketten und
    Schachtelsätze sind unsprechbar.

---

## 2. Slop-Marker-Katalog (deutsch und englisch)

Quellen: 4, 1, 11, 12, 13, 14, 7, 6.

### 2.1 Lexik: verbrannte Wörter

| Kategorie | englisch | deutsch |
|---|---|---|
| klassische Merkmale | delve, tapestry, testament, realm, beacon, landscape, journey, symphony | eintauchen, „tauchen wir ein“, facettenreich, vielschichtig, Meilenstein, Landschaft (bildlich), „das Rückgrat von“ |
| Bedeutungs-Behaupter | pivotal, crucial, vital, key, significant, underscores, showcases | entscheidend, zentral, essenziell, maßgeblich, „spielt eine entscheidende Rolle“, „unterstreicht“, „von zentraler Bedeutung“ |
| aufgeblasene Verben | leverage, utilize, foster, bolster, empower, unlock, unleash, streamline, navigate | ermöglichen, optimieren, fördern (inflationär), „gewinnt zunehmend an Bedeutung“ |
| Werbe-Adjektive | vibrant, seamless, robust, comprehensive, cutting-edge, groundbreaking, transformative, game-changer | nahtlos, ganzheitlich, umfassend, maßgeschneidert, innovativ, revolutionär, spannend, bahnbrechend |
| falsche Präzision | meticulous, intricate, nuanced, multifaceted, myriad, plethora | akribisch, komplex (als Ausweichwort), nuanciert, „eine Vielzahl von“, „ein nicht unerheblicher Teil“ |
| förmliche Verbinder | moreover, furthermore, additionally, consequently, in conclusion | darüber hinaus, des Weiteren, folglich, hinsichtlich, „vor diesem Hintergrund“, „nicht zuletzt“, zusammenfassend |

Laut Quelle 12 steht „spielt eine entscheidende Rolle“ in 43 % der untersuchten KI-Texte und in 6 % der menschlichen.
Kobak et al. (Quelle 1) fanden für „delves“ eine 28-fache Häufigkeit nach der Veröffentlichung von ChatGPT,
„underscores“ 13,8-fach, „showcasing“ 10,7-fach; 66 % der Exzess-Wörter von 2024 waren Verben, 14 % Adjektive. Es sind
Stil-Wörter, keine Inhalts-Wörter. Diese Schicht lässt sich ersetzen, ohne Inhalt zu verlieren.

### 2.2 Syntax: verräterische Satzmuster

| Muster | englisch | deutsch |
|---|---|---|
| Negations-Parallele | "It's not just a tool, it's a paradigm shift." | „Das ist nicht nur ein Werkzeug, sondern ein Paradigmenwechsel.“ |
| Antithesen-Staccato | "No ads. No tracking. Just privacy." | „Kein Abo. Keine Werbung. Nur du.“ |
| symmetrische Dreierliste | "fast, secure, and reliable" | „intuitiv, schnell und effizient“ |
| Partizip-Anhängsel | "…, highlighting the importance of …" | „…, was die Bedeutung von X unterstreicht“ |
| Ist-Vermeidung | "serves as", "stands as" | „fungiert als“, „stellt dar“, „dient als“ statt „ist“ |
| gleichförmige Satzlänge | 15–20 Wörter, jeder Satz | Subjekt, Verb, Objekt, Nebensatz im immer gleichen Takt |
| Gedankenstrich-Inflation | drei Gedankenstriche je Absatz | Gedankenstrich als Dauerstilmittel statt Komma oder Punkt |
| Hedging-Ketten | "may potentially, in some cases" | „kann möglicherweise unter Umständen“ |
| perfekte Grammatik | keine Ellipsen, keine Brüche | keine Umgangssprache, kein „naja“ |

### 2.3 Struktur: verräterische Bauformen

- **Floskel-Einstieg:** „In der heutigen digitalen Welt …“, „Seit jeher …“, „Immer mehr Menschen fragen sich …“.
- **Fazit gleich Einleitung,** dazu „Zusammenfassend lässt sich sagen …“.
- **Frage-Wiederholung:** Die Frage wird erst umformuliert, dann beantwortet.
- **Zwischenüberschrift über jedem Absatz,** Listen statt Fließtext, Fettdruck als Dekoration, Emoji als Gliederung.
- **„Herausforderungen und Ausblick“ als Pflichtmodul.**
- **Hoffnungs-Zwang:** Jeder Text endet hoffnungsvoll, auch wenn der Inhalt es nicht hergibt.
- **Absatz fasst sich selbst zusammen.**

### 2.4 Rhetorik und Ton

- **Vage Autorität:** „Experten gehen davon aus“, „Studien zeigen“ ohne Namen, Quelle, Zahl.
- **Gespielte Zusammenarbeit:** „Lass uns gemeinsam anschauen …“.
- **Schmeichel-Öffner:** „Spannende Frage!“ vor der Antwort.
- **Gespielte Offenheit:** „Ich bin mal ehrlich …“ ohne vorherige Unehrlichkeit.
- **Gleichförmige Begeisterung:** Routine und Neuheit im selben Jubelton.
- **Falsche Dramatik:** „Und jetzt wird es richtig interessant“ vor Unbemerkenswertem.
- **Behauptete Tiefe:** „Etwas hat sich verändert. Für immer.“

---

## 3. Was KI-Text messbar verrät

**Menschen schlagen Werkzeuge.** In Quelle 2 erreichten fünf Vielnutzer im Mehrheitsvotum 99,3 % Genauigkeit über 300
Artikel und schlugen fast alle kommerziellen und alle offenen Detektoren. Ihre Begründungen nach Häufigkeit:

| Hinweis-Klasse | Anteil der Begründungen |
|---|---|
| Vokabular | 53,1 % |
| Satzstruktur („not only … but also“, Dreierlisten) | 35,9 % |
| Grammatik und Zeichensetzung (zu perfekt) | 24,8 % |
| Originalität (wirkt risikolos) | 23,7 % |
| Zitate (zu förmlich, gleichförmig) | 22,3 % |
| Klarheit (Über-Erklären) | 19,5 % |
| Förmlichkeit | 12,3 % |

Satzweises Umformulieren täuschte die Fachleute in dieser Studie nicht. Einzelne Merkmale zu tilgen genügt also nicht;
das Bündel muss weg.

**Stilometrische Größen** (Quellen 3, 12, 16, 17):

- **Perplexität:** Wie vorhersehbar sind die Wortfolgen? In Quelle 3 lag Text eines Modells bei 18,4 gegen 43,0 bei
  Menschen.
- **Burstiness:** Streuung der Satzlängen und der Satz-Perplexität; die am leichtesten selbst prüfbare Größe.
- **Satzlänge und Wortarten-Folgen** sind laut Forschung von 2025 starke Einzelmerkmale.
- **Fehlerrate nahe null** ist selbst ein Signal.
- **Exzess-Wörter:** Kobak et al. fanden 379 Stil-Wörter mit sprunghaftem Anstieg ab 2023; mindestens 13,5 % der
  PubMed-Abstracts von 2024 waren mit Sprachmodellen bearbeitet (Quelle 1).
- **Grenzen der Detektoren:** Fehlalarme bei gleichförmig schreibenden Menschen und bei nicht-englischen Texten;
  neuere Modellarten imitieren menschliche Perplexität (Quelle 3). Deshalb wird gegen den Eindruck des menschlichen
  Lesers geschrieben, nicht gegen Detektoren.

---

## 4. Gegenmittel als Prompt-Baustein

Destilliert aus den Quellen 18, 15, 7, 9, 10, 6:

```text
SCHREIBREGELN (verbindlich):

Substanz
- Jede Kernaussage trägt mindestens ein konkretes Detail: Zahl, Name,
  Produkt, Gesetz, Datum, Ort.
- Bedeutung wird durch Fakten gezeigt, nie durch Adjektive behauptet.
  Verboten: entscheidend, zentral, essenziell, spannend, bahnbrechend,
  revolutionär, nahtlos, ganzheitlich, umfassend, facettenreich.
- Vage Autorität verboten: „Experten sagen“, „Studien zeigen“ nur mit
  Namen und Jahr, sonst streichen.
- Eine klare Haltung pro Text. Kein „einerseits/andererseits“-Fazit.

Syntax
- Verboten: „nicht nur X, sondern auch Y“, „Es ist nicht X. Es ist Y.“,
  „kein X, kein Y, nur Z“, auch keine strukturgleichen Varianten.
- Keine Dreierlisten aus Adjektiven oder Substantiven.
- Satzlängen mischen: nach jedem Satz über 20 Wörtern einer unter 8.
- „ist/sind“ ist ein gutes Verb.
- Höchstens ein Gedankenstrich pro Absatz.
- Keine Partizip-Anhängsel („…, was X unterstreicht“).

Streichliste (ersatzlos, auch Synonyme und Umschreibungen)
- Meta-Kommentar: „Es ist wichtig zu beachten“, „Tauchen wir ein“
- Floskel-Öffner: „In der heutigen … Welt“, „Seit jeher“
- Füll-Verstärker: wirklich, absolut, unglaublich, äußerst
- Hedging: möglicherweise, unter Umständen, Dauer-„kann“
- Abschluss-Formeln: „Zusammenfassend lässt sich sagen“

Ton
- Direkt, kurz, mit Haltung. Jeder Satz muss sprechbar sein.
- Umgangssprache ist erwünscht („gibt's“, „'ne“).
- Kein Jubelton für Routinen. Der Schluss darf hart enden.
```

**Prompt-Techniken, die in den Quellen wirken:**

1. **Bann-Liste mit Synonym-Verbot** (Quellen 15, 9).
2. **Stil-Beispiele statt Stil-Adjektive:** drei bis fünf echte Textproben im Zielton, auch von den Rändern des
   Spektrums.
3. **Rolle mit Material:** wer schreibt, für wen, warum jetzt, statt „Du bist ein professioneller Texter“.
4. **Entwurf, Prüfung, Neufassung:** erst Entwurf, dann ein Durchgang gegen die Streichliste (Suche nach „nicht nur“,
   „sondern“, „entscheidend“, Dreierlisten, gleichen Satzlängen), dann neu schreiben. Die Suche nach „nur“ findet die
   meisten Negations-Parallelen.
5. **Länge deckeln:** Slop ist fast immer ein Längen-Symptom.
6. **Mensch-Modell-Mensch:** Der Mensch setzt These und Aufbau, das Modell füllt, der Mensch kürzt. Das Modell wählt
   nie die Haltung.

---

## 5. Gesprochene Skripte und Hooks

Die Quellen 19 bis 22 sind Blogs von Werkzeug-Anbietern. Ihre Zahlen haben keine offene Methode und sind hier deshalb
nicht übernommen, nur ihre Muster. Für die oft zitierte Regel „die ersten drei Sekunden entscheiden“ gibt es keine
Primärquelle. YouTube selbst nennt in der Hilfe zur Zuschauerbindung die ersten 30 Sekunden als Intro. Gemessen ist,
dass Abbrechen bei Kurzvideos der Normalfall ist (Zannettou et al., „Analyzing User Engagement with TikTok's Short
Format Video Recommendations using Data Donations“, CHI 2024); die genauen Werte dort im Original nachlesen.

**Was funktioniert:**

- **Erste Zeile ist der Hook, nicht der Anlauf.** Kein Intro, kein Logo, kein Kontext.
- **Hook-Formen:** direkte Zusage mit Zahl, Gegen-Intuition, Frage mit Selbstbezug, Ergebnis zuerst, direkte
  Ansprache der Zielgruppe („Wenn du jeden Tag Bahn fährst, betrifft dich das.“).
- **Muster-Unterbrechung:** Bewegung, Bildwechsel oder eine Behauptung, die der Erwartung widerspricht.
- **Schleife:** Der letzte Satz führt zum ersten zurück.
- **Direkte Ansprache** („du“, nicht „man“).
- **Untertitel ab dem ersten Bild,** weil viele Zuschauer ohne Ton starten.

**Was Zuschauer vertreibt:**

- Begrüßung und Kontext-Anlauf („Heute sprechen wir über …“, „In diesem Video …“).
- Die beste Information erst spät.
- Ein Versprechen, das nicht eingelöst wird.
- Gleichförmiger Sprechrhythmus ohne Tempowechsel.

**Gesprochenes Deutsch:** Nominalstil ist unsprechbar („die Implementierung der Maßnahmen erfolgte …“). Verben nach
vorn, Hauptsätze, höchstens ein Nebensatz.

---

## 6. Beispiel-Paare: Slop und gut

Alle Beispiele erfunden.

**1. Hook**
- Slop: „In der heutigen digitalen Welt spielt Mobilität eine immer wichtigere Rolle. Tauchen wir ein!“
- Gut: „Die Straßenbahn in Musterhafen hält aus 50 km/h nach 20 Metern. Dein Auto braucht länger.“

**2. Erklär-Satz**
- Slop: „Es ist wichtig zu beachten, dass Sensoren nicht nur Vorteile bieten, sondern auch Risiken bergen.“
- Gut: „Der Sensor meldet ein Hindernis nach 0,2 Sekunden. Du brauchst eine ganze Sekunde.“

**3. Negations-Parallele**
- Slop: „Die neue Linie ist nicht nur ein Verkehrsmittel, sondern ein echter Paradigmenwechsel.“
- Gut: „Die neue Linie fährt alle vier Minuten. Seitdem steht am Bahnhof kein Taxi mehr.“

**4. Dreierliste**
- Slop: „Die Software der Nordlicht Analytik GmbH ist mächtig, umstritten und teuer.“
- Gut: „Die Software zählt jede Nacht die Fahrräder auf 300 Straßen. Wer sie prüfen will, bekommt keinen Zugang.“

**5. Hedging und vage Autorität**
- Slop: „Experten gehen davon aus, dass die Maßnahme möglicherweise problematisch sein könnte.“
- Gut: „Das Verwaltungsgericht Musterhafen hat die Maßnahme zweimal gestoppt. Sie kommt trotzdem wieder.“

**6. Schluss**
- Slop: „Zusammenfassend lässt sich sagen, dass Pünktlichkeit von zentraler Bedeutung ist. Was denkst du? Schreib es in
  die Kommentare!“
- Gut: „Guck morgen auf die Anzeige an deiner Haltestelle. Dann reden wir weiter.“

**7. Beschreibungstext (englisch)**
- Slop: "In today's rapidly evolving digital landscape, mobility plays a pivotal role. Let's delve into the facts!"
- Good: "The tram in Musterhafen stops in 20 metres. Your car needs more."

**8. Übergabe (englisch)**
- Slop: "It's important to note that this pipeline leverages a comprehensive approach to seamlessly integrate assets."
- Good: "The pipeline copies assets from drops/, trims each to beat length, and fails loudly if a file is missing."

Muster hinter allen Paaren: Die gute Fassung tauscht Behauptung gegen Beleg (Zahl, Akteur, Ort), Ansage gegen Einstieg
im Inhalt und Symmetrie gegen einen harten, kurzen Nachsatz.

---

## 7. Quellen

Wissenschaftlich:

1. https://arxiv.org/abs/2406.07016 — Kobak et al. (Science Advances 2025): 379 Exzess-Stilwörter in 15 Mio.
   PubMed-Abstracts; „delves“ 28-fach häufiger; mindestens 13,5 % der Abstracts von 2024 mit Sprachmodellen bearbeitet.
2. https://aclanthology.org/2025.acl-long.267/ — Russell, Karpinska & Iyyer (ACL 2025): Vielnutzer erkennen KI-Text zu
   99,3 %; Vokabular (53 %) und Satzstruktur (36 %) als Haupthinweise; robust gegen Umformulieren.
3. https://arxiv.org/abs/2507.10475 — Tarım & Onan 2025: Perplexität und Burstiness bei Menschen und Modellen; klassische
   Detektoren versagen bei neueren Modellarten.

Merkmal-Kataloge:

4. https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing — umfangreichster kuratierter Katalog von
   KI-Schreibmustern (WikiProject AI Cleanup).
5. https://techcrunch.com/2025/11/20/the-best-guide-to-spotting-ai-writing-comes-from-wikipedia/ — Einordnung des
   Wikipedia-Leitfadens.
6. https://momenticmarketing.com/blog/avoid-ai-slop — 34 Slop-Typen in fünf Ebenen.
7. https://www.oliviacal.com/post/ai-writing-tells — 17 Merkmale plus Sperrliste mit Alternativen.
8. https://www.ignorance.ai/p/the-field-guide-to-ai-slop — Feldführer, „unearned profundity“.
9. https://www.blakestockton.com/dont-write-like-ai-1-101-negation/ — Analyse der „It's not X, it's Y“-Negation.
10. https://undetectable.ai/blog/common-ai-words/ — Wortliste mit Ersatzvorschlägen.

Deutschsprachige Merkmale:

11. https://wortliga.de/20-top-ki-floskeln-im-januar-2025/ — 20 deutsche KI-Floskeln in vier Kategorien.
12. https://korrektur.de/ki-texte-erkennen-stilmerkmale-studis-2026 — deutsche Stilmetriken („spielt eine entscheidende
    Rolle“ 43 % gegen 6 %, Satzlängen-Streuung unter 3).
13. https://www.contentconsultants.de/ki-texte-erkennen-warum-man-texte-besser-selbst-schreibt/ — Gedankenstrich-Inflation,
    Antithesen, Adjektiv-Dreier.
14. https://www.eology.de/news/merkmale-von-chatgpt-typischen-texten-beim-ai-roundtable — Dauer-„kann“, generisches
    „Menschen“, Überschriften-Schemata.
15. https://t3n.de/news/ki-floskeln-entfernen-prompt-hack-texte-verbessern-1722165/ — Bann-Listen mit Synonym-Verbot.

Detektoren:

16. https://gptzero.me/news/how-ai-detectors-work/ — Funktionsweise und Fehlalarm-Grenzen.
17. https://gptzero.me/news/perplexity-and-burstiness-what-is-it/ — Definitionen der beiden Grundgrößen.

Gegenmittel und Prompts:

18. https://learnaitogethernewsletter.substack.com/p/the-prompt-we-use-to-prevent-ai-slop — wiederverwendbarer
    Prompt mit Struktur-, Ton- und Vokabelgrenzen.

Shorts und Hooks (Anbieter-Blogs, Zahlen ohne offene Methode):

19. https://www.opus.pro/blog/youtube-shorts-hook-formulas — Hook-Formen und Liste der Abbruch-Gründe.
20. https://aibrify.com/blog/youtube-shorts-retention-curve-playbook — Verlaufskurven, Schleifen, Untertitel-Timing.
21. https://www.conbersa.ai/learn/best-youtube-shorts-hooks — fünf Hook-Typen mit Beispielzeilen.
22. https://www.shortimize.com/blog/youtube-shorts-retention-rate — Bindungswerte nach Inhaltsart.
