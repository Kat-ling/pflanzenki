"""Speech to text stays a thin step in front of the normal question path."""
import logging
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.ai.query_interpreter import QueryInterpreterError
from app.ai.transcription import MAX_AUDIO_BYTES, transcribe
from app.config import Settings
from app.importer.csv_importer import row_to_plant
from app.main import app, create_app

client = TestClient(app)
PLANTS = [row_to_plant({"Name": name, "Kategorie": "Tomate"})
          for name in ("Harzfeuer (keine Hybride!)", "Cesky <Rany>", "Harzfeuer")]


def speech(text=" Wie groß wird Yesil Tatli? ", error=None):
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        if error:
            raise error
        return SimpleNamespace(text=text)

    return SimpleNamespace(audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create))), calls


def test_request_uses_german_and_catalogue_names_as_hints():
    fake, calls = speech()
    assert transcribe(b"ton", "audio/webm;codecs=opus", PLANTS, fake) == "Wie groß wird Yesil Tatli?"
    assert calls[0]["model"] == "gpt-transcribe"
    assert calls[0]["languages"] == ["de"]
    assert calls[0]["keywords"] == ["Cesky Rany", "Harzfeuer"]
    assert calls[0]["file"] == ("aufnahme.webm", b"ton", "audio/webm")


@pytest.mark.parametrize("content_type, name", [("audio/mp4", "aufnahme.mp4"), ("audio/wav", "aufnahme.wav"),
                                                ("audio/mpeg", "aufnahme.mp3")])
def test_browser_formats_keep_their_file_type(content_type, name):
    fake, calls = speech()
    transcribe(b"ton", content_type, PLANTS, fake)
    assert calls[0]["file"][0] == name


@pytest.mark.parametrize("audio, content_type", [(b"", "audio/webm"), (b"ton", "text/plain"), (b"ton", None)])
def test_unusable_audio_is_refused_without_a_paid_call(audio, content_type):
    fake, calls = speech()
    with pytest.raises(ValueError):
        transcribe(audio, content_type, PLANTS, fake)
    assert calls == []


def test_service_failure_stays_generic():
    fake, _ = speech(error=RuntimeError("geheimer Dienstfehler"))
    with pytest.raises(QueryInterpreterError) as caught:
        transcribe(b"ton", "audio/webm", PLANTS, fake)
    assert "geheim" not in str(caught.value)


def test_spoken_text_never_reaches_the_log(caplog):
    fake, _ = speech("Ein privater Satz")
    with caplog.at_level(logging.INFO):
        transcribe(b"ton", "audio/webm", PLANTS, fake)
    assert "duration_ms" in caplog.text
    assert "privater" not in caplog.text


def post(audio=b"ton", content_type="audio/webm", target=client):
    return target.post("/api/transcribe", files={"audio": ("a", audio, content_type)})


def test_endpoint_returns_the_text(monkeypatch):
    monkeypatch.setattr("app.main.transcribe", lambda audio, kind, plants: f"{audio.decode()} {kind}")
    monkeypatch.setattr("app.main.load_plants", lambda: PLANTS)
    assert post().json() == {"text": "ton audio/webm"}


def test_endpoint_refuses_other_files():
    assert post(content_type="text/plain").status_code == 400


def test_endpoint_without_a_file_is_refused():
    assert client.post("/api/transcribe").status_code == 422


def test_endpoint_refuses_oversized_audio_before_reading_it():
    response = client.post("/api/transcribe", content=b"x", headers={"content-length": str(MAX_AUDIO_BYTES * 2)})
    assert response.status_code == 413


def test_endpoint_checks_the_size_of_the_file_itself(monkeypatch):
    monkeypatch.setattr("app.main.MAX_AUDIO_BYTES", 2)
    assert post().status_code == 413


def test_service_failure_becomes_a_clear_error(monkeypatch):
    def fail(*_):
        raise QueryInterpreterError("Die Spracherkennung ist gerade nicht erreichbar.")

    monkeypatch.setattr("app.main.transcribe", fail)
    response = post()
    assert response.status_code == 502
    assert response.json()["detail"] == "Die Spracherkennung ist gerade nicht erreichbar."


def test_voice_input_needs_the_access_password_on_the_web():
    guarded = TestClient(create_app(Settings(environment="production", access_password="testwert")))
    assert post(target=guarded).status_code == 401
