# Architektur

Aktiver Antwortweg seit v0.6: `/api/ask` → `app/ai/catalogue_answer.py` → lokale Suche in
`app/advisor/retrieval.py` → ein Modellaufruf → Prüfung der Quellenkennungen →
Gegenprüfung in `app/advisor/answer_check.py` gegen `catalogue_facts.json`.
Die Gegenprüfung nutzt die Dreiwertlogik aus `local_selection.py`. Ein NO bei einer
Pflichtbedingung verhindert eine Empfehlung. UNKNOWN verhindert sie in der Regel nicht, weil
die Regeln weniger wissen als die Beschreibungen, die das Modell gelesen hat. Ausnahme sind
Standorteigenschaften (`site.*`) ohne jeden Beleg: Im echten Test leitete das Modell die
Balkoneignung aus der Wuchshöhe ab, obwohl der Katalog keine belegte Paprika enthielt.
Solche Sorten gelten deshalb als unsicher. Lässt das Modell eine Standortbedingung offen
(`unresolved`), ordnet `pin_site` sie anhand ihres Textes lokal der Eigenschaft zu, denn das
kam im zweiten Echttest trotz klarer Anweisung vor. Grenzen: Andere Aussagen ohne passende Fakten bleiben
ungeprüft, das Modell könnte Bedingungen auslassen oder als Wunsch einstufen, und der Wortlaut
der Erklärung wird nicht inhaltlich verglichen.

Einstellungen stehen in `app/config.py`, der Schutz für den Webbetrieb in `app/security.py`,
die Oberfläche in `static/`, der Katalogimport in `app/importer/update.py`.

Der folgende Abschnitt beschreibt den lokalen Auswahlpfad aus v0.5. Er ist weiterhin
im Code vorhanden und erreichbar über `/api/interpret`, beantwortet aber keine Beratungsfragen.

# Lokaler Auswahlpfad v0.5

FastAPI, lokaler Notion-Import und Pflanzenkarten bleiben bestehen. Der
OpenAI-Pfad ersetzt die Beschränkung auf feste Merkmale durch freie Kriterien.

1. /api/ask nimmt aktuelle Frage und vollständigen mitgesendeten Verlauf
   entgegen. Es gibt keinen gemeinsamen serverseitigen Gesprächsspeicher.
2. interpret_dialogue erzeugt mit einer begrenzten Modellanfrage einen DialoguePlan:
   Kategorien, Sortennamen, Kriterien mit Ausdrucksbäumen, Pflicht/Vorliebe,
   Informationsfragen und ggf. Rückfrage. Originalkatalogfelder bleiben lokal.
3. Bei einer Rückfrage erfolgt noch keine Pflanzenbewertung. Andernfalls werden
   Kategorien und ausdrücklich benannte Sorten lokal aufgelöst.
4. Alle verbleibenden Pflanzen werden lokal gegen vorbereitete Fakten geprüft.
   Registry, Fakten, Originalfelder und Versionsprüfsummen liegen gemeinsam in
   catalogue_facts.json. Fehlende oder veraltete Bestände werden lokal im Speicher
   neu aufgebaut. Die letzten zwei vorbereiteten Bestände werden zwischengespeichert.
5. Der Plan darf höchstens 20 atomare Bedingungen und sechs Ebenen enthalten.
   Form, Datentypen und Einheiten werden geprüft. Unbekannte Eigenschafts-IDs
   ergeben UNKNOWN; ungültige Typen ergeben einen Fehler ohne automatischen Retry.
6. Jede verwendete Quelle muss mit Originalfeld, Zeichenpositionen und Prüfsumme
   übereinstimmen. Beschreibungsbelege haben Vorrang vor strukturierten Fakten.
   Erkannte Einschränkungen und Konflikte erzeugen UNKNOWN. Nicht gesetzte
   Positivcheckboxen sind keine Gegenbelege. Angezeigt wird das ganze Quellenfeld.
7. Python wertet UND/ODER/NOT mit drei Wahrheitswerten aus, prüft numerische Grenzen
   mit passenden Einheiten und sortiert nach Vorlieben. Unbekannte Pflichtbedingungen
   verhindern Empfehlungen; fehlende Angaben werden nicht als Widerlegung gewertet.
8. Die Oberfläche zeigt zunächst 3 Empfehlungen bzw. 6 Katalogeinträge und
   bietet weitere Treffer an. Beschreibungen/Fotos stammen aus den Daten.

## Grenzen der Absicherung

Zitate lassen sich auf Existenz prüfen, ihre Bedeutung nicht vollständig.
Die lokale Extraktion ist konservativ und regelbasiert; neue Formulierungen
können unbekannt bleiben oder falsch erkannt werden. Es gibt keinen bezahlten
semantischen Rückfall. Die Sprachinterpretation wurde noch nicht mit einem
echten Modell abgenommen. Strukturierte Fakten allein sind keine fachliche Freigabe.

## Komponenten

| Datei | Aufgabe |
| --- | --- |
| app/ai/dialogue_models.py | Begrenzte Ausdrucksbäume und Gesprächsplan |
| app/ai/catalogue_dialogue.py | Eine Interpretation, Orchestrierung, Ergebnisaufbereitung |
| app/advisor/local_selection.py | Dreiwertlogik, Zahlen, Quellenprüfung und lokaler Cache |
| app/models/catalogue_facts.py | Registry, Fakten, Originalquellen und Revisionen |
| app/importer/text_facts.py | Konservative Textregeln mit Quellen und Mehrdeutigkeitsmarkierung |
| app/main.py | Endpunkte |
| static/ | Gesprächsoberfläche, vollständige Karten |
| app/importer/ | Notion-ZIP/CSV, Originalfelder und Bildzuordnung |
| app/advisor/engine.py | Bestehender Fake-/Kompatibilitätspfad |

Der Import erzeugt weiterhin plants.json, categories.json, features.json und
lokale Bilder sowie catalogue_facts.json. Maßgeblich bleiben die vollständigen
Originalfelder. Registry-Erweiterungen benötigen kein Feature-Enum; ihre Bedeutung
und Extraktion müssen dennoch verlässlich definiert werden.

Verlauf, vollständiger letzter Plan und sichtbare Pflanzen-IDs leben im Browser-Tab.
Fehlgeschlagene Anfragen verändern sie nicht. IDs werden serverseitig aufgelöst.
Die API akzeptiert höchstens 40 vorherige Nachrichten / 120.000 Zeichen und
weist größere Gespräche zurück, statt sie abzuschneiden. Nur user/assistant
sind zulässig. Pro Frage gelten 1.000 Zeichen, pro Plan maximal 20 Kriterien.

OpenAI Responses mit JSON Schema und store=False; Frage, Verlauf, bisheriger Plan,
Sortennamen, sichtbare Sorten und kompakte Registry werden übertragen.
Keine vollständigen Katalogfelder oder Bilder. Ausgabelimit 4.000 Tokens,
30 Sekunden Transport-Timeout, keine SDK-Retries; keine harte Gesamtfrist.
Bereinigte Metadaten und Nutzungszähler erscheinen im Uvicorn-Serverlog.
Grundlage: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).
