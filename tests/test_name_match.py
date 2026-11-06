"""Misheard or mistyped variety names, checked without any model call."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.advisor.name_match import check_names, cologne
from app.importer.csv_importer import row_to_plant
from app.main import app
from app.repository import load_plants
from catalogue_acceptance_cases import CASES

PLANTS = load_plants()
client = TestClient(app)


@pytest.mark.parametrize("word, code", [
    ("Müller-Lüdenscheidt", "65752682"), ("Wikipedia", "3412"), ("Breschnew", "17863"),
])
def test_cologne_phonetics_follows_the_published_examples(word, code):
    assert cologne(word) == code


# Real transcripts from the speech probe.
@pytest.mark.parametrize("heard, fixed", [
    ("Ist Principe Borghese für den Balkon geeignet?", "Ist Prinzipe Borghese für den Balkon geeignet?"),
    ("Wie groß wird Jessil Tatli?", "Wie groß wird Yesil Tatli?"),
    ("Wie lange lässt sich Uchikikuri lagern?", "Wie lange lässt sich Uchiki Kuri lagern?"),
])
def test_clear_name_is_taken_over_and_reported(heard, fixed):
    check = check_names(heard, PLANTS)
    assert (check.text, check.changed, check.choices) == (fixed, True, [])


@pytest.mark.parametrize("heard, spoken, name", [
    ("Erzähl mir etwas über Cherny Prinz.", "Cherny Prinz", "Tschernij Prinz"),
    ("Wann kann ich Chesky Reni ernten?", "Chesky Reni", "Cesky Rany"),
    ("Passt Sojo Long ins Gewächshaus.", "Sojo Long", "Soo Yoo Long"),
])
def test_doubtful_name_is_asked_about_and_never_replaced(heard, spoken, name):
    check = check_names(heard, PLANTS)
    assert check.text == heard
    assert check.spoken == spoken
    assert check.choices[0] == dict(label=name, question=heard.replace(spoken, name))


@pytest.mark.parametrize("question", [
    "Was ist der Unterschied zwischen Costoluto Genovese und San Marzano Retorta?",
    "Wie schmeckt Pomodorino del Piennolo del Vesuvio?",
    "Was weißt du über Rouge vif d'Etampes?",
    "Passt Fuzzy-Wuzzy in den Topf?",
])
def test_exact_names_stay_untouched(question):
    check = check_names(question, PLANTS)
    assert (check.text, check.changed, check.choices) == (question, False, [])


def test_spelling_variants_of_a_name_are_normalised_without_a_notice():
    check = check_names("Was ist Numex Sandia für eine Chili?", PLANTS)
    assert (check.text, check.changed) == ("Was ist NuMex Sandia für eine Chili?", False)
    check = check_names("Wie scharf ist Pimiento de Padrón?", PLANTS)
    assert (check.text, check.changed) == ("Wie scharf ist Pimiento de Padron?", False)


def test_name_with_a_note_in_brackets_keeps_the_note_out_of_the_question():
    check = check_names("Ist Harzfeier gut?", [row_to_plant({"Name": "Harzfeuer (keine Hybride!)", "Kategorie": "Tomate"})])
    assert check.text == "Ist Harzfeuer gut?"


@pytest.mark.parametrize("question", [
    "Welche Gurke passt ins Gewächshaus?",
    "Ich suche eine kleine, süße Tomate für den Balkon.",
    "Gibt es noch weitere?",
    "Welche Paprika ist nicht scharf und passt auf den Balkon?",
    "Was kann ich im Halbschatten pflanzen?",
    "Hast du etwas für Anfänger?",
    "Gibt es Basilikum mit Zitronenaroma?",
    "Stell dir vor, ich habe nur Schatten.",
    "Hallo, ich bräuchte mal deinen Rat.",
    "Äh, also ich wollte fragen, was so im Mai noch geht.",
    "Kannst du mir eine Tomate für Rentner empfehlen?",
    *[case[1] for case in CASES],
])
def test_ordinary_questions_are_left_alone(question):
    check = check_names(question, PLANTS)
    assert (check.text, check.changed, check.choices) == (question, False, [])


def test_two_similar_names_are_both_offered():
    plants = [row_to_plant({"Name": name, "Kategorie": "Tomate"}) for name in ("Harzfeuer", "Harzfeier")]
    check = check_names("Ist Harzfaier gut?", plants)
    assert check.text == "Ist Harzfaier gut?"
    assert {c["label"] for c in check.choices} == {"Harzfeuer", "Harzfeier"}


def test_nonsense_gets_no_guessed_name():
    check = check_names("Xqzvk blorptatsch?", PLANTS)
    assert (check.changed, check.choices) == (False, [])


def test_very_long_input_stays_quick():
    check_names("Blarg Wurblo " * 80, PLANTS)


def fake_model(monkeypatch, plants):
    calls = []

    def consult(_interpreter, _plants, question, *_):
        calls.append(question)
        return dict(question=question, answer="Antwort", recommendations=[], unknown=[], excluded=[], warnings=[])

    monkeypatch.setattr("app.main.load_plants", lambda: plants)
    monkeypatch.setattr("app.ai.catalogue_answer.consult", consult)
    monkeypatch.setattr("app.main.create_query_interpreter", real_looking_interpreter)
    return calls


def real_looking_interpreter():
    from app.ai.interpreters.openai_interpreter import OpenAIQueryInterpreter
    return OpenAIQueryInterpreter(client=SimpleNamespace(), model="offline", categories=["Tomate"])


def test_doubtful_name_costs_no_model_call(monkeypatch):
    calls = fake_model(monkeypatch, PLANTS)
    body = client.post("/api/ask", json={"question": "Wann kann ich Chesky Reni ernten?"}).json()
    assert calls == []
    assert body["intent"] == "name_check"
    assert body["answer"] == "Meintest du Cesky Rany?"
    assert body["name_choices"][0]["question"] == "Wann kann ich Cesky Rany ernten?"
    assert body["recommendations"] == []


def test_clear_name_reaches_the_model_corrected(monkeypatch):
    calls = fake_model(monkeypatch, PLANTS)
    body = client.post("/api/ask", json={"question": "Wie groß wird Jessil Tatli?"}).json()
    assert calls == ["Wie groß wird Yesil Tatli?"]
    assert body["understood_as"] == "Wie groß wird Yesil Tatli?"


def test_refusing_the_suggestion_keeps_the_own_wording(monkeypatch):
    calls = fake_model(monkeypatch, PLANTS)
    body = client.post("/api/ask", json={"question": "Wann kann ich Chesky Reni ernten?",
                                         "names_checked": True}).json()
    assert calls == ["Wann kann ich Chesky Reni ernten?"]
    assert "understood_as" not in body
