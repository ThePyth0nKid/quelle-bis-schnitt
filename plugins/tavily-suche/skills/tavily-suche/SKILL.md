---
name: tavily-suche
description: 'Tavily als zweite Suchmaschine für Recherchen neben Exa: tavily_search (Suche), tavily_extract (Seiten als Text), tavily_map und tavily_crawl (Seitenstruktur), tavily_research. Erklärt Schlüssel, Datenschutz, Grenzen beim Crawlen und Fehlerbilder mit Ausweichwegen. Nutze diesen Skill bei „Tavily“, „zweite Suche“, „gegenprüfen mit einer anderen Suchmaschine“, „Seite extrahieren“, „Website durchsuchen“, und wenn Exa am Limit ist.'
---

# Tavily-Suche

Das Plugin `tavily-suche` bindet den MCP-Server von Tavily ein (`https://mcp.tavily.com/mcp/`). Eine zweite Suchmaschine
findet, was die erste übersieht, und eignet sich zum Gegenprüfen. Für die Methode der Recherche gilt der Skill
`quellen-zugang`.

## Werkzeuge

| Werkzeug | Wofür | Hinweis |
|---|---|---|
| `tavily_search` | Suche mit Ausschnitten und URLs | Ausschnitte sind kein Beleg; den Wortlaut am Original prüfen |
| `tavily_extract` | Text einer oder mehrerer Seiten | guter Ausweichweg, wenn ein anderer Lesedienst sperrt |
| `tavily_map` | Seitenstruktur einer Website | zum Finden von Unterseiten (Pressemitteilungen, Archive) |
| `tavily_crawl` | mehrere Seiten einer Website lesen | sparsam: Nutzungsbedingungen der Website gelten; keine lizenzierten Inhalte massenhaft abrufen |
| `tavily_research` | mehrstufige Recherche mit Bericht | Ergebnis ist eine Zusammenfassung: jede Aussage am Original belegen |

## Schlüssel

- Einen API-Schlüssel erzeugst du auf [tavily.com](https://tavily.com). Preise und Kontingente stehen dort.
- Claude Code fragt beim Installieren über `/plugin` danach. Der Wert ist als geheim markiert (`sensitive`) und liegt im
  sicheren Speicher deines Systems, nicht in `settings.json`
  ([Claude-Code-Doku zu Plugin-Optionen](https://code.claude.com/docs/en/plugins/manifest-reference.md)).
- Ändern: `/plugin configure tavily-suche@quelle-bis-schnitt`. In der Shell zeigt
  `claude plugin configure tavily-suche@quelle-bis-schnitt`, ob der Wert gesetzt ist.
- Nach einer Änderung Claude Code neu starten.
- Ob der Schlüssel greift, zeigt die Antwort: Steht dort ein Hinweis auf eine Anmeldung mit Schlüssel (z. B.
  `"auth_mode": "keyed"`), wird nicht das Gastkontingent benutzt.
- Den Schlüssel nie in den Chat, in Dateien oder Skripte schreiben.

## Datenschutz

Jede Suchanfrage und jede URL geht an Tavily. Wer zu heiklen Themen recherchiert, verrät dem Anbieter das Thema. Lies die
Datenschutzhinweise des Anbieters.

## Fehlerbilder

| Meldung | Bedeutung | Was tun |
|---|---|---|
| HTTP 401 | Schlüssel fehlt oder ist falsch | `/plugin configure tavily-suche@quelle-bis-schnitt`, dann neu starten |
| Kontingent oder Guthaben erschöpft | Gratis-Credits verbraucht | aufladen, auf den nächsten Zeitraum warten oder ausweichen (unten) |
| Server nicht verbunden (`/mcp`) | Schlüssel fehlt, Netz oder Dienst gestört | `/mcp` prüfen, Schlüssel setzen, neu starten |

**Ausweichwege:** Exa (Plugin `recherche`), Jina (Plugin `jina-lesen`), die eingebaute Websuche, und für Wortlaute `curl -sL`
mit neutraler Kennung. Für Zitate danach `zitate_pruefen.py` (Plugin `recherche`).
