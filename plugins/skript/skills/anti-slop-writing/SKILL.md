---
name: anti-slop-writing
description: 'Regelwerk gegen KI-Klang für alle Texte, die Menschen lesen oder hören: Skripte, Storyboards, Beschreibungstexte, Übergaben, Anleitungen, Issues, E-Mails. Zehn Kernregeln, Bann-Listen mit Synonym-Verbot, Selbstcheck in sieben Schritten, Beispiel-Paare. Grundlage: docs/anti-slop-forschung.md im Plugin (22 Quellen). Nutze diesen Skill, bevor mehr als zwei Sätze für Menschen geschrieben werden, besonders für gesprochene deutsche Skripte und für Prompts von Schreib-Agenten.'
---

# Anti-Slop-Writing

Texte sollen klingen wie ein Mensch mit Haltung, nicht wie eine Vorlage. Vielnutzer von Sprachmodellen erkennen
KI-Text im Mehrheitsvotum zu 99,3 % (Russell, Karpinska & Iyyer, ACL 2025), vor allem am Vokabular und an symmetrischen
Mustern. Dieses Regelwerk entfernt beides. Die Forschung mit allen Quellen steht im Plugin unter
`docs/anti-slop-forschung.md` (relativ zum Plugin-Ordner, also zwei Ebenen über diesem Skill).

Für gesprochene Texte gilt zusätzlich der Skill `sprechtext`: Dort sind Fragmente die Ausnahme, und jeder Satz braucht
ein Verb.

## 1. Zehn Kernregeln (priorisiert)

1. **Konkretes Detail schlägt alles.** Jede Kernaussage trägt Zahl, Name, Gerät, Gesetz, Ort oder Datum. „Die Bahn hält
   nach 20 Metern“ statt „deutlich kürzerer Bremsweg“.
2. **Meta-Kommentar streichen.** „Es ist wichtig zu beachten“, „Tauchen wir ein“, „Werfen wir einen Blick“, „Heute
   sprechen wir über“: Der Satz danach ist der eigentliche Anfang.
3. **„Nicht X, sondern Y“ meiden.** Auch „Es geht nicht um X, es geht um Y“ und gleich gebaute Varianten. Direkt und
   bejahend formulieren.
4. **Dreierlisten brechen.** „schnell, sicher und effizient“ ist ein Reflex. Zwei nennen oder eins ausführen.
5. **Satzlängen streuen.** Nach einem Satz über 20 Wörtern folgt einer unter 8. (KI-Deutsch: 18–24 Wörter mit
   Streuung unter 3; Menschen 6–12, laut korrektur.de, Quelle 12 der Forschung.)
6. **Haltung beziehen.** Kein „einerseits, andererseits“-Fazit, kein „die Zukunft wird zeigen“, kein erzwungener
   Hoffnungs-Schluss.
7. **Bedeutung zeigen, nicht behaupten.** „entscheidend“, „zentral“, „spannend“, „bahnbrechend“ fliegen raus; wenn etwas
   wichtig ist, beweist das ein Fakt. („spielt eine entscheidende Rolle“ steht laut Quelle 12 in 43 % der KI-Texte und
   in 6 % der menschlichen.)
8. **Bann-Liste mit Synonym-Verbot.** Nur Wörter zu verbieten reicht nicht: Das Modell ersetzt „überragend“ durch
   „herausragend“. Muster verbieten.
9. **Hedges und leere Verstärker löschen.** „möglicherweise“, „unter Umständen“, „wirklich“, „absolut“, „unglaublich“:
   Der Satz stimmt ohne sie oder gar nicht.
10. **Laut-Lese-Test.** Jeder Satz muss sprechbar sein. Nominalketten und Schachtelsätze umbauen.

## 2. Bann-Listen (auch Synonyme und Umschreibungen)

**Deutsch, Wörter:** entscheidend, zentral, essenziell, maßgeblich, spannend, bahnbrechend, revolutionär, faszinierend,
nahtlos, ganzheitlich, umfassend, facettenreich, vielschichtig, maßgeschneidert, innovativ (inflationär),
„eintauchen“, „Meilenstein“, „das Rückgrat von“, „gewinnt zunehmend an Bedeutung“, „eine Vielzahl von“.

**Deutsch, Floskeln:** „In der heutigen digitalen Welt“, „Im Zeitalter der …“, „Seit jeher“, „Immer mehr Menschen“,
„Es ist wichtig zu beachten“, „erwähnenswert“, „Zusammenfassend lässt sich sagen“, „Abschließend bleibt festzuhalten“,
„Experten gehen davon aus“ (ohne Name und Jahr), „Schätzungen zufolge“ (ohne Quelle), „vor diesem Hintergrund“,
„nicht zuletzt“.

**Englisch (Übergaben, Anleitungen):** delve, tapestry, testament, realm, landscape, journey, pivotal, crucial,
leverage, utilize, foster, seamless, robust, comprehensive, cutting-edge, transformative, "it's important to note",
"in today's rapidly evolving …", Ketten aus moreover und furthermore.

**Satzmuster:** Negations-Parallelen, symmetrische Dreier, Partizip-Anhängsel („…, was X unterstreicht“), „fungiert als“,
„stellt dar“, „dient als“ statt „ist“, mehr als ein Gedankenstrich je Absatz, Antithesen-Staccato („Kein Abo. Keine
Werbung. Nur du.“).

Die Prüfskripte im Plugin (`skript_pruefen.py`, `hook_pruefen.py`) kennen eine kurze Bann-Liste. Eigene Wörter kommen
über eine Regeldatei dazu (`[bann] zusaetzlich = […]`), siehe Skill `skript` §6.

## 3. Gesprochene Skripte (deutsch)

- Die erste Zeile ist der Hook: ein Ding mit Zahl oder ein Widerspruch. Kein Anlauf, keine Begrüßung, kein „In diesem
  Video“ (Skill `hook`).
- Direkte Du-Ansprache, nie „man“ oder „die Nutzer“.
- Schleife: Der letzte Satz führt zum ersten zurück.
- Verben nach vorn, Hauptsätze, höchstens ein Nebensatz.
- **Keine Sekundenzahl behaupten.** Für „die ersten drei Sekunden entscheiden“ gibt es keine Primärquelle; YouTube nennt
  in der Hilfe zur Zuschauerbindung die ersten 30 Sekunden als Intro. Gemessen ist nur, dass Abbrechen bei Kurzvideos
  der Normalfall ist (Zannettou et al., CHI 2024, Details in der Forschung §5).

## 4. Selbstcheck vor jedem Abgeben

1. Suche nach „nur“ und „sondern“: Negations-Parallele gefunden? Umbauen.
2. Suche nach „entscheidend|zentral|spannend|wichtig zu“: Behauptung durch Fakt ersetzen.
3. Dreierlisten zählen: mehr als eine? Brechen.
4. Satzlängen ansehen: drei Sätze in Folge ähnlich lang? Einen kürzen.
5. Ersten Satz prüfen: Sagt er etwas, oder kündigt er nur an?
6. Letzten Satz prüfen: harter Schluss oder Pflicht-Hoffnung und Zusammenfassung?
7. Laut lesen (bei gesprochenen Texten): Wo es sich staut, umbauen.

## 5. Beispiel-Paare (erfunden)

- „In der heutigen digitalen Welt spielt Mobilität eine immer wichtigere Rolle.“ → „Die Straßenbahn in Musterhafen hält
  aus 50 km/h nach 20 Metern. Dein Auto braucht länger.“
- „Es ist wichtig zu beachten, dass Sensoren nicht nur Vorteile bieten, sondern auch Risiken bergen.“ → „Der Sensor
  meldet ein Hindernis nach 0,2 Sekunden. Du brauchst eine ganze Sekunde.“
- „Experten gehen davon aus, dass die Maßnahme möglicherweise problematisch sein könnte.“ → „Das Verwaltungsgericht
  Musterhafen hat die Maßnahme zweimal gestoppt. Sie kommt trotzdem wieder.“
- „Zusammenfassend lässt sich sagen, dass Pünktlichkeit von zentraler Bedeutung ist.“ → „Guck morgen auf die Anzeige an
  deiner Haltestelle. Dann reden wir weiter.“
- EN: "It's important to note that this pipeline leverages a comprehensive approach to seamlessly integrate assets." →
  "The pipeline copies assets from drops/, trims each to beat length, and fails loudly if a file is missing."

## 6. Anwendung

- **Eigene Texte:** Regelwerk anwenden und Selbstcheck fahren, bevor der Text rausgeht, auch bei Kommentaren,
  Pull-Request-Texten und E-Mails.
- **Prompts für Schreib-Agenten:** Bann-Liste, Synonym-Verbot und zwei bis drei Beispiel-Paare in den Prompt; danach
  ein Prüfdurchgang gegen die Streichliste und eine Neufassung.
- **Vertiefung:** `docs/anti-slop-forschung.md` (Merkmal-Katalog, Detektions-Forschung, Prompt-Baustein, 22 Quellen).

## 7. Fallen

### F1 · KI-Klang ist ein Bau-Problem, kein Wort-Problem
**Symptom:** Zuschauer schreiben „klingt KI-geschrieben“, obwohl kein Bann-Wort im Text steht.
**Ursache:** Muster im Bau: dieselbe Satzschablone mehrfach („Das ist [harmlos]. Aber [Pointe].“ als Absatzschluss),
Anaphern („Ich zeig dir … Ich zeig dir …“), nummerierte Ansagen, Passiv vorn, Signalsätze („Die Wahrheit ist …“),
dieselbe Formel über mehrere Videos.
**Gegenmittel:** Einen blinden Klang-Prüfer (frischer Agent, nur der Sprechtext) Sätze markieren und ersetzen lassen;
eigene, gesprochene Wendungen des Sprechers einbauen, höchstens eine je Absatz.

### F2 · Wörter verboten, Muster bleibt
**Symptom:** Nach der Bann-Liste steht „herausragend“ statt „überragend“.
**Ursache:** Das Modell weicht auf Synonyme aus.
**Gegenmittel:** Muster verbieten und das Synonym-Verbot ausdrücklich in den Prompt schreiben.

### F3 · Schreibregeln im Sprechtext
**Symptom:** Telegrammstil im Prompter.
**Ursache:** „Fragmente sind erlaubt“ wurde auf gesprochenen Text angewandt.
**Gegenmittel:** Für Gesprochenes gilt der Skill `sprechtext`.
