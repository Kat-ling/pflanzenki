# KI-Sister

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
cd C:\Pfad\zu\pflanzenki
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
notepad .env
.\.venv\Scripts\python.exe -m app
```

`.env` nur beim ersten Einrichten anlegen; eine vorhandene Datei behalten.
Dort `OPENAI_API_KEY` setzen. Standard: `QUERY_INTERPRETER_PROVIDER=openai`
und `OPENAI_QUERY_MODEL=gpt-5-mini`. Oberfläche: http://127.0.0.1:8000.
Der Schlüssel bleibt serverseitig und gehört nicht nach GitHub.

## Katalog pflegen

Notion bleibt die Quelle für den gesamten Katalog mit allen Kategorien. Neue Sorten,
geänderte Texte, neue Kategorien und entfernte Sorten brauchen keine Codeänderung.
Vergriffene Sorten in Notion löschen, dann exportieren:

```powershell
.\.venv\Scripts\python.exe -m app.importer.update "C:\Pfad\NotionExport.zip" --vorschau
.\.venv\Scripts\python.exe -m app.importer.update "C:\Pfad\NotionExport.zip"
```

Die Vorschau zeigt neue, entfallende und geänderte Sorten sowie fehlende und nicht mehr
verwendete Bilder und ändert nichts. Ein Neustart ist nach dem Import nicht nötig.

Der Import stoppt, ohne etwas zu schreiben, wenn

- mehr als ein Viertel der Sorten entfallen würde (`--viele-entfernen` bestätigt das),
- Namen fehlen oder doppelt sind,
- Texte auf Personenbezug hindeuten, etwa „von meiner Schwester“ oder ein Vorname
  am Ende des Sortennamens (`--hinweise-ignorieren` lässt Fehltreffer zu).

Solche Stellen am besten direkt in Notion korrigieren. Bildlinks werden immer auf den
Dateinamen gekürzt, nur verlinkte Bilder also nach `static/images` kopieren.
`data/privacy_rules.local.json` kann zusätzlich feste Ersetzungen enthalten. Die Datei
wird nicht versioniert, weil die Begriffe selbst personenbezogen sind:

```json
{"replacements": [{"find": "Tomate von Erika", "replace": "Tomate"}]}
```

Abweichende Pflanzenwörter wie „Melanzani“ stehen in `data/search_synonyms.json`.
Kategorien und zusammengesetzte Wörter wie „Buschbohne“ erkennt die Suche aus dem Katalog.
Bei Arten mit vielen Sorten liefert „Gibt es noch weitere?“ neue statt bereits gezeigter Sorten.

## Webbetrieb

Derselbe Code läuft später als Webdienst. Der Umstieg geschieht nur über Einstellungen:

| Variable | Bedeutung |
| --- | --- |
| `APP_ENV=production` | Aktiviert Anmeldung, Anfragelimit und schaltet `/docs` ab |
| `APP_ACCESS_PASSWORD` | Pflicht im Webbetrieb, sonst startet die App nicht |
| `APP_REQUESTS_PER_MINUTE` | Grenze für API-Aufrufe je Client, Standard 20 |
| `HOST`, `PORT` | Im Webbetrieb standardmäßig `0.0.0.0` und `8000` |
| `OPENAI_API_KEY` | Im Hosting als Geheimnis hinterlegen, nie im Repo |

Das `Dockerfile` startet die App in diesem Modus. `/healthz` dient als Statusprüfung.
HTTPS muss das Hosting bereitstellen; ohne HTTPS gäbe es auch kein Mikrofon im Browser.
Die Anmeldung ist bewusst einfach gehalten: ein gemeinsames Passwort für alle. Für
einzelne Konten wäre eine Erweiterung nötig. Das Limit gilt pro Prozess; bei mehreren
Instanzen müsste es in einen gemeinsamen Speicher wandern.

Die Spracheingabe ist vorbereitet, aber nicht umgesetzt: Sie kommt als eigener Endpunkt
vor `/api/ask` dazu. Der Plan steht in `docs/superpowers/specs/`.

## Verarbeitung und Grenzen

Die lokale Suche stellt bis zu 24 Kandidaten bereit. Das Modell erhält deren
Originalbeschreibungen und weitere Sachfelder, die Frage, den Gesprächsverlauf
und sichtbare Sorten. Bilder bleiben lokal. Es gibt keine Notion-Liveabfrage.
Die Modellantwort verwendet Quellenkennungen, die Python prüft und den
Originalfeldern zuordnet. Die Oberfläche zeigt keine technischen Quellenkürzel.

Das Modell nennt zusätzlich die aktuellen Bedingungen als prüfbare Ausdrücke. Python hält
jede genannte Sorte dagegen: Widerlegt der Katalog eine Pflichtbedingung, erscheint die Sorte
nicht als Empfehlung, sondern mit Gegenbeleg unter „widersprechende Angaben“. Name oder
Kategorie allein belegen keine Bedingung. Sortennamen ohne Karte werden aus dem Antworttext
entfernt. Standorte wie Balkon, Gewächshaus oder „ohne Regenschutz“ müssen im Katalog belegt
sein, sonst gilt die Sorte als unsicher. Fehlt bei anderen Eigenschaften ein passender Fakt,
bleibt die Empfehlung bestehen und diese Aussage ungeprüft.

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
Die Skripte `run_live_model_check.py` und `run_screenshot_check.py` sind ausschließlich
manuell und nach ausdrücklicher Budgetfreigabe zu verwenden.

Der aktive Antwortpfad liegt in `app/ai/catalogue_answer.py`, die Suche in
`app/advisor/retrieval.py`, die Oberfläche in `static/`.
Frühere Regelmodelle und `/api/interpret` bleiben für Entwicklung und Regressionen
vorhanden; sie sind nicht die aktuelle freie Beratung unter `/api/ask`.
Ältere Dokumente unter `docs/` und `UPDATE_v0.5.md` dokumentieren frühere Stände.

Katalogdaten und Bilder sind Bestandteil dieses Projektstands. Eine pauschale
Lizenz für deren Weiterverwendung wird hier nicht erteilt.
