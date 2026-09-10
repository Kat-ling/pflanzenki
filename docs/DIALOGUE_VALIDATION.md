# Gesprächsprüfung v0.5

Aktualisierung 10. September 2026: Die Interpretation liefert jetzt Ausdrucksbäume;
die Pflanzenauswahl erfolgt lokal. Der visuelle Browsertest mit simulierten
Antworten wurde inzwischen bestanden. Ein echter Modelltest steht weiterhin aus.
Die folgenden Gesprächsfälle bleiben fachliche Abnahmekriterien. Aktueller Stand
und bekannte Abdeckungslücken: `LOCAL_SELECTION_PROGRESS.md`.

Diese Fälle sind Akzeptanztests, keine einprogrammierten Antwortvorlagen.
Sie zeigen, was nach dem Update mit echten Modellantworten geprüft werden
sollte. Keine der genannten Eigenschaften darf ohne Notion-Beleg angenommen
werden. Die automatisierten Tests simulieren die strukturierten KI-Antworten.

| Gespräch / Anfrage | Erwartete Verarbeitung |
| --- | --- |
| Welche Tomate eignet sich für Freiland und hat große Früchte? | Zwei Pflichtkriterien; normalgroße oder unbelegte Früchte reichen nicht. |
| Freilandtomate, die groß ist → Ich meine die Früchte | Gezielte Rückfrage; Tomate/Freiland bleiben bei der Antwort erhalten. |
| Doch lieber kleine Früchte | Fruchtgrößenwunsch ersetzen, nicht groß UND klein verlangen. |
| Und wenn möglich gelb? | Bisherige Pflichtkriterien bleiben; gelb ist eine sichtbare Vorliebe. |
| Rot oder gelb, für den Balkon | Farbe ODER, zusammen mit Balkon als UND. |
| Rot und klein oder gelb und groß | Geklammerte Alternativen bleiben als ein Kriterium erhalten. |
| Nicht scharfe Paprika | Fehlende Schärfeangaben reichen nicht; expliziter Beleg nötig. |
| Höchstens 80 cm hoch, aber große Früchte | Wuchshöhe und Fruchtgröße getrennt prüfen. |
| Früchte über 200 g | Kein Umrechnen von Pflanzenhöhe oder Fruchtdurchmesser in Gewicht. |
| Gurken zum Einlegen, ohne Gewächshaus | Beide Wünsche berücksichtigen; fehlende Eignungsangaben offenlegen. |
| Welche Zucchini ist gelb und früh? | Kein Wechsel in die unbeschränkte Katalogliste. |
| Welche Sorte braucht kein Ausgeizen? | Nicht als „ausgeizen“ aus einem fehlerhaften Tag auslegen. |
| Vergleiche die ersten beiden hinsichtlich Erntezeit | Sichtbare Sortenreferenzen verwenden; Originalangaben pro Sorte, Lücken sichtbar. |
| Jetzt suche ich Basilikum für Halbschatten | Klarer Themenwechsel: keine Tomaten-Fruchtkriterien übernehmen. |
| Gibt es noch weitere? | UI: Weitere anzeigen; keine Daten erneut erfinden. |
| Kann ich zehn Stück bestellen? | Auftrag nicht ausführen; fehlende Bestellfunktion erklären. |
| Eine erfundene Sorte / fehlende Eigenschaft | Keine Sorte oder Eigenschaft hinzuerfinden. |

## Technische Prüfungen

`python -m pytest` prüft Quellzitate, Vollständigkeit der Modellantworten,
Pflicht-/Vorliebenlogik, freien Kriterientransport, Gesprächstransport,
API-Fehlerfälle, Import und den bestehenden Fake-Pfad.

`node tests/ui_contract.cjs` prüft den JavaScript-Gesprächsablauf mit einer
minimalen simulierten DOM-Umgebung, ohne Browser und ohne API-Aufrufe.

Der optionale Browsercheck `node tests/ui_smoke.cjs` benötigt separat
Playwright und Chromium sowie einen laufenden Server auf Port 8765
(`PFLANZENKI_TEST_URL` kann eine andere lokale Testadresse setzen). Er simuliert
API-Antworten und prüft Gespräch, Folgeantwort, vollständigen Text, Bilder,
Seitennavigation, Mobilansicht, Fehlerwiederholung und Zurücksetzen. Hier konnte
er ursprünglich mangels Browserprogramm nicht ausgeführt werden; der aktuelle
Arbeitsstand hat ihn bestanden. Optional kann `PFLANZENKI_CHROMIUM_PATH` auf ein
vorhandenes Chromium-Programm zeigen; `PFLANZENKI_UI_ARTIFACTS` speichert Screenshots.

Quellenprüfung erkennt erfundene Zitate, aber nicht jede falsche semantische
Bewertung eines echten Zitats. Für die fachliche Abnahme müssen die sichtbaren
Kriterien und vollständigen Notion-Belege mit echten Modellantworten verglichen
werden. Eine pauschale Zusicherung für alle denkbaren Fragen wäre unbelegt.
