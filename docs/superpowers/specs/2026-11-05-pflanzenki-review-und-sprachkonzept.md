# PflanzenKI: Review und Konzept für die Spracheingabe

Stand: 5. November 2026. Status: Konzept. Die Spracheingabe ist bewusst noch nicht umgesetzt.
Die Befunde B3 und B4 sowie die Web-Vorbereitung wurden in v0.6 teilweise erledigt, die Faktenprüfung
zu B1 und B2 danach ebenfalls; siehe `docs/CHANGELOG.md`.
Methodik: `obra/superpowers`, gelesen aus dem lokalen Ordner und von Hand angewendet
(`brainstorming`, `systematic-debugging`, `test-driven-development`,
`verification-before-completion`, `writing-plans`, `requesting-code-review`).

Für die Messungen wurde nichts am Code geändert und keine bezahlte Modell-API aufgerufen.

## 1. Kurzfazit

Die Spracheingabe selbst ist der kleinere Teil der Aufgabe. Entscheidend ist, was davor
und danach passiert:

1. **Sortennamen gehen auf dem Weg von Sprache zu Text kaputt.** Die heutige Suche fängt
   das nicht auf.
2. **„Passt“ wird heute nicht fachlich geprüft.** Geprüft wird nur, ob die vom Modell
   genannte Quelle existiert. Ob sie die Aussage trägt, prüft niemand.
3. **Richtigkeit wird nicht gemessen.** Ohne Referenzfragen mit erwarteten Antworten lässt
   sich „korrekte Vorschläge“ weder belegen noch verbessern.

Empfehlung: Sprache wird eine vorgeschaltete Stufe, die Text an das unveränderte `/api/ask`
liefert. Davor kommen ein Namensabgleich mit Rückfrage bei Unsicherheit, danach eine lokale
Prüfung der Modellantwort gegen die vorhandenen Katalogfakten.

```
Mikrofon (Taste halten)
  → /api/transcribe: gpt-transcribe mit Sprache de und Katalogbegriffen als keywords
  → lokaler Namensabgleich: Treffer, Rückfrage „Meintest du …?“ oder kein Eingriff
  → editierbarer Text: „Verstanden als …“
  → /api/ask: verbesserte Suche, ein Modellaufruf
  → lokale Faktenprüfung: Widerlegtes wird nie als „passt“ gezeigt
  → schriftliche Vorschläge mit Originalquellen
```

## 2. Was gut ist und bleiben soll

- **Klare Beratungsregeln:** Leeres Feld heißt unbekannt, Ausschluss nur mit Gegenbeleg,
  Beschreibung vor Filterfeld.
- **Ehrliche Dokumentation:** Grenzen und fehlende Nachweise stehen offen in den Dokumenten.
- **Kostendisziplin:** ein Modellaufruf, keine automatischen Wiederholungen,
  Größenlimits für die Anfrage.
- **Vorhandene Faktenbasis:** `catalogue_facts.json` und die Dreiwertlogik in
  `app/advisor/local_selection.py` sind wertvoll, liegen aber auf dem aktiven Weg brach.
- **Testbasis:** 226 Python-Tests und der UI-Vertragstest bestehen.

## 3. Befunde nach Priorität

### P1: Direkt relevant für korrekte Vorschläge

**B1. „Passt“ ist nicht fachlich abgesichert.**
`app/ai/catalogue_answer.py:94` prüft nur, ob Pflanze und Quellenkennung existieren.
Jede vorhandene Quelle genügt, auch das Namensfeld. Der freie Text `answer`
(`catalogue_answer.py:103`) wird gar nicht geprüft. Der Screenshot-Test zeigt den Effekt:
Bei Prinzipe Borghese wurde aus „Regenschutz erforderlich“ in der Erklärung „empfohlen“.

**B2. Zwei Beratungswege, und der besser abgesicherte ist abgehängt.**
`/api/ask` nutzt `catalogue_answer.consult` (`app/main.py:698`). Faktenprüfung und
Dreiwertlogik laufen nur noch über `catalogue_dialogue.consult`, und dieses wird von keinem
Endpunkt aufgerufen; `/api/interpret` liefert nur den Plan. Der Parameter `previous_plan`
wird im aktiven Weg angenommen, aber nicht verwendet. `docs/ARCHITECTURE.md` beschreibt
weiterhin den abgehängten Weg.

Keiner der beiden Wege reicht allein:

| | Plan + lokale Fakten | Suche + Modell (aktiv) |
| --- | --- | --- |
| Stärke | Nachvollziehbar, Widerlegtes fliegt raus | Versteht freie Beschreibungstexte |
| Schwäche | Viel UNKNOWN (Höhenfrage: 0 Empfehlungen, 249 unbekannt) | Keine fachliche Prüfung |

**B3. Die Suche sieht die Checkbox-Felder nicht.**
`app/advisor/retrieval.py:51` indexiert nur Feldwerte. Bei „Balkon / Topf: Yes“ wird also
„yes“ indexiert, nicht „Balkon“. Ein Treffer gelingt nur, wenn der Begriff im Text steht.

| Anfrage | Sorten mit gesetztem Feld | davon unter den 24 Kandidaten |
| --- | ---: | ---: |
| Ich suche eine Tomate für den Balkon | 10 | 6 |
| Tomaten für den Topf | 10 | 9 |
| Tomate fürs Gewächshaus | 39 | 9 |

Beim Gewächshaus ist das nicht zwingend schlimm, weil höchstens vier Sorten gezeigt werden.
Beim Balkon können aber gute Treffer fehlen.

**B4. Die Suche ist für gesprochene Sprache nicht robust.**

- **Füllwörter verzerren die Treffer.** „was“ fehlt in der Stoppwortliste
  (`retrieval.py:8`). Dadurch landen Thai-Five-Star und Zebrino bei fast jeder Frage mit
  „Was ist mit …“ weit oben.
- **Synonyme fehlen.** „Melanzani“ und „Paradeiser“ liefern null Kandidaten,
  „Paradeiser für Freiland“ liefert unter 24 Kandidaten nur eine Tomate, aber neun Gurken.
- **Schreibvarianten kippen das Ergebnis.** Bei „Pepperoni nicht so scharf“ steht
  San Marzano Retorta oben, bei „Peperoni“ dagegen Lombardo.
- **Falsche Kandidaten gehen trotzdem ans Modell.** Bei „Was ist mit Fazzi Wazzi?“ gehen
  nur Thai-Five-Star und Zebrino ans Modell, die gemeinte Sorte fehlt.

**B5. Sortennamen sind die größte Fehlerquelle bei Sprache.**
Test: alle 249 Namen in „Was ist mit …?“, einmal exakt und einmal lautschriftlich verfremdet.

| Eingabe | Heute: Platz 1 | Heute: unter Kandidaten | Prototyp: Platz 1 |
| --- | ---: | ---: | ---: |
| Exakt | 248/249 | 249/249 | 249/249 |
| Lautschriftlich verfremdet | 168/249 | 196/249 | 245/249 |

Der Prototyp kombiniert Zeichenähnlichkeit und Kölner Phonetik, nur mit der
Python-Standardbibliothek. Er fand zum Beispiel „Fazzi Wazzi“ → Fuzzy-Wuzzy,
„Blek Tscherri“ → Black Cherry und „Prinzipe Borgese“ → Prinzipe Borghese.

Grenzen dieser Messung: Die Verfremdung ist selbst gebaut, nicht echte Spracherkennung.
Der Prototyp bekam nur den Namen, nicht den ganzen Satz. Teilnamen scheitern noch
(„Ochsenherz“ → Azur-Star, „San Marzano“ → Sensation). Das Verfahren ist also vielversprechend,
aber nicht fertig: Es braucht Wortfenster, Teilnamen und mehrere mögliche Treffer.

**B6. Es gibt keine Messung der Antwortqualität.**
Die Tests simulieren das Modell. Die 44 fachlichen Paare sind laut Bericht eine
Entwicklungsstichprobe mit vorgegebener Übersetzung der Frage. Der echte Test des aktiven
Weges brach im zweiten Schritt ab (27 Sekunden, dann Timeout). Danach wurde die Anfrage
verkleinert. Das README nennt „meist unter zehn Sekunden“ aus Nutzertests, ein
reproduzierbarer Nachweis fehlt.

### P2: Daten

**B7. Mehrere Checkbox-Felder sind nicht gepflegt.** `Freiland`, `Winterhart`,
`Robust/Resistent` und `Trockenheitsverträglich` stehen bei allen 249 Pflanzen auf „No“.
Die Felder sagen also nichts aus. Der Prompt fängt das ab, sinnvoller ist aber Pflege oder
ein klarer Vermerk im Import.

**B8. Das Höhenfeld ist teilweise falsch.** Der Live-Bericht fand Fruchtmaße und
Pflanzabstände im Höhenfeld (Taubenherz 3 cm, Strubelpeter 35 cm). Die Extraktion meidet
diese Fälle, im Notion-Original stehen sie vermutlich weiter.

**B9. Datenlücken.** 123 Pflanzen haben kein Bild. Die Kategorien sind mit 103 Tomaten
stark ungleich verteilt, dadurch wirkt die Grenze von 24 Kandidaten bei Tomaten am stärksten.

### P3: Wartbarkeit

- **`app/main.py` hat 758 Zeilen**, davon rund 630 eingebettetes HTML und JavaScript. Für
  die Spracheingabe lohnt die Auslagerung nach `static/`.
- **Altlasten:** `evaluate_batch` wirft nur noch einen Fehler. Der Fake-Modus nutzt einen
  anderen Antwortweg als der Normalbetrieb und ist deshalb keine Vorschau auf ihn.
- **Keine CI:** `.github/` fehlt. `pytest` steht in den Laufzeit-Abhängigkeiten.
- **Testzahlen in den Dokumenten sind veraltet** (218 statt 226). Auf diesem Rechner
  scheiterten elf Tests zunächst mit `PermissionError` am temporären Ordner; mit eigenem
  `--basetemp` liefen alle 226 durch.
- **Gesamtzeitlimit fehlt:** Es gibt nur ein Transport-Timeout von 30 Sekunden.

## 4. Konzept Spracheingabe

### Entscheidungen

| Thema | Empfehlung | Begründung |
| --- | --- | --- |
| Spracherkennung | `gpt-transcribe` über eine schlanke Schnittstelle | Laut OpenAI-Doku der empfohlene Einstieg, mit `keywords` für Produktnamen. 0,0045 USD/Minute |
| Bedienung | Taste halten, Aufnahme bis maximal 30 Sekunden | Einfach, kein Dauerzuhören, keine Echtzeit nötig |
| Prüfschritt | Text immer sichtbar und editierbar | Keywords können laut Doku nicht gesprochene Begriffe erzeugen |
| Ausgabe | Bestehende Karten unverändert | Schriftliche Vorschläge sind das Ziel |

Verworfene Alternativen:

- **Web Speech API:** kostenlos, aber keine Katalogbegriffe als Hilfe, Firefox nicht
  regulär unterstützt, und die Audiodaten gehen je nach Browser an einen Fremddienst.
  Der aktuelle Stand dazu ist nicht abschließend belegt.
- **Lokales `faster-whisper`:** gut für Datenschutz und Kosten, aber auf CPU ungemessen.
  Die Schnittstelle hält diesen Weg offen, falls die Datenschutzfrage es verlangt.
- **`gpt-live-transcribe`:** 0,017 USD/Minute für Echtzeit, die hier niemand braucht.
- **`whisper-1`, `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`:** laut Doku abgekündigt,
  Abschaltung am 26. Februar 2027.

### Ablauf

1. **Aufnahme:** `MediaRecorder` mit Formatprüfung über `isTypeSupported`. Eine Pegelanzeige
   zeigt, dass das Mikrofon hört.
2. **`POST /api/transcribe`:** Größe und Dauer begrenzen, `languages: ["de"]` und `keywords`
   setzen. Dafür ist `python-multipart` nötig, das noch nicht installiert ist. Das Audio
   wird nicht gespeichert, Transkripte kommen nicht ins Log.
3. **Namensabgleich** (neu, ohne Modellaufruf):

   | Sicherheit des Treffers | Verhalten |
   | --- | --- |
   | Hoch, mit klarem Abstand zum Zweitbesten | Name wird markiert übernommen |
   | Mittel oder zwei ähnliche Treffer | Rückfrage mit Knöpfen: „Meintest du Fuzzy-Wuzzy?“ |
   | Niedrig | Kein Eingriff, keine geratene Sorte |

   Die Schwellen werden am Referenzsatz festgelegt, nicht vorab geraten. Das Original bleibt
   immer sichtbar.
4. **Bestätigung:** „Verstanden als …“ mit Absenden und Korrigieren. Ob später automatisch
   gesendet werden darf, entscheidet die gemessene Erkennungsqualität.
5. **Beratung:** `/api/ask` bleibt gleich. Text- und Spracheingabe nutzen denselben Weg, also
   gelten alle Verbesserungen für beide.

### Lokale Faktenprüfung

Ein Modellaufruf bleibt die Regel. Die Modellantwort liefert zusätzlich die aktuellen
Bedingungen als Ausdrücke im Format, das `local_selection.py` schon kennt. Python prüft dann
jede als „passt“ gemeldete Sorte:

| Ergebnis der Faktenprüfung | Darstellung |
| --- | --- |
| Bestätigt | Empfehlung |
| Unbekannt | Empfehlung bleibt, weil das Modell den Text gelesen hat und die Regeln oft nichts wissen |
| Widerlegt | Nie als Empfehlung, sichtbar unter „unsicher“ mit Gegenbeleg |

Zusätzlich gilt: Das Namensfeld zählt nicht als Beleg, und sortenbezogene Aussagen gehören
nur in die geprüften Karten.

Das schließt nicht jede Fehldeutung aus. Eine Aussage, zu der keine Fakten vorliegen, bleibt
ungeprüft. Reicht das laut Referenzsatz nicht, wäre der nächste Schritt eine zweistufige
Lösung aus Plan und Antwort. Sie kostet aber einen zweiten Modellaufruf und mehr Wartezeit.

### Suche

- Stoppwörter für gesprochene Sprache ergänzen, zum Beispiel „was“, „äh“, „halt“, „so“.
- Bei gesetzten Checkboxen den Feldnamen mit indexieren.
- Eine gepflegte Synonymliste für Melanzani, Paradeiser und Peperoni-Schreibweisen anlegen.
- Den Namensabgleich aus Schritt 3 auch für getippte Fragen nutzen.

### Datenschutz, Sicherheit, Kosten

- **Mikrofon nur über sichere Verbindung:** `127.0.0.1` bzw. `localhost` funktioniert, ein
  Handy im WLAN über eine IP-Adresse nicht. Dafür wäre HTTPS nötig.
- **Keine Anmeldung vorhanden:** Sobald die App im Netz erreichbar ist, braucht sie Anmeldung
  und Anfragelimits, denn jeder Aufruf kostet Geld.
- **Stimme ist personenbezogen:** Bei Nutzung durch Dritte gehören ein sichtbarer Hinweis vor
  der ersten Aufnahme und eine rechtliche Prüfung des OpenAI-Einsatzes dazu.
- **Kosten pro Sprachfrage, grob:** 15 Sekunden Audio kosten etwa 0,0011 USD. Eine
  Modellantwort kostete im Test vor der Verkleinerung 0,0072 USD. Das ist kein Preisversprechen.

## 5. Nachweis der Richtigkeit

Kern von `verification-before-completion`: keine Qualitätsaussage ohne frische Messung.

**Referenzsatz** (Vorschlag: 60 bis 100 Fragen, vorab von Hand gegen die Originaltexte bewertet):

- Sortennamen, darunter fremdsprachige und Teilnamen
- Eigenschaftsfragen, Verneinungen, UND/ODER
- Folgefragen und Themenwechsel
- Fragen ohne belegbare Antwort
- zu etwa 30 bis 50 Fragen echte Aufnahmen, wenn möglich von verschiedenen Sprechenden

**Vorgeschlagene Ziele**, die wir nach der ersten Messung gemeinsam festlegen:

| Kennzahl | Ziel |
| --- | --- |
| Widerlegte Sorte als Empfehlung | 0 |
| Erfundene Sorte oder Quelle | 0 |
| Gesprochener Sortenname richtig erkannt oder rückgefragt | mindestens 95 % |
| Falscher Name still übernommen | 0 |
| Erwartete Sorte unter den Kandidaten | mindestens 90 % |
| Zeit bis zur Antwort | gemessen und festgelegt, Ziel unter 10 Sekunden |

Reale Fehlerquoten sind erst nach dieser Messung bekannt. Fehlerfreiheit bei beliebigen Fragen
lässt sich auch dann nicht zusagen.

## 6. Umsetzungsreihenfolge

Jede Phase läuft testgetrieben auf eigenem Branch, mit Review vor dem Merge.

| Phase | Inhalt | Ergebnis |
| --- | --- | --- |
| 0 | Referenzsatz und Ausgangsmessung | Belastbarer Ist-Stand. Bezahlte Läufe nur nach Budgetfreigabe |
| 1 | Suche und Namensabgleich | B3, B4 und B5 behoben, auch für Tippen nützlich |
| 2 | Lokale Faktenprüfung | B1 und B2 behoben, Doku auf aktuellem Stand |
| 3 | Spracheingabe | Aufnahme, Transkription, Bestätigung, Rückfrage |
| 4 | Abnahme und Aufräumen | Messung mit echten Aufnahmen, Datenpflege, CI |

Die Reihenfolge ist Absicht: Spracheingabe auf eine ungeprüfte Beratung zu setzen würde
Fehler nur schwerer erkennbar machen.

## 7. Offene Punkte

1. **Wer spricht wo?** Das ist die wichtigste offene Frage (siehe unten).
2. **Länge der `keywords`:** Die Doku nennt kein Limit. Ob alle 249 Namen passen, muss ein
   kurzer Test zeigen.
3. **Konfidenzwerte:** Die Doku nennt keine für `gpt-transcribe`. Das Konzept kommt deshalb
   ohne sie aus.
4. **`gpt-5-mini`:** Die Verfügbarkeit habe ich heute nicht geprüft. Das gehört in Phase 0.

Die Antwort auf Punkt 1 verändert den Umfang:

| Nutzung | Folge |
| --- | --- |
| Allein am eigenen Rechner | Konzept wie beschrieben, kein HTTPS und keine Anmeldung nötig |
| Handy oder Tablet im Garten | Zusätzlich HTTPS und Anmeldung |
| Kundschaft, etwa am Marktstand | Zusätzlich Hinweis zur Stimme, Rechtsprüfung, Störgeräusche, Dialekt, Missbrauchsschutz |

## Quellen

- [OpenAI: Speech to text](https://developers.openai.com/api/docs/guides/speech-to-text)
- [OpenAI: Preise](https://developers.openai.com/api/docs/pricing)
- [Chrome: MediaRecorder und sichere Ursprünge](https://developer.chrome.com/blog/mediarecorder)
- [Mozilla: Web Speech API](https://wiki.mozilla.org/Web_Speech_API_-_Speech_Recognition)
- [Browser-Unterstützung der Spracherkennung](https://www.testmuai.com/learning-hub/speech-recognition-api-browser-support/)
- [Hugging Face: Whisper large-v3 German CT2](https://huggingface.co/tnfru/whisper-large-v3-german-ct2)
