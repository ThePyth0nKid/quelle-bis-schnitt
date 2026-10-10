---
name: belegregeln
description: 'Belegregeln für jede Aussage über reale Personen, Firmen und Behörden: kein Faden ohne Quelle, Wortlaut nur aus dem Original, erwähnt ist nicht Kontakt ist nicht schuldig, Vorwurf nur mit Gericht, Behörde oder Vergleich, Festnahme ist nicht Anklage, keine Charakterworte, Privatpersonen ohne Namen, Verfahrensstand statt Absicht. Jede Regel ist einstellbar (aus, hinweis, sperrt); der Mensch entscheidet je Fund. Nutze diesen Skill bei „Beleg“, „Zitat“, „Vorwurf“, „Verdacht“, „Privatperson“, „darf das raus?“, vor jedem Import in einen Belegspeicher und vor jedem Skript, das reale Personen nennt.'
---

# Belegregeln

Die Regeln beraten, sie entscheiden nicht. Jede Regel hat eine Stufe:

| Stufe | Was passiert |
|---|---|
| `aus` | Die Regel wird nicht geprüft. |
| `hinweis` | Ein Verstoß wird als Befund gemeldet. Der Eintrag darf als Entwurf angelegt werden. **Standard.** |
| `sperrt` | Ein Verstoß wird nicht angelegt, sondern dem Menschen vorgelegt. Ein Mensch kann mit Begründung überstimmen. |

- **Standard ist `hinweis`.** Nur der Schutz von Privatpersonen (B8) steht auf `sperrt`, weil er eine rechtliche Grenze
  schützt. Auch er ist umstellbar.
- **Je Befund entscheidet ein Mensch:** übernehmen, verwerfen oder anders. Wer einen sperrenden Befund überstimmt, schreibt
  eine Begründung dazu. Befund, Entscheidung und Begründung bleiben im Verlauf (Entscheidungstabelle im Skill
  `recherche-runde`).
- **Agenten geben nie frei und überstimmen nie.** Alles, was ein Agent anlegt, bleibt Entwurf.
- **Einstellen:** Die Stufen stehen in einer Datei `belegregeln.toml` im Projekt (Vorlage
  [`belegregeln.beispiel.toml`](belegregeln.beispiel.toml) neben diesem Skill). Fehlt die Datei, gelten die Standardstufen
  unten. Ein Belegspeicher kann die Stufen zusätzlich je Board oder Thema setzen.

Diese Regeln sind Empfehlungen für sorgfältiges Arbeiten, keine Rechtsberatung. Wer Vorwürfe gegen reale Personen
veröffentlicht, lässt das vorher juristisch prüfen.

## Die Regeln

Beispiele sind erfunden: die Freie Stadt Musterhafen, die Nordlicht Analytik GmbH, Bürgermeisterin Erika Mustermann,
Kämmerer Max Mustermann.

### B1 · Kein Faden ohne Quelle (`quelle_pflicht`, Standard `hinweis`)

Jede Verbindung und jede Tatsachenbehauptung braucht mindestens einen Beleg mit URL oder Fundort. Fehlt er, bleibt der
Eintrag ein Entwurf mit Befund.

### B2 · Wortlaut nur aus dem Original (`wortlaut_original`, Standard `hinweis`)

- Das Feld für den wörtlichen Beleg enthält nur den Originalwortlaut der Quelle. Nie den eigenen Skriptsatz, nie eine
  Zusammenfassung.
- Fehlt der Wortlaut: Feld leer lassen und in die Fundstelle schreiben, warum („nur Titel abrufbar“, „Bezahlschranke“).
- Übersetzungen durch Dritte sind kein Originalwortlaut: Feld leer, Vermerk „Übersetzung durch <Medium>, Original nicht
  geprüft“.
- Bei Ton- und Videoquellen steht im Feld nur, was alle Abhörungen gleich hören. Strittige Wörter gehören in die Fundstelle,
  bis ein Mensch selbst abgehört hat.

### B3 · Aussageart ehrlich setzen (`aussageart`, Standard `hinweis`)

- `belegt` nur mit Beleg, der die Aussage trägt.
- `verdacht` gegen Personen nur mit Gelegenheit zur Stellungnahme (Anhörung) und zwei unabhängigen Quellen.
- `meinung` nur, wenn ein Mensch den Satz ausdrücklich als seine Einschätzung markiert hat. Ein Agent schreibt keine Meinung.

### B4 · Erwähnt ≠ Kontakt ≠ schuldig (`erwaehnt_kontakt_schuldig`, Standard `hinweis`)

Das Etikett einer Verbindung sagt, was belegt ist, mit Jahr und Art des Belegs. Es sagt nicht, was daraus folgen könnte.

| Statt | Besser |
|---|---|
| „Mustermann steckt mit Nordlicht unter einer Decke“ | „traf 2025 den Vorstand von Nordlicht (eigene Aussage)“ |
| „Nordlicht kaufte sich den Auftrag“ | „Auftrag 2024, 1,2 Mio. € (Vergabebekanntmachung)“ |
| „in Akten zu Nordlicht aufgetaucht“ | „im Prüfbericht 2025 genannt, ohne Vorwurf“ |

### B5 · Vorwurf nur mit Gericht, Behörde oder Vergleich (`vorwurf_mit_instanz`, Standard `hinweis`)

- Ein Vorwurf gegen eine Person, besonders einer Straftat, kommt nur in den Belegspeicher, wenn ein Gericht, eine Behörde
  oder ein Vergleich daran hängt. Auch nicht als „laut Aussage von …“.
- Eigene Schreiben, Entwürfe und Listen einer Person über Dritte sind ein **Dokument** (mit Datum und Vorbehalt), nie eine
  Verbindung zu dem Dritten. Erlaubt: Verfasser → Dokument „schrieb“, Dritter → Dokument „bestreitet“ (mit Dementi),
  Veröffentlicher → Dokument „veröffentlichte“.
- Wer auf einer Liste, in einem Hinweis oder in einer Arbeitsliste einer Behörde steht, bekommt dadurch keinen Faden. Die
  Liste wird ein Dokument, ihr Vorbehalt kommt wörtlich ins Zitat.
- Empfehlung: bei Sexualstraftaten und bei allem, was Minderjährige betrifft, diese Regel auf `sperrt` stellen.

### B6 · Verfahrensstand statt Absicht (`verfahrensstand`, Standard `hinweis`)

Folgen genau benennen und nie eine Stufe überspringen:

- Festnahme ≠ Anklage ≠ Urteil
- Ermittlung ≠ Vorwurf bewiesen
- Vergleich ≠ Schuldeingeständnis
- beantragt ≠ genehmigt, Entwurf ≠ Gesetz, angekündigt ≠ umgesetzt
- Begriffe aus fremden Rechtsordnungen nicht eindeutschen, wenn das die Stufe verschiebt (Beschuldigter ist nicht Angeklagter)

Statt einer Absicht („wollte die Kontrolle übernehmen“) steht der belegte Schritt („beantragte am 03.03. die Mehrheit im
Aufsichtsrat“).

### B7 · Keine Charakterworte (`keine_charakterworte`, Standard `hinweis`)

Keine Wertungen über den Charakter einer Person. „Täter“ nur nach Urteil, „Komplize“ nur nach Verurteilung, „Vertuschung“
nur als Zitat mit Quelle. Ebenso keine Wörter, die Steuerung oder Verschwörung unterstellen („steuert“, „lenkt“,
„unterwandert“, „Marionette“, „Elite“, „Weltregierung“), außer im Originalzitat.

### B8 · Privatpersonen schützen (`privatpersonen`, Standard `sperrt`)

- Privatpersonen (ohne öffentliche Rolle) erscheinen nicht mit vollem Namen, öffentlich höchstens mit Initialen („T. B.“).
- Privatpersonen nie mit Verdacht oder mit ihrer Familie verbinden.
- Betroffene von Straftaten nie mit Namen, nie mit Tatdetails, nie Minderjährige.
- Namen verstecken sich auch in **Quellentiteln** (z. B. Aktenzeichen „Mustermann gegen Stadt Musterhafen“) und in **URLs**.
  Titel neutralisieren („Klage einer Anwohnerin gegen die Stadt, Az. …“) oder die Quelle durch eine andere ersetzen.
- Organisationen, Behörden und Dokumente sind keine Privatpersonen. Markierungen dafür prüfen, sonst schützt die Regel das
  Falsche.
- Wer durch eine öffentliche Aussage (Anhörung, Interview unter Namen) öffentlich geworden ist, gilt für diese Rolle als
  öffentlich.

### B9 · Entlastendes mitnehmen (`entlastendes`, Standard `hinweis`)

Steht in derselben Quelle etwas Entlastendes (ein Dementi, ein Ergebnis einer Untersuchung, „kein Verfahren“), gehört es in
die Fundstelle oder ins Etikett. Ein Zwischenstand ohne das Ergebnis ist irreführend.

### B10 · Primärwortlaut vor Presse (`primaerwortlaut`, Standard `hinweis`)

Die Primärquelle sagt oft weniger als die Presse („prüft, das Angebot in der bisherigen Form fortzuführen“ statt „stellt ein“).
Belegspeicher **und Sprechtext** folgen dem Primärwortlaut. Deshalb gehören Befunde aus der Faktenprüfung auch gegen das
Skript.

### B11 · Auslassungen verschieben keinen Bezug (`auslassung`, Standard `hinweis`)

- Ein Zitat mit „[…]“ darf Sprecher, Bezug und Reihenfolge nicht verändern. Die Stücke stehen in der Reihenfolge des
  Dokuments.
- Bei verbundenen Stücken den Sprecher jedes Stücks prüfen; zwei Personen im selben Artikel ergeben schnell ein Mischzitat.
- Lieber ein Beleg je Stelle als ein Zitat, das Stellen von weit auseinanderliegenden Seiten zusammensetzt.

### B12 · Zeitangaben ehrlich (`zeitraum`, Standard `hinweis`)

Einmal-Ereignisse (Treffen, Aussage, Urteil, Zahlung) haben ein Ende gleich dem Anfang. Laufende Beziehungen (Amt,
Beteiligung, laufende Ermittlung) sind als laufend markiert. Unbekannte Tage stehen als Monats- oder Jahresanfang, mit Vermerk
in der Fundstelle.

### B13 · Quelle gesichert (`sicherung`, Standard `hinweis`)

Jede Quelle mit Link wird gesichert: Original mit SHA-256, Archivkopie, Fundstelle des Zitats. Ohne Sicherung kann eine
geänderte oder gelöschte Seite die Aussage nachträglich unbelegt machen.

## Selbstprüfung vor der Übergabe

Wer Einträge baut (Mensch oder Agent), prüft vor der Übergabe an den Faktenprüfer:

1. Suche im eigenen Ergebnis nach Charakterworten und Steuerungswörtern (B7). Jeder Treffer braucht einen Grund, sonst raus.
2. Suche nach den Namen aller Personen, für die B5 oder B8 gilt. Jeder Treffer braucht einen Grund.
3. Jede Verbindung mit Vorwurf: Hängt ein Gericht, eine Behörde oder ein Vergleich daran? Wenn nein: kein Vorwurf-Faden.
4. Jedes Zitat mit „[…]“: Sprecher jedes Stücks geprüft?

Die Selbstprüfung ersetzt den unabhängigen Faktenprüfer nicht (Skill `recherche-runde`).
