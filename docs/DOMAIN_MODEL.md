# Domänenmodell v0.5

Plant behält ID, Name, Kategorie, vollständige Beschreibung, Rohfelder,
Bilddateinamen und die bisherigen importierten Merkmalsbelege.

DialoguePlan enthält intent, mehrere Kategorien, benannte Sorten, freie
criteria, eine mögliche Rückfrage und nicht unterstützte Aufträge.

Ein Criterion enthält:

- text: vollständige Bedingung einschließlich Verneinung/Einheit/ODER
- importance: required oder ausdrücklich preferred
- kind: condition (Auswahl) oder information (erfragte Kataloginformation)

Assessment enthält Kriterienindex, yes/no/unknown und Quellenzitate.
Für Bedingungen bedeutet yes erfüllt, no widerlegt, unknown nicht sicher
entscheidbar. Für Informationsfragen bedeutet yes, dass die erfragte Angabe
vorliegt, unabhängig von ihrem positiven oder negativen Inhalt.

Die Antwort enthält alle akzeptierten Karten sowie getrennte unknown/excluded-
Karten. Jede Karte enthält vollständige Beschreibungen, checks pro Kriterium
und catalogue_fields zum Aufklappen. Die UI paginiert die Anzeige, nicht die
zugrunde liegenden Daten. Informationskarten sind keine Eignungsempfehlungen.

ParsedQuery, AdviceResult und die feste Feature-Enum bleiben für den lokalen
Fake-/Kompatibilitätspfad vorhanden. Der OpenAI-Pfad ist nicht daran gebunden.

Woas I ned. bleibt die sichtbare Bezeichnung für fehlendes Wissen. Fehlende
Pflichtbelege dürfen nicht zu einer passenden Empfehlung werden.
