"""One code base: open on the own computer, protected as a web service."""
import base64

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, load_settings
from app.main import app, create_app


def web(**overrides):
    values = dict(environment="production", access_password="geheim", requests_per_minute=100)
    return TestClient(create_app(Settings(**{**values, **overrides})))


def login(password="geheim", user="gast"):
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_local_defaults_stay_on_the_own_computer(monkeypatch):
    for key in ("APP_ENV", "HOST", "PORT", "APP_ACCESS_PASSWORD"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr("app.config.load_dotenv", lambda: None)
    settings = load_settings()
    assert (settings.environment, settings.host, settings.port) == ("local", "127.0.0.1", 8000)


def test_web_settings_come_from_the_environment(monkeypatch):
    monkeypatch.setattr("app.config.load_dotenv", lambda: None)
    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_ACCESS_PASSWORD", "geheim")
    monkeypatch.setenv("PORT", "9000")
    settings = load_settings()
    assert (settings.environment, settings.host, settings.port) == ("production", "0.0.0.0", 9000)


def test_web_operation_refuses_to_start_without_password():
    with pytest.raises(ValueError, match="APP_ACCESS_PASSWORD"):
        create_app(Settings(environment="production", access_password=""))


def test_unknown_environment_is_rejected():
    with pytest.raises(ValueError, match="APP_ENV"):
        create_app(Settings(environment="prod"))


def test_local_page_opens_without_login():
    assert TestClient(app).get("/").status_code == 200


def test_page_assets_are_served_separately():
    client = TestClient(app)
    html = client.get("/").text
    assert "<title>KI-Sister</title>" in html
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/app.css").status_code == 200
    assert "<script>" not in html and "<style>" not in html


def test_web_requires_login_for_page_api_and_images():
    client = web()
    for path in ("/", "/static/app.js", "/docs"):
        response = client.get(path)
        assert response.status_code == 401
        assert response.headers["www-authenticate"].startswith("Basic")
    assert client.post("/api/ask", json={"question": "Tomate"}).status_code == 401


def test_web_accepts_the_right_password_only():
    client = web()
    assert client.get("/", headers=login()).status_code == 200
    assert client.get("/", headers=login("falsch")).status_code == 401
    assert client.get("/", headers={"Authorization": "Basic !!!"}).status_code == 401


def test_health_check_works_without_login_and_reveals_nothing():
    response = web().get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_documentation_is_off_on_the_web():
    assert web().get("/docs", headers=login()).status_code == 404
    assert TestClient(app).get("/docs").status_code == 200


def test_paid_endpoints_are_rate_limited(monkeypatch):
    client = web(requests_per_minute=2)
    def refuse():
        raise ValueError("aus")
    monkeypatch.setattr("app.main.create_query_interpreter", refuse)
    statuses = [client.post("/api/ask", json={"question": "Tomate"}, headers=login()).status_code
                for _ in range(3)]
    assert statuses == [400, 400, 429]


def test_daily_budget_caps_all_clients_together(monkeypatch):
    client = web(requests_per_day=2)
    def refuse():
        raise ValueError("aus")
    monkeypatch.setattr("app.main.create_query_interpreter", refuse)
    responses = [client.post("/api/ask", json={"question": "Tomate"}, headers=login())
                 for _ in range(3)]
    assert [r.status_code for r in responses] == [400, 400, 429]
    assert "heute" in responses[-1].json()["detail"]
    assert client.get("/", headers=login()).status_code == 200


def test_daily_budget_starts_again_the_next_day():
    from datetime import date
    from app.security import DailyBudget
    days = [date(2026, 11, 10)]
    budget = DailyBudget(1, today=lambda: days[0])
    assert [budget.allow(), budget.allow()] == [True, False]
    days[0] = date(2026, 11, 11)
    assert budget.allow()


def test_wrong_passwords_do_not_use_up_the_requests_of_visitors(monkeypatch):
    client = web(requests_per_minute=2)
    def refuse():
        raise ValueError("aus")
    monkeypatch.setattr("app.main.create_query_interpreter", refuse)
    wrong = [client.get("/", headers=login("falsch")).status_code for _ in range(12)]
    assert wrong[:10] == [401] * 10 and wrong[10:] == [429, 429]
    assert client.post("/api/ask", json={"question": "Tomate"}, headers=login()).status_code == 400


def test_earlier_interpretation_endpoint_is_off_on_the_web(monkeypatch):
    monkeypatch.setenv("QUERY_INTERPRETER_PROVIDER", "fake")
    question = {"question": "Welche Tomate eignet sich draußen ohne Dach?"}
    assert web().post("/api/interpret", json=question, headers=login()).status_code == 404
    assert TestClient(app).post("/api/interpret", json=question).status_code == 200


def test_page_says_where_the_question_goes():
    html = TestClient(app).get("/").text
    assert "OpenAI" in html and "keine persönlichen Daten" in html


def test_images_may_be_kept_by_the_browser():
    from app.main import STATIC_DIR
    name = sorted(p.name for p in (STATIC_DIR / "images").iterdir())[0]
    assert TestClient(app).get(f"/static/images/{name}").headers["cache-control"] == "private, max-age=86400"
    assert "cache-control" not in TestClient(app).get("/static/app.js").headers


def test_derived_catalogue_data_is_rebuilt_only_for_other_plants():
    from app.repository import remember_last
    builds = []
    @remember_last
    def build(plants, *state):
        builds.append(state)
        return len(builds)
    first, second = [object(), object()], [object(), object()]
    assert [build(first), build(list(first)), build(second), build(second, 1), build(second, 1)] == [1, 1, 2, 3, 3]


def test_pages_are_not_rate_limited():
    client = web(requests_per_minute=1)
    assert [client.get("/", headers=login()).status_code for _ in range(3)] == [200, 200, 200]


def test_security_headers_prepare_https_and_microphone():
    headers = TestClient(app).get("/").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert "default-src 'self'" in headers["content-security-policy"]
    assert headers["permissions-policy"] == "microphone=(self)"


def test_missing_key_gives_a_helpful_message(monkeypatch):
    monkeypatch.setattr("app.ai.interpreter_factory.load_dotenv", lambda: None)
    monkeypatch.setenv("QUERY_INTERPRETER_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = TestClient(app).post("/api/ask", json={"question": "Tomate"})
    assert response.status_code == 502
    assert "OPENAI_API_KEY" in response.json()["detail"]


def test_catalogue_is_reloaded_only_after_a_change(tmp_path):
    from app.repository import load_plants
    path = tmp_path / "plants.json"
    path.write_text('[{"id": "a", "name": "A"}]', encoding="utf-8")
    first = load_plants(path)
    assert first[0] is load_plants(path)[0]
    path.write_text('[{"id": "b", "name": "Neu und länger"}]', encoding="utf-8")
    assert load_plants(path)[0].name == "Neu und länger"
