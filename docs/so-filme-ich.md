# So filme ich: vom Prompter bis zur Upload-Datei

Diese Anleitung beschreibt einen Arbeitsweg für Sprechvideos mit zwei Kameras: aufnehmen, Ton prüfen, Kameras
synchronisieren, schneiden, abgeben. Sie gehört zum Plugin `studio` und zum Werkzeug `studio`.

**Das Setup unten ist ein Beispiel.** Es zeigt, wie die Teile zusammenhängen, nicht, was du kaufen sollst. Am Ende
steht eine Liste mit den Werten, die du für dein eigenes Setup eintragen solltest. Zahlen ohne Quellenangabe sind als
„Beispielwert“ oder „Faustregel“ gekennzeichnet.

**Der Mensch entscheidet.** Werkzeuge messen und melden. Ob ein Take gut ist, ob der Ton trägt und ob ein Video
rausgeht, entscheidet ein Mensch an Bild und Ton.

## 1. Das Beispiel-Setup

```
Kamera A (frontal) ─HDMI─▶ Capture A ─┐
Kamera B (seitlich) ─HDMI─▶ Capture B ─┼─▶ OBS Studio ─▶ Source Record: je Kamera eine Datei ─▶ <inbox> (interne SSD)
Mikrofon ─▶ Audio-Interface (48 kHz) ─▶ Rauschunterdrückung ─┘   └─▶ Programm-Aufnahme (Gegenprobe)
Teleprompter mit Fußpedal vor Kamera A
```

| Teil | Im Beispiel | Worauf es ankommt |
|---|---|---|
| Kamera A und B | zwei spiegellose Kameras mit sauberem 4K-Ausgang über HDMI | HDMI ohne Einblendungen, Dauerbetrieb ohne Abschaltung, beide auf dieselbe Bildrate |
| Capture | je Kamera ein USB-HDMI-Capture-Gerät für 4K | beide Datenströme gleichzeitig ohne Aussetzer; nach dem Anschließen eine Probe mit beiden Kameras |
| Mikrofon | dynamisches Sprechermikrofon, nah am Mund | dynamisch nimmt wenig Raum auf; Abstand gleich halten |
| Audio-Interface | USB-Interface | im System auf 48 kHz, Gain so, dass Sprache kräftig ist und Spitzen Abstand zu 0 dBFS halten |
| Rauschunterdrückung | Software, die ein bereinigtes virtuelles Mikrofon bereitstellt | wirkt auf alle Aufnahmen; in Pausen kann sie auf digitale Stille gehen (siehe §3) |
| Aufnahme | OBS Studio mit dem Plugin Source Record ([exeldro/obs-source-record](https://github.com/exeldro/obs-source-record), GPL-2.0) | je Kamera eine eigene Datei, dazu die Programm-Aufnahme |
| Prompter | Teleprompter mit Software zum Laden der Texte, Fußpedal zum Blättern | ein Satz je Abschnitt (§4) |
| Schnitt | DaVinci Resolve, Timeline aus einem Bauplan | Skripte von außen: Skill `resolve-schnitt` |
| Werkzeug | `studio` (Python) | Klick-Prüfung, Paar, Prompter, Transkript, Mastern |

Einrichten: in Claude Code `/studio:einrichten`, danach `studio.toml` ausfüllen (`studio konfig zeigen`).

## 2. OBS-Regeln

1. **Source-Record-Filter in der Oberfläche anlegen**, Aufnahme-Modus „Recording“. Im Code des Plugins ist das
   `record_mode = 3`; Wert 2 ist „Streaming“, dann schreibt der Filter bei einer Aufnahme nichts
   ([source-record.c](https://github.com/exeldro/obs-source-record/blob/master/source-record.c)).
   **Dateiname mit Zeitstempel:** im Filter z. B. `cam-A-%CCYY%MM%DD-%hh%mm%ss` bzw. `cam-B-…`. `studio paar` findet
   Paare über `<praefix><JJJJMMTT-HHMMSS><endung>`; Präfixe und Endung stehen in `studio.toml` unter `[kameras]`.
2. **Encoder oder Bitrate nur durch Löschen und Neuanlegen des Filters wechseln.** Geänderte Einstellungen laden den
   Encoder nicht neu. `studio obs-modus <modus>` macht das an derselben Stelle der Filterliste und sichert vorher die
   alten Einstellungen als JSON; es bricht ab, wenn OBS gerade aufnimmt.
3. **Keine eigenen Audiogeräte an den Kameraquellen.** Der Ton kommt aus genau einer Mikrofonquelle. Ein zusätzliches
   Audiogerät an einer Kameraquelle führte im Beispiel-Setup zu Nachlauf-Meldungen im OBS-Protokoll und zu Knacken in
   der Kameradatei.
4. **Aufnahme auf eine interne SSD.** Nicht direkt auf ein USB-Laufwerk mit exFAT schreiben; erst nach dem Dreh ins
   Archiv verschieben.
5. **Eine Bildrate überall:** Kameras, Capture-Geräte und OBS-Profil gleich, z. B. alle 25 fps.
6. **Programm-Aufnahme mitlaufen lassen.** Sie ist die Gegenprobe, wenn eine Kameradatei Fehler hat.
7. **obs-websocket:** Das Passwort steht nie in einer Datei im Projekt, sondern in einer Umgebungsvariable, deren Namen
   `studio.toml` nennt. Das Python-Paket `obsws-python` schreibt das Passwort beim Verbinden auf Log-Stufe INFO ins
   Protokoll; `studio` stellt diesen Logger auf WARNING.

## 3. Ton: Kette und Prüfreihenfolge bei Knacken

**Vor dem ersten Schnittschritt** werden alle Tonquellen eines Takes gemessen:

```
studio klick-check <kamera-a.mp4> <kamera-b.mp4> <programm.mp4>
```

Ampel je Minute: unter 5 grün, 5–15 gelb, über 15 rot (eigene Messung an wenigen Takes, einstellbar; Methode in
`docs/messungen/studio-klicks.md`). Rot heißt: nicht schneiden, sondern Ursache suchen. Ist eine Quelle rot und eine
andere desselben Takes grün, wird das gemeldet, nicht still umgeschwenkt.

**Prüfreihenfolge bei Knacken**, nach jedem Schritt eine kurze Probeaufnahme und erneut `studio klick-check`:

1. **48 kHz überall:** Interface im System, OBS, Rauschunterdrückung. Nach einer Umstellung prüfen, ob OBS noch auf das
   richtige Gerät zeigt: manche Systeme legen dabei ein neues Gerät an, und die nächsten Takes sind stumm.
2. **Audiogerät an Kameraquellen:** abschalten (§2, Regel 3).
3. **Kanten der Rauschunterdrückung in Pausen:** Treffer in Sprechpausen mit exakten Nullwerten ringsum sind Kanten der
   Rauschunterdrückung, kein Defekt im Aufnahmeweg. Abhören und entscheiden, ob sie stören.
4. **Ziellaufwerk:** Viele Klick-Abstände im Raster eines AAC-Blocks (1024 Abtastwerte, bei 48 kHz 21,33 ms) deuten auf
   beschädigte Tonblöcke beim Schreiben. Im Beispiel-Setup verschwand das Dauerknacken, nachdem die Aufnahme von einem
   USB-Laufwerk mit exFAT auf die interne SSD verlegt wurde (Einzelbeobachtung an einer kurzen Probe, keine Messreihe).
5. **Pegel:** Leise aufgenommen und später stark angehoben, werden kleine Störungen hörbar. Außerdem zählt der
   Klickzähler bei lauterem Material mehr Konsonanten mit; deshalb Rohdateien messen.

Danach gilt: **Hörprobe durch einen Menschen**, bevor Bild gebaut wird (Skill `ton-mastering`). Lautheit auf Ziel und
eine saubere Rücktranskription beweisen nicht, dass der Ton gut klingt.

## 4. Prompter

- **Ein Satz je Abschnitt.** Verspricht man sich, wiederholt man nur diesen Satz. Der Schnitt nimmt später den letzten
  vollständigen Anlauf.
- `studio prompter saetze <skript.md> --ausgabe <prompter.md>` teilt das Skript in Sätze und führt Kameramarken (`[A]`,
  `[B]`) vor jedem Satz mit. Ordnungszahlen („3. Oktober“) und Kürzel („z. B.“) bleiben ganz. Ausgabe lesen.
- `studio prompter einspielen prompter.toml --probe`, dann ohne `--probe`: lädt die Texte in die Prompter-Software
  (vorerst Elgato Camera Hub unter Windows). Das Werkzeug prüft vorher, dass OBS nicht aufnimmt.
- **Das Fußpedal ist im Ton:** ein dumpfer Stoß kurz vor dem ersten Wort. Schnittkanten gehören an den Beginn der
  Sprache, nicht an den ersten Pegel-Einsatz.

## 5. Zwei Kameras synchronisieren

OBS startet die Source-Record-Ausgaben nacheinander. Kamera B beginnt deshalb einige Bilder nach Kamera A, je Take
anders (Messung und Spanne im Beispiel-Setup: `docs/messungen/studio-zwei-kamera.md`).

- `studio paar` misst den Versatz: Ton-Kreuzkorrelation (FFT), bei eindeutiger Bewegung im Bild die Bewegung (die
  Kameras laufen frei, ihre Phase zum OBS-Takt wandert), bei sehr kurzen Takes die Bildzahl (OBS stoppt beide
  gleichzeitig). Ergebnis: je Take ein Ordner mit genau zwei deckungsgleichen Dateien und ein Bericht.
- `studio waechter` macht das nach jedem Stopp automatisch und prüft beim Aufnahmestart, ob beide Kameras Bild liefern
  und das Mikrofon Pegel hat.
- **Rohdateien bleiben standardmäßig liegen.** Ob sie nach einem grünen Bau nach `<ziel>/_Papierkorb/<Take>/` wandern
  (verschoben, nie gelöscht), steht in `studio.toml` und ist deine Entscheidung.
- **Keine Hardlinks auf exFAT** und nie zwischen zwei Laufwerken; verschoben wird nur durch Umbenennen auf derselben
  Platte, damit keine halb kopierte Datei entsteht.
- Prüfen am Kontaktbogen: zwei, drei Stellen mit deutlicher Bewegung (Klatschen, Hände), beide Kameras nebeneinander.

## 6. Kadrierung

- **Kopf ganz im Bild, das Kinn nie angeschnitten.** Lieber oben etwas vom Scheitel verlieren als unten das Kinn.
- **Augenlinie ruhig im oberen Drittel** (Faustregel; Beispielwert aus einem Setup: 0,40 der Bildhöhe von oben).
- Größen für Punch-ins aus einer 4K-Kamera in einer 1080p-Timeline: Beispielwerte weit 1,0 · halbnah 1,3 · nah 1,45 ·
  eng 1,9 (nicht gemessen, Geschmack).
- **Hochformat aus einer 4K-Querformat-Kamera:** Eine 3840×2160-Quelle füllt eine 1080×1920-Timeline bei Zoom
  `1920·3840 / (2160·1080) ≈ 3,16`; sichtbar ist dann ein Fenster von etwa 1215×2160 Quellpixeln. In Resolve wirkt Tilt
  im Hochformat mit einem Faktor (Skill `resolve-schnitt`, `referenz/api-fakten.md`).
- Vor dem Schnitt und nach dem Render einen Kontaktbogen ansehen, nicht nur Zahlen.

## 7. Schnitt eines Langvideos in 10 Schritten

1. **Ton messen:** `studio klick-check` auf alle Quellen; rot = nicht schneiden (§3).
2. **Paar bauen:** `studio paar` oder der Wächter; Bericht und Kontaktbogen prüfen (§5).
3. **Transkribieren:** Take erst am Pegel in Äußerungen zerlegen, dann jede Äußerung einzeln transkribieren
   (`studio transkript`). Whisper verschmilzt sonst mehrere Anläufe eines Satzes zu einem. Nie den erwarteten Text als
   Vorgabe an Whisper geben.
4. **Auswahl:** in Reihenfolge des Skripts je Satz der letzte vollständige Anlauf. Kanten aus den Äußerungsgrenzen am
   Pegel, nie aus Whispers Wortzeiten.
5. **Stimme bauen:** ein durchgehendes Tonstück aus den gewählten Anläufen, Nähte gleich laut überblendet, Raumton von
   der gleichmäßigsten ruhigen Stelle, Wortenden nicht abgeschnitten (Skill `ton-mastering`).
6. **Hörprobe:** ein kurzes Stück gemasterte Stimme an einen Menschen, bevor Bild gebaut wird.
7. **Bild planen:** Einstellungen je Satz (Kamera A/B, Größe), Punch-ins, Einsätze (Grafiken, Belege); Kadrierung
   prüfen (§6). Grafiken als Vollbild mit Alpha (ProRes 4444), Musik mit eingerechnetem Ducking.
8. **Bauplan → Resolve:** `bauplan.py pruefen`, dann `resolve_bauen.py` baut eine neue Timeline; jede Platzierung wird
   zurückgelesen (Skill `resolve-schnitt`).
9. **Sichtfassung und Abnahme:** `resolve_rendern.py` (H.264, schnell), dazu Rückcheck des Wortlauts mit
   `studio transkript` gegen das Skript. Ein Mensch sieht und hört die Fassung ganz; Korrekturen gehen in den Bauplan,
   dann ein neuer Bau.
10. **Master und Abgabe:** ProRes 422 HQ aus Resolve, dann `studio mastern` (§9).

## 8. Shorts: Takt

- **Erster Bildwechsel früh, danach etwa 20–40 Wechsel je Minute.** Das ist eine Faustregel, abgeleitet aus einer
  kleinen eigenen Messung an Erklär-Shorts (`docs/messungen/skript-takt.md`); dort stehen Stichprobe und Grenzen.
  `python bauplan.py statistik <plan.json> --spur Kamera` zeigt die Wechsel je Minute eines Bauplans.
- **Kamerawechsel an Satz- oder Phrasengrenzen**, der Ton kommt aus einer durchgehenden Quelle.
- **Sehr kurze Einstellungen vermeiden** (Faustregel: unter etwa 0,6 s wirkt es wie Flackern).
- **Gesetzte Pausen statt Hast:** ungeplante Stille raus, aber eine kurze gesetzte Pause nach einer Pointe und vor der
  Aufforderung am Ende kann bleiben (Faustregel, Geschmack).
- Skript und Hook: Plugin `skript` (`skript-short`, `hook`, `viral-methode`).

## 9. Abgabe

- **Upload-Datei:** `studio mastern <master.mov> <upload.mp4> --hoehe 1440` (erst mit `--probe`): H.264 mit CRF 16 (Voreinstellung) und
  vorn liegendem Index (`+faststart`), Ton auf −14 LUFS und höchstens −1,5 dBTP, danach nachgemessen. Bricht ab, wenn
  der Begrenzer mehr als 3 dB greifen müsste.
- **Woher die Werte kommen:**
  - YouTube empfiehlt MP4 mit dem Index vorn („Fast Start“), AAC-LC mit 48 kHz, H.264 High Profile und für 1440p bei
    24–30 fps 16 Mbit/s, für 1080p 8 Mbit/s ([YouTube-Hilfe](https://support.google.com/youtube/answer/1722171)).
  - −14 LUFS: Spotify normalisiert auf −14 LUFS und empfiehlt True Peak unter −1 dBTP, bei lauten Mischungen unter
    −2 dBTP ([Spotify](https://support.spotify.com/us/artists/article/loudness-normalization/)). YouTube nennt keinen
    festen Wert; prüfe deinen Upload selbst. Messverfahren nach ITU-R BS.1770
    ([ITU](https://www.itu.int/rec/R-REC-BS.1770)).
  - 1440p ist ein Beispiel-Abgabeformat für 4K-Material in einer 1080p- oder 1440p-Timeline; Hochformat 1080×1920.
- **Prüfen:** Nachmessung, `studio klick-check` auf die Upload-Datei, Rückcheck des Wortlauts, Kontaktbogen, dann
  Sicht- und Hörprobe durch den Menschen am Stück.
- **Länge:** Ein YouTube-Konto ohne Bestätigung nimmt standardmäßig höchstens 15 Minuten
  ([YouTube-Hilfe](https://support.google.com/youtube/answer/71673)).
- **Paket:** Upload-Datei, Untertitel (SRT aus dem Transkript, Verhörer nur per ausdrücklicher Liste korrigieren),
  Kapitel aus den Markern, Beschreibung mit Quellenliste (Plugin `recherche`). Skill `abgabe`.

## 10. Offene Lücke: Upload

Hochgeladen wird von Hand im Studio der Plattform. Ein automatischer Upload fehlt bewusst: Er braucht OAuth-Zugang zum
Konto und API-Kontingente, und er nimmt dem Menschen den letzten Blick ab. Wer ihn ergänzt, baut ihn als eigenes
Werkzeug mit eigenem Schlüssel außerhalb des Repos.

## 11. Was du für dein Setup eintragen solltest

Kopiere die Tabelle in deine Projektnotizen und fülle sie aus. Diese Werte entscheiden über Bild und Ton mehr als jedes
Werkzeug; sie gehören nicht in dieses Repo.

| Bereich | Was eintragen | Dein Wert |
|---|---|---|
| Belichtung | Verschlusszeit, Blende, ISO, Belichtung manuell oder automatisch | |
| Objektiv | Brennweite je Kamera, Abstand zum Gesicht | |
| Bildprofil | Farbprofil, Weißabgleich (fest, in Kelvin), Schärfe/Kontrast in der Kamera | |
| Fokus | Autofokus-Modus, Gesichts-/Augenerkennung oder manuell | |
| Kamera-Ausgabe | HDMI-Auflösung und Bildrate, Einblendungen aus, Abschaltung aus | |
| Interface | Abtastrate, Gain-Stellung, Phantomspeisung (bei dynamischem Mikro aus) | |
| Rauschunterdrückung | welche Effekte, welche Stärke, verhält sie sich in Pausen | |
| Licht | Hauptlicht, Aufhellung, Hintergrund; Farbtemperatur; Position | |
| Source Record | Encoder, Modus (VBR/CBR/CQP), Bitrate, Container, Dateiname mit Zeitstempel | |
| OBS-Profil | Auflösung, Bildrate, Abtastrate, Ziel der Programm-Aufnahme | |
| Speicherort | Aufnahmelaufwerk (intern), Archiv, freier Platz je Drehtag | |
| Resolve-Projekt | Auflösung, Bildrate, Farbmanagement, ein Projekt je Format | |
| Raum | Dämpfung, Nachhall, Störquellen (Lüfter, Straße), Hintergrund im Bild | |
| Prompter | Abstand, Schriftgröße, Blättern (Pedal/Fernbedienung) | |
