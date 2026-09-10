from __future__ import annotations

from enum import Enum


class PlantFeature(str, Enum):
    OUTDOOR_UNCOVERED = "outdoor_uncovered"
    BALCONY = "balcony"
    GREENHOUSE = "greenhouse"
    SWEET = "sweet"
    AROMATIC = "aromatic"
    MILD = "mild"
    SPICY = "spicy"
    EASY_CARE = "easy_care"
    EARLY = "early"
    LATE = "late"
    SAUCE = "sauce"
    FRESH_EATING = "fresh_eating"
    DRYING = "drying"
    ROBUST = "robust"
    HIGH_YIELD = "high_yield"
    SMALL_FRUIT = "small_fruit"
    COMPACT = "compact"
    TALL = "tall"
    CLIMBING = "climbing"
    NO_PRUNING = "no_pruning"
    WARM_LOCATION = "warm_location"
    DROUGHT_TOLERANT = "drought_tolerant"
    SUNNY = "sunny"
    PARTIAL_SHADE = "partial_shade"
    STORABLE = "storable"
    OVERWINTERABLE = "overwinterable"
    WINTER_HARDY = "winter_hardy"
    RED = "red"
    YELLOW = "yellow"
    ORANGE = "orange"
    GREEN = "green"
    PURPLE = "purple"
    BLACK = "black"
    WHITE = "white"
    PINK = "pink"
    PEAR_SHAPED = "pear_shaped"


FEATURE_DESCRIPTIONS: dict[PlantFeature, str] = {
    PlantFeature.OUTDOOR_UNCOVERED: "draußen im ungeschützten Freiland, ohne Dach oder Regenschutz",
    PlantFeature.BALCONY: "für Balkon, Terrasse, Topf oder Kübel geeignet",
    PlantFeature.GREENHOUSE: "für Gewächshaus, Folientunnel oder geschützten Anbau",
    PlantFeature.SWEET: "süßer Geschmack",
    PlantFeature.AROMATIC: "aromatischer oder intensiver Geschmack",
    PlantFeature.MILD: "milder, nicht scharfer Geschmack",
    PlantFeature.SPICY: "scharf oder als Chili/Peperoni mit Schärfe gewünscht",
    PlantFeature.EASY_CARE: "pflegeleicht, unkompliziert oder für Anfänger geeignet",
    PlantFeature.EARLY: "frühe Reife oder Ernte",
    PlantFeature.LATE: "späte Reife oder Ernte",
    PlantFeature.SAUCE: "für Soße, Passata oder Einkochen geeignet",
    PlantFeature.FRESH_EATING: "für Frischverzehr, Rohkost oder zum Naschen",
    PlantFeature.DRYING: "zum Trocknen geeignet",
    PlantFeature.ROBUST: "robust, resistent oder widerstandsfähig",
    PlantFeature.HIGH_YIELD: "ertragreich oder hoher Ertrag",
    PlantFeature.SMALL_FRUIT: "kleine Früchte, Snack- oder Cocktailgröße",
    PlantFeature.COMPACT: "kompakt, kleinbleibend oder buschig",
    PlantFeature.TALL: "hoch oder hochwachsend",
    PlantFeature.CLIMBING: "rankend, kletternd oder Stangenform",
    PlantFeature.NO_PRUNING: "muss nicht ausgegeizt werden",
    PlantFeature.WARM_LOCATION: "benötigt oder bevorzugt einen warmen Standort",
    PlantFeature.DROUGHT_TOLERANT: "trockenheitsverträglich oder geringer Wasserbedarf",
    PlantFeature.SUNNY: "sonniger Standort",
    PlantFeature.PARTIAL_SHADE: "halbschattiger Standort",
    PlantFeature.STORABLE: "lagerfähig oder gut haltbar",
    PlantFeature.OVERWINTERABLE: "überwinterbar oder mehrjährig kultivierbar",
    PlantFeature.WINTER_HARDY: "winterhart im Freien",
    PlantFeature.RED: "rote Früchte oder essbare Pflanzenteile",
    PlantFeature.YELLOW: "gelbe oder goldgelbe Früchte oder essbare Pflanzenteile",
    PlantFeature.ORANGE: "orange Früchte oder essbare Pflanzenteile",
    PlantFeature.GREEN: "grüne Früchte oder essbare Pflanzenteile",
    PlantFeature.PURPLE: "violette, lila oder purpurne Früchte oder essbare Pflanzenteile",
    PlantFeature.BLACK: "schwarze oder sehr dunkle Früchte oder essbare Pflanzenteile",
    PlantFeature.WHITE: "weiße Früchte oder essbare Pflanzenteile",
    PlantFeature.PINK: "rosa oder pinke Früchte oder essbare Pflanzenteile",
    PlantFeature.PEAR_SHAPED: "birnenförmige oder birnenähnliche Früchte",
}


FEATURE_TAGS: dict[PlantFeature, set[str]] = {
    PlantFeature.OUTDOOR_UNCOVERED: {"freiland", "freiland-gurke"},
    PlantFeature.BALCONY: {"balkon", "topf/kübel"},
    PlantFeature.GREENHOUSE: {"gewächshaus"},
    PlantFeature.SWEET: {"süß", "süss"},
    PlantFeature.AROMATIC: {"aromatisch"},
    PlantFeature.MILD: {"mild"},
    PlantFeature.EASY_CARE: {"pflegeleicht", "unkompliziert", "anfängergeeignet"},
    PlantFeature.EARLY: {"früh"},
    PlantFeature.LATE: {"spät"},
    PlantFeature.SAUCE: {"sauce", "soße", "sosse"},
    PlantFeature.FRESH_EATING: {"frischverzehr", "rohkost", "snack"},
    PlantFeature.DRYING: {"trocknen"},
    PlantFeature.ROBUST: {"robust", "krautfäuletolerant", "platzfest"},
    PlantFeature.HIGH_YIELD: {"ertragreich"},
    PlantFeature.SMALL_FRUIT: {"cocktailtomate", "snackgurke", "snackpaprika"},
    PlantFeature.COMPACT: {"kompakt", "kleinbleibend", "buschig"},
    PlantFeature.TALL: {"hoch", "hochwachsend"},
    PlantFeature.CLIMBING: {"rankend", "stangen-/kletterform", "stangenbohne"},
    PlantFeature.NO_PRUNING: {"nicht ausgeizen"},
    PlantFeature.WARM_LOCATION: {"warmer standort"},
    PlantFeature.DROUGHT_TOLERANT: {"trockenheitsverträglich"},
    PlantFeature.SUNNY: {"sonne"},
    PlantFeature.PARTIAL_SHADE: {"halbschatten"},
    PlantFeature.STORABLE: {"lagerfähig"},
    PlantFeature.OVERWINTERABLE: {"überwinterbar"},
    PlantFeature.WINTER_HARDY: {"winterhart"},
    PlantFeature.RED: {"rot"},
    PlantFeature.YELLOW: {"gelb", "goldgelb"},
    PlantFeature.ORANGE: {"orange"},
    PlantFeature.GREEN: {"grün", "dunkelgrün"},
    PlantFeature.PURPLE: {"violett", "lila", "purpur"},
    PlantFeature.BLACK: {"schwarz"},
    PlantFeature.WHITE: {"weiß", "weiss"},
    PlantFeature.PINK: {"rosa", "pink"},
    PlantFeature.PEAR_SHAPED: {
        "birnenförmig",
        "birnenform",
        "birnchenform",
    },
}


POSITIVE_CHECKBOX_FIELDS: dict[PlantFeature, tuple[str, ...]] = {
    PlantFeature.BALCONY: ("Balkon / Topf",),
    PlantFeature.GREENHOUSE: ("Gewächshaus / unter Dach", "Geschützter Standort"),
    PlantFeature.ROBUST: ("Robust/Resistent",),
    PlantFeature.CLIMBING: ("Rankend",),
    PlantFeature.WARM_LOCATION: ("Warmer Standort",),
    PlantFeature.DROUGHT_TOLERANT: ("Trockenheitsverträglich",),
    PlantFeature.OVERWINTERABLE: ("Überwinterbar",),
    PlantFeature.WINTER_HARDY: ("Winterhart",),
}
