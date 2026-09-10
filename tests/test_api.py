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


def test_ask_endpoint_is_not_limited_to_tomatoes(monkeypatch):
    monkeypatch.setenv("QUERY_INTERPRETER_PROVIDER", "fake")
    plant = row_to_plant(
        {
            "Name": "Balkongurke",
            "Kategorie": "Gurke",
            "Beschreibung": "Kompakte Gurke für Balkon und Kübel.",
            "Filter_Tags": "Gurke; Balkon; kompakt",
        }
    )
    monkeypatch.setattr("app.main.load_plants", lambda: [plant])

    response = client.post(
        "/api/ask",
        json={"question": "Welche Gurke passt auf meinen Balkon?"},
    )

    assert response.status_code == 200
    assert response.json()["recommendations"][0]["plant_name"] == (
        "Balkongurke"
    )


def test_catalog_question_lists_category(monkeypatch):
    monkeypatch.setenv("QUERY_INTERPRETER_PROVIDER", "fake")
    plants = [
        row_to_plant({
            "Name": "Gold Rush",
            "Kategorie": "Zucchini",
            "Beschreibung": "Gelbe Zucchini.",
        }),
        row_to_plant({
            "Name": "Black Beauty",
            "Kategorie": "Zucchini",
            "Beschreibung": "Grüne Zucchini.",
        }),
    ]
    monkeypatch.setattr("app.main.load_plants", lambda: plants)

    response = client.post(
        "/api/ask",
        json={"question": "Welche Zucchini-Sorten gibt es?"},
    )

    assert response.status_code == 200
    assert len(response.json()["recommendations"]) == 2


def test_recommendation_contains_image_filenames(monkeypatch):
    monkeypatch.setenv("QUERY_INTERPRETER_PROVIDER", "fake")
    plant = row_to_plant({
        "Name": "Birnentomate",
        "Kategorie": "Tomate",
        "Beschreibung": "Birnenförmige rote Früchte.",
        "Bild": "birnentomate.jpg",
    })
    monkeypatch.setattr("app.main.load_plants", lambda: [plant])

    response = client.post(
        "/api/ask",
        json={"question": "Wie heißt die Birnen-förmige Tomate?"},
    )

    assert response.status_code == 200
    item = response.json()["recommendations"][0]
    assert item["plant_name"] == "Birnentomate"
    assert item["image_filenames"] == ["birnentomate.jpg"]


def test_static_plant_image_is_served():
    response = client.get("/static/images/Zuckertomate.jpg")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")
