# Messung: Was findet ein unabhängiger Faktenprüfer vor dem Import?

Verwendet in: Skill `recherche-runde` (Plugin `recherche`), Schritt 5.

| Angabe | Inhalt |
|---|---|
| Frage | Findet ein unabhängiger Faktenprüfer-Agent vor dem Import noch Fehler, wenn die bauenden Agenten ihre Selbstprüfung schon bestanden haben? |
| Stichprobe | n = 3 Recherche-Runden zu politischen Themen mit realen Personen, Firmen und Behörden. Je Runde drei Recherche-Agenten, mehrere Import-Agenten und ein Faktenprüfer in frischem Kontext. |
| Zeitraum | Ende September bis Anfang Oktober 2026 |
| Verfahren | Die Import-Agenten prüften ihre Dateien selbst (Leitplanken-Suche, Zitatprüfung mit einem Vorgänger von `zitate_pruefen.py`). Danach las ein eigener Agent, der nichts gebaut hatte, die Importdateien gegen Auftrag, Berichte und selbst geladene Originale (curl mit neutraler Kennung, PDFs mit pypdf bzw. PyMuPDF, Tonstellen mit mehreren Whisper-Modellen). Er sortierte die Funde nach Schwere (HOCH, MITTEL, NIEDRIG) und schlug Korrekturen vor. Gezählt wurden die Funde in seinem Bericht. |
| Ergebnis | Runde 1: 33 Funde, davon 13 als rechtlich heikel eingestuft (Aufteilung nach Schwere nicht festgehalten). Runde 2: 196 Verbindungen, 30 Funde (3 HOCH, 9 MITTEL, 18 NIEDRIG); 165 von 196 Verbindungen (84 %) am Original geprüft. Runde 3: 241 Verbindungen, 24 Funde (1 HOCH, 11 MITTEL, 12 NIEDRIG) und 7 Hinweise ohne Korrektur; 111 von 241 Verbindungen (46 %) an mindestens einem selbst geladenen Original geprüft. In allen drei Runden hatten die bauenden Agenten ihre Selbstprüfung bestanden. |
| Grenzen | Kleine Stichprobe, ein Team, ein Arbeitsablauf. Die Schwere hat der Prüfer selbst eingestuft. Ob ein zweiter Prüfer dieselben Funde gefunden hätte, wurde nicht gemessen. Der Anteil am Original geprüfter Verbindungen schwankt stark. Die Messung zeigt, dass ein Prüfer vor dem Import etwas findet, nicht, dass er alles findet. |
| Rohdaten | Nicht veröffentlicht: Die Berichte enthalten Recherchen zu realen Personen. |
