import itertools
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.advisor.local_selection import (
    combine, evaluate, prepare_catalogue, validate_expression,
)
from app.ai.catalogue_dialogue import consult
from app.ai.dialogue_models import Criterion, DialoguePlan, Expression
from app.ai.interpreters.openai_interpreter import OpenAIQueryInterpreter
from app.ai.query_interpreter import QueryInterpreterError
from app.importer.catalogue_facts import build_bundle, write_bundle
from app.importer.csv_importer import row_to_plant
from app.main import app


def leaf(key="site.outdoor", value=True, comparator="eq", unit=None, text="Wunsch"):
    return Expression(op="predicate", text=text, property_id=key, comparator=comparator,
                      value=value, unit=unit, children=[])


def group(op, *children):
    return Expression(op=op, text="Kombination", property_id="", comparator="eq",
                      value=None, unit=None, children=list(children))


def check(expr, description="", **fields):
    plant = row_to_plant({"Name": "Test", "Kategorie": "Tomate", "Beschreibung": description, **fields})
    bundle = build_bundle([plant])
    registry = {d.property_id: d for d in bundle.registry}
    validate_expression(expr, registry)
    return evaluate(expr, bundle.plants[0], registry)


def plan(expr, **changes):
    result = dict(intent="recommendation", categories=["Tomate"], plant_names=[],
                  criteria=[Criterion(text=expr.text, importance="required", kind="condition", expression=expr).model_dump()],
                  follow_up_question="", unsupported_requests=[])
    result.update(changes)
    return result


def fake(plan_output):
    calls = []
    def create(**kw):
        calls.append(kw)
        if len(calls) > 1:
            raise AssertionError("Unexpected second model request")
        return SimpleNamespace(status="completed", output_text=json.dumps(plan_output))
    client = SimpleNamespace(responses=SimpleNamespace(create=create))
    return OpenAIQueryInterpreter(client=client, model="test-model", categories=["Tomate"]), calls


@pytest.mark.parametrize("a,b", itertools.product(["yes", "no", "unknown"], repeat=2))
def test_truth_tables(a, b):
    truth = {"yes": True, "no": False, "unknown": None}
    expected_and = "no" if truth[a] is False or truth[b] is False else "yes" if truth[a] is True and truth[b] is True else "unknown"
    expected_or = "yes" if truth[a] is True or truth[b] is True else "no" if truth[a] is False and truth[b] is False else "unknown"
    assert combine("all", [a, b]) == expected_and
    assert combine("any", [a, b]) == expected_or


@pytest.mark.parametrize("a,b", [("yes", "no"), ("no", "yes"), ("unknown", "unknown")])
def test_not_truth_table(a, b):
    assert combine("not", [a]) == b


def test_nested_alternatives_preserve_all_branches_and_sources():
    expr = group("any", group("all", leaf("fruit.color", "rot"), leaf("fruit.small")),
                        group("all", leaf("fruit.color", "gelb"), leaf("fruit.large")))
    result = check(expr, "Große Früchte.", Fruchtfarbe="gelb")
    assert result["status"] == "yes"
    assert len(result["children"]) == 2
    assert {s["field"] for s in result["sources"]} == {"Beschreibung", "Fruchtfarbe"}
    assert check(group("all", expr, leaf("site.uncovered")), "Große Früchte.", Fruchtfarbe="gelb")["status"] == "unknown"


@pytest.mark.parametrize("description,expected", [
    ("Für Freiland geeignet.", "yes"),
    ("Nicht für Freiland geeignet.", "no"),
    ("Für Freiland nur bedingt geeignet.", "unknown"),
    ("Für Freiland geeignet. Nicht für Freiland geeignet.", "unknown"),
    ("Vielleicht für Freiland geeignet.", "unknown"),
])
def test_description_overrides_checkbox_without_hiding_caveats(description, expected):
    result = check(leaf(), description, Freiland="Yes")
    assert result["status"] == expected
    assert result["sources"] == [{"field": "Beschreibung", "text": description}]


def test_freiland_does_not_prove_no_roof_and_unchecked_is_unknown():
    assert check(leaf("site.uncovered"), "Für Freiland geeignet.", Freiland="Yes")["status"] == "unknown"
    assert check(leaf(), Freiland="No")["status"] == "unknown"


@pytest.mark.parametrize("description,expected", [
    ("Ohne Regenschutz geeignet.", "yes"),
    ("Nicht ohne Regenschutz anbauen.", "no"),
    ("Regenschutz erforderlich.", "no"),
    ("Regenschutz ist nicht erforderlich.", "unknown"),
])
def test_roof_context(description, expected):
    assert check(leaf("site.uncovered"), description)["status"] == expected


def test_negative_taste_needs_explicit_evidence():
    expr = leaf("taste.spicy", False)
    assert check(expr)["status"] == "unknown"
    assert check(expr, **{"Schärfegrad MAX": "0"})["status"] == "yes"
    assert check(expr, "Nicht scharf.")["status"] == "yes"
    assert check(expr, "Scharf.")["status"] == "no"
    assert check(expr, "Scharf. Nicht scharf.")["status"] == "unknown"
    assert check(group("not", leaf("taste.spicy")))["status"] == "unknown"


def test_numeric_adjective_is_not_qualitative_large():
    assert check(leaf("fruit.large"), "2 cm große rote Früchte.")["status"] == "unknown"
    assert check(leaf("fruit.large"), "Normalgroße Früchte.")["status"] == "no"
    assert check(leaf("fruit.large"), "Eine Fleischtomate.")["status"] == "unknown"


def test_explicit_no_pruning_is_not_lost_as_generic_negation():
    assert check(leaf("care.no_pruning"), "Die Pflanze wird nicht ausgegeizt.")["status"] == "yes"
    assert check(leaf("care.no_pruning"), "Die Pflanze muss ausgegeizt werden.")["status"] == "no"
    assert check(leaf("care.no_pruning"), "Die Pflanze sollte nur mäßig ausgegeizt werden.")["status"] == "unknown"


def test_wrong_object_is_not_fruit_mass_height_or_color():
    assert check(leaf("fruit.mass", 500, "gte", "g"), "Die Pflanze hat ein Gewicht von 900 g.")["status"] == "unknown"
    assert check(leaf("plant.height", 10, "lte", "cm"), "Die Früchte sind 5 cm hoch.")["status"] == "unknown"
    assert check(leaf("fruit.color", "grün"), "Grüne Blätter und rote Früchte.")["status"] == "unknown"


@pytest.mark.parametrize("height,comparator,target,unit,expected", [
    ("70", "lte", 80, "cm", "yes"),
    ("100", "gt", 80, "cm", "unknown"),
    ("100", "lte", 80, "cm", "unknown"),
    ("70", "gt", 80, "cm", "no"),
    ("70", "lte", .8, "m", "yes"),
    ("0", "lte", 80, "cm", "unknown"),
])
def test_numeric_upper_bounds(height, comparator, target, unit, expected):
    assert check(leaf("plant.height", target, comparator, unit), Wuchshöhe_bis_cm=height)["status"] == expected


def test_numeric_ranges_and_decimal_height():
    assert check(leaf("plant.height", 80, "lte", "cm"), "Wird 60–100 cm hoch.")["status"] == "unknown"
    assert check(leaf("plant.height", 80, "lte", "cm"), "Wird 90–100 cm hoch.")["status"] == "no"
    assert check(leaf("plant.height", 180, "lte", "cm"), "Wird bis 1.8 m hoch.")["status"] == "yes"
    assert check(leaf("fruit.mass", .2, "gte", "kg"), "Die Früchte haben ein Gewicht von 200–300 g.")["status"] == "yes"
    assert check(leaf("fruit.mass", 200, "gt", "g"), "Die Früchte haben ein Gewicht von ca. 500 g.")["status"] == "unknown"
    assert check(leaf("fruit.mass", 100, "gt", "g"), "Früchte mit einem Gewicht bis 200 g.")["status"] == "unknown"
    assert check(leaf("fruit.mass", 300, "gte", "g"), "Die Früchte wiegen mindestens 200 g.")["status"] == "unknown"


@pytest.mark.parametrize("expr", [
    leaf("plant.height", 200, "gte", "g"), leaf("plant.height", True, "eq", "cm"),
    leaf("plant.height", "80", "lte", "cm"), leaf("taste.sweet", "ja"),
    leaf("fruit.color", "rot", "gt"),
])
def test_type_and_unit_mismatch_is_rejected(expr):
    with pytest.raises(ValueError):
        check(expr)


def test_unknown_property_is_visible_unknown_without_enum_change():
    result = check(leaf("fruit.seed_count", 2, "lte"), "Sehr süß.")
    assert result["status"] == "unknown"
    assert "zuordnen" in result["reason"]


def test_tampered_quote_cannot_be_used():
    bundle = build_bundle([row_to_plant({"Name": "A", "Freiland": "Yes"})])
    bundle.plants[0].source_fields["Freiland"] = "No"
    result = evaluate(leaf(), bundle.plants[0], {d.property_id: d for d in bundle.registry})
    assert result["status"] == "unknown"
    assert result["sources"] == []


def test_stale_sidecar_is_rebuilt_locally(tmp_path, monkeypatch):
    from app.advisor import local_selection
    old = row_to_plant({"Name": "A", "Freiland": "Yes"})
    path = tmp_path / "facts.json"
    write_bundle(build_bundle([old]), path)
    before = path.read_bytes()
    monkeypatch.setattr(local_selection, "SIDECAR", path)
    current = row_to_plant({"Name": "A", "Freiland": "No"})
    bundle = prepare_catalogue([current])
    assert not bundle.plants[0].facts
    assert path.read_bytes() == before


def test_legacy_local_consult_preserves_state_and_images():
    p = row_to_plant({"Name": "A", "Kategorie": "Tomate", "Beschreibung": "Für Freiland geeignet.", "Bild": "a.jpg"})
    output = plan(leaf())
    llm, calls = fake(output)
    history = [{"role": "user", "content": "Tomaten"}, {"role": "assistant", "content": "Freiland?"}]
    from app.ai.dialogue_models import ChatMessage
    result = consult(llm, [p], "Ja, die erste", [ChatMessage(**m) for m in history],
                     DialoguePlan.model_validate(output), [{"plant_id": p.id, "name": p.name}])
    assert result["selection_mode"] == "local"
    assert result["plan"] == output
    assert result["recommendations"][0]["image_filenames"] == ["a.jpg"]
    assert result["recommendations"][0]["catalogue_fields"]["Beschreibung"] == p.description
    assert len(calls) == 1 and calls[0]["max_output_tokens"] == 4000
    sent = json.loads(calls[0]["input"])
    assert sent["previous_plan"] == output and sent["history"] == history
    assert sent["visible_plants"] == [{"plant_id": p.id, "name": p.name}]
    assert p.description not in calls[0]["input"]


def test_invalid_visible_id_fails_before_model_call(monkeypatch):
    llm, calls = fake(plan(leaf()))
    monkeypatch.setattr("app.main.create_query_interpreter", lambda: llm)
    response = TestClient(app).post("/api/ask", json={"question": "Die zweite", "visible_plant_ids": ["invented"]})
    assert response.status_code == 400
    assert calls == []


def test_invalid_plan_has_no_fallback_or_retry():
    llm, calls = fake(plan(leaf("plant.height", 80, "lte", "g")))
    with pytest.raises(QueryInterpreterError):
        consult(llm, [row_to_plant({"Name": "A", "Kategorie": "Tomate"})], "80 cm", [])
    assert len(calls) == 1


def test_expression_limits_and_empty_boolean_groups():
    with pytest.raises(ValidationError):
        group("any")
    node = leaf()
    for _ in range(6):
        node = group("not", node)
    with pytest.raises(ValidationError):
        DialoguePlan.model_validate(plan(node))
    too_many = plan(group("all", *[leaf() for _ in range(20)]))
    too_many["criteria"] *= 2
    with pytest.raises(ValidationError):
        DialoguePlan.model_validate(too_many)


def test_information_can_report_negative_fact_but_not_conflict():
    expr = leaf("site.outdoor", None, "exists")
    assert check(expr, "Nicht für Freiland geeignet.")["status"] == "yes"
    assert check(expr, "Für Freiland geeignet. Nicht für Freiland geeignet.")["status"] == "unknown"


def test_full_catalogue_is_local_even_with_twenty_conditions():
    from app.repository import load_plants
    expr = group("all", *[leaf("taste.sweet") for _ in range(20)])
    output = plan(expr, categories=[])
    llm, calls = fake(output)
    plants = load_plants()
    result = consult(llm, plants, "Alle passenden Sorten", [])
    assert sum(len(result[k]) for k in ["recommendations", "unknown", "excluded"]) == len(plants)
    assert len(calls) == 1


@pytest.mark.parametrize("key,field,description", [
    ("plant.winter_hardy", "Winterhart", "Nicht winterhart."),
    ("care.drought_tolerant", "Trockenheitsverträglich", "Nicht trockenheitsverträglich."),
    ("plant.climbing", "Rankend", "Nicht rankend."),
])
def test_other_checkbox_conflicts_are_checked(key, field, description):
    assert check(leaf(key), description, **{field: "Yes"})["status"] == "no"


def test_transport_disables_retries_and_logs_only_safe_metadata(caplog):
    import httpx
    from openai import OpenAI
    from app.ai.catalogue_dialogue import request_structured
    requests = []
    def handle(request):
        requests.append(request)
        assert request.extensions["timeout"]["read"] == 30.0
        return httpx.Response(429, json={"error": {"message": "private error body", "type": "rate_limit"}})
    with OpenAI(api_key="test-key", http_client=httpx.Client(transport=httpx.MockTransport(handle))) as client:
        llm = OpenAIQueryInterpreter(client=client, model="test-model", categories=[])
        with caplog.at_level("INFO", logger="uvicorn.error.pflanzenki.requests"):
            with pytest.raises(QueryInterpreterError):
                request_structured(llm, "", {"question": "private customer text"}, DialoguePlan)
    assert len(requests) == 1
    assert "RateLimitError" in caplog.text
    assert "private error body" not in caplog.text
    assert "private customer text" not in caplog.text
    assert "test-key" not in caplog.text


def test_customer_correction_replaces_plan_and_does_not_accumulate_old_size():
    old = DialoguePlan.model_validate(plan(leaf("fruit.large")))
    output = plan(leaf("fruit.small"))
    llm, calls = fake(output)
    p = row_to_plant({"Name": "A", "Kategorie": "Tomate", "Beschreibung": "Kleine Früchte."})
    result = consult(llm, [p], "Doch lieber kleine Früchte", [], previous_plan=old)
    assert result["total_matches"] == 1
    assert result["plan"]["criteria"][0]["expression"]["property_id"] == "fruit.small"
    assert json.loads(calls[0]["input"])["previous_plan"]["criteria"][0]["expression"]["property_id"] == "fruit.large"


def test_manually_verified_rote_zora_catalogue_case():
    # Expectations come from the original catalogue sentences, not from rules.
    from app.repository import load_plants
    p = next(p for p in load_plants() if p.name == "Rote Zora")
    assert "Die Früchte sind groß" in p.description
    assert "für den Freilandanbau geeignet" in p.description
    expr = group("all", leaf("site.outdoor"), leaf("fruit.large"))
    assert check(expr, p.description)["status"] == "yes"
