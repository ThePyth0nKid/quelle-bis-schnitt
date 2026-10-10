---
name: deploy-lock
description: Deploy-Wächter für parallele Agenten-Stränge. Vor jedem Deploy (Server hochladen, App-Build, Store-Einreichung, Produktions-Migration) einen Lock je Projekt holen, dann mit der Obermenge-Prüfung beweisen, dass jeder schon ausgelieferte Stand im neuen Stand steckt und die Arbeitskopie sauber ist; danach den Lock mit Ergebnis freigeben. Exit 1 heißt nicht deployen. Nutze diesen Skill bei „deploy“, „live bringen“, „hochladen“, „Build einreichen“, „Migration auf Produktion“, „wer deployt gerade?“, „Lock“, „Obermenge“, und immer, wenn mehrere Agenten oder Sitzungen am selben Projekt arbeiten.
---

# Deploy-Lock und Obermenge

Zwei Gefahren, sobald mehrere Agenten-Stränge am selben Projekt arbeiten:

1. **Zwei Stränge deployen gleichzeitig.** Store-Einreichungen überschreiben sich, Build-Nummern doppeln sich, ein
   Server-Deploy ersetzt den anderen. Oft scheitern beide still.
2. **Ein Strang deployt einen Stand, dem die Arbeit eines anderen fehlt.** Seine Tests sind grün, denn aus Sicht seines
   Branches ist alles in Ordnung. Live verschwindet trotzdem, was schon ausgeliefert war.

Der Wächter `deploy_waechter/waechter.py` beantwortet beides: ein Lock je Projekt gegen Gleichzeitigkeit, die
Obermenge-Prüfung gegen Rückwürfe. Nur Standardbibliothek, Python 3.11 oder neuer.

## Aufruf

Das Skript liegt in diesem Plugin unter `werkzeuge/deploy_waechter/waechter.py` (`${CLAUDE_PLUGIN_ROOT}` ist der Ordner
des Plugins). Du kannst es auch in dein Projekt kopieren; es braucht nichts außer Python und Git.

```bash
python "${CLAUDE_PLUGIN_ROOT}/werkzeuge/deploy_waechter/waechter.py" --help
```

Im Folgenden steht `waechter` für diesen Aufruf.

## Ablauf, immer in dieser Reihenfolge

```bash
# 1. Lock holen. Exit 0 = gehört dir. Exit 1 = ein anderer Strang deployt DASSELBE Projekt: nicht deployen.
waechter acquire --halter "<strang-kürzel>" --bereich "<backend|app-ios|migration|…>" --notiz "<was, aus welchem Branch>"

# 2. Obermenge prüfen, aus genau dem Ordner, der hochgeladen wird. Exit 1 = nicht deployen.
waechter obermenge --art <art>

# 3. Deployen (dein eigener Befehl).

# 4. Lock freigeben, auch wenn der Deploy scheiterte. Den ausgelieferten Commit merken.
waechter release --halter "<strang-kürzel>" --ergebnis "<z. B. Build 142 ok | abgebrochen>" --ausgeliefert <commit>
```

Wer gerade deployt: `waechter status --alle`. Eine Notiz ins Log: `waechter log "Text"`.

## Exit-Codes

| Befehl | 0 | 1 | 2 |
|---|---|---|---|
| `acquire` | Lock gehört dir | anderer Strang deployt dasselbe Projekt, oder die Lock-Datei ist unlesbar | Fehler, z. B. Log nicht schreibbar (der Lock wird dann wieder entfernt) |
| `release` | frei | fremder oder unlesbarer Lock; Übersteuern nicht bestätigt | Fehler (z. B. `--erzwingen` ohne ausreichenden Grund) |
| `status` | frei | belegt, auch bei unlesbarer Lock-Datei (mit `--alle`: mindestens ein Projekt belegt) | Fehler |
| `obermenge` | deployen erlaubt | **nicht deployen**; Übersteuern nicht bestätigt | Fehler |

Exit 2 heißt immer Aufruf-, Konfigurations- oder Dateifehler, nie „belegt“. Behandle 2 wie 1: nicht deployen.

## Nie pipen

```bash
waechter acquire … | tail -1     # FALSCH: der Exit-Code ist der von tail, also immer 0
waechter acquire …               # richtig: Ausgabe direkt lesen
echo $?                          # oder den Exit-Code sofort danach prüfen
```

In einer Pipe liefert die Shell den Exit-Code des letzten Befehls. Ein belegter Lock sieht dann aus wie ein freier, und
der Deploy läuft gegen einen fremden Strang.

## Lock je Projekt

- Verschiedene Projekte sperren sich nie gegenseitig. Innerhalb eines Projekts sperrt jeder Bereich jeden anderen: Ein
  Server-Deploy und eine Migration im selben Projekt gehen sich an die Wurzel.
- Das Projekt kommt aus `--projekt`, sonst `$DEPLOY_PROJEKT`, sonst `projekt` in der Konfiguration, sonst aus dem Namen
  der Git-Wurzel. Bedient ein Repo mehrere Deploy-Ziele (z. B. Staging und Produktion als getrennte Projekte), gib es
  ausdrücklich an.
- Die Lock-Datei wird atomar angelegt (`O_EXCL`): Zwei Stränge können nicht beide gewinnen.
- **Verwaisung:** Ein Lock, der älter als `verwaist_nach_minuten` ist (Voreinstellung 90, nicht gemessen, einstellbar,
  `0` = nie), gilt als liegen geblieben und wird beim nächsten `acquire` übernommen, mit Eintrag im Log. Die Übernahme
  ist atomar: Der alte Lock wird erst weggezogen (`os.replace`), nur wer das schafft, legt den neuen an. Stellt sich
  heraus, dass inzwischen ein frischer Lock dort lag, wird er zurückgelegt.
- **Unlesbare Lock-Datei** (leer, kaputt, ohne gültigen Zeitpunkt): gilt in `acquire`, `status` und `release` als
  belegt bzw. fremd, wird nie still gelöscht und erst übernommen, wenn die Datei selbst älter als die Verwaisung ist.
- **Fremden Lock freigeben** darf nur ein Mensch, bewusst: `release --erzwingen --grund "…"` an einem Terminal (siehe
  „Der Mensch entscheidet“).
- Projektnamen werden zu Dateinamen normalisiert (Kleinbuchstaben, `-`). Unter Windows reservierte Namen wie `con` oder
  `nul` bekommen das Präfix `p-`.

## Obermenge: nichts Ausgeliefertes fällt heraus

**Hart (Exit 1):** Jeder ausgelieferte Stand muss ein Vorfahre des Ziels sein. Ausgeliefert ist, was

- auf eine der Referenzen in `obermenge.ausgeliefert_refs` zeigt (z. B. Tags `ausgeliefert/*`, die du nach jedem Deploy
  setzt), oder
- per `release --ausgeliefert <commit>` im Log steht (in den letzten `tage` Tagen, Voreinstellung 10).

Fehlt ein Stand, wirft dieser Deploy genau diese Arbeit zurück. Richtig ist: die fehlende Arbeit **herein** mergen, nie
umgekehrt, und neu prüfen. Ist ein Commit im Repo unbekannt (nicht geholt), ist die Obermenge nicht beweisbar:
`--fetch` oder `git fetch` und neu prüfen.

**Mit `--art`:** Ein fehlender Commit zählt nur hart, wenn er in den Pfaden dieser Deploy-Art
(`[obermenge.arten.<art>] pfade = [...]`) etwas mitbringt, das dem Ziel fehlt. Ein Commit, der nur die App ändert, ist
für einen Server-Deploy kein Rückwurf.

**Arbeitskopie (Exit 1):** Ist das Ziel `HEAD`, prüft der Wächter uncommittete und neue Dateien (mit `--art` nur in deren
Pfaden). Viele Deploy-Werkzeuge laden den Ordner hoch, nicht den Commit: Halbfertiges fährt sonst mit. Baut dein Deploy
nachweislich aus dem Commit (z. B. in der CI), schalte das mit `--ohne-arbeitskopie` ab.

**Weich (nur Bericht):** Branches mit Arbeit der letzten Tage, die nicht im Ziel stecken. Das ist kein Fehler, aber es
muss eine Entscheidung sein, kein Versehen.

**Ohne bekannte Basis** (noch nie etwas ausgeliefert) sperrt die Prüfung ebenfalls. Beim allerersten Deploy übersteuert
ein Mensch bewusst am Terminal: `obermenge --trotzdem --grund "erster Deploy dieses Projekts"`.

## Der Mensch entscheidet

Der Wächter meldet und sperrt per Exit-Code. Übersteuern kann nur ein Mensch, ausdrücklich und mit Begründung:

- `obermenge --trotzdem --grund "…"`: diesen Deploy trotz Befund erlauben.
- `obermenge --bewusst-draussen <commit> --grund "…"`: einen ausgelieferten Stand dauerhaft ausnehmen (z. B. weil er
  zurückgezogen wurde). Der Vermerk selbst blockiert später nichts.
- `release --erzwingen --grund "…"`: einen fremden Lock freigeben.

Technisch abgesichert:

- Die Schalter wirken nur **interaktiv an einem Terminal**. Der Wächter fragt nach und übersteuert nur, wenn der Mensch
  mit `ja` antwortet. Ohne Terminal (wie bei einem Agenten im Hintergrund) kommt „Übersteuern nur interaktiv durch einen
  Menschen“ und Exit 1.
- `--grund` braucht mindestens 10 Zeichen (Voreinstellung).
- Ins Log kommen Grund, Halter und der Benutzername des Betriebssystems (`getpass.getuser()`).

Agenten nutzen diese Schalter nicht. Sie zeigen dem Menschen den Befund und den passenden Befehl, und der Mensch führt ihn
selbst im Terminal aus.

## Konfiguration

`.deploy-waechter.toml` in der Git-Wurzel (oder `--konfig <datei>`, sonst im Benutzer-Konfigordner). Alle Angaben sind
optional; ohne Datei liegen Lock und Log im Benutzer-Zustandsordner. Vorlage mit Erklärungen:
`werkzeuge/deploy_waechter/deploy-waechter.beispiel.toml`.

**Konfiguration aus dem Repo ist eingeschränkt.** Ein geklontes Repo ist fremder Inhalt. Liegt die Datei in der
Git-Wurzel, dürfen `lock.ordner` und `log.datei` nur relative Pfade **unterhalb des Zustandsordners** sein (kein `~`,
kein `$VAR`/`%VAR%`, kein absoluter Pfad, kein `..` hinaus). Der Wächter meldet beim Laden, dass er eine
Repo-Konfiguration nutzt. Andere Orte gehören in die Benutzer-Konfiguration oder werden per `--konfig` übergeben. Werte
werden auf ihren Typ geprüft: `log_als_quelle = "false"` (Text statt Wahrheitswert) ist ein Fehler, keine stille
Umdeutung.

| Schlüssel | Bedeutung |
|---|---|
| `projekt` | Projektname für Lock und Log |
| `lock.ordner` | Ordner der Lock-Dateien; alle Stränge, die sich absprechen, brauchen denselben |
| `lock.verwaist_nach_minuten` | ab wann ein Lock als verwaist gilt (Voreinstellung 90, `0` = nie) |
| `log.datei` | append-only Log, eine Zeile je Ereignis: `- Zeit · [Projekt] Ereignis` |
| `obermenge.ausgeliefert_refs` | Git-Referenzmuster für ausgelieferte Stände |
| `obermenge.log_als_quelle` | auch `release --ausgeliefert` aus dem Log lesen (Standard ja) |
| `obermenge.tage` | Zeitfenster für Log-Einträge und die weiche Liste (Voreinstellung 10) |
| `obermenge.arten.<art>.pfade` | Pfade, die eine Deploy-Art ausliefert |

Das Log wird nur angehängt, nie umgeschrieben. Zeilenumbrüche in Notizen werden zu Leerzeichen, damit jede Zeile ein
Ereignis bleibt.

## Fallen

### F1 · Gepipter Exit-Code

**Symptom:** Ein Deploy lief, obwohl ein anderer Strang den Lock hielt.
**Ursache:** `acquire … | tail -1`: Der Exit-Code war der von `tail`.
**Gegenmittel:** Nie pipen. Ausgabe direkt lesen oder `$?` sofort prüfen.

### F2 · Zwei Stränge, ein Projekt

**Symptom:** Zwei Store-Einreichungen scheitern still, Build-Nummern doppeln sich, ein Server-Deploy überschreibt den
anderen.
**Ursache:** Keine Absprache zwischen parallelen Strängen.
**Gegenmittel:** Lock je Projekt vor jedem Deploy, alle Bereiche eines Projekts sperren sich gegenseitig.

### F3 · Ein globaler Lock blockiert unnötig

**Symptom:** Ein Strang wartet auf einen Deploy, der ein ganz anderes Projekt betrifft, oder deployt aus Ungeduld gegen
den Lock.
**Ursache:** Ein Lock für alle Projekte, obwohl getrennte Projekte sich gar nicht in die Quere kommen können.
**Gegenmittel:** Lock je Projekt. Ein Lock, der mehr sperrt als nötig, wird umgangen.

### F4 · Grüner Branch, verlorene Arbeit

**Symptom:** Nach dem Deploy fehlen live Funktionen, die schon ausgeliefert waren. Kein Test hat angeschlagen.
**Ursache:** Der Strang baute aus seinem eigenen Branch, der die Arbeit eines parallelen Strangs nicht kannte.
**Gegenmittel:** `obermenge` vor jedem Deploy. Fehlende Arbeit herein mergen, nie umgekehrt.

### F5 · Die Arbeitskopie fährt mit

**Symptom:** Halbfertige, uncommittete Arbeit landet im Build.
**Ursache:** Das Deploy-Werkzeug lädt den Ordner hoch, nicht den Commit.
**Gegenmittel:** `obermenge` prüft die Arbeitskopie. Aus einem sauberen Stand bauen: `git clone --local` oder
`git worktree add --detach <pfad> <commit>`.

### F6 · Mergen im geteilten Arbeitsbaum

**Symptom:** Beim Hereinmergen der fehlenden Arbeit landen fremde, uncommittete Änderungen im Deploy oder gehen verloren.
**Ursache:** Im Hauptbaum arbeiten andere Stränge, deren Arbeit noch nicht committet ist.
**Gegenmittel:** Hereinmergen in einer eigenen Kopie (`git clone --local`), nicht im geteilten Hauptbaum.

### F7 · Fehlalarme machen den Wächter wertlos

**Symptom:** Agenten lernen, die Prüfung zu überspringen.
**Ursache:** Der Wächter meldet Commits als Rückwurf, die dieses Ziel gar nicht ausliefert, oder ein Vermerk „bewusst
draußen“ blockiert selbst den nächsten Deploy.
**Gegenmittel:** `--art` mit den Pfaden je Deploy-Art; Ausnahmen über `--bewusst-draussen`, die nie selbst sperren.

### F8 · Der Wächter wird nicht aufgerufen

**Symptom:** Der Rückwurf passiert, obwohl der Wächter ihn gestoppt hätte.
**Ursache:** Die Prüfung stand in keiner Deploy-Anleitung.
**Gegenmittel:** Lock und Obermenge als Pflichtschritte in jede Deploy-Anleitung und ins `CLAUDE.md` schreiben (Baustein im
Skill `arbeitsweise`).

### F9 · Liegen gebliebener Lock

**Symptom:** Alle warten, aber niemand deployt.
**Ursache:** Ein Strang brach ab, ohne `release` aufzurufen.
**Gegenmittel:** `release` immer aufrufen, auch nach einem Fehlschlag (`--ergebnis "abgebrochen"`). Für den Notfall greift
die Verwaisung nach `verwaist_nach_minuten`.
