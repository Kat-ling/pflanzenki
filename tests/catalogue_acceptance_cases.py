"""Manually labelled original catalogue cases; no generated expectations.

Each target is a checked question/plant pair, not an exhaustive catalogue answer.
The question-to-expression translation is supplied, so this is not an LLM test.
"""


def leaf(key, value=True, comparator="eq", unit=None):
    return dict(op="predicate", text=key, property_id=key, value=value,
                comparator=comparator, unit=unit, children=[])


def group(op, *children):
    return dict(op=op, text=op, property_id="", value=None,
                comparator="eq", unit=None, children=list(children))


# name, expected status, literal description excerpt, editorial justification
CASES = [
    ("01", "Welche Tomate hat große Früchte und eignet sich für Freiland?",
     group("all", leaf("site.outdoor"), leaf("fruit.large")), [
         ("Rote Zora", "yes", "für den Freilandanbau geeignet", "Große Früchte und Freiland sind ausdrücklich beschrieben."),
         ("Matina", "unknown", "für das Freiland geeignet", "Normale Salattomate belegt keine großen Früchte."),
     ]),
    ("02", "Kann ich diese Tomate ohne Regenschutz anbauen?", leaf("site.uncovered"), [
        ("Justens Zuckertomate", "no", "Regenschutz erforderlich", "Erforderlicher Schutz widerlegt ohne Schutz."),
        ("Rote Zora", "unknown", "für den Freilandanbau geeignet", "Freiland allein sagt nichts über Regenschutz."),
    ]),
    ("03", "Ich suche kleine gelbe Früchte.", group("all", leaf("fruit.small"), leaf("fruit.color", "gelb")), [
        ("Golden Currant", "yes", "kleiner, gelber Früchte", "Beide Eigenschaften stehen im selben Satz."),
    ]),
    ("04", "Kleine orange Früchte, für Freiland.", group("all", leaf("fruit.small"), leaf("fruit.color", "orange"), leaf("site.outdoor")), [
        ("Orange Wildtomate", "yes", "Die kleinen orangen Früchte", "Auch Freilandeignung ist genannt, mit Schreibfehler Feilandkultur."),
    ]),
    ("05", "Welche Sorte muss ich nicht ausgeizen?", leaf("care.no_pruning"), [
        ("Small Egg", "yes", "Die Pflanze nicht ausgeizen", "Klare Pflegeanweisung."),
        ("Justens Zuckertomate", "yes", "muß nicht ausgegeizt werden", "Ausdrückliche Negation darf erhalten bleiben."),
        ("Golden Currant", "unknown", "nur mäßig ausgegeizt", "Mäßiges Ausgeizen ist keine uneingeschränkte Aussage über Verzicht."),
    ]),
    ("06", "Welche davon schmecken süß?", leaf("taste.sweet"), [
        ("Zuckertomate", "yes", "sehr süß", "Direkte Geschmacksangabe."),
        ("Justens Zuckertomate", "yes", "angenehm süße", "Negationen zu Pflege ändern den Geschmack nicht."),
        ("Sweet Chocolate", "yes", "ein sehr süßer Gemüsepaprika", "Süßer enthält die Adjektivendung er."),
    ]),
    ("07", "Ich möchte ausdrücklich nicht süß.", leaf("taste.sweet", False), [
        ("Chocolate Cherry Hot", "yes", "nicht mehr süß sondern scharf", "Korrektur der ursprünglichen Eigenschaft ist ausdrücklich."),
        ("Zuckertomate", "no", "sehr süß", "Süß ist ein Gegenbeleg."),
    ]),
    ("08", "Welche Paprika ist nicht scharf?", leaf("taste.spicy", False), [
        ("Roter Augsburger", "yes", "ohne Schärfe", "Explizit schärfefrei."),
        ("Lady Lou", "yes", "Spitzpaprika ohne Schärfe", "Explizit schärfefrei."),
        ("Chocolate Cherry Hot", "no", "sondern scharf", "Beschreibung widerspricht dem importierten Schärfegrad 0."),
        ("King of the North", "unknown", "Sehr knackig und saftig", "Kein Beleg für Schärfefreiheit; Namen/Typ reichen nicht."),
    ]),
    ("09", "Ich suche scharfe Paprika.", leaf("taste.spicy"), [
        ("Sibirischer Hauspaprika", "yes", "ein scharfer Haupaprika", "Scharfer ist eine ausdrückliche Geschmacksangabe."),
        ("Mustafa", "yes", "mit leichter Schärfe", "Leichte Schärfe ist Schärfe, keine unbekannte Negation."),
    ]),
    ("10", "Welche Pflanze eignet sich für den Topf?", leaf("site.container"), [
        ("Small Egg", "yes", "Ampel- oder Topfkultur", "Topfkultur ausdrücklich."),
        ("Huberts Beste", "yes", "Bestens für Töpfe", "Plural Töpfe belegt Eignung."),
        ("Basilico a foglia larga", "yes", "Eignet sich gut für Kästen und Töpfe", "Anbaugefäße ausdrücklich."),
    ]),
    ("11", "Garantiert höchstens 80 cm hoch?", leaf("plant.height", 80, "lte", "cm"), [
        ("Snackpaprika Carina", "unknown", "nur etwa 40 cm hoch", "Ungefähre Höhe wird nicht zur garantierten Obergrenze."),
        ("Huberts Beste", "unknown", "nur etwa 40 cm hoch", "Ungefähre Beschreibung reicht nicht für die Garantie."),
    ]),
    ("12", "Sind die Früchte sicher über 200 g schwer?", leaf("fruit.mass", 200, "gt", "g"), [
        ("Französisches Ochsenherz (Coeur de boef)", "unknown", "ca. 500-800g", "Ungefähres Gewicht ist keine garantierte Mindestmasse jeder Frucht."),
    ]),
    ("13", "Welche Gurke eignet sich zum Einlegen?", leaf("use.pickling"), [
        ("Lemon (Zitronengurke)", "yes", "oder zum Einlegen", "Verwendung ausdrücklich angegeben."),
        ("Vorgebirgstraube", "yes", "geerntet und eingelegt werden", "Verwendungsverb ist ebenfalls ein Beleg."),
        ("Tanja", "unknown", "eine bitterfreie schlanke", "Bitterfrei ist kein Beleg zum Einlegen."),
    ]),
    ("14", "Welche Gurke geht im Freiland?", leaf("site.outdoor"), [
        ("La Diva", "yes", "auch im Freiland kultiviert werden", "Ausdrückliche Anbaumöglichkeit."),
        ("Qualitas", "yes", "auch im Freiland angebaut werden", "Ausdrückliche Anbaumöglichkeit."),
        ("Chinesische Schlange", "yes", "Nur für das Freiland geeignet", "Nur schränkt auf Freiland ein, widerlegt es nicht."),
        ("Tanja", "unknown", "Anbau mit Regenschutz", "Geschützter Anbau belegt keine Freilandeignung, widerlegt sie aber auch nicht."),
    ]),
    ("15", "Welche Zucchini hat gelbe Früchte?", leaf("fruit.color", "gelb"), [
        ("Gold Rush", "yes", "gelbe Zucchini", "Farbe ausdrücklich; spätere Ernte ändert sie nicht."),
    ]),
    ("16", "Hat dieses Basilikum weiße Früchte?", leaf("fruit.color", "weiß"), [
        ("Kleines Buschbasilikum", "unknown", "mit weißen Blüten", "Importiertes Fruchtfarbe=weiß stammt erkennbar von Blüten, nicht Früchten."),
    ]),
    ("17", "Ist dieses Basilikum winterhart?", leaf("plant.winter_hardy"), [
        ("Everleaf Lemon", "no", "Die Pflanzen sind nicht winterhart", "Expliziter Gegenbeleg, unabhängig von Überwinterung im Haus."),
        ("Kaprao", "unknown", "bei 15 Grad", "Überwinterung im Warmen beweist keine Winterhärte."),
    ]),
    ("18", "Süß und ohne Schärfe, bitte.", group("all", leaf("taste.sweet"), leaf("taste.spicy", False)), [
        ("Roter Augsburger", "yes", "ohne Schärfe,süß", "Beide Teilbedingungen ausdrücklich."),
        ("Chocolate Cherry Hot", "no", "nicht mehr süß sondern scharf", "Beide Teilbedingungen widersprochen."),
    ]),
    ("19", "Gelb und klein oder rot und groß.", group("any", group("all", leaf("fruit.color", "gelb"), leaf("fruit.small")), group("all", leaf("fruit.color", "rot"), leaf("fruit.large"))), [
        ("Golden Currant", "yes", "kleiner, gelber Früchte", "Der vollständige erste ODER-Zweig genügt."),
        ("Zuckertomate", "unknown", "Tischtennisballgroße", "Keine erfundene qualitative Größenklasse aus dem Vergleich ableiten."),
    ]),
    ("20", "Welche hat eine dünne Schale?", leaf("fruit.thin_skin"), [
        ("Justens Zuckertomate", "yes", "mit dünner Schale", "Neue Eigenschaft ist direkt belegt."),
        ("Minipaprika Merino", "yes", "dünnschaligen Früchten", "Dasselbe Merkmal als Adjektiv."),
        ("Matina", "unknown", "ausgeprägtes Aroma", "Aroma verrät keine Schalendicke."),
    ]),
]
