# Architektur v0.1

```text
Notion-Export/CSV
      ↓
Importer + Belegextraktion
      ↓
normalisierte Pflanzenobjekte
      ↓
deterministische Beratungslogik
      ↓
FastAPI + Weboberfläche
```

Die Beratungslogik kennt weder Notion noch konkrete CSV-Spalten.
