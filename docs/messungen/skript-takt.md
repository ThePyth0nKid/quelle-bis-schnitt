# Takt: Bildwechsel je Minute in Erklär-Shorts

Eigene Messung, Grundlage der Takt-Angaben im Skill `viral-methode`.

## Frage

Wie oft wechselt das Bild in erfolgreichen Erklär-Shorts, und wann kommt der erste Wechsel?

## Stichprobe

1. **Sprecher-Shorts:** 6 öffentliche Shorts von zwei englischsprachigen Tech-Erklärkanälen (je 3), Länge 57 bis
   179 s.
2. **Erklär-Reels mit Grafikbühne:** die 5 meistgesehenen Reels eines Erklärkanals, der fast nur Grafik zeigt.

## Zeitraum

1: 07.09.2026. 2: 05.10.2026.

## Verfahren

1. **Sprecher-Shorts:** Kontaktbogen mit 2 Bildern je Sekunde, jedes Bild von Hand in eine von sechs Klassen gelegt
   (Sprecher voll, Split, Sprecher im Rahmen, Sprecher freigestellt vor Grafik, Hände ohne Gesicht, nur Grafik).
   Szenenwechsel zusätzlich mit ffmpeg `select=gt(scene,0.3)` bei 1080p. Jeder Wechsel der Klasse oder Szene zählt.
2. **Grafik-Reels:** Harte Schnitte (Szenenwert über 0,3) sind dort selten; gezählt wurde deshalb der
   **Inhaltswechsel** (neue Karte, neue große Zahl, neues Diagramm). Der Detektor wurde gegen eine Handzählung geprüft
   (53 von 56 Wechseln getroffen).

## Ergebnis

- **Sprecher-Shorts:** 12 bis 46 Bildwechsel je Minute. Die drei Shorts des einen Kanals lagen bei 26, 27 und 46,
  die des anderen bei 12, 14 und 16 (dort sind die Shorts teils länger als zwei Minuten). Das Band „20 bis 40 Wechsel
  je Minute“ im Skill ist eine daraus abgeleitete Faustregel für Shorts unter einer Minute, keine gemessene Grenze.
  „Erster Wechsel spätestens bei 3 s“ und „Sprecher alle 4 bis 8 s wieder im Bild“ sind Faustregeln, nicht gemessen.
- **Grafik-Reels:** 16 bis 29 Inhaltswechsel je Minute (Median 23), harte Schnitte 0 bis 0,7 je Minute. Für
  Erklärfolgen auf einer Grafikbühne gilt deshalb der Inhaltswechsel als Maß, nicht der harte Schnitt.

## Grenzen

- Sehr kleine Stichproben, nur Erfolgsvideos, keine schwachen Videos zum Vergleich.
- Zwei Kanäle bzw. ein Kanal: Der Takt ist Stil dieser Kanäle, kein allgemeines Gesetz.
- Kein Zusammenhang mit Reichweite gemessen.

## Rohdaten

Nicht veröffentlicht (Bilder und Kennungen fremder Videos).
