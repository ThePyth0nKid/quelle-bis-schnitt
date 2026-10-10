# Messung: Klicks im Aufnahmeton (Schwellen von `studio klick-check`)

| Angabe | Inhalt |
|---|---|
| Frage | Ab wie vielen Klicks je Minute ist eine Aufnahme hörbar beschädigt, und wie trennt der Zähler Klicks von Sprache und Rauschen? |
| Stichprobe | Aufnahmen aus EINEM Aufbau: zwei Kameras per HDMI-Capture in OBS (Source Record), dazu die Programm-Aufnahme von OBS, alle mit derselben Mikrofonspur (dynamisches Mikrofon, Interface, Rauschunterdrückung). Ausgewertet: für die Ampel zwei Takes an zwei Tagen (ein hörbar knackender, ein sauberer; je Kameradateien und Programm-Aufnahme), für die Zähler-Schwelle die Takes eines weiteren Drehtags, an denen Kamera B hörbar knackte. Insgesamt n = 3 Drehtage. |
| Zeitraum | September bis Oktober 2026 |
| Verfahren | Ton per ffmpeg als Mono, 48 kHz, float. Klick = Sprung zwischen zwei benachbarten Abtastwerten, der den lokalen Pegel (Effektivwert der Sprünge in ±50 ms) um das 12-fache übersteigt und absolut über 0,03 liegt; Treffer binnen 20 ms zählen als einer; je 50 ms am Datei-Anfang und -Ende zählen nicht. Danach Klicks je Minute. Abhören der Stellen durch einen Menschen. Implementierung: `plugins/studio/werkzeuge/src/studio_werkzeuge/klicks.py`. |
| Ergebnis | Faktor 12 und Minimum 0,03: auf dem Drehtag mit knackender Kamera B 8–16 Klicks je Take in B, 0 in A und in der Programm-Aufnahme; Rauschen und Sprache ohne Aussetzer ergaben 0. Klicks je Minute: Kameradateien eines hörbar knackenden Takes rund 85–97, Programm-Aufnahme desselben Takes rund 2–3, ein sauberer Take rund 2–3. Daraus die Ampel: unter 5 grün, 5–15 gelb, über 15 rot. Die Grenzen 5 und 15 sind eine Festlegung zwischen den gemessenen Gruppen, kein gemessener Kipppunkt. |
| Grenzen | Ein Aufbau, wenige Takes, ein Sprecher. Die Ampel trennt „sauber“ von „deutlich kaputt“; Werte zwischen 5 und 15 wurden kaum beobachtet. Viele Klicks in Sprechpausen können auch Kanten einer Rauschunterdrückung sein, die in Pausen auf digitale Stille schaltet. Der Zähler hört nicht: im Zweifel die Stellen anhören. Alle Werte sind in `[klicks]` der `studio.toml` einstellbar. |
| Rohdaten | Nicht veröffentlicht (private Aufnahmen). Der Test `tests/test_klicks.py` prüft den Zähler an synthetischen Signalen mit eingesetzten Spitzen und Aussetzern. |

## Hinweis Pegel

Der Hinweis „Pegel weit vom Bezug“ (Voreinstellung −23 dBFS Effektivwert, Toleranz ±10 dB) ist keine Messung. Er lehnt
sich an den Zielwert −23 LUFS aus EBU R 128 an (https://tech.ebu.ch/publications/r128) und soll nur auf eine falsch
eingestellte Eingangsverstärkung aufmerksam machen.
