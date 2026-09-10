"""Deterministic contract/grounding tests, NOT live LLM quality evaluations."""
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.ai.catalogue_dialogue import (
    batches, consult, evaluate_batch, interpret_dialogue,
    request_structured, verified_checks,
)
from app.ai.dialogue_models import (
    Assessment, ChatMessage, Criterion, DialoguePlan, AssessmentBatch,
)
from app.ai.interpreters.openai_interpreter import OpenAIQueryInterpreter
from app.ai.query_interpreter import QueryInterpreterError
from app.importer.csv_importer import row_to_plant
from app.main import app
from app.repository import load_plants


def criterion(text="Freiland", importance="required", kind="condition"):
    mapping = {"Freiland": ("site.outdoor", True), "Große Früchte": ("fruit.large", True),
               "gelb": ("fruit.color", "gelb")}
    key, value = mapping.get(text, ("", None))
    return Criterion(text=text, importance=importance, kind=kind, expression={
        "op": "predicate" if key else "unresolved", "text": text, "property_id": key,
        "comparator": "eq", "value": value, "unit": None, "children": [],
    })


def plan(criteria=None, **changes):
    output = dict(intent="recommendation", categories=["Tomate"], plant_names=[],
                  criteria=[c.model_dump() for c in (criteria or [])],
                  follow_up_question="", unsupported_requests=[])
    output.update(changes)
    return output


def plant(name="Test", description="Für Freiland geeignet. Große Früchte.", **fields):
    return row_to_plant({"Name": name, "Kategorie": "Tomate",
                         "Beschreibung": description, **fields})


def assessment(index=0, status="yes", field="Beschreibung", quote="Für Freiland geeignet."):
    return {"criterion_index": index, "status": status,
            "citations": [{"field": field, "quote": quote}] if quote else []}


class Responses:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(output_text=json.dumps(self.outputs.pop(0)), status="completed")


def interpreter(outputs):
    return OpenAIQueryInterpreter(client=SimpleNamespace(responses=Responses(outputs)),
                                  model="test-model", categories=["Tomate"])


def batch_output(entries):
    return {"plants": [{"plant_id": p.id, "assessments": checks} for p, checks in entries]}


@pytest.mark.parametrize("second_status,expected", [
    ("yes", "recommendations"), ("no", "excluded"), ("unknown", "unknown"),
])
def test_and_requires_both_criteria(second_status, expected):
    p = plant(description="Für Freiland geeignet. " + {
        "yes": "Große Früchte.", "no": "Kleine Früchte.", "unknown": "Guter Geschmack."
    }[second_status])
    criteria = [criterion(), criterion("Große Früchte")]
    llm = interpreter([plan(criteria)])
    result = consult(llm, [p], "Freiland und große Früchte", [])
    assert len(result[expected]) == 1
    if expected != "recommendations":
        assert result["recommendations"] == []
    assert len(llm.client.responses.requests) == 1


def test_preference_does_not_exclude_but_stays_visible():
    p = plant()
    llm = interpreter([plan([criterion(), criterion("gelb", "preferred")])])
    result = consult(llm, [p], "Freiland, gern gelb", [])
    assert result["recommendations"][0]["checks"][1]["status"] == "unknown"


@pytest.mark.parametrize("text", [
    "Freiland und Fruchtgewicht mindestens 200 g",
    "rote ODER gelbe Früchte", "(rot UND klein) ODER (gelb UND groß)",
    "nicht scharf", "maximal 80 cm Wuchshöhe", "Ernte zwischen Juli und September",
    "geeignet zum Einlegen", "wenig Kerne und dünne Schale",
])
def test_arbitrary_criteria_survive_without_feature_enum(text):
    llm = interpreter([plan([criterion(text)])])
    parsed = interpret_dialogue(llm, [plant()], text, [])
    assert parsed.criteria[0].text == text


def test_conversation_and_correction_are_sent_without_truncation():
    history = [ChatMessage(role="user", content="Tomate im Freiland und groß"),
               ChatMessage(role="assistant", content="Meinst du Früchte oder Wuchshöhe?")]
    llm = interpreter([plan([criterion(), criterion("Große Früchte")])])
    parsed = interpret_dialogue(llm, [plant()], "Ich meine die Früchte", history)
    payload = json.loads(llm.client.responses.requests[0]["input"])
    assert payload["history"] == [m.model_dump() for m in history]
    assert payload["question"] == "Ich meine die Früchte"
    assert len(parsed.criteria) == 2
    assert llm.client.responses.requests[0]["store"] is False


def test_follow_up_skips_evaluation_and_preserves_criteria():
    llm = interpreter([plan([criterion()], follow_up_question="Früchte oder Wuchshöhe?")])
    result = consult(llm, [plant()], "groß", [])
    assert result["intent"] == "follow_up"
    assert result["criteria"][0]["text"] == "Freiland"
    assert len(llm.client.responses.requests) == 1


@pytest.mark.parametrize("field,quote", [
    ("Beschreibung", "Erfundener Satz"), ("Erfundene Spalte", "ja"),
    ("Freiland", "No"), ("Wuchshöhe_bis_cm", "0"), ("Beschreibung", ""),
])
def test_unverifiable_or_empty_evidence_becomes_unknown(field, quote):
    p = plant(Freiland="No", Wuchshöhe_bis_cm="0")
    checks = verified_checks(p, [Assessment(**assessment(field=field, quote=quote))], [criterion()])
    assert checks[0]["status"] == "unknown"


def test_citations_display_full_original_field_including_caveat():
    description = "Große Früchte. Für Freiland nur bedingt geeignet. Nicht ohne Regenschutz."
    p = plant(description=description)
    checks = verified_checks(p, [Assessment(**assessment(quote="Große Früchte."))], [criterion("groß")])
    assert checks[0]["sources"][0]["text"] == description


def test_original_fields_stay_local_and_do_not_reach_model():
    description = "Ein vollständiger Satz. " * 2500
    p = plant(description=description, Neu_im_Notion_Katalog="Spezielle neue Eigenschaft")
    llm = interpreter([plan([criterion("unbekannt")])])
    result = consult(llm, [p], "unbekannt", [])
    payload = json.loads(llm.client.responses.requests[0]["input"])
    assert "plants" not in payload
    assert description not in llm.client.responses.requests[0]["input"]
    assert result["unknown"][0]["catalogue_fields"]["Beschreibung"] == description
    assert result["unknown"][0]["catalogue_fields"]["Neu_im_Notion_Katalog"] == "Spezielle neue Eigenschaft"
    assert list(batches([p], budget=100)) == [[p]]


def test_legacy_catalogue_model_evaluation_is_disabled():
    llm = interpreter([])
    with pytest.raises(QueryInterpreterError, match="deaktiviert"):
        evaluate_batch(llm, [plant()], [criterion()])
    assert llm.client.responses.requests == []


@pytest.mark.parametrize("indices", [[], [0, 0], [1], [0, 2]])
def test_missing_duplicate_or_wrong_criterion_rejected(indices):
    with pytest.raises(QueryInterpreterError):
        verified_checks(plant(), [Assessment(**assessment(i)) for i in indices], [criterion()])


def test_incomplete_model_response_never_becomes_result():
    llm = interpreter([])
    llm.client.responses.create = lambda **kw: SimpleNamespace(status="incomplete", output_text="{}")
    with pytest.raises(QueryInterpreterError, match="unvollständig"):
        request_structured(llm, "", {}, AssessmentBatch)


def test_all_catalogue_results_retained_for_pagination():
    plants = [plant(str(i)) for i in range(10)]
    result = consult(interpreter([plan(intent="catalog")]), plants, "Alle Tomaten", [])
    assert result["total_matches"] == 10
    assert len(result["recommendations"]) == 10


def test_multiple_categories_do_not_drop_cucumbers():
    cucumber = row_to_plant({"Name": "Gurke", "Kategorie": "Gurke"})
    result = consult(interpreter([plan(intent="catalog", categories=["Tomate", "Gurke"])]),
                     [plant(), cucumber], "Tomaten oder Gurken", [])
    assert result["total_matches"] == 2


def test_unknown_category_not_silently_ignored():
    with pytest.raises(QueryInterpreterError):
        consult(interpreter([plan(categories=["Erfunden"])]), [plant()], "?", [])


def test_unknown_named_plant_is_not_replaced():
    result = consult(interpreter([plan(intent="information", plant_names=["Erfundene Sorte"])]),
                     [plant()], "Erfundene Sorte", [])
    assert result["intent"] == "follow_up"
    assert not result["recommendations"]


def test_information_unknown_remains_visible_not_invented():
    p = plant()
    llm = interpreter([plan([criterion("Erntezeit", kind="information")],
                           intent="information", plant_names=[p.name])])
    result = consult(llm, [p], "Wann ernte ich Test?", [])
    card = result["recommendations"][0]
    assert card["checks"][0]["status"] == "unknown"
    assert card["description"] == p.description


def test_unsupported_task_does_not_list_random_plants():
    result = consult(interpreter([plan(intent="information", unsupported_requests=["Bestellung"])]),
                     [plant()], "Bestelle mir 10", [])
    assert not result["recommendations"]
    assert "Woas I ned." in result["answer"]


def test_full_catalogue_is_batched_without_missing_entries():
    plants = load_plants()
    flattened = [p for group in batches(plants) for p in group]
    assert flattened == plants
    assert len({p.id for p in plants}) == len(plants)


def test_legacy_dialogue_passes_history():
    llm = interpreter([plan([criterion()], follow_up_question="Welche Größe?")])
    history = [{"role": "user", "content": "Freilandtomate"},
               {"role": "assistant", "content": "Was ist dir noch wichtig?"}]
    from app.ai.dialogue_models import ChatMessage
    result = consult(llm, [plant()], "groß", [ChatMessage(**m) for m in history])
    assert result["intent"] == "follow_up"
    assert json.loads(llm.client.responses.requests[0]["input"])["history"] == history


def test_history_over_limit_is_rejected_not_clipped():
    response = TestClient(app).post("/api/ask", json={
        "question": "Hallo", "history": [{"role": "user", "content": "x"}] * 41})
    assert response.status_code == 422


def test_fake_mode_does_not_pretend_to_remember(monkeypatch):
    monkeypatch.setenv("QUERY_INTERPRETER_PROVIDER", "fake")
    response = TestClient(app).post("/api/ask", json={
        "question": "Die Früchte", "history": [{"role": "user", "content": "groß"}]})
    assert response.status_code == 400
    assert "keine Gespräche" in response.json()["detail"]


def test_page_has_reply_reset_and_unclipped_layout():
    html = TestClient(app).get("/").text
    for marker in ["Deine Antwort auf die Rückfrage", "Neue Beratung", "history: requestHistory",
                   "Weitere anzeigen", "white-space: pre-wrap", "object-fit: contain"]:
        assert marker in html
    assert "line-clamp" not in html


def test_rule_evidence_preserves_original_description():
    text = "Eine frühe Sorte. " + "Zusätzliche vollständige Angaben. " * 30
    p = plant(description=text)
    assert p.evidence
    assert all(e.quote == text for e in p.evidence if e.source.value == "description")


def test_structured_schemas_require_every_property():
    def verify(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            for value in node.values():
                verify(value)
        elif isinstance(node, list):
            for value in node:
                verify(value)
    verify(DialoguePlan.model_json_schema())
    verify(AssessmentBatch.model_json_schema())
