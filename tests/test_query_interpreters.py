import json
from types import SimpleNamespace

import pytest

from app.ai.interpreter_factory import create_query_interpreter
from app.ai.query_interpreter import QueryInterpreterError
from app.ai.interpreters.fake_interpreter import FakeQueryInterpreter
from app.ai.interpreters.openai_interpreter import (
    OpenAIQueryInterpreter,
    QUERY_SCHEMA,
)
from app.ai.query_models import (
    PlantFeature,
    RequirementImportance,
)


class FakeResponses:
    def __init__(self, output: dict):
        self.output = output
        self.request = None

    def create(self, **kwargs):
        self.request = kwargs
        return SimpleNamespace(output_text=json.dumps(self.output))


def test_fake_interpreter_returns_structured_query():
    parsed = FakeQueryInterpreter().interpret(
        "Ich suche eine süße Tomate für meinen Balkon."
    )

    assert parsed.original_question.endswith("Balkon.")
    assert parsed.category == "Tomate"
    assert {item.feature for item in parsed.requirements} == {
        PlantFeature.BALCONY,
        PlantFeature.SWEET,
    }
    assert (
        parsed.requirements[0].importance
        == RequirementImportance.REQUIRED
    )


def test_openai_interpreter_uses_responses_structured_output():
    responses = FakeResponses(
        {
            "intent": "recommendation",
            "category": "Tomate",
            "plant_names": [],
            "requirements": [
                {
                    "feature": "outdoor_uncovered",
                    "value": "yes",
                    "importance": "required",
                    "reason": "Ohne Dach wird ausdrücklich genannt.",
                }
            ],
            "follow_up_question": "",
            "unsupported_requests": [],
        }
    )
    client = SimpleNamespace(responses=responses)

    parsed = OpenAIQueryInterpreter(
        client=client,
        model="test-model",
        categories=["Tomate", "Gurke"],
    ).interpret("Welche Tomate geht ohne Dach?")

    assert parsed.category == "Tomate"
    assert responses.request["model"] == "test-model"
    assert "Gurke" in responses.request["instructions"]
    assert (
        responses.request["text"]["format"]["schema"]
        == QUERY_SCHEMA
    )


def test_schema_features_come_from_feature_catalog():
    schema_features = set(
        QUERY_SCHEMA["properties"]["requirements"]["items"]
        ["properties"]["feature"]["enum"]
    )

    assert schema_features == {feature.value for feature in PlantFeature}


def test_empty_requirement_reason_is_repaired():
    responses = FakeResponses(
        {
            "intent": "recommendation",
            "category": "Zucchini",
            "plant_names": [],
            "requirements": [
                {
                    "feature": "yellow",
                    "value": "yes",
                    "importance": "preferred",
                    "reason": "",
                }
            ],
            "follow_up_question": "",
            "unsupported_requests": [],
        }
    )
    interpreter = OpenAIQueryInterpreter(
        client=SimpleNamespace(responses=responses),
        model="test-model",
        categories=["Zucchini"],
    )

    parsed = interpreter.interpret("Welche Zucchini ist gelb?")

    assert parsed.requirements[0].reason


def test_factory_defaults_to_openai(monkeypatch):
    monkeypatch.delenv("QUERY_INTERPRETER_PROVIDER", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    options = {}
    def make_client(**kwargs):
        options.update(kwargs)
        return SimpleNamespace()
    monkeypatch.setattr(
        "app.ai.interpreters.openai_interpreter.OpenAI",
        make_client,
    )

    assert isinstance(create_query_interpreter(), OpenAIQueryInterpreter)
    assert options == {"timeout": 30.0, "max_retries": 0}


def test_factory_can_explicitly_use_fake(monkeypatch):
    monkeypatch.setenv("QUERY_INTERPRETER_PROVIDER", "fake")

    assert isinstance(create_query_interpreter(), FakeQueryInterpreter)


def test_openai_interpreter_explains_missing_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(
        QueryInterpreterError,
        match="OPENAI_API_KEY ist nicht konfiguriert",
    ):
        OpenAIQueryInterpreter()


def test_factory_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("QUERY_INTERPRETER_PROVIDER", "unknown")

    with pytest.raises(ValueError, match="fake, openai"):
        create_query_interpreter()
