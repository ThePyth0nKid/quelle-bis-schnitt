# Runde <nummer> „<thema>“: Bericht des unabhängigen Faktenprüfers (<TT.MM.JJJJ>)

Ich habe die Dateien vor dem Import geprüft. Gebaut habe ich keine davon, geändert habe ich nichts.

**Geprüft:** <Dateien, Zahl der Quellen, Karten, Verbindungen, Notizen>
**Maßstab:** <Auftrag mit Leitplanken>, `belegregeln.toml` (Stufen), die Recherche-Berichte, der Zitat-Prüfbericht
**Vorgehen:** <wie Originale geladen wurden: curl mit neutraler Kennung, PDFs mit pypdf, Wayback als Prüfweg, Tonstellen mit
welchen Whisper-Modellen>; <Zahl> Websuchen

**Ergebnis:** <n> Funde: **<h> HOCH**, **<m> MITTEL**, **<l> NIEDRIG**, dazu <k> Hinweise ohne Korrekturvorschlag.
**Umfang:** <x> von <y> Verbindungen (<p> %) an mindestens einem selbst geladenen Original geprüft.

Schwere:
- **HOCH:** rechtliches Risiko. Einer realen Person wird ein Satz oder eine Tat zugeschrieben, die die Quelle nicht trägt;
  Vorwurf ohne Gericht, Behörde oder Vergleich; Privatperson erkennbar; falscher Verfahrensstand.
- **MITTEL:** Der Beleg trägt die Aussage nur teilweise; Entlastendes aus derselben Quelle fehlt; Übersetzung als Wortlaut;
  Zahl ohne Stand oder Bezugsgröße.
- **NIEDRIG:** Form, Datum, Titel, ungenaue Fundstelle, Doppelung.

---

## Sonderprüfungen (falls nötig)

### <z. B. strittige Tonstelle in Quelle Q12, 18:20–18:45>

| Prüfung | Ergebnis |
|---|---|
| Whisper <Modell 1>, ohne Vorgabe, greedy und Strahlsuche | „…“ |
| Whisper <Modell 2>, ohne Vorgabe | „…“ |
| manuelle Untertitelspur (von Menschen gesetzt), falls vorhanden | „…“ |
| automatische Spur der Plattform | „…“ |

Bewertung: <was alle gleich hören, was strittig bleibt>. Bis ein Mensch abgehört hat, steht im Zitat nur der übereinstimmende
Teil. **Mensch hört <Zeitbereich>.**

---

## Funde

Schreibweise: Verbindung = `Datei: von → nach [art]`, Beleg = Quelle und Wortlaut am Original.

### HOCH

**1 · HOCH · `<datei>: <von> → <nach> [<art>]`, Beleg `<quelle>`**
- Regel: <B-Nummer und Name>
- Problem: <was falsch ist und warum es zählt>
- Beleg am Original: <URL>, <Fundstelle>: „<Wortlaut>“
- Vorschlag: Feld `<feld>` alt „<exakter alter Wortlaut>“ → neu „<neuer Wortlaut>“

### MITTEL

**<n> · MITTEL · …**

### NIEDRIG

**<n> · NIEDRIG · …**

---

## Hinweise ohne Korrekturvorschlag

- <z. B. Korrektur am Bestand nach dem Import nötig, Reihenfolge der Belege>

## Geprüft und in Ordnung

- <Datei: Verbindungen, die am Original geprüft wurden, mit den gelesenen Originalen>
- **Leitplanken-Suche** (<Suchwörter>): <Treffer und Bewertung>
- **Datenschutz:** <Privatpersonen nur mit Initialen? Titel und URLs geprüft?>
- **Nicht geprüft:** <was offen blieb und warum>

Der Prüfer berät. Über jeden Fund entscheidet ein Mensch in der Entscheidungstabelle.
