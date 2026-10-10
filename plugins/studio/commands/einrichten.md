---
description: Richtet das Werkzeug studio ein – prüft die Installation, legt studio.toml aus der Vorlage an (nie überschreiben) und zeigt die wirksame Konfiguration.
argument-hint: "[zielordner für studio.toml, Vorgabe: aktueller Ordner]"
allowed-tools: Bash(studio --version), Bash(studio konfig zeigen), Bash(studio konfig vorlage:*), Read
---

# Werkzeug `studio` einrichten

Arbeite die Schritte der Reihe nach ab. Ändere nichts außerhalb des genannten Zielordners und überschreibe keine Datei.

1. **Installation prüfen:** Führe `studio --version` aus.
   - Klappt das nicht, installiere nichts selbst. Zeige dem Menschen diesen Befehl und erkläre die Extras:
     ```
     uv tool install "git+https://github.com/ThePyth0nKid/quelle-bis-schnitt#subdirectory=plugins/studio/werkzeuge"
     ```
     Extras: `[obs]` für OBS-Steuerung (`studio obs-modus`, `studio waechter`, `studio prompter einspielen`),
     `[whisper]` für `studio transkript`, z. B.
     `uv tool install "studio-werkzeuge[obs,whisper] @ git+https://github.com/ThePyth0nKid/quelle-bis-schnitt#subdirectory=plugins/studio/werkzeuge"`.
     Für Messen und Mastern braucht es außerdem `ffmpeg` und `ffprobe` im Suchpfad.
     Dann hier aufhören und den Menschen bitten, den Befehl nach der Installation erneut aufzurufen.

2. **Zielort klären:** Ziel ist `$ARGUMENTS/studio.toml`, ohne Argument `./studio.toml`. Sag dem Menschen, wo das
   Werkzeug sonst sucht: `$STUDIO_KONFIG`, dann `./studio.toml`, dann der Benutzer-Konfigordner
   (Windows `%APPDATA%\studio\studio.toml`, sonst `~/.config/studio/studio.toml`).

3. **Vorlage anlegen:** Prüfe mit Read, ob die Zieldatei schon existiert.
   - Existiert sie: **nicht überschreiben**. Frag den Menschen, ob er sie behalten will (Standard) oder einen anderen
     Zielort nennt.
   - Existiert sie nicht: Frag kurz nach, dann `studio konfig vorlage --ziel <zielpfad>` (ohne `--ueberschreiben`).

4. **Konfiguration zeigen:** `studio konfig zeigen`. Geheimnisse erscheinen maskiert. Gib keine Werte aus der Datei
   wieder, die wie Passwörter oder Schlüssel aussehen.

5. **Was der Mensch eintragen muss:** Fasse zusammen, welche Werte noch Platzhalter in `<spitzen Klammern>` sind
   (z. B. `inbox`, Namen der Kameraquellen und Source-Record-Filter in OBS, Prozessname der Prompter-Software). Das
   OBS-Passwort gehört nie in die Datei, sondern in die Umgebungsvariable, deren Name dort steht.

6. **Nächste Schritte nennen:** Probeaufnahme und `studio klick-check` (Skill `dreh-setup`), ausführliche Anleitung in
   `docs/so-filme-ich.md` im Repo.
