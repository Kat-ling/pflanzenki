# Lokale Auswahl: Umsetzungsstand

Aktueller Richtungswechsel: Die aktive Antwortstrecke verwendet jetzt lokale
Kandidatensuche plus freie Modellantwort aus Originaltexten. Siehe
`RETRIEVAL_APPROACH.md`. Die folgenden Abschnitte beschreiben den früheren
Ansatz und dessen Tests, nicht einen Live-Nachweis der neuen Strecke.

## Ergänzung: echter Modelltest und Quellenprüfung, 10. September 2026

Sechs echte Fragen mit gpt-5-mini wurden abgeschlossen (5,6–12,0 Sekunden,
zusammen 0,01222730 USD laut Tokenzählern). Das freigegebene Budget von 0,25 €
wurde einschließlich einer vorsichtigen Reserve für einen Verbindungsfehler
eingehalten. Die Suchpläne bildeten die sechs geprüften Wünsche passend ab.

Die Quellenprüfung fand vier falsch belegte Höhentreffer aus importierten
Fruchtmaßen/Pflanzabständen. Extraktorversion 4 lässt diese Angaben unbekannt.
Gespeicherte echte Antworten wurden ohne weitere Kosten erneut lokal geprüft:
nur die unbelegten Höhentreffer entfallen. 207 Tests plus sechs zusätzliche
Replay-Tests bestanden, insgesamt 213. Vollständige Details und Grenzen:
`LIVE_MODEL_TEST_REPORT.md`. Die folgenden Abschnitte dokumentieren frühere Stände.

## Ergänzung: fachlicher Offline-Abgleich, 10. September 2026

20 typische Kundenfragen wurden in 44 einzeln anhand der Originalbeschreibungen
festgelegten Frage-Pflanzen-Paaren geprüft. Vor der Korrektur stimmten 23/44
Bewertungen, danach 44/44. Es handelte sich um 20 übersehene Belege/Gegenbelege
und eine fälschlich als Fruchtfarbe verwendete Blütenfarbe.

Verbessert wurden der Geltungsbereich von Negationen in langen Sätzen,
Freiland-/Topfformulierungen, Schärfeangaben und Einlege-Verwendung.
„Dünne Fruchtschale“ ist als weitere belegbare Eigenschaft ergänzt.
Ein Vergleich geänderter Entscheidungen außerhalb der Stichprobe deckte zudem
eine zwischenzeitlich zu breite Freiland-Regel auf; Versuche mit offenem Ausgang
und ausdrücklich geschützter Anbau bleiben unbekannt.

Die 44 Paare, drei zusätzliche echte Katalogfälle und 18 synthetische Gegenbeispiele
sind als Regressionen festgehalten. **194 Python-Tests bestanden**, bei gesperrten
externen Netzwerkverbindungen; zwei bestehende Deprecation-Warnungen verbleiben.
Der Extraktor hat Version 3; der Faktenbestand
wurde lokal neu erzeugt. Originalkatalog, Quellen und Bilder bleiben unverändert.
Dies ist keine unabhängige Qualitätsquote für alle Pflanzen oder alle Formulierungen.
Kein echter Modelltest, kein kostenpflichtiger API-Aufruf, kein Commit/Deployment.

Der [vollständige Prüfbericht](CATALOGUE_ACCEPTANCE_REPORT.md) enthält Vorher/Nachher,
Begründungen und vollständige Originalbeschreibungen. Die eingefrorene Baseline
liegt in CATALOGUE_ACCEPTANCE_BASELINE.json; Ergebnisse sind reproduzierbar mit
`python -B tests/run_catalogue_acceptance.py`.

## Vorheriger Stand: Anbindung der lokalen Auswahl, 10. September 2026

Die OpenAI-Beratung verwendet jetzt den lokalen Auswahlpfad. `/api/ask` und
`/api/interpret` senden einen begrenzten Interpretationsauftrag mit Frage,
Verlauf, bisherigem Plan, sichtbaren Sorten, Sortennamen und Registry.
Vollständige Katalogfelder werden nicht mehr zur Modellbewertung gesendet.
Die bisherige Funktion `evaluate_batch` ist ausdrücklich deaktiviert; kein
Fehler und kein unbekanntes Kriterium schaltet auf den alten Pfad zurück.

Implementiert sind UND/ODER/NOT-Bäume, Typ-/Einheitenprüfung, konservative
Zahlenvergleiche, getrennte Pflichtbedingungen und Vorlieben sowie Quellenprüfung
an den aktuellen Originalfeldern. Die Oberfläche behält Plan und sichtbare IDs,
zeigt Gründe für UNKNOWN und kann Teilauswertungen einer Kombination öffnen.
Originalbeschreibungen, Quellenfelder, Bilder und Seitennavigation bleiben erhalten.

Beschreibungen werden beim Aufbereiten mit versionierten Regeln ausgewertet.
Erkannte Einschränkungen oder nicht auflösbare relevante Textstellen werden als
mehrdeutige Belege gespeichert. Diese verhindern eine unberechtigte Übernahme
strukturierter Positivwerte. Bekannte Beschreibungskonflikte bleiben UNKNOWN.
Nicht unterstützte Eigenschaften bleiben als offenes Kriterium sichtbar.

Fehlende/veraltete Faktenbestände werden lokal neu aufgebaut. Geprüft werden
Katalogrevision, Schema-/Extraktorversion, Registry, Pflanzenzuordnung und
Originalquellen. Der Anfragenpfad schreibt dabei keine Dateien. Der Import schreibt
die gesamte Faktendatei atomar; ein atomarer Austausch aller Importdateien zusammen
und eine inkrementelle Extraktion sind weiterhin offen.

Kostenbegrenzung: eine SDK-Anfrage, null automatische Wiederholungen,
maximal 4.000 Ausgabetokens und 30 Sekunden Transport-Timeout. Letzterer ist
keine harte Gesamtfrist; die laufende HTTP-Operation besitzt noch keine separate
Gesamtzeit-Abbruchsteuerung. Unvollständige Ausgaben werden nicht automatisch
wiederholt. Tokenzähler (soweit vorhanden), Dauer, Modell und bereinigte Fehlerklasse
werden im Serverlog erfasst, keine Schlüssel oder Gesprächsinhalte.

Offline geprüft: 153 Python-Tests bestanden, einschließlich des anhand der
Originalbeschreibung manuell festgelegten Katalogfalls „Rote Zora“ (große Früchte
und Freilandanbau). Externe Netzwerkverbindungen waren gesperrt.
JavaScript-Ablauftest bestanden. Visueller Browsertest mit vorhandenen Playwright-
und Chromium-Installationen bestanden, einschließlich Desktop/Mobil, Gespräch,
Plan-/ID-Transport, vollständiger Quellen, Kombinationsanzeige, Bilder, Navigation,
Fehlerwiederholung und Zurücksetzen. Die Browserantworten wurden simuliert.

Lokale Messung auf diesem Rechner: 249 Pflanzen mit 20 Bedingungen in etwa
52 ms ausgewertet; Vorbereitung aus dem Sidecar etwa 152 ms beim ersten Aufruf
und 24 ms bei Wiederverwendung. Einzelmessung ohne Modelllaufzeit, keine SLA.

Der aktualisierte Sidecar enthält für 249 Pflanzen 1.466 Belege: 517 strukturierte
Fakten, 299 durch Textregeln erkannte Aussagen und 650 ausdrücklich mehrdeutige
Textbelege. Diese Zahlen sind keine Anzahl belegter Empfehlungen. Die ursprünglichen
Pflanzen-JSON-Daten, CSV-Dateien und Bilder wurden dabei nicht überschrieben.

Fachliche Grenzen: Der Regelbestand versteht nicht beliebige freie Katalogtexte.
Insbesondere qualitative Ernteaussagen und neue Eigenschaften können UNKNOWN
bleiben, obwohl ein Mensch eine Aussage aus dem Originaltext ableiten könnte.
Textsuche oder semantische Importaufbereitung zur Erweiterung der Abdeckung
sind noch nicht implementiert. Ein echter, separat budgetierter Modelltest und
breitere manuell geprüfte Fachfälle bleiben nötig. Bisher keine kostenpflichtigen
PflanzenKI-Aufrufe, kein Commit und keine Veröffentlichung.

API-Grundlagen geprüft anhand der offiziellen Dokumentation:
[Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[Responses](https://developers.openai.com/api/reference/python/resources/responses/methods/create),
[GPT-5 mini](https://developers.openai.com/api/docs/models/gpt-5-mini).

## Historisch: erster Umsetzungsschritt

Stand: 9. September 2026.

## Implementiert

- Typisierte Registry und Faktenmodelle in `app/models/catalogue_facts.py`.
- Rein lokale Extraktion aus strukturierten Originalfeldern in
  `app/importer/catalogue_facts.py`, ohne Übernahme alter Merkmalsableitungen.
- Exakte Originalzitate mit Unicode-Positionen und Feld-Prüfsummen.
- Getrennte Kennzeichnung von geprüfter Quelle und noch ungeprüfter Semantik.
- Vollständige nichtleere Rohfelder als lokaler Textbestand, auch ohne Extraktionsregel.
- Getrennte Eigenschaften für Freiland, geschützten Standort und Gewächshaus/Dach.
- Unbekannte Positivcheckboxen, Null-Platzhalter und ungültige Zahlen ergeben
  keine behaupteten Fakten. Gepflegter Schärfegrad 0 bleibt erhalten.
- Prüfung auf doppelte Pflanzen-IDs vor dem Schreiben normalisierter Ausgaben.
- Versions- und Inhaltsprüfsummen für Katalog, Registry und Pflanzen.
- Ein atomar ersetzter Fakten-Sidecar enthält Registry und Quellen zusammen.
  Unveränderte Sidecars werden nicht erneut geschrieben. Die Extraktion wird
  derzeit noch vollständig lokal ausgeführt; inkrementelle Extraktion folgt später.
- CSV- und ZIP-Import erzeugen den Fakten-Sidecar zusätzlich zu bisherigen Dateien.
- Windows-Zeilenendenfehler beim Schreiben der Notion-CSV behoben.

Abweichung vom Entwurf: Registry und Manifestdaten liegen zunächst gemeinsam in
`catalogue_facts.json`, damit diese Daten nicht aus unterschiedlichen Revisionen
stammen können. Die gesamten bisherigen Importausgaben werden damit noch nicht
als eine gemeinsame atomare Transaktion geschrieben. Ein späterer Leser muss
die gespeicherte Katalogrevision gegen den geladenen Originalbestand prüfen.

## Bestehenden Katalog nur zusätzlich aufbereiten

```powershell
.\.venv\Scripts\python.exe -B -m app.importer.catalogue_facts data/normalized/plants.json data/normalized/catalogue_facts.json
```

Dieser Befehl schreibt ausschließlich den Sidecar. Originalkatalog und Bilder
werden nicht neu importiert oder überschrieben. Er verwendet keine API und
gibt einen Abdeckungsbericht auf der Konsole aus.

Ergebnis für den vorhandenen Katalog: 249 Pflanzen, 517 strukturierte Fakten.
Darunter 198 Farbangaben, 19 Höhenobergrenzen, 19 Schärfeobergrenzen und je
100 Erntestart-/Ernteendmonate. Alle nichtleeren Originalfelder bleiben im
Textbestand enthalten. Farbangaben sind vollständige, noch nicht semantisch
zerlegte Texte; beispielsweise wird eine mehrfarbige oder bedingte Farbangabe
nicht automatisch in einzelne bestätigte Farben aufgeteilt.

281 fehlende Feldbelegungen, 528 Null-Platzhalter und 2.409 nicht gesetzte
Positivcheckboxen wurden als Datenlücken erfasst. Das sind Feldzählungen,
keine Anzahlen von Pflanzen. Die 517 Fakten sind keine 517 bestätigten
Empfehlungsentscheidungen: Beschreibungen können sie einschränken oder widerlegen.

## Validierung

100 Python-Tests bestanden; externe Netzwerkverbindungen während des Laufs
blockiert. Die 21 neuen Testfälle prüfen unter anderem Herkunft, Zahlen,
unbekannte Werte, Registry-Erweiterung, doppelte IDs, Revisionswechsel,
atomaren Ersatz bei Schreibfehler und Quellenvollständigkeit des echten Katalogs.
Zwei Deprecation-Warnungen stammen aus FastAPI/Starlette-Testabhängigkeiten.

Kein echter Modelltest, kein neuer visueller Browsertest. Kein API-Aufruf,
kein Commit und keine Veröffentlichung in diesem Umsetzungsschritt.

## Noch nicht implementiert

Die Beratungsendpunkte verwenden weiterhin den v0.5-Pfad; Kundenanfragen können
deshalb weiterhin vollständige kostenpflichtige Katalogprüfungen auslösen.
Der neue Faktenbestand wird dort noch nicht verwendet.

Als Nächstes folgen die quellengebundene Textaufbereitung und Konfliktprüfung,
das UND/ODER/NOT-Ausdrucksmodell und die lokale Dreiwert-Auswertung. Danach erst
werden Gesprächsinterpretation, API und Oberfläche auf diesen Pfad umgestellt.
Zeit-/Tokenlimits und Protokollierung aus dem Entwurf sind ebenfalls noch offen.
Kein unbekanntes Merkmal darf dabei verschwinden oder automatisch die alte
kostenpflichtige Katalogbewertung starten.
