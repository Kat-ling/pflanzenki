from app.advisor.engine import advise, resolve_feature
from app.ai.query_models import (
    ParsedQuery,
    PlantFeature,
    PlantRequirement,
    RequirementImportance,
    RequirementValue,
    QueryIntent,
)
from app.importer.csv_importer import row_to_plant
from app.models.domain import ConfidenceLevel, SourceType, TruthValue


def requirement(
    feature: PlantFeature = PlantFeature.OUTDOOR_UNCOVERED,
    value: RequirementValue = RequirementValue.YES,
    importance: RequirementImportance = RequirementImportance.REQUIRED,
) -> PlantRequirement:
    return PlantRequirement(
        feature=feature,
        value=value,
        importance=importance,
        reason="Testanforderung",
    )


def query(
    *requirements: PlantRequirement,
    category: str = "",
    follow_up_question: str = "",
) -> ParsedQuery:
    return ParsedQuery(
        original_question="Testfrage",
        category=category,
        requirements=list(requirements),
        follow_up_question=follow_up_question,
    )


def outdoor_plant(
    name: str,
    description: str,
    category: str = "Tomate",
):
    return row_to_plant(
        {
            "Sorte": name,
            "Kategorie": category,
            "Regenschutz": "",
            "Beschreibung": description,
        }
    )


def test_description_wins_over_conflicting_structured_field():
    plant = row_to_plant(
        {
            "Sorte": "Widerspruch",
            "Regenschutz": "ja",
            "Beschreibung": (
                "Diese Sorte wächst im ungeschützten "
                "Freiland problemlos."
            ),
        }
    )

    result = resolve_feature(plant, "outdoor_uncovered")

    assert result.verdict == TruthValue.YES
    assert result.reasons[0].source == SourceType.DESCRIPTION
    assert result.conflicts
    assert result.confidence == ConfidenceLevel.MEDIUM


def test_description_without_conflict_has_high_confidence():
    plant = outdoor_plant(
        "Freilandsorte",
        "Diese Sorte wächst im ungeschützten Freiland problemlos.",
    )

    result = resolve_feature(plant, "outdoor_uncovered")

    assert result.verdict == TruthValue.YES
    assert result.reasons[0].source == SourceType.DESCRIPTION
    assert not result.conflicts
    assert result.confidence == ConfidenceLevel.HIGH


def test_unknown_required_feature_is_not_excluded():
    plant = outdoor_plant("Unklar", "Sehr süß.")

    result = advise(
        [plant],
        query(requirement()),
    )

    assert not result.excluded
    assert len(result.unknown) == 1
    assert result.unknown[0].confidence == ConfidenceLevel.UNKNOWN


def test_explicit_conflict_with_required_feature_excludes():
    plant = outdoor_plant("Geschützt", "Regenschutz ist notwendig.")

    result = advise(
        [plant],
        query(requirement()),
    )

    assert len(result.excluded) == 1
    assert result.excluded[0].verdict == TruthValue.NO


def test_preference_does_not_exclude():
    plant = outdoor_plant("Geschützt", "Regenschutz ist notwendig.")

    result = advise(
        [plant],
        query(
            requirement(
                importance=RequirementImportance.PREFERRED,
            )
        ),
    )

    assert not result.excluded
    assert len(result.unknown) == 1


def test_negative_requirement_matches_negative_evidence():
    plant = outdoor_plant("Geschützt", "Regenschutz ist notwendig.")

    result = advise(
        [plant],
        query(
            requirement(value=RequirementValue.NO)
        ),
    )

    assert [item.plant_name for item in result.recommendations] == [
        "Geschützt"
    ]


def test_category_limits_advisor_candidates():
    tomato = outdoor_plant(
        "Tomate",
        "Für das ungeschützte Freiland geeignet.",
        category="Tomate",
    )
    cucumber = outdoor_plant(
        "Gurke",
        "Für das ungeschützte Freiland geeignet.",
        category="Gurke",
    )

    result = advise(
        [tomato, cucumber],
        query(requirement(), category="tomate"),
    )

    assert [item.plant_name for item in result.recommendations] == [
        "Tomate"
    ]
    assert not result.unknown
    assert not result.excluded


def test_only_three_recommendations_are_returned():
    plants = [
        outdoor_plant(
            f"Freilandsorte {number}",
            "Für das ungeschützte Freiland geeignet.",
        )
        for number in range(1, 6)
    ]

    result = advise(
        plants,
        query(requirement()),
    )

    assert len(result.recommendations) == 3


def test_follow_up_question_short_circuits_advisor():
    result = advise(
        [],
        query(follow_up_question="Wo soll die Pflanze wachsen?"),
    )

    assert result.intent == "follow_up"
    assert result.answer == "Wo soll die Pflanze wachsen?"
    assert not result.recommendations


def test_query_without_requirements_returns_unknown():
    result = advise([], query())

    assert result.intent == "unknown"
    assert result.answer == "Woas I ned."


def test_information_query_finds_named_plant():
    plant = outdoor_plant(
        "Marketmore",
        "Robuste Gurke für das Freiland.",
        category="Gurke",
    )
    parsed = ParsedQuery(
        original_question="Was weißt du über Marketmore?",
        intent=QueryIntent.INFORMATION,
        plant_names=["Marketmore"],
    )

    result = advise([plant], parsed)

    assert result.intent == "information"
    assert result.recommendations[0].plant_name == "Marketmore"
    assert result.recommendations[0].plant_category == "Gurke"


def test_unknown_named_plant_uses_dialect_fallback():
    parsed = ParsedQuery(
        original_question="Was weißt du über Fantasiepflanze?",
        intent=QueryIntent.INFORMATION,
        plant_names=["Fantasiepflanze"],
    )

    result = advise([], parsed)

    assert result.answer == "Woas I ned."


def test_category_catalog_lists_existing_entries():
    plants = [
        outdoor_plant("Gold Rush", "Gelbe Früchte.", "Zucchini"),
        outdoor_plant("Black Beauty", "Grüne Früchte.", "Zucchini"),
    ]
    parsed = ParsedQuery(
        original_question="Welche Zucchini-Sorten gibt es?",
        intent=QueryIntent.CATALOG,
        category="Zucchini",
    )

    result = advise(plants, parsed)

    assert result.intent == "catalog"
    assert len(result.recommendations) == 2
    assert "2 Einträge" in result.answer


def test_required_unknown_explains_the_data_gap():
    plant = outdoor_plant("Gold Rush", "Gelbe Zucchini.", "Zucchini")
    parsed = query(requirement(), category="Zucchini")

    result = advise([plant], parsed)

    assert result.answer.startswith("Woas I ned.")
    assert "fehlen im Katalog" in result.answer


def test_plain_recommendation_is_not_mistaken_for_catalog_listing():
    plant = outdoor_plant("A", "Leckere Sorte.", "Tomate")
    parsed = ParsedQuery(
        original_question="Wie heißt die unbekannte Tomate?",
        intent=QueryIntent.RECOMMENDATION,
        category="Tomate",
        unsupported_requests=["unbekannte Eigenschaft"],
    )

    result = advise([plant], parsed)

    assert result.answer == "Woas I ned."
    assert not result.recommendations


def test_catalog_listing_is_limited_to_six_cards():
    plants = [
        outdoor_plant(f"Tomate {number}", "Leckere Sorte.", "Tomate")
        for number in range(10)
    ]
    parsed = ParsedQuery(
        original_question="Welche Tomaten gibt es?",
        intent=QueryIntent.CATALOG,
        category="Tomate",
    )

    result = advise(plants, parsed)

    assert len(result.recommendations) == 6
    assert "ersten 6" in result.answer
