# PflanzenKI MVP v0.1

Erster technischer Kern für nachvollziehbare Pflanzenberatung.

## Enthalten

- normalisiertes Pflanzen- und Belegmodell
- CSV-Importer für Notion-Exporte
- Auswertung strukturierter Felder **und** Freitextbeschreibungen
- Regel: Leere Felder bedeuten `unbekannt`, niemals automatisch `ungeeignet`
- Regel: Eine eindeutige Beschreibung hat im MVP Vorrang
- erste Beratung für „mit/ohne Dach“
- kleine FastAPI-Weboberfläche
- automatisierte Tests

## Schnellstart

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest
uvicorn app.main:app --reload
```

Danach: http://127.0.0.1:8000

## Eigene Daten importieren

Eine CSV-Datei nach `data/input/plants.csv` kopieren. Unterstützte Spaltennamen
werden flexibel erkannt, unter anderem:

- Sorte / Name
- Kategorie
- Beschreibung / Rohbeschreibung
- Regenschutz
- Freiland
- Gewächshaus
- Balkon / Topf

Dann:

```bash
python -m app.importer.cli data/input/plants.csv data/normalized/plants.json
```

## Zentrale fachliche Regel

Strukturierte Felder werden nie isoliert betrachtet. Jede Bewertung prüft zusätzlich
die Beschreibung. Ein leeres Feld ist nur fehlendes Wissen. Eine Pflanze wird nur
bei einem expliziten negativen Beleg ausgeschlossen.
