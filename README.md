# Mery-Güüger Übungs-App

Übungs-App der Guggenmusik Mery-Güüger Merenschwand: Musiktheorie mit Quiz und Lieder üben (mitspielen oder Ventile auswendig lernen).

Die App ist eine einfache Webseite ohne Server. Sie läuft unter https://mery-gueueger.github.io/

- `index.html` – die ganze App
- `abcjs-basic-min.js` – Bibliothek zum Zeichnen der Noten (abcjs, MIT-Lizenz, siehe `abcjs-LICENSE.txt`)
- `manifest.webmanifest`, `icon-*.png` – App-Symbol für den Startbildschirm
- `sw.js` – damit die App auch ohne Internet funktioniert
- `daten/` – eure Lieder (Noten, Griffe, Aufnahmen), **verschlüsselt**. Ohne das Gugge-Passwort kann niemand etwas damit anfangen. `schluessel.json` enthält nur den Zufallswert („Salz“) für die Verschlüsselung, nicht das Passwort.
- `werkzeuge/` – Skripte, mit denen die Lieder aus den PDF-Stimmen ausgelesen, geprüft und verschlüsselt werden

## Neue Lieder dazufügen (Kurzfassung)

1. `extract.py` und `build.py` lesen eine Stimme aus einer PDF (Sibelius oder Finale) aus: Noten, Rhythmus, Bindebögen, Doppelgriffe und die Ventil- bzw. Zugzahlen. `python3 build.py stimme.pdf valve` (oder `slide` für Posaune) meldet Takte mit falscher Länge und Griffe, die nicht zur Note passen.
2. `compare.py` vergleicht eine Stimme mit der Partitur, falls vorhanden.
3. In `gen.py` das Lied eintragen (Tempo, Tonart, Dateien, Wiederholungen) und ausführen.
4. `encrypt.py` verschlüsselt alles in den Ordner `daten/`. Das Passwort wird dabei als Umgebungsvariable `GUGGE_PW` übergeben und nie gespeichert.
5. Eine Aufnahme nie unter gleichem Namen ersetzen: die App speichert Aufnahmen dauerhaft auf dem Handy.
6. In `sw.js` die `VERSION` erhöhen.
