# PflanzenKI unter Windows starten

## 1. Dateien ablegen

Den Inhalt des ZIP-Archivs direkt nach folgendem Ordner entpacken:

```text
C:\Users\Kamikaze\Documents\GitHub\pflanzenki
```

Danach muss beispielsweise diese Datei vorhanden sein:

```text
C:\Users\Kamikaze\Documents\GitHub\pflanzenki\app\main.py
```

Es darf keine zusätzliche Zwischenebene wie
`pflanzenki\PflanzenKI_MVP_v0.5\app` entstehen.

## 2. PowerShell öffnen

```powershell
cd C:\Users\Kamikaze\Documents\GitHub\pflanzenki
```

## 3. Alte virtuelle Umgebung optional entfernen

Wenn die bestehende `.venv` unvollständig ist, PowerShell schließen, den Ordner
`.venv` in `pflanzenki` löschen und PowerShell erneut öffnen.

## 4. Umgebung erstellen und Abhängigkeiten installieren

Jede Zeile einzeln ausführen:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Wenn das Aktivierungsskript blockiert wird:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 5. OpenAI konfigurieren

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

In der geöffneten Datei den eigenen OpenAI-API-Schlüssel ergänzen:

```dotenv
QUERY_INTERPRETER_PROVIDER=openai
OPENAI_API_KEY=DEIN_API_SCHLUESSEL
OPENAI_QUERY_MODEL=gpt-5-mini
```

Die Datei speichern und schließen. `.env` ist von Git ausgeschlossen. Den
Schlüssel niemals in Python-Dateien, Screenshots, Commits oder Chatnachrichten
einfügen.

## 6. Tests ausführen

```powershell
$env:QUERY_INTERPRETER_PROVIDER="fake"
python -m pytest
Remove-Item Env:QUERY_INTERPRETER_PROVIDER
```

Der erwartete Stand ist:

```text
79 passed
```

## 7. Anwendung mit OpenAI starten

Erst nach Abschluss der Tests einen separaten Befehl ausführen:

```powershell
python -m uvicorn app.main:app --reload
```

Anschließend im Browser öffnen:

```text
http://127.0.0.1:8000
```

Der Server läuft weiter, solange das PowerShell-Fenster geöffnet ist. Beenden
mit `Strg+C`.

Für ein Update einer bestehenden Installation siehe `UPDATE_v0.5.md`.
Die freie Beratung benötigt `QUERY_INTERPRETER_PROVIDER=openai`. Der
Fake-Modus ist ausschließlich für begrenzte lokale Tests vorgesehen.

## Pflanzenkatalog später aktualisieren

Den neuen Notion-Export als ZIP-Datei herunterladen und dann im aktivierten
Projektordner ausführen:

```powershell
python -m app.importer.notion_zip "C:\Pfad\zum\NotionExp.zip"
```

Dabei werden die Notion-CSV übernommen, die Katalogdaten neu erzeugt und die
in der CSV referenzierten Pflanzenfotos nach `static\images` kopiert. Danach
die Tests erneut ausführen und den Server neu starten.

## Häufiger Fehler

Dieser Befehl ist falsch:

```powershell
pytest uvicorn app.main:app --reload
```

`pytest` und `uvicorn` sind zwei verschiedene Programme. Mit
`python -m ...` wird außerdem zuverlässig die Installation aus der aktuell
aktivierten virtuellen Umgebung verwendet.
