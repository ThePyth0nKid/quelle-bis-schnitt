# Auftrag Recherche-Runde <nummer>: <thema>

Stichtag: <JJJJ-MM-TT> · Belegspeicher: <tabelle | datenbank | akte> · Ordner für Berichte: `<projektordner>/recherche/`

## Was du darfst und was nicht

- Du schreibst nur deinen Bericht `<nummer><buchstabe>_bericht_<teilthema>.md` in den Ordner oben.
- Du importierst nichts und änderst keinen Belegspeicher, keine Datenbank, kein Repo.
- Keine Umgehung von Bezahlschranken, archive.today nie als Beleg (Skill `quellen-zugang`).
- Abrufe mit neutraler Kennung, ohne E-Mail-Adresse im User-Agent.
- Keine Schlüssel in Dateien oder Text.
- Privatpersonen nennst du im Bericht nur mit Initialen.

## Fragen

1. <Frage 1>
2. <Frage 2>
3. <Frage 3>

## Teilthemen und Zuständigkeit

| Agent | Teilthema | Bericht |
|---|---|---|
| A | <z. B. Vergabe und Verträge der Freien Stadt Musterhafen> | `<nummer>a_bericht_….md` |
| B | <z. B. Rat, Ausschüsse, Abstimmungen> | `<nummer>b_bericht_….md` |
| C | <z. B. Nordlicht Analytik GmbH: Eigentum, Register, Geschäftsberichte> | `<nummer>c_bericht_….md` |

Bei Überschneidungen legt nur der hier genannte Agent die Verbindung an; die anderen nennen die Karte nur als Verweis.

| Thema | Zuständig |
|---|---|
| <Überschneidung> | <A/B/C> |

## Leitplanken (Belegregeln dieser Runde)

Stufen aus `belegregeln.toml` (Standard `hinweis`, Privatpersonen `sperrt`). Für diese Runde zusätzlich:

| Regel | Stufe | Themenbezogene Leitplanke |
|---|---|---|
| B5 Vorwurf nur mit Instanz | <hinweis/sperrt> | <wer darf mit welchem Vorwurf vorkommen, wer ausdrücklich nicht> |
| B6 Verfahrensstand | <hinweis/sperrt> | <z. B. Ermittlung läuft, keine Anklage> |
| B8 Privatpersonen | sperrt | <welche Beteiligten Privatpersonen sind> |
| … | | |

**Lies die Leitplanken zweimal.**

## Bestand

Vorhandene Karten und Quellen: `<bestand_karten.tsv>`, `<bestand_quellen.tsv>`. Bekannte Quellen übernimmst du mit genau dem
dortigen Titel, bekannte Karten mit genau dem dortigen Schlüssel.

## Berichtsformat

Je Behauptung ein Block:

```text
**<A07> · <Behauptung in einem Satz, mit Datum>**
- Quelle: <Titel> | <Herausgeber> | <URL> | <TT.MM.JJJJ> | primaer|sekundaer
- Wörtlich: „<Originalwortlaut>“   (oder: – <Grund: nur Titel abrufbar, Bezahlschranke, Übersetzung durch …>)
- Stand: am Original geprüft | Wortlaut offen | nur Presse
```

- `primaer` nur für das Original (Gericht, Behörde, Parlament, Register, Gesetz, Firmenmitteilung, eigene Erklärung, eigener
  Post, Transkript). Presse ist `sekundaer`, auch wenn sie ein Original zitiert.
- Übersetzungen durch Dritte sind kein Originalwortlaut.
- Belastendes und Entlastendes aus derselben Quelle gehören zusammen.

Am Ende des Berichts:
- **Was die Recherche NICHT trägt:** Negativbefunde mit Quelle und Stichtag, Behauptungen ohne Beleg
- **Offene Fragen** (höchstens acht)

## Zum Schluss (Pflicht)

1. Leitplanken-Selbstprüfung: Charakterworte, Steuerungswörter, Namen aus B5/B8. Jeder Treffer braucht einen Grund.
2. Zitate prüfen: `python "${CLAUDE_PLUGIN_ROOT}/werkzeuge/zitate_pruefen.py" <belege.json>`; jedes `nicht_gefunden` am
   Original klären oder „Wörtlich: –“ mit Grund.
3. Kurzer Abschluss (höchstens 25 Zeilen): Zahl der Behauptungen, davon primär, Wortlaut geprüft, was du nach den
   Leitplanken weggelassen hast und warum.
