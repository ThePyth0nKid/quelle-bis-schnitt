<!-- SPDX-License-Identifier: MIT -->
<!-- Baustein zum Einfügen in ein eigenes CLAUDE.md. Passe die Platzhalter in <spitzen Klammern> an. -->

## Arbeitsweise

### Review nach Code-Änderungen
- Erst selbst verifizieren: Typecheck, Build, Tests, Smoke-Test, der die Änderung wirklich ausführt.
- Dann EIN unabhängiger Review-Agent über den Diff (nicht über die Zusammenfassung des Bau-Agenten).
- Bei Auth, Eingaben von außen, Secrets oder Geld zusätzlich ein Security-Review.
- Die Selbstbewertung eines Bau-Agenten zählt nicht als Review.
- Volles Multi-Agent-Fan-out nur bei echtem Sicherheits- oder Datenschutzrisiko.
- Review-Befunde sind Empfehlungen. Ich entscheide je Befund: übernehmen, verwerfen oder anders.

### Planen
- Komplexe Aufgaben (mehrere Dateien, Umbau, Recherche plus Entwurf): Planmodus, Bestand erkunden, Plan zur Freigabe
  vorlegen. Gebaut wird erst nach meiner Freigabe.
- Einfache Mehrschritt-Aufgaben: eine Aufgabenliste reicht.

### Secrets
- Keine Secrets im Code, in Commits oder im Chat. Umgebungsvariablen oder Secret-Manager.
- Ein möglicherweise offengelegtes Secret sofort rotieren.
- Hooks nie mit `--no-verify` umgehen.

### Ablage
- Repos und Code: `<projektordner>`
- Proben, Zwischenstände, Wegwerf-Ausgaben: Scratchpad der Sitzung, sonst `<scratch-ordner>`
- Dokumente: `<dokumentenordner>/<thema>`
- Nichts Neues auf den Desktop.

### Commits
- Format `<type>: <beschreibung>`, Typen feat, fix, refactor, docs, test, chore, perf, ci.
- Commit und Push nur auf meinen Wunsch.

### Deploys
- Vor jedem Deploy: `python <pfad>/deploy_waechter/waechter.py acquire --halter "<strang>" --bereich "<was>"`,
  dann `… obermenge [--art <art>]`. Exit 1 heißt: nicht deployen.
- Danach immer `… release --halter "<strang>" --ergebnis "<ergebnis>" --ausgeliefert <commit>`.
- Die Ausgabe des Wächters nie pipen (`| tail`, `| head`): Dann geht sein Exit-Code verloren.
