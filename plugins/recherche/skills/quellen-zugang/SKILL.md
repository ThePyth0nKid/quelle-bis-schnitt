---
name: quellen-zugang
description: 'Wie man für Recherchen (Belegtabellen, Skripte, Faktenprüfung) an Originalquellen kommt: Reihenfolge Original vor Presse, amtliche Quellen und Schnittstellen aus Deutschland, der EU und den USA (Bundestag DIP, Lobbyregister, Parteispenden, Destatis, Bundesbank, Handelsregister, EUR-Lex, SEC EDGAR, FEC, OpenSanctions), die Such- und Lese-Werkzeuge Exa, Jina und Tavily und legale Wege hinter Bezahlschranken (Bibliotheken, Fernleihe, eigene Abos). Nutze diesen Skill bei „recherchier“, „Quelle finden“, „Beleg suchen“, „wer hat gespendet“, „Lobbyregister“, „Drucksache“, „hinter die Paywall“, „Originaldokument“ und vor jedem Recherche-Agenten. Grenze: keine Umgehung von Bezahlschranken, archive.today nie als Beleg.'
---

# Quellen-Zugang

Primärquellen schlagen jeden Artikel hinter einer Bezahlschranke, und für den Rest gibt es legale Zugänge. Umgangen wird
nichts: Wer veröffentlicht, haftet für jede Aussage, und das Umgehen wirksamer Schutzmaßnahmen ist verboten
([§ 95a UrhG](https://www.gesetze-im-internet.de/urhg/__95a.html), [§ 108b UrhG](https://www.gesetze-im-internet.de/urhg/__108b.html)).

## 1. Reihenfolge bei jeder Behauptung

1. **Original suchen:** Behörde, Gericht, Parlament, Register, Geschäftsbericht, eigene Erklärung oder eigener Post der
   Person. Güte `primaer`.
2. **Nur wenn es kein Original gibt: Presse** mit Datum. Güte `sekundaer`, im Text „laut <Medium>“.
3. **Neuester Stand zuerst:** Suchbegriff mit dem laufenden Jahr. Empfehlung: Zahlen nicht älter als zwölf Monate, sonst den
   Stand ausdrücklich dazuschreiben.
4. **Wortlaut nur, was wirklich in der Quelle steht.** Übersetzungen getrennt markieren. Regeln dazu im Skill `belegregeln`.

## 2. Werkzeuge

| Werkzeug | Wofür | Hinweis |
|---|---|---|
| **Exa** (`https://mcp.exa.ai/mcp`, Plugin `recherche`) | Websuche mit Volltext und Original-URL | ohne Schlüssel mit begrenztem Gratiskontingent |
| **Jina** (`https://mcp.jina.ai/v1`, Plugin `jina-lesen`) | `read_url` (Seiten und PDFs als Markdown), `guess_datetime_url` (Datum geschätzt), Suche | eigener Schlüssel; geschätztes Datum immer auf der Seite nachprüfen |
| **Tavily** (`https://mcp.tavily.com/mcp/`, Plugin `tavily-suche`) | zweite Suchmaschine, dazu Extract, Map, Crawl | eigener Schlüssel |
| WebSearch / WebFetch (eingebaut) | Suche, Seite lesen | WebFetch fasst zusammen: Wortlaute nie aus der Zusammenfassung übernehmen, sondern am Rohtext prüfen |
| `zitate_pruefen.py` (Plugin `recherche`, Ordner `werkzeuge/`) | prüft jedes Zitat am Original | berät nur, siehe Skill `recherche-runde` |

**Datenschutz:** Suchbegriffe und URLs gehen an externe Anbieter, unter anderem in den USA. Wer zu heiklen Themen recherchiert,
verrät dem Anbieter sein Thema.

Bewusst nicht empfohlen: Werkzeuge, die Browser-Cookies auslesen; inoffizielle Clients für soziale Netzwerke; fremde Gateways,
über die alle Anfragen laufen; alles mit Sci-Hub-Funktion; Server mit Lizenzen, die eine Nutzung in der eigenen Arbeit
ausschließen (z. B. „NC“).

## 3. Amtliche Quellen (direkt abrufen: curl, WebFetch, Jina)

| Quelle | Adresse | Zugang |
|---|---|---|
| Bundestag DIP (Drucksachen, Plenarprotokolle, Vorgänge) | API `https://search.dip.bundestag.de/api/v1/`, Doku `https://dip.bundestag.de/über-dip/hilfe/api` | öffentlicher Schlüssel steht in der Doku, Gültigkeit dort prüfen; eigener Schlüssel auf Anfrage beim Bundestag |
| Drucksache oder Protokoll als PDF | `https://dserver.bundestag.de/btd/<WP>/<nnn>/<WPnnnnn>.pdf`, `…/btp/<WP>/<WPnnn>.pdf` | frei |
| Lobbyregister (Einträge, Ausgaben, Stellungnahmen) | `https://www.lobbyregister.bundestag.de/suche/<R-Nummer>`, Open Data über die Hilfeseiten des Registers | frei |
| Parteispenden über 35.000 € (Anzeigepflicht nach [§ 25 Abs. 3 PartG](https://www.gesetze-im-internet.de/partg/__25.html)) | Veröffentlichungen des Bundestagspräsidenten unter `https://www.bundestag.de/parlament/praesidium/parteienfinanzierung` | frei, nur HTML; je Jahr eine Quelle anlegen |
| Rechenschaftsberichte der Parteien | `https://www.bundestag.de/parlament/praesidium/parteienfinanzierung` | frei |
| abgeordnetenwatch (Abstimmungen, Nebentätigkeiten) | `https://www.abgeordnetenwatch.de/api` | frei; Lizenz und Drossel laut API-Seite |
| Destatis GENESIS | `https://www-genesis.destatis.de/genesisWS/`, Pressemitteilungen `https://www.destatis.de/DE/Presse/Pressemitteilungen/` | kostenlose Registrierung |
| Deutsche Bundesbank (Zeitreihen) | SDMX-Webservice der Bundesbank | frei |
| Handels- und Unternehmensregister | `https://www.handelsregister.de`, `https://www.unternehmensregister.de` | kostenlos; laut Nutzungshinweisen von handelsregister.de höchstens 60 Abrufe pro Stunde, Massenabfragen verboten |
| Gerichte | `bundesverfassungsgericht.de`, `bundesverwaltungsgericht.de`, Justizportale der Länder | frei |
| EU-Recht (Verordnungen, Richtlinien, Entwürfe) | EUR-Lex `https://eur-lex.europa.eu`, maschinenlesbar über Cellar | frei; Webseiten laden teils per JavaScript, dann Cellar nehmen |
| EU-Transparenzregister | `https://data.europa.eu/data/datasets/transparency-register` | Open Data |
| FragDenStaat (IFG-Anfragen, Dokumente) | `https://fragdenstaat.de/api/` | frei |
| Mitschriften der Regierungspressekonferenz | `https://www.bundesregierung.de` (Suche „Regierungspressekonferenz vom <Datum>“) | frei |
| SEC EDGAR (US-Firmen: 10-K, 8-K, Form 4, S-1, 13F) | `https://www.sec.gov/cgi-bin/browse-edgar`, API `https://data.sec.gov/` | frei; die SEC verlangt eine Kontaktangabe im User-Agent und höchstens 10 Anfragen pro Sekunde ([Regeln](https://www.sec.gov/os/accessing-edgar-data)) |
| FEC (US-Wahlkampfgeld) | `https://www.fec.gov/data/`, API `https://api.open.fec.gov/` | Schlüssel von api.data.gov ([Drossel](https://api.data.gov/docs/rate-limits/)); `DEMO_KEY` reicht für einzelne Abfragen |
| US-Gerichtsakten (RECAP) | `https://www.courtlistener.com/docket/<id>/`, PDFs unter `https://storage.courtlistener.com/recap/…` | frei; gescannte PDFs haben oft keine Textebene |
| US-Kongress: Anhörungen und Vernehmungsprotokolle | Seiten der Ausschüsse, PDFs meist unter `…/wp-content/uploads/<Jahr>/<Monat>/` | frei; Zeilennummern stören die Zitatsuche |
| OpenSanctions | `https://www.opensanctions.org` | Schlüssel für nichtkommerzielle Nutzung auf Antrag |
| Bücher: DNB-Katalog (SRU) | `https://services.dnb.de/sru/dnb?version=1.1&operation=searchRetrieve&query=per%3D<Autor>%20and%20tit%3D<Wort>&recordSchema=oai_dc` | frei, ohne Schlüssel; liefert Titel, Verlag, Jahr, ISBN |
| Bücher: Verlagsseite und Leseprobe | Verlagsseite über die ISBN, Leseprobe als PDF | frei; das Inhaltsverzeichnis liefert zitierbare Kapitelsätze |
| Aktuelle Ämter und Titel | Wikidata (Beschreibung und Aussagen mit Datum) | frei; danach mit einer Suche gegenprüfen |

## 4. Hinter Bezahlschranken, legal

- **Bibliotheksausweis:** Staats-, Landes-, Stadt- und Universitätsbibliotheken lizenzieren Pressedatenbanken (z. B. Nexis,
  Genios, PressReader, Munzinger) und Zeitungsarchive, viele davon auch von zu Hause. Beispiele: Staatsbibliothek zu Berlin,
  Stadtbibliotheken mit Onlineangebot.
- **Nur von Hand abrufen.** Die Lizenzbedingungen solcher Datenbanken verbieten meist Programme und Massenabrufe. Ein Verstoß
  kann den Zugang für alle Nutzer einer Bibliothek kosten.
- **Fernleihe** für Bücher und Aufsätze, die die eigene Bibliothek nicht hat.
- **Eigene Abos:** einzelne Artikel im eigenen, angemeldeten Browser lesen (z. B. über Claude in Chrome). Kein Massenabruf.
- **Wissenschaft:** Unpaywall, OpenAlex, CORE, Semantic Scholar, arXiv. Viele Aufsätze haben eine frei zugängliche Fassung.
- **Wayback Machine** (`web.archive.org`) für ältere Fassungen einer Seite. Als Prüfweg ja, als Beleg zählt die Original-URL
  (siehe F11).

## 5. Nie

- **Keine Umgehungswerkzeuge** (Erweiterungen gegen Bezahlschranken, Vorschaltdienste, eigene Skripte). Das ist rechtlich
  verboten, und ein so geholtes Zitat trägt vor Gericht nicht.
- **archive.today / archive.ph nie als Beleg.** Betreiber und Verfahren sind nicht nachprüfbar.
- **Keine automatisierten Massenabfragen** im Handelsregister und in lizenzierten Datenbanken.
- **Keine Sci-Hub-Funktionen.**
- **Keine Schlüssel in Dateien, Skripte oder den Chat.** Schlüssel gehören in Umgebungsvariablen oder in die geschützte
  Plugin-Konfiguration.

## 6. Fallen

### F1 · Negativbefunde sind Befunde
- **Symptom:** „X hat nicht gespendet“ steht im Text, aber niemand weiß, wie das geprüft wurde.
- **Ursache:** Ein fehlender Treffer in der Suche wurde als Beleg genommen.
- **Gegenmittel:** Die vollständige Liste durchsehen (z. B. alle Spendenmeldungen der fraglichen Jahre). Den Negativbefund mit
  Quelle und Stichtag notieren, aber nie als Verbindung zwischen zwei Akteuren anlegen.

### F2 · Revidierte Zahlen
- **Symptom:** Eine amtliche Zahl stimmt nicht mehr mit der aktuellen Veröffentlichung überein.
- **Ursache:** Statistische Ämter korrigieren frühere Werte; die erste Trefferseite zeigt oft den alten Stand.
- **Gegenmittel:** Immer die jüngste Pressemitteilung oder Tabelle suchen und den Stand (Datum) mitschreiben.

### F3 · Presse-Zitat ist nicht das Original
- **Symptom:** Ein Wortlaut „laut Sender X“ weicht vom Protokoll oder Video ab.
- **Ursache:** Medien kürzen, übersetzen oder paraphrasieren in Anführungszeichen.
- **Gegenmittel:** Vor der Veröffentlichung am Protokoll, an der Mitschrift oder am Video prüfen. Bis dahin Güte `sekundaer`.

### F4 · Posts in sozialen Netzwerken
- **Symptom:** Der Post lässt sich nicht abrufen, oder es gibt nur Text aus einem Suchindex.
- **Ursache:** Die Plattformen sperren Bots und Leseprogramme.
- **Gegenmittel:** Text aus einem Suchindex ist kein Beleg. Den Post im eigenen Browser öffnen und als Bildschirmfoto sichern.
  Für einzelne Posts auf X liefert die öffentliche Einbett-Schnittstelle, die auch eingebettete Posts auf Webseiten nutzt, den
  Text: `https://cdn.syndication.twimg.com/tweet-result?id=<ID>&token=a` (HTML-Entitäten entschlüsseln, lange Posts sind
  gekürzt). Gelöschte Posts: den Wortlaut einer Nachrichtenagentur in deren Schreibweise zitieren, mit der Agentur als Quelle.

### F5 · Video-Untertitel gesperrt oder automatisch
- **Symptom:** Die Untertitel lassen sich nicht laden (HTTP 429), oder ein Zitat stammt aus einem automatischen Transkript.
- **Ursache:** Drosselung durch die Plattform; automatische Spuren verhören sich.
- **Gegenmittel:** Nur die Minuten um die Stelle laden (`yt-dlp --download-sections "*MM:SS-MM:SS" -x`) und lokal mit Whisper
  transkribieren. Strittige Stellen mit mehreren Modellen prüfen, nie mit dem erwarteten Text als Prompt (siehe Agent
  `faktenpruefer`). Zitate aus automatischen Transkripten nie ungeprüft übernehmen.

### F6 · Zitate von Hand prüfen kostet zu viel
- **Symptom:** Bei vielen Belegen wird nur ein Teil am Original geprüft.
- **Ursache:** Jede Prüfung von Hand dauert Minuten.
- **Gegenmittel:** `werkzeuge/zitate_pruefen.py belege.json` prüft alle Zitate in einem Lauf. Danach nur noch die Fälle
  `nicht_gefunden`, `mehrdeutig` und `nicht_pruefbar` von Hand.

### F7 · Buch prüfen ohne Websuche
- **Symptom:** Titel oder Autorenname wurden falsch genannt, eine Websuche findet nichts Brauchbares.
- **Ursache:** Schreibfehler im Namen, Suchmaschinen raten.
- **Gegenmittel:** Der DNB-Katalog (SRU, Tabelle oben) findet auch ungenaue Namen; die Verlagsseite liefert Datum und
  Klappentext, die Leseprobe das Inhaltsverzeichnis. Verlage behalten sich Text- und Data-Mining oft vor
  ([§ 44b UrhG](https://www.gesetze-im-internet.de/urhg/__44b.html)): einzeln lesen, kurz zitieren, nichts massenhaft auslesen.

### F8 · US-Wahlkampfgeld nur über die API lesbar
- **Symptom:** `zitate_pruefen.py` meldet bei `fec.gov/data` „nicht_pruefbar“.
- **Ursache:** Die Webseite lädt ihre Daten per JavaScript.
- **Gegenmittel:** Die API abfragen, z. B. `https://api.open.fec.gov/v1/schedules/schedule_b/?api_key=DEMO_KEY&committee_id=<ID>&two_year_transaction_period=<Jahr>`
  (Ausgaben eines Komitees), `…/v1/committee/<ID>/`, `…/v1/candidate/<ID>/`. Zitat leer lassen, Beträge und Daten in die
  Fundstelle schreiben.

### F9 · Organisationen werden umbenannt
- **Symptom:** Derselbe Akteur taucht unter zwei Namen auf, oder ein alter Vorgang trägt den heutigen Namen.
- **Ursache:** Komitees, Firmen und Vereine ändern ihren Namen, die Kennung bleibt.
- **Gegenmittel:** Den Namen aus dem Datensatz des jeweiligen Jahres nehmen, den heutigen in die Kurzbeschreibung. Über die
  Kennung (Registernummer, Komitee-ID) zusammenführen.

### F10 · Schlüssel fehlt, Kontingent leer
- **Symptom:** HTTP 401 oder 402 von einem Such- oder Lesedienst, mitten im Lauf.
- **Ursache:** 401 heißt meist: Schlüssel fehlt oder ist falsch. 402 heißt: Guthaben verbraucht. Anonyme Gratiskontingente
  sind nach wenigen Dutzend Abrufen leer.
- **Gegenmittel:** Schlüssel über die Plugin-Konfiguration setzen (Skills `jina-lesen`, `tavily-suche`). Ausweichwege für
  Wortlaute: `curl -sL` mit neutraler Kennung, PDFs mit `pypdf` oder PyMuPDF im Speicher lesen, ein anderer Dienst (Exa
  `web_fetch`, Tavily `extract`). Vor einem großen Lauf prüfen, ob alle Dienste verbunden sind (`/mcp`).

### F11 · Wayback ist ein Prüfweg, keine Quelle
- **Symptom:** Ein Server sperrt Bots mit 403, der Wortlaut lässt sich nicht prüfen.
- **Ursache:** Bot-Schutz auf Behörden-, Presse- und Firmenseiten.
- **Gegenmittel:** Den Wortlaut an der Wayback-Kopie desselben Originals prüfen. Als Beleg bleibt die Original-URL;
  archive.today bleibt ausgeschlossen.

### F12 · Titel und Ämter ändern sich
- **Symptom:** Eine Beschreibung nennt ein Amt, das die Person nicht mehr hat, oder einen alten Titel.
- **Ursache:** Die Berichte sind älter als der heutige Stand.
- **Gegenmittel:** Vor dem Eintragen den aktuellen Stand prüfen (Wikidata zeigt ihn oft zuerst, danach mit einer Suche
  gegenprüfen) und das Datum mitschreiben.

### F13 · Primärquelle statt Paywall-Zitat
- **Symptom:** Eine Aussage hängt an einem Artikel hinter einer Bezahlschranke.
- **Ursache:** Die Presse war schneller in der Suche als das Original.
- **Gegenmittel:** Erst die Firma, das Gericht oder die Behörde suchen (Mitteilung, Beschluss, Pflichtmeldung), dann die Presse.

### F14 · Parlamentarische Anfragen sind starke Primärquellen
- **Symptom:** Was eine Behörde zu einem Thema weiß oder einstuft, steht nur in der Presse.
- **Ursache:** Die Antworten der Regierung auf Kleine und Große Anfragen werden selten direkt gesucht.
- **Gegenmittel:** Im DIP nach Drucksachen zum Thema suchen. Ob etwas als „VS-NfD“, „VS-Vertraulich“ oder „geheim“
  eingestuft ist, steht im Text; nie aus der Presse übernehmen. Eine Drucksache kann im DIP stehen und als PDF noch 404
  liefern: Bis das PDF lesbar ist, nichts daraus behaupten.

### F15 · Agenturen paraphrasieren in Anführungszeichen
- **Symptom:** Ein Zitat aus einer Pressekonferenz weicht zwischen zwei Agenturen ab.
- **Ursache:** Agenturtexte kürzen und glätten.
- **Gegenmittel:** Das Zitat zählt nur aus der Mitschrift (z. B. Regierungspressekonferenz auf bundesregierung.de) oder aus dem
  Video.

### F16 · Lange PDFs gezielt lesen
- **Symptom:** Ein Lesedienst liefert bei langen PDFs nur Ausschnitte oder meldet, die gezielte Auszugsfunktion sei nicht
  verfügbar.
- **Ursache:** Grenzen des Dienstes bei großen Dokumenten.
- **Gegenmittel:** Das PDF selbst laden, Text mit `pypdf` oder PyMuPDF ziehen und mit `grep` nachlesen. Zeilennummern und
  Fußnotenziffern beim Vergleich herausrechnen.

### F17 · Öffentlicher Schlüssel abgelaufen
- **Symptom:** Eine amtliche API antwortet plötzlich 401.
- **Ursache:** Der veröffentlichte Gemeinschaftsschlüssel (z. B. beim DIP) wurde getauscht.
- **Gegenmittel:** Den gültigen Schlüssel aus der API-Doku nehmen. Nie in Dateien oder Skripte schreiben, nur als
  Umgebungsvariable.

### F18 · Großer Prüflauf ohne Pilot
- **Symptom:** Ein Lauf über viele Behauptungen kostet ein Vielfaches der Schätzung.
- **Ursache:** Die Kosten je Behauptung wurden nicht gemessen.
- **Gegenmittel:** Erst einen kleinen Pilot mit der vollen Prüfkette fahren, Zeit und Kosten messen, hochrechnen und den
  Menschen vor dem Voll-Lauf mit diesen Zahlen fragen. Eine Abbruchregel wie „derselbe Mangel zum zweiten Mal → raus“ nur
  anwenden, wenn der Satz seit der letzten Prüfung unverändert ist (gleicher Hash), sonst fliegen nachgebesserte Sätze raus.

### F19 · Presseanfrage, die selbst etwas behauptet
- **Symptom:** Eine Anfrage an eine Behörde setzt ein Verfahren „gegen X“ voraus, das die Behörde so nie genannt hat.
- **Ursache:** Die Anfrage übernimmt eine Zuspitzung aus der Recherche.
- **Gegenmittel:** Den Wortlaut der Pressemitteilung übernehmen und erst fragen, ob X dort Beschuldigter ist. Jede Anfrage vor
  dem Senden von einem frischen Agenten gegenlesen lassen.

### F20 · Auskunftsanspruch ohne Presseausweis
- **Symptom:** Eine Behörde bittet um einen Presseausweis, bevor sie antwortet.
- **Ursache:** Der Auskunftsanspruch hängt am journalistischen Angebot, nicht am Ausweis.
- **Gegenmittel:** Nachweis über Veröffentlichungen, ein Impressum mit verantwortlicher Person
  (§ 18 Abs. 2 Medienstaatsvertrag) und eine redaktionelle Adresse.
  Gegenüber Landesbehörden das Landespressegesetz nennen; für Online-Angebote § 18 Abs. 4 in Verbindung mit § 5 MStV.
  Anfragen von einer redaktionellen Adresse senden, nicht von einer Firmenadresse. Die Rechtsprechung dazu (u. a. BVerwG
  10 C 2.23, BVerwG 7 C 26.17) vor der Nutzung selbst nachlesen. Das ist keine Rechtsberatung.

### F21 · Geschätztes Datum
- **Symptom:** Ein Beleg trägt ein falsches Veröffentlichungsdatum.
- **Ursache:** Werkzeuge wie `guess_datetime_url` schätzen das Datum aus Metadaten.
- **Gegenmittel:** Das Datum immer auf der Seite selbst nachprüfen (Zeile unter dem Titel, Impressum der Mitteilung,
  Drucksachendatum).
