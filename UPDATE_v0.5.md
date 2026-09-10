# Update auf PflanzenKI v0.5

Hinweis zum Arbeitsstand vom 10. September 2026: Die folgende Anleitung
beschreibt das ursprüngliche v0.5-Paket. Der aktuelle Code verwendet inzwischen
eine lokale Katalogauswahl mit einer Interpretationsanfrage pro Gesprächsschritt.
Aktueller Prüfstand und Grenzen: `docs/LOCAL_SELECTION_PROGRESS.md`.

1. Laufenden Server mit Strg+C beenden. Den bisherigen Projektordner zur
   Rückkehr zum alten Stand sichern.
2. Den ZIP-Inhalt direkt in diesen Ordner entpacken und enthaltene Dateien
   ersetzen, ohne eine zusätzliche Zwischenebene anzulegen:

   `C:\Users\Kamikaze\Documents\GitHub\pflanzenki`

3. Die vorhandene `.env` und `.venv` behalten. Das Paket enthält keinen Key,
   keine `.env`, keine Git-Daten und keine virtuelle Umgebung.
4. In PowerShell starten:

```powershell
cd C:\Users\Kamikaze\Documents\GitHub\pflanzenki
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest
python -m uvicorn app.main:app --reload
```

Test und Serverstart sind getrennte Befehle. Die Konfiguration bleibt:

```dotenv
QUERY_INTERPRETER_PROVIDER=openai
OPENAI_QUERY_MODEL=gpt-5-mini
```

Den vorhandenen Schlüssel in `.env` behalten. `.env.example` nicht über eine
schon konfigurierte `.env` kopieren. Danach im Browser Strg+F5 drücken.

## Katalog

Das Paket enthält den zuletzt bereitgestellten Katalog mit 249 Pflanzen und
126 Bilddateien. Die vollständigen Beschreibungsbelege wurden neu erzeugt;
ein weiterer Notion-Import ist für dieses Update nicht nötig. Falls du lokal
inzwischen einen neueren Katalog hast, diesen sichern und anschließend den
neueren Notion-Export erneut importieren.

## Bedienung

- Rückfragen im beschrifteten Feld unter den Ergebnissen beantworten.
- Wünsche im selben Gespräch ergänzen oder korrigieren.
- „So habe ich dich verstanden“ zeigt die aktuell geprüften Kriterien.
- Jede Pflichtbedingung muss belegt sein. Unbekannt ist kein Treffer.
- „Vollständiger Beleg“ zeigt den gesamten Originalfeldwert.
- „Alle Katalogangaben“ öffnet sämtliche nichtleeren Felder der Pflanze.
- „Weitere anzeigen“ öffnet zusätzliche Ergebnisse ohne erneute KI-Anfrage.
- „Neue Beratung“ setzt den Verlauf zurück. Neuladen des Browsers ebenfalls.

## Prüfung und ehrliche Grenzen

Automatisierte Tests verwenden kontrollierte KI-Antworten; sie prüfen den
Programmablauf und die Quellenabsicherung, nicht die tatsächliche Qualität des
Modells. In der Bearbeitungsumgebung war kein API-Key vorhanden. Deshalb ist
die neue freie Auswertung noch nicht mit echten OpenAI-Antworten abgenommen.
Bitte mit deinem konfigurierten Key prüfen; Gesprächsfälle und Prüfkriterien
stehen in `docs/DIALOGUE_VALIDATION.md`.

Freie Eigenschaften brauchen keine neue Programmierung, solange ihre Bedeutung
aus den vorhandenen Katalogangaben belegbar ist. Die KI kann trotzdem eine
Formulierung oder einen Beleg falsch deuten. Fehlende Notion-Angaben werden
nicht ergänzt. Externe Recherche, Bestellungen und Live-Verfügbarkeit sind
nicht Bestandteil der Beratung.

Die vollständigen Katalogprüfungen benötigen mehr API-Tokens und Zeit als der
frühere reine Frage-Interpreter. Die Oberfläche zeigt währenddessen den
Bearbeitungsstatus. Es wird kein fertiges Teilergebnis als vollständige Antwort
ausgegeben, wenn eine Prüfung fehlschlägt.

Im mitgelieferten Stand entstehen bei der Suche in allen Tomaten fünf
Katalogprüfungen plus eine Interpretation; bei einer katalogweiten Suche elf
Prüfungen plus Interpretation. Reine Listen und Rückfragen benötigen keine
zusätzliche Katalogbewertung. Das kann sich mit dem Katalogumfang ändern.

Prüfstand: 79 Python-Tests bestanden; der JavaScript-Ablauftest ohne Browser
bestanden. Alle 249 Beschreibungen und Rohfelder wurden mit der CSV abgeglichen,
alle 126 Bildreferenzen sind vorhanden.

Der visuelle Browsertest konnte hier mangels Browserprogramm nicht ausgeführt
werden; dessen Download scheiterte. Das vorbereitete Playwright-Testskript ist
enthalten, aber kein bestandener Browsertest wird behauptet.
