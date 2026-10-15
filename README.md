# quelle-bis-schnitt

Ein Marktplatz für Claude-Code-Plugins. Er bildet einen Arbeitsweg ab, der mit einer Frage beginnt und mit einem fertigen Video endet:

**Recherche → Belege → Skript → Dreh → Schnitt → Abgabe**

Leitsatz: **Agenten recherchieren, Regeln beraten, der Mensch entscheidet und gibt frei.**

[English version](README.en.md)

## Was drin ist

| Plugin | Wofür | Bestandteile |
|---|---|---|
| `recherche` | Quellen finden, Belege sammeln, Zitate prüfen | Skills `quellen-zugang`, `belegregeln`, `recherche-runde`; Agent `faktenpruefer`; Werkzeug `zitate_pruefen.py`; MCP Exa |
| `jina-lesen` | Webseiten und PDFs als Text lesen | MCP Jina mit eigenem Schlüssel |
| `tavily-suche` | zweite Suchmaschine neben Exa | MCP Tavily mit eigenem Schlüssel |
| `skript` | Sprechtexte für Lang- und Kurzvideos | Skills `skript`, `skript-lang`, `skript-short`, `skript-snack`, `skript-trailer`, `hook`, `sprechtext`, `anti-slop-writing`, `viral-methode`; Agenten `hook-blind`, `skript-kritiker`; Prüfskripte |
| `studio` | Dreh mit zwei Kameras, Prompter, Ton, Schnitt in DaVinci Resolve, Abgabe | Skills `dreh-setup`, `zwei-kamera`, `prompter`, `ton-mastering`, `resolve-schnitt`, `abgabe`; Befehl `/studio:einrichten`; Werkzeug `studio` |
| `arbeitsweise` | Regeln für die Arbeit mit Agenten | Skills `arbeitsweise`, `deploy-lock`; Werkzeug `deploy_waechter` |
| `akte` | Ermittler-Board mit Belegpflicht als MCP | Skill `akte-fuehren`; MCP `akte-mcp` aus der [Ultra-Akte](https://github.com/ThePyth0nKid/ultra-akte) ab 0.3.0 (braucht eine lokale Ultra-Akte und `uv`) |

## Installieren

In Claude Code:

```text
/plugin marketplace add ThePyth0nKid/quelle-bis-schnitt
/plugin install recherche@quelle-bis-schnitt
/plugin install skript@quelle-bis-schnitt
/plugin install studio@quelle-bis-schnitt
/plugin install arbeitsweise@quelle-bis-schnitt
```

Jedes Plugin lässt sich einzeln installieren. Nimm nur, was du brauchst.

**Jina und Tavily** brauchen einen eigenen Schlüssel des Anbieters. Claude Code fragt beim Installieren in `/plugin` danach
und legt ihn als geheimen Wert (`sensitive`) im sicheren Speicher deines Systems ab, nicht in `settings.json`.
Nachträglich geht das mit `/plugin configure jina-lesen@quelle-bis-schnitt`.

**Das Werkzeug `studio`** (Klick-Prüfung, Mastern, Kamera-Paare, Prompter, Transkript) ist ein Python-Paket:

```text
uv tool install "git+https://github.com/ThePyth0nKid/quelle-bis-schnitt#subdirectory=plugins/studio/werkzeuge"
studio --version
```

Danach in Claude Code `/studio:einrichten`. Der Befehl legt eine `studio.toml` aus der Vorlage an. Das Werkzeug kennt keine
Standardpfade: Ohne Konfiguration bricht es mit einer klaren Meldung ab.

## Grundsätze

1. **Der Mensch entscheidet.** Prüfskripte und Faktenprüfer beraten nur. Jede Regel ist einstellbar: `aus`, `hinweis` oder
   `sperrt`, Standard `hinweis`. Für jeden Fund entscheidet ein Mensch: übernehmen, verwerfen oder anders. Agenten geben nie
   selbst frei.
2. **Jede Zahl behält ihre Quelle.** Entweder eine öffentliche Quelle mit Link oder eine eigene Messung mit Stichprobengröße
   und Methode in [`docs/messungen/`](docs/messungen/).
3. **Nur die Methode.** Die Skills beschreiben Abläufe, keine bestimmte Person, keinen Kanal und keinen Rechner. Beispiele sind
   erfunden: die Freie Stadt Musterhafen, die Nordlicht Analytik GmbH, Erika und Max Mustermann.
4. **Lokal zuerst.** Alles läuft auf deinem Rechner. Es gibt keinen Server und keine Betriebskosten. Exa, Jina und Tavily sind
   externe Dienste: Deine Suchbegriffe gehen an diese Anbieter.
5. **Keine Umgehung von Bezahlschranken.** `quellen-zugang` zeigt legale Wege (Bibliotheken, Primärquellen, eigene Abos).

## Der Arbeitsweg

| Schritt | Was passiert | Plugin |
|---|---|---|
| Recherche | Primärquellen zuerst, Suche über Exa, Lesen über Jina oder Tavily | `recherche`, `jina-lesen`, `tavily-suche` |
| Belege | drei Recherche-Agenten, ein unabhängiger Faktenprüfer, eine Entscheidungstabelle für den Menschen | `recherche` |
| Skript | sechs Slots, ein Hook, Sprechtext statt Schreibtext, Prüfskripte mit harten Punkten | `skript` |
| Dreh | Prompter mit einem Satz je Abschnitt, zwei Kameras, Ton auf 48 kHz | `studio` |
| Schnitt | Kameras synchronisieren, Knacken messen, Timeline in DaVinci Resolve aus einem Bauplan | `studio` |
| Abgabe | Ton auf −14 LUFS, Video als H.264 | `studio` |

Die ausführliche Anleitung für Dreh und Schnitt steht in [`docs/so-filme-ich.md`](docs/so-filme-ich.md). Das Setup dort ist
ein Beispiel. Trage deine eigenen Werte ein.

## Mitmachen

```text
git config core.hooksPath .githooks      # vor jedem Commit: gitleaks und Sperrliste
uv venv
uv pip install pytest ruff requests -e "plugins/studio/werkzeuge[test]"
uv run --no-sync ruff check .
uv run --no-sync pytest
claude plugin validate --strict .
```

- Der Hook `pre-commit` prüft mit [gitleaks](https://github.com/gitleaks/gitleaks) und mit
  `werkzeuge/scrub/pruefen.py`. Das Skript kennt öffentliche Regeln (Benutzerpfade, private Netze, Schlüsselmuster) und
  optional eine private Sperrliste unter `~/.config/oss-scrub/sperrliste.txt`. Diese Liste gehört nie ins Repo.
- Fremde Skills werden nicht kopiert, nur verlinkt: [`docs/fremde-skills.md`](docs/fremde-skills.md).
- Beispiele bleiben erfunden. Keine realen Personen mit Vorwürfen als Beispiel.

## Lizenz

- Code, Skills, Agenten, Befehle und Werkzeuge: [MIT](LICENSES/MIT.txt)
- Dokumentation in `docs/` und diese READMEs: [CC BY 4.0](LICENSES/CC-BY-4.0.txt)

Die Zuordnung je Datei steht maschinenlesbar in [`REUSE.toml`](REUSE.toml).

Die Belegregeln in `recherche` sind Empfehlungen für sorgfältiges Arbeiten. Sie sind keine Rechtsberatung.
