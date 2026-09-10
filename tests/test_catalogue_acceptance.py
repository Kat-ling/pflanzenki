from pathlib import Path
"""Offline acceptance of manually reviewed question/plant pairs."""
import pytest

from app.advisor.local_selection import evaluate, validate_expression
from app.ai.dialogue_models import Expression
from app.importer.catalogue_facts import build_bundle
from app.repository import load_plants
from catalogue_acceptance_cases import CASES


@pytest.fixture(scope="module")
def catalogue():
    plants = load_plants(Path(__file__).parent / "fixtures/catalogue_legacy.json")
    bundle = build_bundle(plants)
    return {p.name: (p, f) for p, f in zip(plants, bundle.plants)}, {d.property_id: d for d in bundle.registry}


@pytest.mark.parametrize("case_id,question,expression,targets", CASES, ids=[c[0] for c in CASES])
def test_reviewed_catalogue_case(catalogue, case_id, question, expression, targets):
    by_name, registry = catalogue
    expr = Expression.model_validate(expression)
    validate_expression(expr, registry)
    for name, expected, quote, reason in targets:
        plant, prepared = by_name[name]
        assert quote in plant.description, f"Originalquelle geändert: {name}"
        result = evaluate(expr, prepared, registry)
        assert result["status"] == expected, f"{case_id}: {question} / {name}: {reason}; tatsächlich {result}"


@pytest.mark.parametrize("name,quote", [
    ("Zebrino", "Ergebnis steht allerdings noch aus"),
    ("Little Brinjal", "geschützt im Freiland"),
    ("Blaukönigin", "vierwöchiger Folienbedeckung"),
])
def test_additional_catalogue_caveats(catalogue, name, quote):
    # Found during review of changed decisions outside the original 44 pairs.
    by_name, registry = catalogue
    plant, prepared = by_name[name]
    assert quote in plant.description
    expr = Expression(op="predicate", text="uneingeschränkt Freiland", property_id="site.outdoor",
                      comparator="eq", value=True, unit=None, children=[])
    assert evaluate(expr, prepared, registry)["status"] == "unknown"
