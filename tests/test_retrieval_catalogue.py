"""Search behaviour must hold for the complete catalogue, whatever it contains."""
from collections import Counter
from types import SimpleNamespace

import pytest

from app.advisor.retrieval import retrieve
from app.repository import load_plants

PLANTS = load_plants()
BY_ID = {p.id: p for p in PLANTS}
COUNTS = Counter(p.category for p in PLANTS if p.category)


def categories(question, history=(), visible=()):
    return Counter(BY_ID[c["plant_id"]].category for c in retrieve(PLANTS, question, history, visible))


def names(question):
    return [BY_ID[c["plant_id"]].name for c in retrieve(PLANTS, question, [])]


@pytest.mark.parametrize("category", sorted(COUNTS))
def test_every_category_is_found(category):
    expected = min(COUNTS[category], 24)
    found = [BY_ID[c["plant_id"]].category for c in retrieve(PLANTS, f"Welche {category} gibt es?", [])]
    assert found[:expected] == [category] * expected


@pytest.mark.parametrize("question, category", [
    ("Melanzani", "Aubergine"), ("Paradeiser für den Balkon", "Tomate"), ("Pepperoni", "Peperoni"),
    ("Welche Cocktailtomaten gibt es?", "Tomate"), ("Ich suche Buschbohnen", "Bohne"),
    ("Salatgurken bitte", "Gurke"), ("Kapuzinerkresse für den Topf", "Kresse"),
])
def test_synonyms_and_compound_words_reach_the_category(question, category):
    assert BY_ID[retrieve(PLANTS, question, [])[0]["plant_id"]].category == category


def test_compound_uses_the_last_word_part():
    found = categories("Welche Salattomaten gibt es?")
    assert found["Tomate"] == 24 and found["Salat"] == 0


@pytest.mark.parametrize("question, field, category", [
    ("Ich suche eine Tomate für den Balkon", "Balkon / Topf", "Tomate"),
    ("Welche Paprika passt auf den Balkon?", "Balkon / Topf", "Paprika"),
    ("Tomate fürs Gewächshaus", "Gewächshaus / unter Dach", "Tomate"),
    ("Gurke für das Gewächshaus", "Gewächshaus / unter Dach", "Gurke"),
])
def test_ticked_catalogue_fields_are_searchable(question, field, category):
    expected = {p.id for p in PLANTS if p.category == category and p.raw_fields.get(field) == "Yes"}
    found = {c["plant_id"] for c in retrieve(PLANTS, question, [])}
    assert len(expected & found) == min(len(expected), 24)


def test_filler_words_do_not_decide_the_result():
    assert names("Was ist mit Quatschwort?") == []


def test_more_results_are_not_the_ones_already_shown():
    first = retrieve(PLANTS, "Tomate fürs Gewächshaus", [])[:4]
    visible = [{"plant_id": c["plant_id"], "name": ""} for c in first]
    history = [SimpleNamespace(role="user", content="Tomate fürs Gewächshaus")]
    following = {c["plant_id"] for c in retrieve(PLANTS, "Gibt es noch weitere?", history, visible)}
    assert following
    assert not following & {v["plant_id"] for v in visible}
    assert categories("Gibt es noch weitere?", history, visible).most_common(1)[0][0] == "Tomate"


def test_more_results_stay_with_the_latest_topic():
    # Live test: after tomatoes, then peppers, "weitere" jumped back to tomatoes.
    history = [SimpleNamespace(role="user", content="Ich möchte eine Cocktailtomate ohne Regenschutz anbauen."),
               SimpleNamespace(role="assistant", content="Antwort"),
               SimpleNamespace(role="user", content="Welche Paprika ist nicht scharf?"),
               SimpleNamespace(role="assistant", content="Antwort")]
    found = categories("Gibt es noch weitere?", history)
    assert found["Paprika"] == COUNTS["Paprika"]
    assert found["Tomate"] == 0


def test_explicit_topic_change_beats_the_history():
    history = [SimpleNamespace(role="user", content="Welche Paprika ist nicht scharf?")]
    assert categories("Und bei Zucchini?", history).most_common(1)[0][0] == "Zucchini"


def test_comparing_shown_varieties_keeps_them():
    first = retrieve(PLANTS, "Zucchini gelb", [])[:2]
    visible = [{"plant_id": c["plant_id"], "name": ""} for c in first]
    found = {c["plant_id"] for c in retrieve(PLANTS, "Vergleiche die beiden", [], visible)}
    assert {v["plant_id"] for v in visible} <= found
