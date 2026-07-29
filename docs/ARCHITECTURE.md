# Architektur v0.2

## Laufzeit

```text
Kundenfrage
      ↓
QueryInterpreter
      ↓
ParsedQuery
      ↓
Advisor
      ↓
AdviceResult
      ↓
Frontend
```

Der `QueryInterpreter` ist die einzige Komponente, die natürliche Sprache
verarbeitet. Implementiert sind `FakeQueryInterpreter` und
`OpenAIQueryInterpreter`; die Auswahl erfolgt über
`QUERY_INTERPRETER_PROVIDER`.

Der OpenAI-Interpreter verwendet die Responses API mit Structured Outputs. Er
kennt nur den Merkmalskatalog und die Regeln zur Übersetzung in `ParsedQuery`.
Er kennt weder konkrete Pflanzen noch deren Eigenschaften.

Der Advisor erhält ausschließlich `ParsedQuery`. Er filtert die erkannte
Kategorie, löst Merkmalsbelege deterministisch auf und erzeugt Empfehlungen,
unbekannte Ergebnisse und Ausschlüsse.

## Datenfluss

```text
Notion
  ↓ Export
CSV
  ↓ Importer
plants.json
  ↓ Repository
Advisor
```

Notion ist ein Redaktionssystem und keine Laufzeitabhängigkeit. Die Anwendung
arbeitet ausschließlich mit lokalen, reproduzierbaren JSON-Daten.

## Verantwortlichkeiten

| Komponente | Verantwortlich für |
| --- | --- |
| Query Interpreter | Sprache, Synonyme, Kategorie, Anforderungen, Rückfrage, nicht unterstützte Wünsche |
| Advisor | Evidenz, Score, Konflikte, `UNKNOWN`, Ausschluss, Sortierung |
| Importer | Notion-Spalten, Normalisierung, technische Ausgabedateien |
| Repository | Laden lokaler Pflanzendaten |

## Zielbild nach Datenbereinigung

```text
Notion-Export
      ↓
Importer
  ├── plants.json
  ├── features.json
  ├── categories.json
  └── synonyms.json
```

Feature-Katalog, OpenAI-Prompt und JSON-Schema sollen langfristig aus derselben
importierten Quelle erzeugt werden.
