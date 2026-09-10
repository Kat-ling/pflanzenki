# KI-Birgit

Lokale Pflanzenberatung in natürlicher Sprache mit Python und FastAPI.
Frage nach Sorten, Farben, Fruchtgrößen, Standort oder Verwendung und verfeinere
Wünsche im Gespräch. Antworten stammen aus dem importierten Notion-Katalog.

## Aktueller Zwischenstand

- 249 Pflanzen aus dem aktualisierten Notion-Export, 128 lokale Bilddateien.
- Lokale Kandidatensuche und höchstens eine Modellanfrage pro Gesprächsschritt.
- Bis zu vier Vorschläge mit kurzen Erklärungen und Bildern.
- Sämtliche Originalfelder unter „Alle Katalogangaben anzeigen“.
- Unsichere Angaben werden getrennt von Empfehlungen dargestellt.
- Nutzererprobte Fragen zu Cocktail-, Salat-, Topf- und niedrigen Tomaten,
  Snackpaprika, scharfen Chilis, Basilikum und gelben Zucchini.
- Bei den letzten Nutzertests lagen Antworten meist unter zehn Sekunden.
  Dies ist eine Beobachtung, keine garantierte Antwortzeit oder Qualitätszusage.

## Lokal starten (Windows)

```powershell
cd C:\Users\Kamikaze\Documents\GitHub\pflanzenki
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

`.env` nur beim ersten Einrichten anlegen; eine vorhandene Datei behalten.
Dort `OPENAI_API_KEY` setzen. Standard: `QUERY_INTERPRETER_PROVIDER=openai`
und `OPENAI_QUERY_MODEL=gpt-5-mini`. Oberfläche: http://127.0.0.1:8000.
Der Schlüssel bleibt serverseitig und gehört nicht nach GitHub.

## Daten aktualisieren

```powershell
.\.venv\Scripts\python.exe -m app.importer.notion_zip "C:\Pfad\NotionExport.zip"
```

Vor dem Import `data/input`, `data/normalized` und `static/images` lokal sichern.
Der Import liest die Katalog-CSV und übernimmt mitgelieferte Bilder. Nur verlinkte
Bilder werden nicht heruntergeladen; passende bereits vorhandene Dateien bleiben
nutzbar. Fehlende Bilder nach `static/images` kopieren. Danach eine neue Beratung
beginnen. Der Suchindex wird bei geänderten Katalogdaten neu aufgebaut.

Alternativ CSV importieren:

```powershell
.\.venv\Scripts\python.exe -m app.importer.cli data/input/notion_pflanzen.csv data/normalized/plants.json
```

## Verarbeitung und Grenzen

Die lokale Suche stellt bis zu 24 Kandidaten bereit. Das Modell erhält deren
Originalbeschreibungen und weitere Sachfelder, die Frage, den Gesprächsverlauf
und sichtbare Sorten. Bilder bleiben lokal. Es gibt keine Notion-Liveabfrage.
Die Modellantwort verwendet Quellenkennungen, die Python prüft und den
Originalfeldern zuordnet. Die Oberfläche zeigt keine technischen Quellenkürzel.

Für `gpt-5-mini` und den Snapshot `gpt-5-mini-2025-08-07` wird minimaler
Denkaufwand angefordert. Es gelten 4.000 Output-Tokens, 30 Sekunden
Transport-Timeout und keine automatischen Wiederholungen. Die Kandidatendaten
sind auf 28.000 Zeichen, das Gesamt-Payload auf 60.000 Zeichen begrenzt.
Dies sind technische Grenzen, keine Eurogarantie. API-Aufrufe kosten Geld.

Die Wortsuche kann passende Sorten übersehen; Ergebnisse sind keine vollständige
Trefferliste. Eine korrekte Quellenkennung garantiert noch keine korrekte
Interpretation. Fehlende Angaben dürfen nicht als belegte Eigenschaften gelten.
Eine neue Beratung oder Neuladen der Seite löscht den lokalen Gesprächsverlauf.

Spracheingabe ist ein späterer Ausbauschritt und noch nicht implementiert.
Die App ist für lokalen Betrieb gedacht; sie enthält keine Benutzeranmeldung.

## Entwicklung und Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
node tests/ui_contract.cjs
```

Die Python-Tests verwenden simulierte Modellantworten und benötigen keine
bezahlten Aufrufe. Historische Katalogregressionen verwenden eingefrorene Daten
unter `tests/fixtures`; die aktuelle Suche wird auch mit dem aktuellen Katalog
geprüft. Lokale Live-Testprotokolle und Sicherungen werden nicht versioniert.
Skripte `run_live_model_check.py` und `run_screenshot_check.py` sind ausschließlich
manuell und nach ausdrücklicher Budgetfreigabe zu verwenden.

Der aktive Antwortpfad liegt in `app/ai/catalogue_answer.py`, die Suche in
`app/advisor/retrieval.py`, die Oberfläche in `app/main.py`.
Frühere Regelmodelle und `/api/interpret` bleiben für Entwicklung und Regressionen
vorhanden; sie sind nicht die aktuelle freie Beratung unter `/api/ask`.
Ältere Dokumente unter `docs/` und `UPDATE_v0.5.md` dokumentieren frühere Stände.

Katalogdaten und Bilder sind Bestandteil dieses Projektstands. Eine pauschale
Lizenz für deren Weiterverwendung wird hier nicht erteilt.
