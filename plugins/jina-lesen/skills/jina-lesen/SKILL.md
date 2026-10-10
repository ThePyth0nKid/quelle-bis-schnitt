---
name: jina-lesen
description: 'Jina als Lesewerkzeug für Recherchen: Webseiten und PDFs mit read_url als Text holen, gezielt Stellen zu einer Frage auslesen, das Veröffentlichungsdatum schätzen, im Netz suchen. Erklärt Schlüssel, Datenschutz und Fehlerbilder (401, 402) mit Ausweichwegen. Nutze diesen Skill bei „Seite lesen“, „PDF lesen“, „Jina“, „read_url“, „Datum der Seite“, wenn Jina 401 oder 402 meldet, und vor jedem Recherche-Agenten, der Originale lesen soll.'
---

# Jina lesen

Das Plugin `jina-lesen` bindet den MCP-Server von Jina ein (`https://mcp.jina.ai/v1`). Er liest Webseiten und PDFs als
Markdown und hilft beim Finden. Für die Methode der Recherche gilt der Skill `quellen-zugang`.

## Werkzeuge

| Werkzeug | Wofür | Hinweis |
|---|---|---|
| `read_url` | Seite oder PDF als Markdown | mit `question` nur die passenden Stellen; bei langen PDFs `question` weglassen und gezielt lesen |
| `guess_datetime_url` | Veröffentlichungsdatum schätzen | nur eine Schätzung: Datum immer auf der Seite nachprüfen |
| `search_web`, `search_arxiv`, `search_ssrn` | Suche im Netz und in Preprints | Treffer-Ausschnitte sind kein Beleg; den Wortlaut am Original prüfen |

Ein Wortlaut für einen Beleg kommt nie aus einer Zusammenfassung, sondern aus dem Rohtext der Quelle.

## Schlüssel

- Einen API-Schlüssel erzeugst du auf [jina.ai](https://jina.ai) im Bereich für die API.
- Claude Code fragt beim Installieren über `/plugin` danach. Der Wert ist als geheim markiert (`sensitive`) und liegt im
  sicheren Speicher deines Systems, nicht in `settings.json`
  ([Claude-Code-Doku zu Plugin-Optionen](https://code.claude.com/docs/en/plugins/manifest-reference.md)).
- Ändern: `/plugin configure jina-lesen@quelle-bis-schnitt`. In der Shell zeigt
  `claude plugin configure jina-lesen@quelle-bis-schnitt`, ob der Wert gesetzt ist.
- Nach einer Änderung Claude Code neu starten, damit der MCP-Server den neuen Schlüssel nimmt.
- Den Schlüssel nie in den Chat, in Dateien oder Skripte schreiben.

## Datenschutz

Jede URL und jede Frage geht an Jina. Wer zu heiklen Themen recherchiert, verrät dem Anbieter das Thema. Lies die
Datenschutzhinweise des Anbieters.

## Fehlerbilder

| Meldung | Bedeutung | Was tun |
|---|---|---|
| HTTP 401 | Schlüssel fehlt oder ist falsch | `/plugin configure jina-lesen@quelle-bis-schnitt`, dann neu starten |
| HTTP 402 | Guthaben aufgebraucht | aufladen oder ausweichen (unten) |
| Sperre für einzelne Seiten (z. B. soziale Netzwerke) | der Anbieter oder die Seite blockt | Skill `quellen-zugang`, Falle zu Posts in sozialen Netzwerken |
| „Question-grounded extraction was unavailable“ | gezieltes Auslesen ging nicht, die ganze Seite kommt zurück | bei kurzen Seiten egal; bei langen Dokumenten selbst laden und gezielt lesen |
| Server nicht verbunden (`/mcp`) | Schlüssel fehlt, Netz oder Dienst gestört | `/mcp` prüfen, Schlüssel setzen, neu starten |

**Ausweichwege, wenn Jina nicht geht:** Exa `web_fetch` (Plugin `recherche`), Tavily `extract` (Plugin `tavily-suche`),
`curl -sL` mit neutraler Kennung und PDFs mit `pypdf` im Speicher. Für Zitate danach `zitate_pruefen.py` (Plugin `recherche`).
