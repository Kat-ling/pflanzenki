"""Adversarial near-neighbours of the real catalogue acceptance examples."""
import pytest

from app.advisor.local_selection import evaluate
from app.ai.dialogue_models import Expression
from app.importer.catalogue_facts import build_bundle
from app.importer.csv_importer import row_to_plant


@pytest.mark.parametrize("key,description,expected", [
    ("taste.sweet", "Sehr süße Früchte, muss nicht ausgegeizt werden.", "yes"),
    ("taste.sweet", "Nicht süße Früchte, muss ausgegeizt werden.", "no"),
    ("taste.sweet", "Nicht mehr süß sondern scharf.", "no"),
    ("taste.sweet", "Nicht nur süß sondern auch aromatisch.", "unknown"),
    ("taste.spicy", "Ohne Schärfe, süß und knackig.", "no"),
    ("taste.spicy", "Nicht ohne Schärfe.", "unknown"),
    ("site.outdoor", "Nur für das Freiland geeignet!", "yes"),
    ("site.outdoor", "Nur bedingt für das Freiland geeignet.", "unknown"),
    ("site.outdoor", "Nicht für das Freiland geeignet.", "no"),
    ("site.uncovered", "Wenn es trocken bleibt, wird ohne Regenschutz angebaut.", "unknown"),
    ("site.uncovered", "Falls es trocken bleibt, wird ohne Regenschutz angebaut.", "unknown"),
    ("site.uncovered", "Solange es trocken bleibt, wird ohne Regenschutz angebaut.", "unknown"),
    ("site.container", "Nicht für Töpfe geeignet.", "unknown"),
    ("use.pickling", "Früchte dürfen nicht eingelegt werden.", "no"),
    ("use.pickling", "Früchte können vielleicht eingelegt werden.", "unknown"),
    ("fruit.thin_skin", "Nicht dünnschalige Früchte.", "no"),
    ("fruit.thin_skin", "Früchte mit nur teilweise dünner Schale.", "unknown"),
    ("fruit.thin_skin", "Eine dicke Schale.", "no"),
])
def test_scope_and_negations(key, description, expected):
    bundle = build_bundle([row_to_plant({"Name": "Probe", "Beschreibung": description})])
    expression = Expression(op="predicate", text=key, property_id=key, comparator="eq", value=True, unit=None, children=[])
    result = evaluate(expression, bundle.plants[0], {d.property_id: d for d in bundle.registry})
    assert result["status"] == expected
    assert all(s["text"] == description for s in result["sources"])
