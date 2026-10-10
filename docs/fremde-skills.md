# Fremde Skills, die gut dazu passen

Diese Skills und Plugins stammen nicht aus diesem Repo. Sie werden hier **nur verlinkt, nie kopiert**: Sie gehören ihren
Autorinnen und Autoren, haben eigene Lizenzen und werden dort gepflegt. Installiere sie aus der jeweiligen Quelle und lies
vorher deren Lizenz und Hinweise.

Stand der Links: Oktober 2026. Prüfe vor der Installation, ob die Quelle noch die offizielle ist.

## Video und Bewegtbild

| Skill | Wofür | Quelle | Lizenz |
|---|---|---|---|
| HyperFrames (`hyperframes`, `hyperframes-*`, `general-video`, `motion-graphics`, `embedded-captions`, `media-use` …) | Videos und Animationen als HTML-Kompositionen bauen und rendern | [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | siehe Repo |
| `capcut-edit` | CapCut-Entwürfe per Kommandozeile bearbeiten (inoffiziell, nicht von ByteDance) | [renezander030/capcut-cli](https://github.com/renezander030/capcut-cli) | siehe Repo |

Das Plugin `studio` schneidet in DaVinci Resolve über die offizielle Skript-Schnittstelle. Eine CapCut-Kette ist bewusst nicht
enthalten, weil sie auf einer inoffiziellen Schnittstelle beruht.

## Bild, 3D und Spiele-Assets

| Skill | Wofür | Quelle | Lizenz |
|---|---|---|---|
| Scenario (`scenario`, `scenario-*`) | Bilder, Video, 3D und Spiele-Assets über den Scenario-MCP | [mcp.scenario.com/docs](https://mcp.scenario.com/docs) | laut Skill-Frontmatter MIT |

## Design und Marke

| Skill | Wofür | Quelle | Lizenz |
|---|---|---|---|
| `impeccable` | Oberflächen entwerfen, prüfen und verfeinern | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | siehe Repo |
| `ui-ux-pro-max` | Stile, Farbpaletten, Schriftpaare für Oberflächen | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | MIT |
| `claude-design` | HTML-Entwürfe: Präsentationen, Landingpages, Prototypen | mehrere Fassungen auf GitHub, z. B. [jiji262/claude-design-skill](https://github.com/jiji262/claude-design-skill); Herkunft vor der Nutzung prüfen | siehe Repo |
| RampStack (`brand-identity`, `brand-ideation`, `brand-style-guide`, `art-direction`, `logo-design`) | Marke, Logo, Stilhandbuch, Bildsprache | [rampstackco/claude-skills](https://github.com/rampstackco/claude-skills) | siehe Repo |

## Von Anthropic

| Skill | Wofür | Quelle | Lizenz |
|---|---|---|---|
| `theme-factory`, `canvas-design`, `algorithmic-art`, `web-artifacts-builder`, Dokument-Skills (`docx`, `pdf`, `pptx`, `xlsx`) | Gestaltung, Artefakte, Office-Dateien | [anthropics/skills](https://github.com/anthropics/skills) | je Skill unterschiedlich, siehe Repo |
| offizielle Plugins (z. B. Sicherheits-Scan, Plugin-Entwicklung) | Plugins von Anthropic und Partnern | [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) | je Plugin |

## Code-Review und Planung

| Skill oder Agent | Wofür | Quelle | Lizenz |
|---|---|---|---|
| ECC: Agenten `code-reviewer`, `python-reviewer`, `security-reviewer`, `architect`; Skill `blueprint` | Review nach Änderungen, Sicherheitsprüfung, Pläne über mehrere Sitzungen | [affaan-m/ECC](https://github.com/affaan-m/ECC) (früher `everything-claude-code`) | MIT |

Das Plugin `arbeitsweise` beschreibt, **wann** ein unabhängiger Review-Agent laufen soll. Welchen Agenten du dafür nimmst,
entscheidest du. Die ECC-Agenten sind eine Möglichkeit, die eingebauten Befehle von Claude Code (`/code-review`,
`/security-review`) eine andere.

## Warum nicht kopieren?

- **Lizenz und Urheberschaft:** Auch freie Lizenzen verlangen Namensnennung und den Lizenztext. Ein Link erfüllt das sauberer
  als eine Kopie, die veraltet.
- **Pflege:** Die Originale werden weiterentwickelt. Eine Kopie friert einen alten Stand ein.
- **Sicherheit:** Skills mit Skripten führen Code aus. Installiere sie aus der offiziellen Quelle, nicht aus einer Kopie.
