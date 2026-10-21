# YAVIS – kostenloser, lokaler Sprachassistent für Windows 11

Schwarz-rot-gelbe Oberfläche mit einem Kreis in der Mitte, der mit der Stimme atmet. Läuft ohne Konsolenfenster.

## Status (ehrlich)

- Getestet (automatisch, 26 Tests): Gedächtnis, Aktivierungswörter (auch mit kleinen Hörfehlern), „Master“-Anrede, Gefühls-Tags, Neutral-Befehl, Stimmenkatalog, Musik-Player (Lautstärke, leiser beim Sprechen, Lieder hinzufügen/löschen, Sprachbefehle), Tonhöhe/Lautstärke, Kreis-Zeichnung, App-Freigabeliste, Sicherheitssperren, Bestätigung beim Löschen, Entwürfe.
- **Nicht getestet:** Mikrofon, echte Stimmen-Klänge, Ollama-Anbindung, Installer und das Fenster selbst – das braucht einen echten Windows-PC. Rückmeldungen bitte mit `%APPDATA%\YAVIS\yavis.log`.

## Installation (nur herunterladen)

1. `YAVIS-Setup.exe` unter *Releases* herunterladen und ausführen (Windows SmartScreen: „Weitere Informationen → Trotzdem ausführen“).
2. YAVIS starten. **Beim ersten Start richtet sich alles selbst ein** (Internet nötig, einmalig, ca. 5–6 GB): Ollama, KI-Modell, Spracherkennung, Stimme. Der Fortschritt steht unter dem Kreis.
3. Sage „YAVIS“ und dann deinen Befehl.

Selbst bauen: GitHub-Reiter *Actions → Build YAVIS-Setup.exe → Run workflow*, oder lokal `.\build.ps1`.

## Bedienung

„YAVIS, öffne den Rechner“ · „YAVIS, suche Datei Rechnung“ · „YAVIS, recherchiere Preise für …“ · „YAVIS, schreibe eine Produktbeschreibung für …“ · „YAVIS, merk dir, dass …“ · „YAVIS, das war falsch, weil …“ · „YAVIS, beenden“.

Nach einer Antwort läuft das Gespräch ca. 10 Sekunden ohne erneutes „YAVIS“ weiter.

## Gefühle

YAVIS antwortet mit Gefühl: nett, lieb, fröhlich, traurig, böse (gereizt, nie verletzend) oder neutral. Man hört es an Tempo, Tonhöhe und Betonung; der Kreis ändert Farbe und Bewegung. Mit der Stimme „Thorsten Emotional“ kommen echte Emotions-Sprecher dazu.
Neutral befehlen: „YAVIS, sei neutral“ – zurück: „YAVIS, zeig wieder Gefühle“ (oder Schalter in den Einstellungen).

## Hintergrundmusik

Im Menü **Musik**: Lieder hinzufügen (MP3, WAV, WMA, M4A), abspielen, überspringen, löschen und die **Lautstärke** per Regler einstellen (zusätzlich ein kleiner Regler links in der Seitenleiste). Die Musik läuft in Endlosschleife, startet beim Programmstart von selbst (abschaltbar) und wird **leiser, solange YAVIS spricht oder zuhört**.
Lieder liegen in `%APPDATA%\YAVIS\music`. Ein mitgeliefertes Lied aus dem Ordner `music\` wird beim ersten Start dorthin kopiert.
Per Sprache: „YAVIS, Musik aus / an“, „Musik leiser / lauter“, „nächstes Lied“, „vorheriges Lied“.
Hinweis: Das Repo ist öffentlich – nur Musik in `music\` legen, die du veröffentlichen darfst, sonst über „Musik hinzufügen“ im Programm einfügen.

## Einstellungen (im Programm)

Aktivierungswörter (eigene eintragen, Genauigkeit einstellbar) · Stimme (Frau/Mann, „Mommy“, „Muskelmann“, offline oder online) · Tempo · Stimme mit Gefühl testen · Mikrofon · Spracherkennung (tiny/base/small/medium) · KI-Modell · Neutral-Modus · Text unter dem Kreis ein/aus.
Datei: `%APPDATA%\YAVIS\config.json`.

## Kosten & Lizenzen

| Baustein | Lizenz | Kosten |
|---|---|---|
| Ollama | MIT | 0 € |
| Qwen2.5-7B (Standardmodell) | Apache 2.0 | 0 € |
| faster-whisper / Whisper | MIT | 0 € |
| Piper-Stimmen (offline) | MIT (Programm); Stimmenlizenzen der einzelnen Sprecher bitte prüfen | 0 € |
| Edge-Stimmen (optional, online) | inoffizielle, kostenlose Schnittstelle ohne Schlüssel, kann ausfallen | 0 € |
| ddgs (DuckDuckGo-Suche) | MIT | 0 € |
| GitHub Actions (öffentliche Repos), Inno Setup, PyInstaller | frei | 0 € |

Lizenzen vor Weitergabe/gewerblicher Nutzung bitte selbst gegenprüfen. Online verifiziert wurde hier nur, dass die Stimmen im Piper-Katalog existieren.

## Einschränkungen

- **Zuhören:** Lokal mit Whisper „small“, automatische Rauschanpassung, Vorlauf, Fuzzy-Aktivierung. „Perfekt“ ist bei Sprache nie garantiert: Hintergrundgeräusche, Mikrofonqualität und Dialekt wirken sich aus. Tipp: gutes Mikrofon wählen, bei Bedarf „medium“ einstellen (genauer, langsamer).
- **Hardware:** 7B-Modell braucht ca. 8 GB RAM, ohne GPU 10–30 s pro Antwort. Schwächerer PC: `"model": "llama3.2:3b"`.
- **Stimmen:** Klang von „Mommy“ und „Muskelmann“ entsteht durch Auswahl einer passenden Stimme plus Tempo-/Tonhöhen-Feinabstimmung. Wie echt das für dich klingt, hängt vom Geschmack ab – bitte im Programm ausprobieren. Online-Stimmen klingen meist natürlicher, schicken den Text aber an Microsoft.
- **Gefühle:** Das Sprachmodell wählt das Gefühl, die Stimme setzt es um. Bei Offline-Stimmen ist der Ausdruck dezenter als bei Menschen.
- **Musik und Zuhören:** Läuft die Musik laut über Lautstärke-Lautsprecher, hört das Mikrofon sie mit und YAVIS versteht dich schlechter. Mit Kopfhörer oder niedriger Lautstärke klappt es am besten. Wiedergabe über die Windows-Mediensteuerung (MP3/WAV/WMA/M4A; OGG/FLAC werden nicht abgespielt).
- **Gesprächsfenster:** Nach einer Antwort reagiert YAVIS kurz ohne „YAVIS“; Fernseher/Gespräche im Raum können dann hineinreden (`conversation_seconds` auf 0 setzen zum Abschalten).
- **Websuche:** DuckDuckGo ohne Schlüssel; kann gedrosselt werden oder ausfallen.
- **Lernen:** Nur über gespeichertes Feedback im Prompt, kein Selbst-Umprogrammieren.
- **Verkaufshilfe:** Nur Entwürfe in `Dokumente\YAVIS\Entwuerfe` und Preisrecherche. Veröffentlichen/Kaufen/Bezahlen/Senden sind absichtlich nicht eingebaut.
- **Datenschutz:** Gedächtnis liegt in `%APPDATA%\YAVIS`. Das Mikrofon lauscht lokal dauerhaft, nichts wird gespeichert oder hochgeladen. Internet nur für Einrichtung, Websuche und optionale Online-Stimmen.
- Keine Code-Signatur: Windows SmartScreen warnt evtl.
