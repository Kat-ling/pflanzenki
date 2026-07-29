from fastapi.testclient import TestClient

from app.importer.csv_importer import row_to_plant
from app.main import app


client = TestClient(app)


def test_interpret_endpoint_uses_configured_fake_interpreter(
    monkeypatch,
):
    monkeypatch.setenv("QUERY_INTERPRETER_PROVIDER", "fake")

    response = client.post(
        "/api/interpret",
        json={
            "question": "Welche Tomate eignet sich draußen ohne Dach?"
        },
    )

    assert response.status_code == 200
    parsed = response.json()
    assert parsed["category"] == "Tomate"
    assert parsed["requirements"][0]["feature"] == "outdoor_uncovered"


def test_ask_endpoint_runs_interpreter_then_advisor(monkeypatch):
    monkeypatch.setenv("QUERY_INTERPRETER_PROVIDER", "fake")
    plant = row_to_plant(
        {
            "Sorte": "Freilandtomate",
            "Kategorie": "Tomate",
            "Beschreibung": "Für das ungeschützte Freiland geeignet.",
        }
    )
    monkeypatch.setattr("app.main.load_plants", lambda: [plant])

    response = client.post(
        "/api/ask",
        json={
            "question": "Welche Tomate eignet sich draußen ohne Dach?"
        },
    )

    assert response.status_code == 200
    assert response.json()["recommendations"][0]["plant_name"] == (
        "Freilandtomate"
    )
