# Freie Katalogantwort – Arbeitsstand 10. September 2026

Aktuelle Laufzeit-Einstellung: Für `gpt-5-mini` und dessen Snapshot
`gpt-5-mini-2025-08-07` wird ausdrücklich `reasoning.effort=minimal` gesendet.
Bisher fehlte diese Einstellung. Andere Modellnamen erhalten keinen solchen
Override. Die Einstellung wird zusammen mit Tokenzählern protokolliert.
Modell, Timeout und Ausgabelimit bleiben gleich. Offline geprüft; Zeitgewinn
und mögliche Qualitätseinbußen sind noch nicht live gemessen.
Referenz: https://developers.openai.com/api/docs/guides/reasoning

## Korrekturen nach den Nutzertests

Die Modellantwort gibt jetzt Quellenkennungen statt abgeschriebener Zitate
zurück. Kennungen werden pro Pflanze geprüft; Originalfelder lokal ergänzt und
doppelte Quellen entfernt. Ungültige Kennungen bleiben ein erkennbarer Fehler.
Die Suche gewichtet ausdrücklich genannte Kategorien und bei Höhenfragen
Wuchsbeschreibungen stärker. Namen werden auch mit abweichenden Bindestrichen
gefunden. Das ist Suchgewichtung, keine botanische Zertifizierung.

Das Modell unterscheidet passende Empfehlungen, reine Informationen und
unsichere Angaben. Unsichere Sorten erscheinen getrennt unter unbekannten
Ergebnissen. Die Anleitung erhält Auswahlbedingungen bei namentlichen
Nachfragen und unterscheidet kleine Früchte/niedrigen Wuchs sowie scharf/sehr
scharf ausdrücklich. Eine semantische Fehlentscheidung des Modells bleibt
möglich; die Offline-Prüfung belegt keine perfekte Antwortqualität.

API-Zeitüberschreitungen erhalten eine eigene Meldung statt eines allgemeinen
Konfigurationshinweises. Aus den Screenshots allein lassen sich die übrigen
502-Ursachen nicht sicher bestimmen. Keine neuen Live-Aufrufe und keine
Modell- oder Timeoutänderung. Eine Beschleunigung ist noch nicht gemessen.

Nach dem Timeout wurde die Übertragung offline verkleinert: Export-Metadaten,
abgeleitete Filtertags, nicht gesetzte Positivfelder, Null-Platzhalter und
doppelte Beschreibungen entfallen im Modellkontext. Schärfegrad 0 bleibt als
echte Angabe erhalten; vollständige Originaltexte und zusätzliche Sachfelder
bleiben verfügbar. Lokale Karten enthalten weiterhin sämtliche Originalfelder.
Antworten sind nun auf vier Sorten begrenzt, mit kurzen Erklärungen und Zitaten.
Keine freiwilligen Zusatzfragen; erforderlicher Schutz darf nicht zu einer
bloßen Empfehlung abgeschwächt werden. Sieben gezielte Offline-Tests bestanden.
Laufzeit und tatsächliche Kosten dieser Kürzung sind noch nicht live gemessen.

Nachtrag zum begrenzten echten Test: erste Screenshot-Frage beantwortet mit
acht belegten Sorten in 27 Sekunden, zweite Frage nach 31 Sekunden mit Timeout
abgebrochen, dritte nicht gesendet. Details: `SCREENSHOT_MODEL_REPORT.md`.
Die folgenden Offline-Befunde bleiben gültig; eine verlässlich schnelle
Gesprächsantwort ist damit noch nicht nachgewiesen.

Ziel: ein natürliches Eingabefeld, Antworten aus eigenen Datensätzen, geringer
Aufwand pro Frage, aktualisierbarer Katalog. Sprache kann später Text an dieselbe
`/api/ask`-Schnittstelle liefern. Veröffentlichung auf GitHub folgt erst später.

Der aktive OpenAI-Antwortpfad ist jetzt `app/ai/catalogue_answer.py`.
`app/advisor/retrieval.py` durchsucht Originalfelder lokal, gewichtet die neue
Frage stärker als alte Nachrichten und reicht bis zu 24 Kandidaten weiter.
Wortbestandteile und Suchsynonyme dienen nur dem Finden, nicht als Wahrheitsregeln.
Ein im Speicher gecachter Index wird bei geänderten Katalogdaten neu aufgebaut.
Der bestehende Import bleibt nutzbar; kein Embedding-Dienst, keine neue Datenbank.

Ein Modellaufruf liest die Kandidatenbeschreibungen und den vollständigen
übergebenen Gesprächsverlauf. Das Antwortschema enthält eine natürliche
Zusammenfassung, bis zu vier Sorten mit Erklärungen und genauen Zitaten sowie
gegebenenfalls eine Rückfrage. Der frühere Pflichtplan wird nicht weitergeführt.
IDs und wörtliche Fundstellen werden lokal geprüft. Originalfelder und Bilder
kommen unverändert aus dem Katalog. Teilinformationen sollen ausdrücklich als
solche benannt werden; fehlendes Wissen bleibt „Woas I ned.“.

Grenzen: 24 Kandidaten, 28.000 Zeichen Kandidaten-JSON, 60.000 Zeichen
Gesamt-Payload, 4.000 Output-Tokens, 30 Sekunden Transport-Timeout, keine
automatischen Wiederholungen. Kein Anspruch auf vollständige Trefferlisten.
Es gibt keinen neuen Live-Nachweis für Kosten, Laufzeit oder Antwortqualität.
Quellenzitate verhindern nicht jede semantische Fehlinterpretation.
Die Wortsuche kann unbekannte Synonyme und komplexe Themenwechsel verfehlen.

Offline-Prüfung: Die drei Fragen aus dem Screenshot liefern echte Quellen mit
Cocktailtomaten und kleinen Früchten. Geprüft wurden außerdem die aktive
API-Route, eine einzelne Modellanfrage mit simuliertem Ergebnis, Verlauf,
Originalquellen/Bilder, Ablehnung erfundener IDs/Zitate und Datenaktualisierung.
218 Python-Tests bestanden. Historische Regeltests bleiben als solche erhalten;
ihre Ergebnisse sind kein Nachweis der neuen Antwortqualität.

Nächster sinnvoller Schritt ist ein kleiner gemeinsam beurteilter Modelltest
mit genau dem Screenshot-Gespräch, sobald weitere bezahlte Aufrufe gewünscht
sind. Vorher keine neue breite Regel- oder Testkampagne.
