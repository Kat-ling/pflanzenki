# Changelog

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
