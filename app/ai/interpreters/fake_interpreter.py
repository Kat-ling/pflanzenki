from __future__ import annotations

from app.ai.query_models import (
    ParsedQuery,
    PlantFeature,
    PlantRequirement,
    QueryIntent,
    RequirementImportance,
    RequirementValue,
)


CATEGORY_TERMS = {
    "Tomate": ("tomate", "tomaten"),
    "Paprika": ("paprika",),
    "Chili": ("chili", "chilis"),
    "Peperoni": ("peperoni",),
    "Gurke": ("gurke", "gurken"),
    "Zucchini": ("zucchini",),
    "Kürbis": ("kürbis", "kuerbis", "kürbisse"),
    "Aubergine": ("aubergine", "auberginen"),
    "Salat": ("salat", "salate"),
    "Basilikum": ("basilikum",),
    "Bohne": ("bohne", "bohnen"),
    "Kohlrabi": ("kohlrabi",),
    "Mangold": ("mangold",),
}


FEATURE_TERMS = {
    PlantFeature.OUTDOOR_UNCOVERED: (
        "ohne dach", "ohne regenschutz", "ungeschützt",
        "ungeschuetzt", "freiland",
    ),
    PlantFeature.BALCONY: ("balkon", "terrasse", "topf", "kübel"),
    PlantFeature.GREENHOUSE: ("gewächshaus", "gewaechshaus", "folientunnel", "unter dach"),
    PlantFeature.SWEET: ("süß", "suess", "süss"),
    PlantFeature.AROMATIC: ("aromatisch", "würzig"),
    PlantFeature.MILD: ("mild",),
    PlantFeature.SPICY: ("scharf", "feurig"),
    PlantFeature.EASY_CARE: ("pflegeleicht", "unkompliziert", "anfänger"),
    PlantFeature.EARLY: ("früh", "frühe ernte"),
    PlantFeature.LATE: ("spät", "späte ernte"),
    PlantFeature.SAUCE: ("soße", "sosse", "sauce", "passata", "einkochen"),
    PlantFeature.FRESH_EATING: ("frischverzehr", "naschen", "rohkost", "snack"),
    PlantFeature.ROBUST: ("robust", "resistent", "widerstandsfähig"),
    PlantFeature.HIGH_YIELD: ("ertragreich", "hoher ertrag"),
    PlantFeature.SMALL_FRUIT: ("kleine früchte", "cocktail", "snack"),
    PlantFeature.COMPACT: ("kompakt", "kleinbleibend", "buschig"),
    PlantFeature.CLIMBING: ("rankend", "kletternd"),
    PlantFeature.DROUGHT_TOLERANT: ("trockenheitsverträglich", "wenig wasser"),
    PlantFeature.SUNNY: ("sonnig", "sonne"),
    PlantFeature.PARTIAL_SHADE: ("halbschatten",),
    PlantFeature.STORABLE: ("lagerfähig", "haltbar"),
    PlantFeature.WINTER_HARDY: ("winterhart",),
    PlantFeature.RED: ("rot", "rote"),
    PlantFeature.YELLOW: ("gelb", "gelbe"),
    PlantFeature.ORANGE: ("orange",),
    PlantFeature.GREEN: ("grün", "gruene", "grüne"),
    PlantFeature.PEAR_SHAPED: (
        "birnenförmig",
        "birnen- förmig",
        "birnen-förmig",
        "birnenfoermig",
    ),
}


class FakeQueryInterpreter:
    """Lokaler, einfacher Interpreter für Entwicklung und Tests."""

    def interpret(self, question: str) -> ParsedQuery:
        cleaned_question = question.strip()
        if not cleaned_question:
            raise ValueError("Die Kundenfrage darf nicht leer sein.")

        normalized = cleaned_question.casefold()
        category = next(
            (
                category_name
                for category_name, terms in CATEGORY_TERMS.items()
                if any(term in normalized for term in terms)
            ),
            "",
        )

        requirements: list[PlantRequirement] = []
        for feature, terms in FEATURE_TERMS.items():
            matched = next((term for term in terms if term in normalized), None)
            if not matched:
                continue

            importance = (
                RequirementImportance.REQUIRED
                if feature in {
                    PlantFeature.OUTDOOR_UNCOVERED,
                    PlantFeature.BALCONY,
                    PlantFeature.GREENHOUSE,
                }
                else RequirementImportance.PREFERRED
            )
            requirements.append(PlantRequirement(
                feature=feature,
                value=RequirementValue.YES,
                importance=importance,
                reason=f"Die Frage enthält „{matched}“.",
            ))

        if "nicht scharf" in normalized or "ohne schärfe" in normalized:
            requirements = [
                item
                for item in requirements
                if item.feature != PlantFeature.SPICY
            ]
            requirements.append(PlantRequirement(
                feature=PlantFeature.SPICY,
                value=RequirementValue.NO,
                importance=RequirementImportance.PREFERRED,
                reason="Eine nicht scharfe Sorte wird gewünscht.",
            ))

        is_catalog_question = (
            category
            and not requirements
            and any(
                phrase in normalized
                for phrase in (
                    "gibt es",
                    "gibt's",
                    "habt ihr",
                    "welche sorten",
                    "welche zucchini-sorten",
                )
            )
        )
        intent = (
            QueryIntent.CATALOG
            if is_catalog_question
            else QueryIntent.RECOMMENDATION
        )

        follow_up_question = ""
        if category and not requirements and not is_catalog_question:
            follow_up_question = (
                "Wo soll die Pflanze wachsen: im Freiland, "
                "im Gewächshaus oder auf dem Balkon?"
            )

        return ParsedQuery(
            original_question=cleaned_question,
            intent=intent,
            category=category,
            plant_names=[],
            requirements=requirements,
            follow_up_question=follow_up_question,
            unsupported_requests=[],
        )
