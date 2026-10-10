---
name: arbeitsweise
description: Arbeitsregeln für Claude Code und seine Agenten. Nach jeder Code-Änderung erst selbst prüfen (Typecheck, Build, Smoke-Test), dann EIN unabhängiger Review-Agent über den Diff, bei Auth, Eingaben von außen, Secrets oder Geld zusätzlich ein Security-Review; die Selbstbewertung eines Bau-Agenten zählt nicht. Dazu Planmodus für Komplexes, Secrets nie im Code, Ablage nach Prinzip, Commit-Format. Nutze diesen Skill nach jeder Code-Änderung vor dem „fertig“, bei „Review“, „prüf das“, „ist das fertig?“, „Plan“, „Secret“, „API-Schlüssel“, „wohin speichern“, „commit“, und bevor du einem Bau-Agenten glaubst, dass etwas funktioniert.
---

# Arbeitsweise

Agenten bauen schnell. Diese Regeln sorgen dafür, dass das Ergebnis geprüft ist, bevor jemand „fertig“ sagt, und dass
der Mensch die Entscheidungen trifft, die ihm gehören.

## 1. Review nach jeder Code-Änderung

Reihenfolge, immer:

1. **Selbst prüfen.** Typecheck, Build, Tests, ein Smoke-Test, der die Änderung wirklich ausführt (Befehl starten, Seite
   öffnen, Endpunkt aufrufen). Ein grüner Test, der die geänderte Stelle nicht berührt, ist kein Beleg.
2. **EIN unabhängiger Review-Agent über den Diff.** Er bekommt den Diff (`git diff`, Branch-Vergleich oder PR), nicht
   die Zusammenfassung des Bau-Agenten. Er kennt den Bauweg nicht und urteilt nur über das Ergebnis. Für Python ein
   Python-spezifischer Reviewer, sonst ein allgemeiner.
3. **Zusätzlich ein Security-Review**, wenn die Änderung eines davon berührt:
   - Anmeldung, Rechte, Sitzungen, Tokens
   - Eingaben von außen (Formulare, URLs, Dateien, Webhooks, Daten aus dem Netz)
   - Secrets (Schlüssel, Passwörter, Zugangsdaten)
   - Geld (Zahlungen, Rechnungen, Abrechnung)
4. **Der Mensch entscheidet je Befund:** übernehmen, verwerfen oder anders lösen. Review-Agenten beraten, sie geben nicht
   frei.

Welchen Review-Agenten du nimmst, entscheidest du. Claude Code bringt `/code-review` und `/security-review` mit; fremde
Review-Agenten stehen in `docs/fremde-skills.md` im Repo dieses Plugins.

**Die Selbstbewertung eines Bau-Agenten zählt nicht als Review.** „Ich habe alles geprüft, es funktioniert“ ist eine
Behauptung desselben Agenten, der die Fehler gemacht hat. Ein Review braucht einen frischen Kontext.

**Volles Fan-out (mehrere Reviewer parallel, mehrere Linsen) nur bei echtem Sicherheits- oder Datenschutzrisiko.** Für
alles andere reicht ein Reviewer. Mehr Agenten heißt mehr Kosten, mehr Rauschen und mehr Befunde, die niemand liest.

## 2. Planen

- **Komplexe Aufgaben** (Recherche plus Entwurf, mehrere Dateien, Umbau, unklare Anforderungen): den eingebauten
  Planmodus von Claude Code nutzen. Erst den Bestand erkunden, dann den Plan vorlegen. Gebaut wird erst, wenn der Mensch
  den Plan freigegeben hat.
- **Einfache Mehrschritt-Aufgaben:** eine Aufgabenliste (Checkliste) reicht. Kein Plan-Dokument für drei Schritte.
- Ein Plan nennt: Ziel, betroffene Dateien, Schritte, wie geprüft wird, was bewusst nicht gemacht wird.

## 3. Secrets

- **Nie im Code, nie in Commits, nie im Chat.** Schlüssel kommen aus Umgebungsvariablen oder einem Secret-Manager.
  Beispiel- und Vorlagedateien enthalten nur den Namen der Variablen, nie den Wert.
- **Vor jedem Commit scannen**, z. B. mit [gitleaks](https://github.com/gitleaks/gitleaks) als `pre-commit`-Hook.
- **Ein möglicherweise offengelegtes Secret sofort rotieren.** Erst neu ausstellen und das alte sperren, dann aufräumen.
  Aus der Git-Historie löschen allein reicht nicht: Wer geklont oder gecacht hat, hat es schon.
- Agenten lesen keine Dateien mit Zugangsdaten aus, nur um „nachzusehen“. Wer einen Schlüssel braucht, fragt den Menschen,
  wo er liegt.

## 4. Ablage nach Prinzip

- **Projekte, Daten und Wegwerf-Ausgaben trennen.** Code und Repos in einen Projektordner, Proben und Zwischenstände in
  einen Scratch-Ordner (bei Claude Code: das Scratchpad der Sitzung), Dokumente in einen Dokumentenordner nach Thema.
- **Nichts Neues auf den Desktop.** Der Desktop gehört dem Menschen.
- **Einen festen Ort je Art.** Wer etwas ablegt, legt es dorthin, wo die nächste Person es sucht, nicht dorthin, wo es
  gerade bequem ist.
- **Verschieben ist eine Entscheidung des Menschen.** Agenten kopieren lieber, als bestehende Ordner umzubauen, und
  löschen nichts, was sie nicht selbst angelegt haben.
- Verknüpfungen (Junctions, Symlinks) nur mit dem passenden Befehl entfernen, nie mit rekursivem Löschen: Das löscht das
  Ziel mit.

## 5. Commits

```
<type>: <beschreibung>

<optionaler Text: was und warum>
```

Typen: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`.

- Ein Commit je zusammenhängender Änderung; jeder Commit soll für sich bauen und testen.
- Hooks nie mit `--no-verify` umgehen. Schlägt ein Hook an, den Inhalt bereinigen.
- Commit und Push nur, wenn der Mensch es will. Auf dem Hauptbranch zuerst einen eigenen Branch anlegen.

## 6. Deploys

Vor jedem Deploy: Lock holen und die Obermenge prüfen. Das beschreibt der Skill `deploy-lock` in diesem Plugin.

## 7. Fallen

### F1 · „Alles geprüft“ ohne Prüfung

**Symptom:** Der Bau-Agent meldet „fertig, getestet“, beim ersten echten Aufruf bricht es.
**Ursache:** Der Agent hat seine eigene Arbeit bewertet oder nur Tests laufen lassen, die die Änderung nicht berühren.
**Gegenmittel:** Smoke-Test, der die geänderte Stelle wirklich ausführt, dann ein Review-Agent mit frischem Kontext über
den Diff.

### F2 · Review über die Zusammenfassung statt über den Diff

**Symptom:** Der Reviewer findet nichts, der Fehler steht trotzdem im Code.
**Ursache:** Der Reviewer hat nur die Beschreibung des Bau-Agenten gelesen und dessen Annahmen übernommen.
**Gegenmittel:** Dem Reviewer den Diff oder die Dateien geben, nicht den Bericht.

### F3 · Secret im Beispiel

**Symptom:** Ein echter Schlüssel steht in `.env.example`, einer Vorlage oder einem Testfall.
**Ursache:** Beim Anlegen der Vorlage wurde die echte Datei kopiert.
**Gegenmittel:** Vorlagen nur mit Variablennamen und Platzhaltern; Secret-Scan im `pre-commit`-Hook; offengelegte
Schlüssel sofort rotieren.

### F4 · Hook umgangen

**Symptom:** Ein Commit enthält, was der Hook hätte stoppen sollen.
**Ursache:** `git commit --no-verify`, weil der Hook „im Weg“ war.
**Gegenmittel:** Nie `--no-verify`. Den Fund lesen und den Inhalt bereinigen. Fehlalarme im Hook beheben, nicht den Hook
umgehen.

### F5 · Zu viele Reviewer

**Symptom:** Fünf Agenten liefern vierzig Befunde, die Hälfte widerspricht sich, niemand arbeitet sie ab.
**Ursache:** Volles Fan-out für eine gewöhnliche Änderung.
**Gegenmittel:** Ein Reviewer als Standard, Security-Review nur bei den Auslösern aus Abschnitt 1, Fan-out nur bei echtem
Sicherheits- oder Datenschutzrisiko.

## Vorlage

Ein Baustein zum Einfügen in das eigene `CLAUDE.md` liegt unter `vorlagen/CLAUDE.md-baustein.md` neben dieser Datei.
