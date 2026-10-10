# API-Fakten DaVinci Resolve Studio 21.1 (Skript-Schnittstelle von außen)

Gemessen an Resolve Studio 21.1 unter Windows in einem Wegwerf-Projekt mit synthetischem Material (4K-Bildzähler,
Alpha-Karten). Jede Zeile wurde am laufenden Programm geprüft, nicht aus der Doku übernommen. Methode und Grenzen:
`docs/messungen/studio-doku-resolve-api.md` im Repo. **Nach jedem Resolve-Update den Messlauf an einem Wegwerf-Projekt
wiederholen**, bevor echtes Material gebaut wird.

## Setzen von Clips (`MediaPool.AppendToTimeline`)

| Punkt | Messwert |
|---|---|
| `recordFrame` | absolut: `timeline.GetStartFrame()` (90000 bei 01:00:00:00 und 25 fps) + Versatz |
| `endFrame` | **exklusiv**: `startFrame=100, endFrame=149` ergibt 49 Bilder (100…148). Für n Bilder `endFrame = startFrame + n` |
| `mediaType` | 1 nur Bild, 2 nur Ton; ohne Angabe Bild auf der V-Spur und verknüpfter Ton auf derselben A-Spurnummer |
| fehlende Spur | wird NICHT angelegt; Rückgabe ist eine Liste mit einem toten Objekt (`GetStart()` ist `None`). Vorher `AddTrack` |
| Überlappung | wird abgelehnt (totes Objekt), nichts wird überschrieben |
| Erfolg prüfen | `item.GetStart() is not None`, nie `bool(liste)` |
| andere Bildrate | ein 30-fps-Clip in einer 25-fps-Timeline läuft in Echtzeit; `startFrame`/`endFrame` zählen in Quellbildern |
| Standbild (PNG) | Bereich wird ignoriert, Länge immer 5 s. Für andere Längen vorher als Videoclip rendern |
| 4K in 1080p-Timeline | wird eingepasst (ganzes Bild sichtbar), Punch-in über `ZoomX/ZoomY` nutzt die volle Quellauflösung |

## Bildlage (`TimelineItem.SetProperties`)

| Schlüssel | Einheit und Richtung |
|---|---|
| `ZoomX`, `ZoomY` | Faktor um die Bildmitte, 2.0 = doppelt |
| `Pan` | Timeline-Pixel, positiv = nach rechts |
| `Tilt` | Timeline-Pixel, positiv = nach oben (im Querformat; Hochformat siehe unten) |
| `CropLeft/Right/Top/Bottom` | Timeline-Pixel des eingepassten Bildes (960 bei 1920 Breite = halbes Bild) |
| `Opacity` | 0–100 |

**Hochformat (1080×1920) mit 4K-Quelle (3840×2160):** Die Quelle wird in die Breite eingepasst und steht bei Zoom 1 als
1080×607 in der Mitte. Die Höhe füllt Zoom `1920·3840 / (2160·1080) ≈ 3,1605`; sichtbar ist dann ein Fenster von etwa
1215×2160 Quellpixeln. **Tilt wirkt dort nicht in Timeline-Pixeln:** gemessen Pan 300 → 300 px, Tilt 300 → 95 px,
Faktor ≈ 0,3167 (= eingepasste Höhe / Timeline-Höhe, unabhängig vom Zoom). Im Querformat ist der Faktor 1.
Einfacher: eigene Grafik als Vollbild-Alpha in Timeline-Größe auf eine eigene Spur legen (Zoom 1, keine Lage) und nur
der Kamera eine Lage geben.

## Alpha

| Material | Erkennung |
|---|---|
| ProRes 4444 (`yuva444p10le`) | `Alpha mode = Straight`, liegt ohne Zutun durchsichtig über der Spur darunter |
| VP9-WebM mit Alpha | `Alpha mode = Premultiplied` |
| `SetClipProperty("Alpha mode", …)` | wird abgelehnt (False). WebM mit geradem Alpha vorher nach ProRes 4444 wandeln |

## Übergänge und Blenden

- `item.AddTransition({"type", "category", "position": "end", "alignment": "center", "duration": n})` liefert das
  Übergangs-Item. Der Name kommt in der Sprache der Oberfläche zurück.
- Gültig, Kategorie `simple`: `Cross Dissolve`, `Blur Dissolve`, `Dip To Color Dissolve`, `Additive Dissolve`, `Smooth Cut`.
- Gültig, Kategorie `fusion`: `Brightness Flash`, `Zoom In`, `Crash Zoom`, `Camera Shake`, `Glitch`, `Slide Left`.
- Unbekannter Name oder zweiter Übergang auf demselben Schnitt: Rückgabe `None`, kein Absturz.
- Ein zentrierter Übergang braucht Material an beiden Clips (je die halbe Dauer).
- `SetFades({"FadeIn": a, "FadeOut": b})` in Bildern, auf Bild- und Ton-Items; Bruchteile von Bildern gehen.

## Ton

- `SetProperties({"AudioVolume": dB})` je Clip, gelesen wie gesetzt.
- `SetVoiceIsolationState({"isEnabled": True, "amount": 0–100})` und `AudioDialogueLevelerEnabled` je Clip setzbar.
- `Timeline.GetNormalizeAudioModes()` kennt u. a. `ITU-R BS.1770-4`, `EBU R128`, `YouTube`, `Netflix`.
- `SetTrackName`, `SetTrackEnable(…, False)` (Spur stumm) gehen.

## Marker

- `Timeline.AddMarker(frameId, farbe, name, notiz, dauer, customData)`: `frameId` ist **relativ zum Timeline-Start**
  (30 = Bild 30). Wer `GetStartFrame()` addiert, landet eine Stunde später.
- Clip-Marker zählen ab Clip-Anfang. `GetMarkers()` liefert `{frameId: {color, duration, note, name, customData}}`.
  Eigene Marker über `customData` kennzeichnen.

## Fusion (Keyframes)

- `comp = item.AddFusionComp()` liefert `MediaIn1` und `MediaOut1`. Zeit 0 = erstes Bild des Clips.
- **Verdrahten per Zuweisung:** `xf = comp.AddTool("Transform", -32768, -32768)`, `xf.Input = mi.Output`,
  `mo.Input = xf.Output`. Statische Werte: `xf.Size = 0.5`.
- **Keyframes:** `xf.Size = comp.BezierSpline()`, dann `xf.Size[0] = 1.0`, `xf.Size[124] = 1.10`.
- Zoom 1,0 → 1,10 über 125 Bilder läuft im Render ohne Stufen, auch auf Standbildern.
- `Transform.Pivot = {1: x, 2: y}` in 0–1, Ursprung unten links.

## Standbilder und Render

- `SetCurrentTimecode("HH:MM:SS:FF")`, kurz warten, `Project.ExportCurrentFrameAsStill(pfad.png)`: geht auf der
  Edit-Seite, Bildgröße = Timeline.
- `SetCurrentRenderFormatAndCodec("mp4", "H264")` (auch `H264_NVIDIA`, `H265`, `H265_NVIDIA` …), `mov`: `ProRes422`,
  `ProRes422HQ`, `ProRes4444`; Ton `aac`, `flac`, `lpcm`.
- `AddRenderJob()` liefert die Job-ID, `StartRendering([id], False)`, warten auf `IsRenderingInProgress()`,
  `GetRenderJobStatus(id)` → `{'JobStatus': 'Complete', 'CompletionPercentage': 100}`.
- Fertige Presets u. a. `YouTube - 1080p`, `H.264 Master`, `ProRes 422 HQ`.

## Transkription in Resolve

- `MediaPoolItem.TranscribeAudio()` blockiert; Sprache über den Projekt-Schlüssel `transcriptionLanguage`.
- `GetTranscription()` verschmilzt Neuansätze (mehrere Anläufe eines Satzes werden zu einem). Für die Wahl des besten
  Anlaufs ungeeignet, als Gegenprobe am fertigen Schnitt brauchbar.

## Projekt und Start

- Projekt-Schlüssel `timelineFrameRate` vor dem ersten Import setzen.
- `Timeline.SetSetting("useCustomSettings", "1")` zuerst, dann Auflösung und Bildrate je Timeline.

## Fallen

### F1 · Import einer Einzeldatei hängt
**Symptom:** `ImportMedia([{"FilePath": …}])` hängt minutenlang und importiert nichts.
**Ursache:** Die Dict-Form ist für Bildfolgen gedacht.
**Gegenmittel:** Immer die Pfadliste `ImportMedia([pfad, …])`.

### F2 · Wiedergabe-Bildrate wird abgelehnt
**Symptom:** `SetSetting("timelinePlaybackFrameRate", …)` liefert False.
**Ursache:** Sie folgt `timelineFrameRate`.
**Gegenmittel:** Weglassen.

### F3 · Skriptordner nicht im Suchpfad
**Symptom:** `import bauplan` scheitert im mitgelieferten Python von Resolve.
**Ursache:** Dieses Python läuft isoliert (eigene `._pth`-Datei).
**Gegenmittel:** Jedes Skript beginnt mit `sys.path.insert(0, str(Path(__file__).resolve().parent))`.

### F4 · Resolve wird von außen taub
**Symptom:** „Failed to connect to script server“, danach antwortet die Instanz nicht mehr.
**Ursache:** `scriptapp()` wurde abgefragt, während Resolve noch startete.
**Gegenmittel:** Erst warten, bis der Prozess `fuscript` läuft (`resolve_bereit.py`), sonst Resolve neu starten.

### F5 · Speichern hängt auf einem unbenannten Projekt
**Symptom:** Jeder weitere API-Aufruf hängt.
**Ursache:** `SaveProject()` auf „Untitled Project“ öffnet den Dialog „Neues Projekt erstellen“.
**Gegenmittel:** Unbenannte Projekte nie speichern (`projekt_holen` tut das), offenen Dialog von Hand schließen.

### F6 · Untertitel per AppendToTimeline stürzt ab
**Symptom:** Resolve beendet sich mit Problembericht.
**Ursache:** SRT aus dem Media Pool per `AppendToTimeline` setzen.
**Gegenmittel:** Nicht tun. Wortlaut als Marker, Untertitel als Alpha-Video oder als SRT bei der Abgabe.

### F7 · Leeres Protokoll nach einem Hänger
**Symptom:** Eine umgeleitete Ausgabe bleibt leer, wenn Resolve mitten im Lauf hängt.
**Ursache:** Ausgabe gepuffert.
**Gegenmittel:** Immer mit `-u` starten und vor riskanten Aufrufen eine Zeile ausgeben.

### F8 · Verbindung gemeldet, im Bild wirkungslos
**Symptom:** Eine Fusion-Verbindung steht als gesetzt da, das Bild ändert sich nicht.
**Ursache:** `comp.Lock()`/`Unlock()` und `tool.ConnectInput()` beim Bau einer Komposition.
**Gegenmittel:** Verdrahten per Zuweisung (`xf.Input = mi.Output`).

### F9 · Ein Fehlschlag sieht aus wie ein Erfolg
**Symptom:** `AppendToTimeline` liefert eine nicht leere Liste, aber nichts liegt in der Timeline.
**Ursache:** Die Liste enthält tote Objekte.
**Gegenmittel:** Jede Platzierung über `GetStart()` und `GetDuration()` zurücklesen.

### F10 · Start durch eine Pipe kehrt nie zurück
**Symptom:** Ein Startbefehl für Resolve hängt.
**Ursache:** Resolve im Hintergrund starten und die Ausgabe durch eine Pipe leiten.
**Gegenmittel:** Startskripte ohne Pipe im Hintergrund laufen lassen.

### F11 · Absturz bleibt unbemerkt
**Symptom:** Der Prozess läuft weiter, die API antwortet nicht.
**Ursache:** Nach einem Absturz zeigt Resolve nur ein Fenster mit dem Problembericht.
**Gegenmittel:** Offene Fenster prüfen, Resolve neu starten, dann `resolve_bereit.py`.

### F12 · Keine Bitrate für H.264
**Symptom:** `VideoQuality` wird in jeder Form abgelehnt; der H.264-Render hat eine niedrige feste Bitrate.
**Ursache:** Die Render-API bietet dafür keinen Regler.
**Gegenmittel:** Master als ProRes 422 HQ rendern und mit `studio mastern` nach H.264 wandeln.

### F13 · Ton 3 dB zu leise
**Symptom:** Jeder Clip auf einer neu angelegten Tonspur ist leiser als erwartet.
**Ursache:** `AddTrack("audio")` legt eine Mono-Spur an.
**Gegenmittel:** `AddTrack("audio", "stereo")`.

### F14 · Neuer Render auf denselben Pfad scheitert
**Symptom:** Render oder Löschen meldet Erfolg, die Datei bleibt oder der Clip steht später auf „Media Offline“.
**Ursache:** Resolve hält jede importierte Datei offen; gelöscht wird sie erst, wenn Resolve schließt.
**Gegenmittel:** Neue Fassung = neuer Dateiname (`resolve_rendern.py` hängt -2, -3 an). Nie die alte Datei vor dem
neuen Render löschen. Reparatur: `MediaPool.RelinkClips([clip], <ordner der neuen Fassung>)`.

### F15 · Übergang zwischen Spuren
**Symptom:** `AddTransition` liefert `None` zwischen Kamera A auf V1 und Kamera B auf V2.
**Ursache:** Übergänge verbinden nur Nachbarn derselben Spur.
**Gegenmittel:** Übergang als Alpha-Overlay auf einer Spur darüber, sonst harte Schnitte.

### F16 · Kamera-Ton auf der Spur der Stimme
**Symptom:** Kamera-Ton landet auf A1, die Platzierung der Stimme kommt als totes Objekt zurück.
**Ursache:** Bild ohne `mediaType` gesetzt: der verknüpfte Ton geht auf dieselbe Spurnummer.
**Gegenmittel:** Bild mit `mediaType 1`, Originalton getrennt auf eine eigene stumme Spur und verknüpfen.

### F17 · Kein Ducking per Skript
**Symptom:** Musik lässt sich nicht automatisch unter die Stimme absenken.
**Ursache:** Ducking, Spur-Automation und Clip-Effekte gibt es in der Skript-API nicht.
**Gegenmittel:** Musik mit eingerechnetem Ducking als ein Stück liefern, Klänge mit festem `AudioVolume`, Lautheit an
der Renderdatei messen.

### F18 · Ton-Clips ein Bild zu kurz
**Symptom:** Ein Ton-Clip kommt ein Bild kürzer an als geplant.
**Ursache:** Das Projekt steht auf einer anderen Bildrate als die Timeline (z. B. nach einer Probe-Timeline mit 24 fps);
bereits importierte Clips behalten ihre alte Rate.
**Gegenmittel:** Projekt-Bildrate und -Auflösung bei jedem Bau setzen (`resolve_bauen.py`), bei Umstellung einen neuen
Plan-Namen (neuer Media-Pool-Ordner) nehmen. Ein Resolve-Projekt je Format (16:9 und 9:16 getrennt).

### F19 · Standbild zeigt die falsche Stelle
**Symptom:** `ExportCurrentFrameAsStill` liefert direkt nach dem Laden `None` oder das Bild einer früheren Stelle.
**Ursache:** Resolve hinkt nach dem Laden hinterher.
**Gegenmittel:** Ein Aufwärmbild schreiben und verwerfen, nur `True` zählen, die Prüfsumme jedes Bildes mit dem
vorigen vergleichen (gleich bei anderer Stelle = noch einmal). `resolve_rendern.py --stills` tut das.

### F20 · Bauskript mit dem falschen Python
**Symptom:** `resolve_bereit.py` meldet nach der Wartezeit „antwortet nicht“, obwohl Resolve läuft.
**Ursache:** Gestartet mit einem System-Python ohne die Skript-Module von Resolve.
**Gegenmittel:** Mit dem Python von Resolve starten oder die Umgebung nach der Scripting-README von Resolve setzen.

### F21 · Von außen unerreichbar, nur „Untitled Project“
**Symptom:** `LoadProject` liefert False, `GetCurrentDatabase()` ist leer.
**Ursache:** Resolve ist noch nicht vollständig bereit oder keine Datenbank gewählt.
**Gegenmittel:** In Resolve von Hand ein Projekt anlegen oder öffnen, dann erneut `resolve_bereit.py --projekt <Name>`.

### F22 · Untertitel nach Ähnlichkeit „korrigieren“
**Symptom:** Aus Gesprochenem wird der Skript-Wortlaut („zeige“ → „zeig“).
**Ursache:** Eine Ähnlichkeitsregel ersetzt Wörter des Transkripts durch Wörter des Skripts.
**Gegenmittel:** Nur Groß-/Kleinschreibung und Satzzeichen angleichen; verhörte Namen und Fachwörter als ausdrückliche
Liste führen und prüfen.
