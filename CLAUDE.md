# TikTok-Videoprojekt

## Arbeitsweise (Wunsch des Nutzers, immer einhalten)
- **Freigabe-Befehl: „du darfst“.** Ein Video wird NUR gerendert, wenn der Nutzer „du darfst“ schreibt. Vorher nur Storyboard (bzw. ElevenLabs-Text) liefern – auch wenn er „erstell ein Video“ schreibt.
- **Vor jedem Video zuerst ein Storyboard zeigen** – als **Bilder** (ein echtes Vorschaubild pro Szene, so wie es im Video aussieht, mit Zeit + Beschreibung darunter) plus kurze Tabelle (Szenen, Zeiten, Einblendungen, Bewegungen, Sounds). Auf Freigabe warten, erst nach dem OK rendern.
- TikTok-Abstände einhalten: nichts Wichtiges oben < 190 px, rechts > 930 px (Like-/Kommentar-/Teilen-Spalte) und unten > 1480 px (Bildunterschrift).
- Videos für das Creator-Rewards-Programm müssen **länger als 60 Sekunden** sein.
- Untertitel Wort für Wort, Soundeffekte, Einblendungen passend zum Gesprochenen.
- Sprache der Inhalte: Deutsch.

## Serie „Käsemann wird reich“
- Käsemann: Käsestick-Figur mit roter Kappe, gelber Warnweste, blauer „Käsemann“-Verpackung, roten Sneakern.
- Kontostand-Zähler und Ziel 1.000.000 € in jeder Folge; Ende: Zuschauer stimmen in den Kommentaren über den nächsten Schritt ab.
- Folge 1: 5 Pfandflaschen → 1,25 €.

## Technik
- Engine: `engine/` (Canvas, SFX, Render). Schnitt hochgeladener Videos: siehe `films/clip_gymfehler.py`.
- Transkription: faster-whisper (Audio vorher per ffmpeg in 16-kHz-Raw umwandeln).
- Freistellen der Figur: rembg mit Modell `isnet-general-use` (ca. 1,3 s pro Bild).
