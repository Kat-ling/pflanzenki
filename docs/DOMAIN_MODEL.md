# Domänenmodell v0.2

Das fachliche Modell umfasst Identität, Eigenschaften, Standort, Umwelt, Pflege,
Verwendung, Qualitätsmerkmale, Erfahrungswissen und Kundenanforderungen.

## Wissenswerte

Jede fachliche Aussage besteht aus:

- Merkmal
- Wert: `yes`, `no` oder `unknown`
- Quelle
- Belegtext oder Feldname
- Sicherheit
- möglichen Widersprüchen

`unknown` ist ein eigenständiger Wert und darf nicht wie `no` behandelt werden.

## ParsedQuery

Der Query Interpreter liefert:

- `original_question`
- `category`
- `requirements`
- `follow_up_question`
- `unsupported_requests`

Jede Anforderung enthält Merkmal, gewünschten Wert, Wichtigkeit und eine kurze
sprachliche Herleitung. Der Advisor erhält keine freie Kundenfrage zur Analyse.

## AdviceResult

Der Advisor liefert:

- `recommendations`: passende, sortierte Pflanzen (maximal drei)
- `unknown`: wegen fehlender Evidenz nicht entscheidbare Pflanzen
- `excluded`: nur durch Pflichtanforderungen ausgeschlossene Pflanzen
- `answer`: deterministisch formulierte Zusammenfassung
