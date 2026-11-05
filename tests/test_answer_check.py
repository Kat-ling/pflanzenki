"""A model recommendation must survive the catalogue facts before it is shown."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.advisor.answer_check import contradictions
from app.advisor.local_selection import prepare_catalogue
from app.ai.catalogue_answer import CatalogueAnswer, consult
from app.ai.interpreters.openai_interpreter import OpenAIQueryInterpreter
from app.importer.catalogue_facts import build_bundle
from app.importer.csv_importer import row_to_plant
from app.repository import load_plants
from catalogue_acceptance_cases import CASES

DESCRIPTION = "Beschreibung"
NO_RAIN_SHELTER = dict(op="predicate", text="ohne Regenschutz", property_id="site.uncovered",
                       comparator="eq", value=True, unit=None, children=[])


def plant(name="Probe", description="Kleine Früchte. Anbau mit Regenschutz erforderlich.", **fields):
    return row_to_plant({"Name": name, "Kategorie": "Tomate", DESCRIPTION: description, **fields})


def condition(expression=NO_RAIN_SHELTER, importance="required", kind="condition"):
    return dict(text=expression["text"], importance=importance, kind=kind, expression=expression)


def llm(plants, conditions=(), answer="Hier ist eine Auswahl.", suitability="matches", source="s2"):
    output = dict(understood_request="Tomate", answer=answer, follow_up_question="",
                  conditions=list(conditions),
                  plants=[dict(plant_id=p.id, explanation="Passt.", source_ids=[source],
                               suitability=suitability) for p in plants])
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(status="completed", output_text=json.dumps(output))

    client = SimpleNamespace(responses=SimpleNamespace(create=create))
    return OpenAIQueryInterpreter(client=client, model="offline", categories=["Tomate"]), calls


def ask(plants, **options):
    interpreter, _ = llm(plants, **options)
    return consult(interpreter, plants, "Tomate ohne Regenschutz", [])


def test_contradicted_variety_is_never_recommended():
    result = ask([plant()], conditions=[condition()])
    assert result["recommendations"] == [] and result["total_matches"] == 0
    assert [card["plant_name"] for card in result["excluded"]] == ["Probe"]


def test_contradiction_shows_the_counter_evidence():
    check = ask([plant()], conditions=[condition()])["excluded"][0]["checks"][0]
    assert check["status"] == "no"
    assert check["criterion"] == "ohne Regenschutz"
    assert "Regenschutz erforderlich" in check["reason"]


def test_answer_explains_that_varieties_were_sorted_out():
    fitting = plant("Andere", "Kann problemlos ohne Regenschutz angebaut werden.")
    result = ask([plant(), fitting], conditions=[condition()])
    assert [card["plant_name"] for card in result["recommendations"]] == ["Andere"]
    assert "1 Sorte" in result["answer"]


def test_contradicted_uncertain_variety_is_sorted_out_too():
    result = ask([plant()], conditions=[condition()], suitability="uncertain")
    assert result["unknown"] == [] and len(result["excluded"]) == 1


def test_contradicted_wish_does_not_exclude():
    result = ask([plant()], conditions=[condition(importance="preferred")])
    assert len(result["recommendations"]) == 1


def test_missing_fact_keeps_the_model_reading_of_the_text():
    sweet = dict(op="predicate", text="süß", property_id="taste.sweet", comparator="eq",
                 value=True, unit=None, children=[])
    result = ask([plant(description="Kleine Früchte.")], conditions=[condition(sweet)])
    assert len(result["recommendations"]) == 1


BALCONY = dict(op="predicate", text="für den Balkon", property_id="site.container",
               comparator="eq", value=True, unit=None, children=[])


def test_site_suitability_needs_evidence_in_the_catalogue():
    # Live test: the model inferred balcony use from plant height.
    low = plant("Niedrig", "Handliche Schoten.", **{"Wuchshöhe_bis_cm": "40", "Balkon / Topf": "No"})
    result = ask([low], conditions=[condition(BALCONY)], answer="Passt gut auf den Balkon.")
    assert result["recommendations"] == []
    assert result["unknown"][0]["checks"][0]["reason"] == "Im Katalog nicht belegt: für den Balkon"
    assert result["answer"].startswith("Für diese Anfrage kann ich keine belegte Sorte empfehlen.")


def test_ticked_site_field_is_evidence():
    fitting = plant("Topfsorte", "Handliche Schoten.", **{"Balkon / Topf": "Yes"})
    assert len(ask([fitting], conditions=[condition(BALCONY)])["recommendations"]) == 1


def test_site_condition_inside_an_and_group_counts():
    group = dict(op="all", text="Balkon und süß", property_id="", comparator="eq", value=None, unit=None,
                 children=[BALCONY, {**BALCONY, "text": "süß", "property_id": "taste.sweet"}])
    assert ask([plant(description="Text.")], conditions=[condition(group)])["recommendations"] == []


def test_site_alternatives_are_not_each_required():
    group = dict(op="any", text="Balkon oder Gewächshaus", property_id="", comparator="eq", value=None, unit=None,
                 children=[BALCONY, {**BALCONY, "text": "Haus", "property_id": "site.greenhouse_or_roof"}])
    fitting = plant("Haus", "Text.", **{"Gewächshaus / unter Dach": "Yes"})
    assert len(ask([fitting], conditions=[condition(group)])["recommendations"]) == 1


def test_a_site_wish_stays_a_wish():
    result = ask([plant(description="Text.")], conditions=[condition(BALCONY, importance="preferred")])
    assert len(result["recommendations"]) == 1


def test_partly_unproven_answer_says_so():
    fitting = plant("Topfsorte", "Text.", **{"Balkon / Topf": "Yes"})
    result = ask([fitting, plant("Ohne", "Text.")], conditions=[condition(BALCONY)])
    assert [c["plant_name"] for c in result["recommendations"]] == ["Topfsorte"]
    assert "1 Sorte ist nicht eindeutig belegt." in result["answer"]


def test_technical_property_names_never_reach_the_reader():
    shown = {**NO_RAIN_SHELTER, "text": "Paprika ohne Schärfe (taste.spicy = false)"}
    result = ask([plant()], conditions=[condition(shown)])
    assert result["excluded"][0]["checks"][0]["criterion"] == "Paprika ohne Schärfe"
    assert result["criteria"][0]["text"] == "Paprika ohne Schärfe"


def test_unknown_property_keeps_the_recommendation():
    unknown = {**NO_RAIN_SHELTER, "property_id": "gibt.es.nicht"}
    result = ask([plant()], conditions=[condition(unknown)])
    assert len(result["recommendations"]) == 1 and result["warnings"] == []


@pytest.mark.parametrize("broken", [
    {**NO_RAIN_SHELTER, "value": "ja"},
    {**NO_RAIN_SHELTER, "comparator": "exists", "value": None},
])
def test_uncheckable_condition_is_disclosed(broken):
    result = ask([plant()], conditions=[condition(broken)])
    assert len(result["recommendations"]) == 1
    assert any("nicht lokal geprüft" in warning for warning in result["warnings"])


def test_information_requests_are_not_conditions():
    exists = {**NO_RAIN_SHELTER, "comparator": "exists", "value": None}
    result = ask([plant()], conditions=[condition(exists, kind="information")], suitability="information")
    assert len(result["recommendations"]) == 1 and result["warnings"] == []


@pytest.mark.parametrize("source", ["s0", "s1"])
def test_name_or_category_alone_is_no_evidence_for_a_condition(source):
    result = ask([plant(description="Kleine Früchte.")], conditions=[condition()], source=source)
    assert result["recommendations"] == []
    assert result["unknown"][0]["checks"][0]["status"] == "unknown"


def test_category_is_enough_for_a_plain_listing():
    result = ask([plant()], source="s1", suitability="information")
    assert len(result["recommendations"]) == 1


def test_answer_text_must_not_praise_a_rejected_variety():
    result = ask([plant()], conditions=[condition()], answer="Probe passt perfekt.")
    assert "Probe" not in result["answer"].replace("Probe:", "")
    assert "passt perfekt" not in result["answer"]


def test_answer_text_must_not_name_varieties_without_a_card():
    other = plant("Unbelegt", "Text.")
    shown = plant("Gezeigt", "Kleine Früchte.")
    interpreter, _ = llm([shown], answer="Unbelegt wäre auch toll.")
    result = consult(interpreter, [shown, other], "Tomate", [])
    assert "Unbelegt" not in result["answer"]


def test_answer_text_may_name_shown_varieties():
    result = ask([plant("Gezeigt", "Kleine Früchte.")], answer="Gezeigt passt gut.")
    assert result["answer"] == "Gezeigt passt gut."


def test_conditions_are_kept_for_the_next_question():
    result = ask([plant(description="Kleine Früchte.")], conditions=[condition()])
    assert [c["text"] for c in result["criteria"]] == ["ohne Regenschutz"]


def test_model_receives_the_checkable_properties():
    plants = [plant()]
    interpreter, calls = llm(plants)
    consult(interpreter, plants, "Tomate", [])
    properties = {p["property_id"] for p in json.loads(calls[0]["input"])["available_properties"]}
    assert "site.uncovered" in properties and len(calls) == 1
    assert "conditions" in calls[0]["instructions"]


def test_answer_schema_satisfies_strict_mode():
    schema = CatalogueAnswer.model_json_schema()

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False
                assert set(node["required"]) == set(node["properties"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(schema)
    assert "conditions" in schema["required"]


LEGACY = load_plants(Path(__file__).parent / "fixtures/catalogue_legacy.json")
BUNDLE = build_bundle(LEGACY)
PREPARED = {p.name: f for p, f in zip(LEGACY, BUNDLE.plants)}
REGISTRY = {d.property_id: d for d in BUNDLE.registry}
REVIEWED = [(case_id, name, expected, expression) for case_id, _, expression, targets in CASES
            for name, expected, _, _ in targets]


@pytest.mark.parametrize("case_id,name,expected,expression", REVIEWED,
                         ids=[f"{r[0]}-{r[1]}" for r in REVIEWED])
def test_reviewed_pairs_are_vetoed_exactly_when_contradicted(case_id, name, expected, expression):
    from app.ai.dialogue_models import Criterion
    criterion = Criterion.model_validate(dict(text="Bedingung", importance="required", kind="condition",
                                              expression=expression))
    assert bool(contradictions([criterion], PREPARED[name], REGISTRY)) == (expected == "no")


def test_veto_works_with_the_real_catalogue():
    plants = load_plants()
    variety = next(p for p in plants if p.name == "Justens Zuckertomate")
    interpreter, _ = llm([variety], conditions=[condition()])
    result = consult(interpreter, plants, "Justens Zuckertomate ohne Regenschutz", [])
    assert [card["plant_name"] for card in result["excluded"]] == ["Justens Zuckertomate"]
    assert "Regenschutz erforderlich" in result["excluded"][0]["checks"][0]["reason"]


def unresolved(text="Eignung laut Quellen"):
    return dict(op="unresolved", text=text, property_id="", comparator="eq", value=None, unit=None, children=[])


def wished(expression, text):
    return dict(text=text, importance="required", kind="condition", expression=expression)


def test_unmapped_balcony_condition_still_needs_evidence():
    # Second live test: the model kept the balcony as required but left it unresolved.
    low = plant("Niedrig", "Handliche Schoten.", **{"Wuchshöhe_bis_cm": "40"})
    result = ask([low], conditions=[wished(unresolved(), "passt auf den Balkon/Topf")])
    assert result["recommendations"] == []
    assert result["unknown"][0]["checks"][0]["reason"] == "Im Katalog nicht belegt: passt auf den Balkon/Topf"


def test_half_mapped_balcony_alternative_still_needs_evidence():
    group = dict(op="any", text="Balkon oder Beschreibung", property_id="", comparator="eq", value=None, unit=None,
                 children=[BALCONY, unresolved()])
    result = ask([plant("Niedrig", "Handliche Schoten.")], conditions=[wished(group, "passt auf den Balkon")])
    assert result["recommendations"] == []


def test_unmapped_balcony_condition_accepts_catalogue_evidence():
    fitting = plant("Topfsorte", "Handliche Schoten.", **{"Balkon / Topf": "Yes"})
    conditions = [wished(unresolved(), "passt auf den Balkon/Topf")]
    assert len(ask([fitting], conditions=conditions)["recommendations"]) == 1


def test_a_refused_site_is_not_turned_into_a_site_requirement():
    result = ask([plant("Beet", "Handliche Schoten.")], conditions=[wished(unresolved(), "nicht für den Balkon")])
    assert len(result["recommendations"]) == 1


def test_other_unmapped_wishes_stay_unchecked():
    result = ask([plant("Andere", "Handliche Schoten.")], conditions=[wished(unresolved(), "gute Lagerfähigkeit")])
    assert len(result["recommendations"]) == 1
