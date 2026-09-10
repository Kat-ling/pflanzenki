# Changelog

## v0.5.0

- Freie statt ausschließlich fest vorgegebener Kriterien im OpenAI-Modus
- Vollständige Katalogfelder als Grundlage der semantischen Prüfung
- Alle Pflichtbedingungen müssen belegt sein; Vorlieben werden gekennzeichnet
- Quellzitate/IDs werden gegen die tatsächlichen Datensätze geprüft
- Gesprächsverlauf, Rückfragen beantworten, gezielte Korrekturen, neue Beratung
- Vollständige Originalbeschreibungen und vollständige Quellenfelder
- Weitere Treffer per Knopf, Datenlücken und Gegenbelege separat aufklappbar
- Bestehende Fotos und kompakte responsive Karten bleiben erhalten
- Offline-Vertrags-/Regressionstests; kein behaupteter Live-Modelltest

## v0.4.0

- Pflanzenbilder aus der Notion-Spalte `Bild` in allen Pflanzenkarten
- direkter Import eines vollständigen Notion-ZIP-Exports
- 126 Bilddateien für 125 Katalogeinträge übernommen
- mehrere Bilddateien pro Datensatz werden ohne CSV-Verlust erhalten
- neue Merkmalsinterpretation `pear_shaped` für birnenförmige Früchte
- Katalogansicht auf sechs Karten begrenzt
- Katalogauflistung nur noch bei ausdrücklich erkanntem Katalog-Intent

## v0.3.1

- intermittierende Schemafehler bei leeren Begründungstexten abgefangen
- eigener Antwortpfad für Katalogfragen wie „Welche Zucchini-Sorten gibt es?“
- Kategoriefragen ohne Kriterien liefern vorhandene Katalogeinträge
- Datenlücken werden nach „Woas I ned.“ verständlich erklärt

## v0.3.0

- freie Interpretation über alle 43 Kategorien des aktuellen Exports
- zentraler Katalog mit 35 Merkmalen
- Empfehlungen, Sorteninformationen und Vergleiche als getrennte Intents
- Auswertung von Filter-Tags, Besonderheiten, Verwendung, Beschreibungen,
  Positiv-Checkboxen, Fruchtfarbe, Wuchshöhe und Schärfegrad
- ungepflegte Checkboxen bleiben `UNKNOWN` statt automatisch `NO`
- Kategorien und Merkmale werden beim CSV-Import als JSON aktualisiert
- kategorieoffene Suche, explizite Sortennamen und Negationen
- nachvollziehbare Belege in der Oberfläche
- allgemeines Eingabefeld ohne voreingestellte Tomatenfrage
- `Woas I ned.` als sichtbarer Fallback

## v0.2.0

- gemeinsame `QueryInterpreter`-Schnittstelle
- Fake- und OpenAI-Interpreter mit Provider-Factory
- OpenAI Responses API und Structured Outputs
- strukturierte `ParsedQuery` mit Pflichtanforderungen und Präferenzen
- Advisor verarbeitet ausschließlich strukturierte Anforderungen
- Kategorie-Filterung im Advisor
- allgemeine deterministische Bewertung mehrerer Anforderungen
- getrennte Empfehlungen, unbekannte Ergebnisse und Ausschlüsse
- Endpunkte `/api/interpret` und `/api/ask`
- OpenAI als Standardprovider mit lokaler `.env`-Konfiguration

## v0.1.0

- technisches Grundgerüst
- Belegmodell
- CSV-Importer
- Beschreibungsauswertung
- Priorität Beschreibung > strukturiertes Feld
- `unknown` statt automatischem Ausschluss
- End-to-End-Fall „ohne Dach“
- Tests und lokale Weboberfläche
