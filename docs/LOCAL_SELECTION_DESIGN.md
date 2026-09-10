# Entwurf: sparsame Beratung mit lokaler Katalogauswahl

Stand: 9. September 2026. Dies ist ein Umsetzungsvorschlag, keine implementierte
oder mit echten Modellantworten abgenommene Funktion. Der Anwendungscode bleibt
in diesem Arbeitsschritt unverändert. Alle Beispiele sind synthetisch.

## Ziel und Grenze

Normalfall: eine kurze Interpretation pro Gesprächsschritt, danach lokale
Auswertung aller infrage kommenden Pflanzen. Keine wiederholte vollständige
Katalogbewertung durch OpenAI. Kataloglisten, Karten und Seitennavigation
benötigen keine zusätzliche Modellbewertung.

Freie Sprache ist nicht gleich beliebig vollständig automatisch verstehbare
Katalogsemantik. Ein endlicher Faktenindex kann neue Eigenschaften übersehen.
Deshalb bleiben unbekannte Kriterien erhalten und werden als unbekannt
ausgewertet. Sie dürfen weder verschwinden noch in ein ähnliches bekanntes
Merkmal umgedeutet werden. Ein späterer begrenzter semantischer Zusatzpfad kann
die Abdeckung erweitern; er ist zunächst deaktiviert.

## 1. Originaldaten und vorbereitete Fakten

`plants.json` bleibt die Quelle für IDs, Namen, Kategorien, vollständige
Beschreibungen, Rohfelder und Bildreferenzen. Ein zusätzlicher Faktenbestand
und ein lokaler Textindex werden beim Import erzeugt. Sie ersetzen keine
Originalfelder und kürzen keine angezeigten Belege.

Vorgeschlagene Dateien:

| Datei | Inhalt |
| --- | --- |
| `data/normalized/catalogue_facts.json` | Fakten je Pflanze mit Quellen und Prüfstatus |
| `data/normalized/property_registry.json` | Erweiterbare Eigenschaftsdefinitionen, Typen, Einheiten, geprüfte Synonyme |
| `data/normalized/catalogue_manifest.json` | Katalogrevision, Inhaltsprüfsummen, Schema- und Extraktorversion |
| lokaler, regenerierbarer Textindex | Originalfelder und zusammengehörige Textpassagen für offene Kriterien |

Ein Fakt enthält:

| Feld | Bedeutung |
| --- | --- |
| `fact_id`, `plant_id` | Eindeutige Zuordnung |
| `property_id` | Erweiterbare Eigenschaft, etwa `plant.height` oder `fruit.mass` |
| `value` | Typisierter Wahrheitswert, Textwert, Zahl oder Intervall |
| `unit`, `value_semantics` | Einheit und Bedeutung, etwa Höchstwert, typischer Bereich, Reifezustand |
| `polarity` | Positive oder ausdrücklich negative Aussage |
| `qualifiers` | Bedingungen wie geschützter Standort, Reife oder eingeschränkte Eignung |
| `sources` | Originalfeldname, Feld-Prüfsumme, Textpositionen und Originalzitat |
| `origin` | Strukturierte Extraktion, versionierte Textregel oder spätere semantische Extraktion |
| `validation` | Quellenprüfung und fachliche Freigabe getrennt |

Textpositionen beziehen sich auf Unicode-Zeichen des unveränderten Feldwerts.
Die Prüfung verlangt `field_text[start:end] == quote`. Angezeigt wird stets
der vollständige Feldwert. Normalisierte Suchtexte werden getrennt gespeichert.
Ein echtes Zitat beweist allein noch keine korrekte semantische Ableitung.

Neue Eigenschaften sind Daten in der Registry, keine Erweiterung eines
Python-Enums. Allgemeine Operatoren bleiben typisiert und fest implementiert.
Neue Bedeutung oder Synonyme brauchen eine nachvollziehbare Zuordnung; frei
erfundene Eigenschafts-IDs aus einer Anfrage werden nicht automatisch vertraut.

### Importregeln

- Originalfelder zuerst übernehmen und prüfen; Extraktion ausschließlich daraus.
- Zahlen, Einheit und Bezugsobjekt getrennt halten: Fruchtgewicht ist weder
  Fruchtgröße noch Wuchshöhe. Keine erfundenen Schwellen für „groß“ oder „früh“.
- Nicht gesetzte Positivcheckboxen bedeuten unbekannt. Null-Platzhalter ebenfalls;
  ausdrücklich gepflegter Schärfegrad 0 behält seine besondere Bedeutung.
- Einschränkungen gehören zum Fakt. „Bedingt für Freiland“ wird nicht zu
  uneingeschränkter Eignung. „Freiland“ beweist keinen Anbau ohne Regenschutz.
- Eindeutige Beschreibung hat Vorrang vor abgeleiteten Tags und Checkboxen.
  Widersprüche innerhalb der Beschreibung ergeben unbekannt; alle beteiligten
  Quellen bleiben erhalten. Konflikte ohne sichere Vorrangregel bleiben offen.
- Ein neues nicht erkanntes Textmerkmal bleibt vollständig im Textindex erhalten.
- Die bisherigen `evidence`-Einträge nicht blind übernehmen: Der alte Import
  setzt unter anderem `Freiland` mit `OUTDOOR_UNCOVERED` gleich, fasst mehrere
  Quellenfelder zusammen und erzeugt teils normalisierte statt wörtliche Zitate.
  Fakten daher aus Originalfeldern mit überprüften Regeln neu aufbauen.

Pro Pflanze wird eine Inhaltsprüfsumme über die relevanten Originalfelder
gebildet. Unveränderte Pflanzen übernehmen gültige Fakten; Änderungen an Text,
Registry, Extraktor oder Schema invalidieren die betroffenen Ableitungen.
Gelöschte Pflanzen verschwinden auch aus Index und Cache. Bilder bleiben über
das Originalobjekt erreichbar und werden nicht zur KI-Eigenschaftserkennung genutzt.

Die bestehenden IDs hängen nur vom Namen ab. Vor Verwendung als Indexschlüssel
Duplikate erkennen und den neuen Faktenbestand bei Kollision nicht aktivieren.
Keine stillen ID-Änderungen während dieser Migration.

Import zuerst in einen temporären Bestand schreiben, Quellen und Referenzen
prüfen, dann eine vollständige Revision aktivieren. Beratung liest immer eine
zusammengehörige Revision. Ein Extraktionsfehler darf nicht unbemerkt alte Fakten
an neue Originaltexte hängen; betroffene Fakten bleiben unbekannt.

## 2. Freie Frage als ausführbarer Suchauftrag

Der Interpreter erhält Frage, Gesprächsverlauf, bisherigen Suchauftrag,
sichtbare Sortenreferenzen und eine kompakte Eigenschaftsregistry. Vollständige
Pflanzendatensätze werden nicht mitgesendet. Kategorien und Namensauflösung
bleiben lokal geprüft. Bei stark wachsender Registry dürfen unbekannte Begriffe
nicht durch eine zu enge Vorauswahl verloren gehen.

Der neue Plan enthält Kategorien, erwähnte Sorten, Pflichtausdruck, Vorlieben,
Informationswünsche, offene Kriterien und gegebenenfalls eine Rückfrage.
Jeder Ausdruck trägt zusätzlich den ursprünglichen Wortlaut.

Ausdrucksarten:

- `all`: alle Teilausdrücke müssen gelten.
- `any`: mindestens ein Teilausdruck muss gelten.
- `not`: ausdrückliche logische Verneinung.
- `predicate`: Eigenschaft, Operator, typisierter Vergleichswert und Bedingungen.
- `unresolved`: vollständiger Wunsch, für den keine sichere lokale Abbildung besteht.

Beispiel „Rot und klein oder gelb und groß, höchstens 80 cm hoch; gern süß“:

```text
Pflicht = all(
  any(
    all(fruit.color enthält rot, fruit.size entspricht klein),
    all(fruit.color enthält gelb, fruit.size entspricht groß)
  ),
  plant.height <= 80 cm
)
Vorliebe = taste.sweet == true
```

„Entspricht groß“ verlangt einen belegten qualitativen Wert oder eine ausdrücklich
definierte passende Bedeutung; aus Grammwerten wird keine beliebige Grenze geraten.
Mehrfarbigkeit oder verschiedene Reifezustände verhindern pauschale Ableitungen
wie „gelb bedeutet nicht rot“.

Der Plan wird auf erlaubte Operatoren, passende Typen/Einheiten, bekannte IDs,
Baumgröße und Tiefe geprüft. Vorschlag: maximal 20 atomare Kriterien und Tiefe 6.
Zu komplexe Wünsche werden nicht abgeschnitten, sondern zur Präzisierung
zurückgegeben. Freitext wird niemals als Python, SQL oder anderer Code ausgeführt.

## 3. Lokale Auswertung mit drei Wahrheitswerten

| Operation | Belegt | Widerlegt | Unbekannt |
| --- | --- | --- | --- |
| UND | Alle Kinder belegt | Mindestens eines widerlegt | Sonst |
| ODER | Mindestens eines belegt | Alle Kinder widerlegt | Sonst |
| NICHT | Kind widerlegt | Kind belegt | Kind unbekannt |

Vor dieser Verknüpfung werden Quellenkonflikte am einzelnen Prädikat aufgelöst.
Ein unbekannter Pflichtteil verhindert einen Treffer, sofern nicht ein anderer
ODER-Zweig den gesamten Ausdruck belegt. Ein fehlender Wert ist kein Gegenbeleg.
Vorlieben ändern nur die Reihenfolge, niemals die Pflichtauswahl.

Numerische Regeln berücksichtigen die Bedeutung der Quelle. Ein dokumentierter
Bereich 60–100 cm ist für die Grenze „höchstens 80 cm“ nicht vollständig passend;
ein exakter belegter Höchstwert 70 cm erfüllt sie. Eine bloße Obergrenze von
100 cm beweist dagegen keine Mindesthöhe über 80 cm. Überlappende oder unklare
Bereiche bleiben unbekannt, wenn die Vergleichsaussage nicht folgt. Umgerechnet
wird nur zwischen kompatiblen Einheiten derselben Größe.

Alle Kategorie-/Namenskandidaten werden lokal geprüft. Die Kandidatenzahl ist
bei 249 Pflanzen klein genug für eine vollständige Prüfung ohne Modellaufruf.
Eine Textsuche kann offene Stellen finden, aber ein fehlender Suchtreffer wird
niemals zu „widerlegt“. Unaufgelöste Kriterien liefern unbekannt mit Ursache
`mapping_unresolved`; fehlende Fakten `evidence_missing`; Konflikte `conflict`.

Informationsfragen zeigen vorhandene Angaben auch dann, wenn sie negativ sind.
Vergleiche nennen Datenlücken pro Sorte. Reine Listen benötigen keine Faktenprüfung.
Karten behalten `checks`, `catalogue_fields`, Beschreibung und Bildreferenzen;
für komplexe Ausdrücke kommt eine nachvollziehbare Baum-Auswertung hinzu.

Ohne vollständig belegten Pflichtausdruck: „Woas I ned.“ mit konkreter Datenlücke.
Technische Fehler erhalten eine eigene Fehlermeldung und werden nicht als
fehlendes Pflanzenwissen ausgegeben. Teilresultate werden nicht als vollständige
Prüfung dargestellt.

## 4. Gespräch und Wiederverwendung

Der Browser behält Frage-/Antwortverlauf sowie einen versionierten Suchauftrag.
Sichtbare Sorten werden mit ID und Reihenfolge gespeichert, damit „die zweite“
eindeutig auflösbar ist. Das Backend prüft diesen Zustand gegen den Katalog;
vom Browser gelieferte Pflanzenfakten oder Empfehlungen werden nicht vertraut.

Der Interpreter liefert jeweils den vollständigen aktuellen Auftrag:
„doch lieber klein“ ersetzt die Größe; „auch gelb“ ergänzt eine Pflicht;
„wenn möglich gelb“ ergänzt eine Vorliebe. Ein Themenwechsel setzt nur die
unpassenden alten Wünsche zurück. Der erkannte Auftrag bleibt sichtbar.
Bestehender Verlauf wird nicht still gekürzt; Größenlimits führen zur bekannten
Aufforderung, eine neue Beratung zu beginnen. Fehlgeschlagene Anfragen verändern
keinen erfolgreichen Gesprächszustand.

Lokale Prüfung kann mit Schlüssel aus Katalogrevision, Faktenversion und
kanonischem Suchausdruck wiederverwendet werden. Ein Interpretationscache muss
zusätzlich Frage, gesamten relevanten Gesprächszustand, sichtbare IDs, Modell
und Promptversion berücksichtigen. Kein Cache nur anhand des Fragetexts.

## 5. Kosten und Laufzeit begrenzen

Vorgeschlagene Startwerte, noch nicht mit echtem Modell abgenommen:

| Bereich | Vorgabe |
| --- | --- |
| Interpretation | Höchstens 1 SDK-Anfrage je neuem Gesprächsschritt |
| SDK-Wiederholungen | 0 automatische Wiederholungen |
| Zeitbudget | Ziel: 30 Sekunden Gesamtfrist; Transport-Timeout separat konfigurieren |
| Ausgabe | Explizites konfigurierbares Tokenlimit; Startvorschlag 4.000 |
| Katalogprüfung | 0 externe Modellaufrufe im normalen Betrieb |
| Semantische Ergänzung | Standardmäßig aus; kein automatischer Rückfall auf v0.5 |
| Import | Zunächst vollständig lokal, keine impliziten API-Aufrufe |

Die Gesamtfrist muss mit echter Abbruchfähigkeit implementiert werden; ein
Timeout auf einem wartenden Thread beendet dessen HTTP-Anfrage nicht automatisch.
Auch ein rechtzeitiger Abbruch garantiert keine ausbleibende Abrechnung einer
bereits beim Anbieter bearbeiteten Anfrage. Tokenlimit und Frist sind Schutzgrenzen,
keine garantierte Antwortzeit oder feste Cent-Zusage. Zu kurze/unvollständige
Modellausgaben werden sauber zurückgewiesen, nicht automatisch neu angefordert.

Pro Anfrage lokal erfassen: Request-ID, Modell, Dauer, Anzahl API-Aufrufe,
gemeldete Eingabe-/Ausgabe-Tokens einschließlich verfügbarer Detailzähler,
Cache-Nutzung und bereinigte Fehlerklasse. Keine Schlüssel oder vollständigen
Kundengespräche im technischen Log. Fehlende Nutzungsdaten heißen unbekannt,
nicht null. Eine Geldanzeige braucht gesondert verifizierte Preise.

Eine spätere KI-Aufbereitung beim Import verarbeitet nur geänderte Originalfelder,
verifiziert jede Quelle und speichert Extraktor-/Modellversion. Sie benötigt ein
explizites Budget und fachliche Stichproben. Alternativ wäre eine begrenzte
Nachprüfung offener Eigenschaften denkbar; ohne vollständige Abdeckung darf sie
keine erschöpfende Trefferliste behaupten. Beides gehört nicht zum ersten Ausbau.

## 6. Umsetzung in überprüfbaren Schritten

1. Quellenmodell, Registry und lokale Extraktion aus Originalfeldern ergänzen;
   Importbericht mit Abdeckung, Konflikten und ungültigen Quellen erzeugen.
   Den bestehenden Windows-Zeilenendentest gezielt korrigieren.
2. Ausdrucksmodell und lokalen Dreiwert-Auswerter implementieren. Mit synthetischen
   Fakten und manuell geprüften Katalogbelegen testen, ohne Modellverbindung.
3. Gesprächsinterpretation auf den neuen Plan umstellen. `catalogue_dialogue.py`
   verwendet im neuen Pfad keine vollständigen Modell-Katalogprüfungen mehr.
   `dialogue_models.py` erhält die Ausdrucksmodelle; `main.py` die Zustandstransporte
   und verständliche Anzeige. Neue Auswertungslogik in eigenem Modul halten.
4. Quellenkarten, Bilder, Seitennavigation und Fehlerbehandlung im echten lokalen
   Browser mit simulierten API-Antworten prüfen. Keine Downloads implizit voraussetzen.
5. Erst nach separater Freigabe einen kleinen echten Modelltest mit definiertem
   Anfrage-/Tokenbudget durchführen. Offline-Tests belegen keine Sprachqualität.

Alten Stand während der Migration erhalten. Keine automatische Umschaltung auf
den kostspieligen alten Pfad bei Fehlern oder unbekannten Eigenschaften.

## 7. Offline-Abnahme

| Prüfung | Erwartetes Ergebnis |
| --- | --- |
| Vollständigkeit | 249 Originaldatensätze unverändert lesbar, alle 126 Bildreferenzen vorhanden |
| Provenienz | Jede entscheidende Quelle exakt im Originalfeld; vollständige Felder auf Karten |
| UND/ODER/NOT | Alle Dreiwert-Kombinationen und verschachtelte Alternativen korrekt |
| Negation | „Nicht scharf“ bei fehlender Angabe unbekannt, bei belegtem Schärfegrad 0 belegt |
| Einschränkung | Freiland ist kein Beweis für fehlenden Regenschutzbedarf |
| Zahlen | cm/m zulässig; Gramm/Höhe unzulässig; Intervalle und Grenzwerte korrekt |
| Konflikt | Widersprüchliche Beschreibung ergibt unbekannt, Tags überschreiben sie nicht |
| Freie neue Eigenschaft | Kein Enum-Zwang; sichere Registry-Abbildung oder sichtbares ungelöstes Kriterium |
| Gespräch | Ergänzung, Korrektur, Rückfrage, Themenwechsel und „die zweite“ mit simulierten Plänen |
| Ergebnisse | Pflichtlücken getrennt von Gegenbelegen; Vorlieben lockern keine Pflicht |
| Listen/Bilder | Alle Ergebnisse paginierbar, Originalbeschreibungen und Bilder sichtbar |
| Änderungsimport | Unveränderte Fakten wiederverwendet, geänderte/gelöschte Quellen invalidiert |
| IDs | Doppelte IDs verhindert, keine still verlorenen Datensätze |
| Kostenpfad | Ein simulierter Interpretationsaufruf, null Katalog-Modellaufrufe; keine stillen Retries |
| Fehler | Ungültiger Plan, Zeitüberschreitung und unvollständige Ausgabe ohne Teilerfolg |
| Performance | Lokale Auswahl für 249 Pflanzen und 20 Kriterien messen; Ziel unter 1 Sekunde ohne Import/Netzwerk |

Zusätzlich die Fälle aus `DIALOGUE_VALIDATION.md` übernehmen. Erwartete Fakten
für ausgewählte echte Pflanzen manuell anhand der Originalfelder festlegen,
statt erwartete Antworten aus dem Extraktor selbst zu erzeugen. Abdeckung pro
Eigenschaft und Anteil unbekannter Ergebnisse berichten: Weniger Kosten bei
gleichzeitig verschwundenen Wünschen wären kein erfolgreicher Umbau.

## Entscheidung dieses Entwurfs

Empfohlen ist ein zunächst lokaler Import- und Auswahlpfad mit einem kleinen
freien Gesprächsinterpreter. Die vorbereitete Semantik ist erweiterbar, aber
ihre Abdeckung wird offen ausgewiesen. Unbekannt bleibt „Woas I ned.“. Die
größte fachliche Arbeit ist die saubere Faktenextraktion samt Quellenprüfung;
ein bloßer Wechsel des Modells oder kleinere Prüfgruppen löst das Grundproblem nicht.
