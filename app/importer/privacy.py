"""Keeps personal data out of the public catalogue.

Exact replacements live in a local file that is never committed, because the
terms themselves are personal. The generic patterns below find new cases.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from app.importer.csv_importer import split_image_names

MAX_EXCERPT = 40
RELATIVES = (r"Schwester|Bruder|Mutter|Vater|Oma|Opa|Tante|Onkel|Tochter|Sohn|"
             r"Nachbar\w*|Freund\w*|Kolleg\w*|Bekannt\w*")
TEXT_PATTERNS = [
    re.compile(rf"\b(?:mein|meine[rmns]?|unser|unsere[rmns]?)\s+(?:{RELATIVES})\b", re.I),
    re.compile(r"\bvon\s+(?:einem|einer|unserem|unserer|meinem|meiner)\s+"
               r"(?:Freund\w*|Kolleg\w*|Bekannt\w*|Nachbar\w*|Kund\w*)", re.I),
    re.compile(r"\bvon\s+(?:Freunden|Bekannten|Kollegen|Nachbarn)\b", re.I),
    re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", re.I),
]
# A plant name ending in "von <Name>" records who it came from.
NAME_PATTERN = re.compile(r"\bvon\s+[A-ZÄÖÜ][a-zäöüß]+\)?\s*$")
NAME_FIELDS = {"Name", "Name_für_Katalog"}


def load_privacy_rules(path: str | Path) -> list[dict[str, str]]:
    path = Path(path)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))["replacements"]


def sanitize_row(row: dict, rules: list[dict[str, str]]) -> dict:
    cleaned = {}
    for key, value in row.items():
        if isinstance(value, str):
            for rule in rules:
                value = value.replace(rule["find"], rule["replace"])
        cleaned[key] = value
    if cleaned.get("Bild"):
        # Links point into private storage; only the file name is needed.
        cleaned["Bild"] = ", ".join(split_image_names(cleaned["Bild"]))
    return cleaned


def excerpt(text: str, match: re.Match) -> str:
    start = max(0, match.start() - MAX_EXCERPT)
    return " ".join(text[start:match.end() + MAX_EXCERPT].split())


def find_personal_hints(rows: list[dict]) -> list[str]:
    hints = []
    for row in rows:
        label = str(row.get("Name") or "ohne Name")
        for field, value in row.items():
            if not isinstance(value, str) or not value:
                continue
            if field == "Bild":
                if "://" in value:
                    hints.append(f"{label} / Bild: Link statt Dateiname")
                continue
            patterns = TEXT_PATTERNS + ([NAME_PATTERN] if field in NAME_FIELDS else [])
            hints += [f"{label} / {field}: {excerpt(value, match)}"
                      for pattern in patterns for match in pattern.finditer(value)]
    return hints
