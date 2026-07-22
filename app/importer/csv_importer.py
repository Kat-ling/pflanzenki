from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Any

from app.advisor.text_rules import extract_outdoor_uncovered_evidence
from app.models.domain import Evidence, Plant, SourceType, TruthValue


NAME_KEYS = ("Sorte", "Name", "Pflanze", "Titel")
CATEGORY_KEYS = ("Kategorie", "Typ", "Unterkategorie")
DESCRIPTION_KEYS = ("Beschreibung", "Rohbeschreibung", "Description", "Text")
RAIN_PROTECTION_KEYS = ("Regenschutz", "Dach", "Überdacht", "Geschützter Standort")


def first_value(row: dict[str, Any], keys: tuple[str, ...]) -> str:
    lowered = {str(k).strip().lower(): v for k, v in row.items()}
    for key in keys:
        value = lowered.get(key.lower())
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def parse_checkbox(value: Any) -> TruthValue:
    text = str(value or "").strip().lower()
    if not text:
        return TruthValue.UNKNOWN
    if text in {"1", "true", "yes", "ja", "x", "✓", "checked"}:
        return TruthValue.YES
    if text in {"0", "false", "no", "nein", "unchecked"}:
        return TruthValue.NO
    return TruthValue.UNKNOWN


def stable_id(name: str) -> str:
    return hashlib.sha1(name.encode("utf-8")).hexdigest()[:12]


def row_to_plant(row: dict[str, Any]) -> Plant:
    name = first_value(row, NAME_KEYS) or "Unbenannte Pflanze"
    description = first_value(row, DESCRIPTION_KEYS)
    category = first_value(row, CATEGORY_KEYS) or None
    evidence = extract_outdoor_uncovered_evidence(description)

    # Ein aktiv gesetztes Feld „Regenschutz“ bedeutet: ohne Dach eher ungeeignet.
    # Leer bleibt UNKNOWN und erzeugt ausdrücklich keinen Negativbeleg.
    rain_value = first_value(row, RAIN_PROTECTION_KEYS)
    parsed = parse_checkbox(rain_value)
    if parsed == TruthValue.YES:
        evidence.append(Evidence(
            feature="outdoor_uncovered",
            value=TruthValue.NO,
            source=SourceType.STRUCTURED_FIELD,
            field_name="Regenschutz",
            quote=str(rain_value),
            confidence=0.85,
        ))
    elif parsed == TruthValue.NO:
        evidence.append(Evidence(
            feature="outdoor_uncovered",
            value=TruthValue.YES,
            source=SourceType.STRUCTURED_FIELD,
            field_name="Regenschutz",
            quote=str(rain_value),
            confidence=0.75,
        ))

    return Plant(
        id=stable_id(name),
        name=name,
        category=category,
        description=description,
        raw_fields={str(k): v for k, v in row.items()},
        evidence=evidence,
    )


def import_csv(path: str | Path) -> list[Plant]:
    path = Path(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(8192)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        return [row_to_plant(row) for row in csv.DictReader(handle, dialect=dialect)]
