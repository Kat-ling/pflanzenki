# PflanzenKI MVP v0.2

Deterministische Pflanzenberatung mit austauschbarem Sprach-Interpreter.

## Architektur

```text
Kundenfrage
    ↓
Query Interpreter (Fake oder OpenAI)
    ↓
ParsedQuery
    ↓
Advisor (deterministisch)
    ↓
AdviceResult
    ↓
FastAPI + Weboberfläche
```

Das Sprachmodell empfiehlt keine Pflanzen. Es übersetzt ausschließlich freie
Kundenfragen in strukturierte Anforderungen. Auswahl, Ausschluss, Bewertung,
Konflikte und `UNKNOWN` liegen vollständig im Advisor.

Die Pflanzendaten werden offline aus einem Notion-CSV-Export importiert. Zur
Laufzeit besteht keine Verbindung zu Notion.

## Schnellstart

### Windows PowerShell

Die folgenden Zeilen sind einzelne Befehle und müssen nacheinander ausgeführt
werden:

```powershell
cd C:\Users\katrin.tindl\02_Anbau-KI
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
$env:QUERY_INTERPRETER_PROVIDER="fake"
python -m pytest
Remove-Item Env:QUERY_INTERPRETER_PROVIDER
python -m uvicorn app.main:app --reload
```

`python -m pytest` prüft das Projekt. Erst nachdem dieser Befehl beendet wurde,
wird die Anwendung separat mit `python -m uvicorn ...` gestartet.

Falls PowerShell das Aktivierungsskript blockiert:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### macOS und Linux

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest
python -m uvicorn app.main:app --reload
```

Danach ist die Anwendung unter <http://127.0.0.1:8000> erreichbar.

Standardmäßig wird der OpenAI-Interpreter verwendet. Dazu die Vorlage kopieren:

```powershell
Copy-Item .env.example .env
notepad .env
```

In `.env` den Platzhalter `sk-...` durch den eigenen API-Schlüssel ersetzen:

```dotenv
QUERY_INTERPRETER_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_QUERY_MODEL=gpt-5-mini
```

Die Datei `.env` ist von Git ausgeschlossen und darf nicht committed werden.
Für lokale Tests ohne API-Aufruf kann der Provider vorübergehend auf `fake`
gesetzt werden.

Unterstützte Provider:

- `fake`
- `openai`

## API

- `POST /api/interpret` übersetzt eine Frage in `ParsedQuery`.
- `POST /api/ask` interpretiert die Frage und führt anschließend die
  deterministische Beratung aus.

Beispiel:

```json
{
  "question": "Welche süße Tomate eignet sich draußen ohne Dach?"
}
```

## Daten importieren

Eine CSV-Datei nach `data/input/plants.csv` kopieren und ausführen:

```bash
python -m app.importer.cli \
  data/input/plants.csv \
  data/normalized/plants.json
```

Der Importer erkennt derzeit insbesondere:

- Sorte oder Name
- Kategorie
- Beschreibung
- Regenschutz

Der nächste fachliche Schritt ist die Bereinigung und Vervollständigung der
Notion-Daten. Danach soll der Importer zusätzlich `features.json`,
`categories.json` und `synonyms.json` erzeugen.

## Zentrale Regeln

- Beschreibung hat Vorrang vor strukturiertem Feld und Ableitung.
- Konflikte senken Konfidenz und Score, ändern aber nicht den Sieger.
- Pflichtanforderungen mit explizitem Gegenbeleg schließen Pflanzen aus.
- Fehlende Informationen bleiben `UNKNOWN` und führen nicht zum Ausschluss.
- Präferenzen beeinflussen die Sortierung, nicht den Ausschluss.
- Der Advisor analysiert niemals freie Sprache.
