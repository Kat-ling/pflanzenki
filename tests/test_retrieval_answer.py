import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.advisor.retrieval import retrieve
from app.ai.catalogue_answer import consult
from app.ai.dialogue_models import ChatMessage
from app.ai.interpreters.openai_interpreter import OpenAIQueryInterpreter
from app.ai.query_interpreter import QueryInterpreterError
from app.importer.csv_importer import row_to_plant
from app.main import app
from app.repository import load_plants


def fake(plant, source_id="s2", plant_id=None, suitability="matches"):
    calls = []
    output = dict(understood_request="Tomaten mit kleinen Früchten, Standort egal.",
                  answer="Hier findest du eine Sorte mit kleinen Früchten.",
                  plants=[dict(plant_id=plant_id or plant.id, explanation="Kleine Früchte laut Beschreibung.",
                               source_ids=[source_id], suitability=suitability)],
                  follow_up_question="")
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(status="completed", output_text=json.dumps(output))
    llm = OpenAIQueryInterpreter(client=SimpleNamespace(responses=SimpleNamespace(create=create)),
                                model="offline", categories=["Tomate"])
    return llm, calls


def test_screenshot_questions_retrieve_real_sources():
    history = []
    for question in ["Welche Cocktailtomaten gibt es?", "Ich suche Tomaten mit kleinen Früchten",
                     "Du wirst doch Tomaten nennen können, die geschützt oder ohne Schutz kleine Früchte haben in der Größe von Cocktailtomaten."]:
        candidates = retrieve(load_plants(), question, history)
        descriptions = " ".join(p["fields"]["Beschreibung"] for p in candidates).casefold()
        assert "cocktailtomate" in descriptions
        assert "klein" in descriptions
        assert 0 < len(candidates) <= 24
        assert len(json.dumps(candidates, ensure_ascii=False)) <= 28000
        history.append(ChatMessage(role="user", content=question))


def test_api_uses_sources_once_and_keeps_images_and_context(monkeypatch):
    plant = row_to_plant({"Name": "Probe", "Kategorie": "Tomate", "Beschreibung": "Kleine rote Früchte.", "Bild": "probe.jpg"})
    llm, calls = fake(plant)
    monkeypatch.setattr("app.main.create_query_interpreter", lambda: llm)
    monkeypatch.setattr("app.main.load_plants", lambda: [plant])
    history = [{"role": "user", "content": "Welche Cocktailtomaten gibt es?"}]
    response = TestClient(app).post("/api/ask", json={"question": "Kleine Früchte, Schutz egal", "history": history})
    assert response.status_code == 200
    result = response.json()
    assert result["selection_mode"] == "retrieval"
    assert result["plan"] is None
    card = result["recommendations"][0]
    assert card["image_filenames"] == ["probe.jpg"]
    assert card["catalogue_fields"]["Beschreibung"] == plant.description
    assert len(calls) == 1
    sent = json.loads(calls[0]["input"])
    assert sent["history"] == history
    assert sent["candidates"][0]["sources"]["s2"]["text"] == plant.description


@pytest.mark.parametrize("changes", [{"source_id": "invented"}, {"plant_id": "invented"}])
def test_invalid_sources_are_rejected_without_retry(changes):
    plant = row_to_plant({"Name": "Probe", "Kategorie": "Tomate", "Beschreibung": "Kleine Früchte."})
    llm, calls = fake(plant, **changes)
    with pytest.raises(QueryInterpreterError):
        consult(llm, [plant], "Tomate", [])
    assert len(calls) == 1


def test_updated_catalogue_is_immediately_searchable():
    before = row_to_plant({"Name": "Probe", "Beschreibung": "Alte Beschreibung."})
    assert not retrieve([before], "zitronenduftend", [])
    after = row_to_plant({"Name": "Probe", "Beschreibung": "Zitronenduftend."})
    assert retrieve([after], "zitronenduftend", [])[0]["fields"]["Beschreibung"] == after.description


def test_uncertain_plant_is_not_a_recommendation():
    plant = row_to_plant({"Name": "Probe", "Kategorie": "Tomate", "Beschreibung": "Kleine Früchte."})
    llm, _ = fake(plant, suitability="uncertain")
    result = consult(llm, [plant], "Niedrige Tomate", [])
    assert not result["recommendations"]
    assert result["total_matches"] == 0
    assert result["unknown"][0]["checks"][0]["status"] == "unknown"


@pytest.mark.parametrize("model,expected", [("gpt-5-mini", "minimal"),
                                          ("gpt-5-mini-2025-08-07", "minimal"),
                                          ("different-model", None)])
def test_reasoning_setting_is_model_specific(model, expected):
    plant = row_to_plant({"Name": "Probe", "Kategorie": "Tomate", "Beschreibung": "Kleine Früchte."})
    llm, calls = fake(plant)
    llm.model = model
    consult(llm, [plant], "Tomaten", [])
    assert calls[0].get("reasoning", {}).get("effort") == expected
    assert len(calls) == 1
    assert calls[0]["max_output_tokens"] == 4000


def test_height_search_finds_explicit_growth_sources():
    candidates = retrieve(load_plants(), "Welche niedrig-wachsende Tomatenpflanze gibt es?", [])
    names = [p["fields"]["Name"] for p in candidates]
    assert "Fuzzy-Wuzzy" in names[:12]
    assert "Huberts Beste" in names[:12]
    assert "Benarys Gartenfreude" not in names[:4]


def test_named_followup_ignores_hyphen_difference():
    candidates = retrieve(load_plants(), 'Was ist mit "Fuzzy Wuzzy"?', [])
    assert candidates[0]["fields"]["Name"] == "Fuzzy-Wuzzy"


def test_compaction_keeps_real_evidence_and_zero_heat():
    from app.advisor.retrieval import answer_fields
    source = {"Name": "Probe", "Kategorie": "Paprika", "Beschreibung": "Regenschutz erforderlich.",
              "Freiland": "No", "Wuchshöhe_bis_cm": "0", "Schärfegrad MAX": "0",
              "Ernte_von_Monat": "7", "Filter_Tags": "Paprika; rot",
              "Neues Originalfeld": "Nur im Gewächshaus.", "Doppeltext": "Regenschutz erforderlich."}
    compact = answer_fields(source)
    assert compact["Beschreibung"] == source["Beschreibung"]
    assert compact["Schärfegrad MAX"] == "0"
    assert compact["Ernte_von_Monat"] == "7"
    assert compact["Neues Originalfeld"] == source["Neues Originalfeld"]
    assert not {"Freiland", "Wuchshöhe_bis_cm", "Filter_Tags", "Doppeltext"} & compact.keys()
    assert source["Freiland"] == "No"


def test_screenshot_payload_stays_small_without_clipping_descriptions():
    plants = load_plants()
    candidates = retrieve(plants, "Welche Cocktailtomaten gibt es?", [])
    assert len(candidates) == 24
    assert len(json.dumps(candidates, ensure_ascii=False)) <= 28000
    originals = {p.id: p for p in plants}
    for candidate in candidates:
        assert candidate["fields"]["Beschreibung"] == originals[candidate["plant_id"]].description
