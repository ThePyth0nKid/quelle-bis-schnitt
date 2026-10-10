---
name: resolve-schnitt
description: Baut ein Video als vollständig bearbeitbare Timeline in DaVinci Resolve aus einem Bauplan (JSON) – Projekt, benannte Spuren, bildgenaue Clips, Bildlage und Punch-ins, Fusion-Push-ins, Alpha-Overlays, Pegel, Blenden, Marker, Render und Standbilder – über die Skript-Schnittstelle von außen. Enthält die am Programm gemessenen API-Fakten und Fallen. Nutze diesen Skill bei „in Resolve schneiden“, „Timeline bauen“, „Resolve-Projekt“, „DaVinci“, „Zwei-Kamera-Schnitt in Resolve“, „Sichtfassung rendern“ und immer, bevor ein Skript die Resolve-API anfasst.
---

# Schnitt in DaVinci Resolve aus einem Bauplan

Der Bauplan ist eine werkzeugneutrale Schnittliste. Aus ihm entsteht in Resolve eine **neue** Timeline, in der jeder
Baustein einzeln auf einer benannten Spur liegt, damit ein Mensch danach alles von Hand schieben kann. Die API hat kein
Undo: Jeder Bau ist eine neue Timeline, vor jedem schreibenden Lauf entsteht eine `.drp`-Sicherung.

**Der Mensch entscheidet.** Der Bau ist ein Vorschlag. Abgenommen wird an der Sichtfassung mit Bild und Ton durch einen
Menschen, nicht an einem grünen Bericht.

## 1. Erst lesen

1. `referenz/api-fakten.md`: was die API wirklich tut (gemessen, nicht aus der Doku), dazu die Fallen F1–F22.
2. Bevor eine Timeline gebaut wird: Ton gemessen (`studio klick-check`, Skill `ton-mastering`) und Kameras gepaart
   (Skill `zwei-kamera`). Ein Schnitt auf kaputtem Ton ist verlorene Arbeit.

## 2. Werkzeuge (`scripts/`)

| Skript | Aufruf | Zweck |
|---|---|---|
| `resolve_bereit.py` | `<resolve-python> -u resolve_bereit.py [--warten 120] [--projekt <Name>]` | wartet, bis Resolve von außen antwortet (erst der Prozess `fuscript`, dann die API, F4) |
| `bauplan.py` | `python bauplan.py pruefen <plan.json>` · `… statistik <plan.json> --spur Kamera` | Format, Prüfung (Fehler gegen Hinweise), Bildrechnung, Schnittzahlen |
| `resolve_bauen.py` | `<resolve-python> -u resolve_bauen.py <plan.json> [--sicherung <ordner>] [--bericht <datei>]` | Projekt, Media Pool, neue Timeline `<name>-HHMM`, Spuren, Clips, Lage, LUT, Pegel, Blenden, Paare, Fahrten, Übergänge, Marker; liest jede Platzierung zurück |
| `resolve_rendern.py` | `<resolve-python> -u resolve_rendern.py --ziel <ordner> [--projekt …] [--timeline …] [--format mov --codec ProRes422HQ] [--stills 1.5,12]` | Render über die Queue, nie auf eine vorhandene Datei; Standbilder mit Aufwärmbild und Prüfsummen (F19) |
| `resolve_api.py` | (Modul) | gemeinsame Hüllen: verbinden, Projekt holen ohne „Untitled“ zu speichern, sichern, importieren, neue Timeline |

`<resolve-python>` ist ein Python, das die Skript-Module von Resolve findet:
- das mit Resolve mitgelieferte Python, falls deine Version eines hat (unter Windows z. B.
  `%ProgramFiles%\Blackmagic Design\DaVinci Resolve\ResolvePython\ResolvePython.exe`; überschreibbar mit
  `$RESOLVE_PYTHON`), oder
- ein System-Python mit `RESOLVE_SCRIPT_API`, `RESOLVE_SCRIPT_LIB` und `PYTHONPATH` nach der Scripting-README im
  Developer-Ordner von Resolve.

In Resolve unter **Preferences › System › General › External scripting using** „Local“ einstellen. Getestet ist die
Kette mit Resolve Studio 21.1 unter Windows. Ob deine Fassung Skripte von außen annimmt, zeigt `resolve_bereit.py`.

Die Skripte brauchen nur die Standardbibliothek. Alles mit numpy, ffmpeg oder Whisper läuft im System-Python (Werkzeug
`studio`) und reicht Dateien weiter.

## 3. Der Bauplan

Format und Einheiten stehen im Kopf von `scripts/bauplan.py`. Das Wichtigste:

- Zeiten in Sekunden; umgerechnet in Bilder wird **nur** in `bauplan.py` (kumulativ gerundet, damit lückenlose Spuren
  lückenlos bleiben).
- `pan`/`tilt`/`crop` in Timeline-Pixeln mit Resolves Vorzeichen, `zoom` als Faktor. `lage_aus_fenster()` rechnet einen
  Ausschnitt der Quelle (x, y, b, h) in zoom/pan/tilt um (Querformat; Hochformat siehe api-fakten.md).
- `fahrt` (von, bis, pivot) wird ein Fusion-Keyframe-Zoom mit Subpixel-Bewegung.
- `paar` verknüpft Bild und Ton, damit sie beim Handschnitt zusammen wandern.
- `lut`: Datei unter Resolves LUT-Ordner (`$RESOLVE_LUT_ORDNER` oder Standardort des Systems).
- `pruefen` bricht bei **Fehlern** ab (Überlappung, Lücke in einer lückenlosen Spur, fehlende Quelle, Standbild als
  Videoquelle, unbekannte Markerfarbe …) und gibt **Hinweise** zurück (z. B. Einblendung ohne Handlung). Hinweise
  entscheidet der Mensch.

**Spurbild (Vorschlag):** V1 Kamera A · V2 Kamera B · V3 Einsätze (Grafiken, Ausschnitte) · V4 Belege · V5–V7 Overlays ·
A1 Stimme · A2 Originalton der Kameras (stumm, verknüpft) · A3/A4 Klänge · A5 Musik. Ein Baustein je Spur hält die
Timeline von Hand bearbeitbar.

**Bildlage aus einem Gesichtskasten** (Querformat, 4K-Kamera in 1080p-Timeline, Zoom z; alle Lagen relativ 0–1 von
links oben): `fx` = Gesichtsmitte und `augen` = Augenhöhe in der Quelle, `ox`/`oy` = wo Gesichtsmitte und Augenlinie im
fertigen Bild stehen sollen. Dann `Pan = (ox − 0,5 − (fx − 0,5)·z)·1920` und `Tilt = (0,5 + (augen − 0,5)·z − oy)·1080`,
begrenzt auf `±(z−1)·960` und `±(z−1)·540`, damit kein Rand ins Bild rutscht. Größen und Augenlinie sind Geschmack: Beispielwerte aus einem Setup (nicht gemessen) sind weit 1,0,
halbnah 1,3, nah 1,45, eng 1,9, Augenlinie bei 0,40 der Bildhöhe von oben.

## 4. Ablauf

1. `python bauplan.py pruefen <plan.json>`: 0 Fehler, Hinweise gelesen.
2. Resolve offen, ein echtes (benanntes) Projekt geladen, kein Render läuft. `resolve_bereit.py --projekt <Name>`.
3. `resolve_bauen.py <plan.json>`: Exit 0 = alles gesetzt und zurückgelesen; Exit 1 = Liste der Fehlschläge im Bericht
   `<plan>.bau.json`. Nie mit Fehlern weiterarbeiten, ohne sie dem Menschen zu zeigen.
4. Sichtfassung: `resolve_rendern.py --ziel <ordner>` (H.264, schnell). Standbilder an kritischen Stellen mit `--stills`.
5. Abnahme durch den Menschen an der Sichtfassung (Bild, Ton, Kadrierung, Wortlaut). Korrekturen fließen in den
   Bauplan, dann ein neuer Bau (neue Timeline).
6. Master: `resolve_rendern.py --format mov --codec ProRes422HQ --ziel <ordner>`, dann Skill `abgabe`.

## 5. Grenzen

- Nie in eine Timeline schreiben, die ein Mensch angefasst hat; kein Bau, während Resolve rendert.
- Kein Upload, kein Posten.
- Ducking, Spur-Automation und Clip-Effekte gibt es per Skript nicht (F17): Musik mit eingerechnetem Ducking liefern.
- Die vollständige Kette für Langvideos (Auswahl der Anläufe, Stimme bauen, Grafiken, Musik) ist hier nur als Ablauf in
  `docs/so-filme-ich.md` beschrieben; die Werkzeuge dafür folgen in einer späteren Welle.
