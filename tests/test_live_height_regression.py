from pathlib import Path
"""Offline regressions discovered while reviewing the real model test."""
import pytest

from app.advisor.local_selection import evaluate
from app.ai.dialogue_models import Expression
from app.importer.catalogue_facts import build_bundle, source_is_valid
from app.importer.csv_importer import row_to_plant
from app.repository import load_plants


def height_result(plants):
    bundle = build_bundle(plants)
    node = Expression(op="predicate", text="Höchstens 80 cm", property_id="plant.height",
                      comparator="lte", value=80, unit="cm", children=[])
    registry = {d.property_id: d for d in bundle.registry}
    for prepared in bundle.plants:
        assert all(source_is_valid(f.source, prepared.source_fields) for f in prepared.facts)
        yield evaluate(node, prepared, registry)


@pytest.mark.parametrize("name", ["Taubenherz", "Strubelpeter", "Flashy Butter Oak", "Filderkraut"])
def test_real_imported_dimensions_do_not_certify_height(name):
    plant = next(p for p in load_plants(Path(__file__).parent / "fixtures/catalogue_legacy.json") if p.name == name)
    result = next(height_result([plant]))
    assert result["status"] == "unknown"
    assert "Woas I ned." in result["reason"]
    assert any(s["text"] == plant.description for s in result["sources"])


@pytest.mark.parametrize("description,height,expected", [
    ("Pflanzabstand 40 x 40 cm.", "40", "unknown"),
    ("Die Früchte sind 7 cm groß.", "7", "unknown"),
    ("Wird bis 70 cm hoch. Pflanzabstand 40 cm.", "70", "yes"),
    ("Die Früchte sind 7 cm groß.", "70", "yes"),
])
def test_dimension_collision_is_conservative(description, height, expected):
    plant = row_to_plant({"Name": "Probe", "Beschreibung": description, "Wuchshöhe_bis_cm": height})
    assert next(height_result([plant]))["status"] == expected
