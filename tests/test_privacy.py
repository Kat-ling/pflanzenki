"""Personal data must neither enter the catalogue nor the public repository."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

from app.importer.privacy import find_personal_hints, load_privacy_rules, sanitize_row

ROOT = Path(__file__).resolve().parents[1]
# Hashed so that this public test does not itself publish the terms.
FORBIDDEN_WORD_HASHES = {
    "448ff49f79b249a748decb4003d7e17f957351d79344c34cf9d31cec5fe5f2cc",
    "6cf3323e3c6670a17a231cc175ddd48d7e9a7c83bf3536199d60ef24c6b3522a",
    "82280bb7b30905f97322961a56e3c119150a246cb47293607c23385110c73d52",
    "b0e28b52361ccc296795cdb6956329d2570dda297e556c0a1ad9bd8daf30530e",
    "b4ad95e3decba61fb2f13bdd7f360fff7ce009e833eece72ba4587c59812cee6",
}


def test_image_links_are_reduced_to_file_names():
    row = sanitize_row({"Name": "A", "Bild": "https://cloud.example/geheim/a.jpg, b.jpg"}, [])
    assert row["Bild"] == "a.jpg, b.jpg"


def test_local_rules_replace_text_in_every_field():
    rules = [{"find": "Tomate von Erika", "replace": "Tomate"}]
    row = sanitize_row({"Name": "Tomate von Erika", "Name_für_Katalog": "Die Tomate von Erika"}, rules)
    assert row == {"Name": "Tomate", "Name_für_Katalog": "Die Tomate"}


def test_missing_rules_file_means_no_rules(tmp_path):
    assert load_privacy_rules(tmp_path / "fehlt.json") == []


def test_rules_file_is_read(tmp_path):
    path = tmp_path / "regeln.json"
    path.write_text(json.dumps({"replacements": [{"find": "a", "replace": "b"}]}), encoding="utf-8")
    assert load_privacy_rules(path) == [{"find": "a", "replace": "b"}]


@pytest.mark.parametrize("row", [
    {"Name": "Tomate (von Erika)"},
    {"Name": "Rumänische Tomaten von Erika"},
    {"Name": "A", "Beschreibung": "Eine Tomate von meiner Schwester."},
    {"Name": "A", "Beschreibung": "Wir haben sie von einer Kollegin bekommen."},
    {"Name": "A", "Beschreibung": "Diesen Paprika haben wir von Freunden bekommen."},
    {"Name": "A", "Beschreibung": "Kontakt: erika@example.org"},
    {"Name": "A", "Bild": "https://cloud.example/abc/a.jpg"},
])
def test_personal_hints_are_found(row):
    assert find_personal_hints([row])


@pytest.mark.parametrize("row", [
    {"Name": "Justens Zuckertomate", "Beschreibung": "Aus dem Projekt von Dreschflegel."},
    {"Name": "A", "Beschreibung": "Ernte von Juli bis Oktober, der rote Bruder von Salad Bowl."},
    {"Name": "A", "Beschreibung": "Gut für die kleinere Familie."},
])
def test_ordinary_catalogue_text_is_not_flagged(row):
    assert find_personal_hints([row]) == []


def tracked_text_files():
    try:
        names = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                               cwd=ROOT, capture_output=True, text=True, check=True,
                               encoding="utf-8").stdout.splitlines()
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("Kein Git-Arbeitsverzeichnis")
    for name in names:
        path = ROOT / name
        if path.is_file() and path.suffix not in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".pyc"}:
            yield name, path.read_text(encoding="utf-8", errors="ignore")


def test_repository_contains_no_private_paths_links_or_addresses():
    forbidden = re.compile(r"[A-Za-z]:\\Users\\|https?://filedn\.|[\w.+-]+@(?:gmail|gmx|web|t-online|outlook)\.")
    hits = [name for name, text in tracked_text_files() if forbidden.search(text)]
    assert hits == []


def test_repository_contains_no_listed_personal_terms():
    hits = set()
    for name, text in tracked_text_files():
        for word in set(re.findall(r"\w+", text.casefold())):
            if hashlib.sha256(word.encode()).hexdigest() in FORBIDDEN_WORD_HASHES:
                hits.add(name)
    assert hits == set()


def test_catalogue_has_no_personal_hints():
    rows = json.loads((ROOT / "data/normalized/plants.json").read_text(encoding="utf-8"))
    assert find_personal_hints([p["raw_fields"] for p in rows]) == []
