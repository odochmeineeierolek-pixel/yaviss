# YAVIS – kostenloser, lokaler Sprachassistent für Windows 11

## Status (ehrlich)
- Getestet: Gedächtnis, Aktivierungswort-Erkennung, „Master“-Anrede, App-Freigabeliste, Sicherheitssperren, Bestätigungspflicht beim Löschen, Entwürfe (9 Unit-Tests, bestanden).
- **Nicht getestet:** Mikrofon, Stimme, Ollama-Anbindung, PyInstaller-Build und Installer. Das braucht einen echten Windows-PC.
- Die `YAVIS-Setup.exe` ist **noch nicht gebaut**.

## YAVIS-Setup.exe kostenlos bauen (Weg A, ohne eigene Entwicklungsumgebung)
1. Kostenloses GitHub-Konto, neues **öffentliches** Repository, Projektordner hochladen.
2. Reiter **Actions** → „Build YAVIS-Setup.exe“ → *Run workflow*.
3. Nach ca. 10–20 Minuten unter *Artifacts* `YAVIS-Setup` herunterladen.

## Weg B: lokal auf Windows 11
Python 3.11 und Inno Setup 6 installieren, dann in PowerShell: `.\build.ps1`
Ergebnis: `installer\YAVIS-Setup.exe`

## Installation
1. `YAVIS-Setup.exe` ausführen (Desktop-Verknüpfung; Autostart optional ankreuzbar).
2. Ersteinrichtung läuft am Ende automatisch (Internet nötig, einmalig): installiert Ollama per winget, lädt das Modell (~4,7 GB) und das Whisper-Modell.
3. YAVIS starten, „YAVIS“ sagen, dann den Befehl.

## Bedienung
„YAVIS, öffne den Rechner“ · „YAVIS, suche Datei Rechnung“ · „YAVIS, recherchiere Preise für …“ · „YAVIS, schreibe eine Produktbeschreibung für …“ · „YAVIS, merk dir, dass …“ · „YAVIS, das war falsch, weil …“ · „YAVIS, beenden“.
Einstellungen: `%APPDATA%\YAVIS\config.json` (Modell, Apps, Aktivierungswörter). Beenden auch über das Tray-Symbol.

## Kosten & Lizenzen
| Baustein | Lizenz | Kosten |
|---|---|---|
| Ollama | MIT | 0 € |
| Qwen2.5-7B (Standardmodell) | Apache 2.0 | 0 € |
| faster-whisper / Whisper | MIT | 0 € |
| Windows-Stimme (SAPI) | in Windows enthalten | 0 € |
| ddgs (DuckDuckGo-Suche, ohne API-Schlüssel) | MIT | 0 € |
| GitHub Actions (öffentliche Repos), Inno Setup, PyInstaller | frei | 0 € |

Lizenzen vor Weitergabe/gewerblicher Nutzung bitte selbst gegenprüfen. Ich konnte sie hier nicht online verifizieren.

## Einschränkungen
- **Hardware:** 7B-Modell braucht ca. 8 GB RAM, ohne GPU 10–30 s pro Antwort. Schwächerer PC: `"model": "llama3.2:3b"` setzen.
- **Aktivierung „YAVIS“:** Whisper-basiert (kein Spezial-Wakeword), das Mikrofon lauscht lokal dauerhaft, es wird nichts gespeichert oder hochgeladen. Es kann mal etwas falsch verstanden werden. Variationen stehen in `wake_words`.
- **Stimme:** Windows-Stimme „Hedda“ (weiblich, deutsch), verständlich aber nicht so natürlich wie Cloud-Stimmen. Upgrade später: Piper-TTS (frei).
- **Websuche:** DuckDuckGo-Scraping ohne Schlüssel; kann gedrosselt werden oder ausfallen.
- **Lernen:** Nur über gespeichertes Feedback im Prompt, kein Selbst-Umprogrammieren.
- **Verkaufshilfe:** Nur Entwürfe in `Dokumente\YAVIS\Entwuerfe` und Preisrecherche. Veröffentlichen/Kaufen/Bezahlen/Senden sind absichtlich nicht eingebaut.
- **Datenschutz:** Gedächtnis liegt in `%APPDATA%\YAVIS`. Internet nur für Einrichtung und Websuche.
- Keine Code-Signatur: Windows SmartScreen warnt evtl. („Trotzdem ausführen“).
