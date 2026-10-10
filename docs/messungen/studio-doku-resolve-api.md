# Messung: Verhalten der Skript-Schnittstelle von DaVinci Resolve Studio 21.1

Verwendet in: `plugins/studio/skills/resolve-schnitt/referenz/api-fakten.md` und den Skripten des Skills
`resolve-schnitt`.

| Angabe | Inhalt |
|---|---|
| Frage | Was tun die Aufrufe der Skript-Schnittstelle wirklich (Einheiten, Vorzeichen, Rückgaben bei Fehlern), unabhängig davon, was die Doku sagt? |
| Stichprobe | Eine Installation von DaVinci Resolve Studio 21.1 unter Windows. Je Aufruf ein bis wenige Versuche in einem Wegwerf-Projekt. Material synthetisch: 4K-Video mit eingebranntem Bildzähler (Nummer je Bild), Alpha-Karten in ProRes 4444 und VP9-WebM, Testtöne. |
| Zeitraum | Oktober 2026. |
| Verfahren | Jeder Aufruf von außen (Python mit den Skript-Modulen von Resolve), danach Zustand zurückgelesen (`GetStart`, `GetDuration`, `GetProperty`, `GetMarkers` …). Bildlage, Blenden und Keyframes zusätzlich an gerenderten Bildern oder Standbildern geprüft: Bildzähler ablesen, Verschiebungen per Phasenkorrelation messen. Fehlerfälle (fehlende Spur, Überlappung, falscher Name) absichtlich ausgelöst. |
| Ergebnis | Die Tabellen und Fallen in `api-fakten.md`, z. B. `endFrame` exklusiv, Marker relativ zum Timeline-Start, Tilt-Faktor ≈ 0,3167 im Hochformat (Pan 300 → 300 px, Tilt 300 → 95 px), totes Objekt statt Fehlermeldung bei fehlender Spur. |
| Grenzen | Eine Version, ein Betriebssystem, eine Maschine. Andere Versionen oder macOS/Linux können abweichen. Zeiten (Renderdauer, Transkriptionsdauer) hängen von der Hardware ab und stehen deshalb nicht im Skill. Die freie Fassung von Resolve wurde nicht geprüft. |
| Rohdaten | Nicht veröffentlicht (Protokolle eines Arbeitsrechners). Der Messlauf lässt sich mit synthetischem Material in einem Wegwerf-Projekt wiederholen; das ist nach jedem Resolve-Update empfohlen. |
