from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Any

from app.advisor.text_rules import extract_text_evidence
from app.feature_catalog import (
    FEATURE_TAGS,
    POSITIVE_CHECKBOX_FIELDS,
    PlantFeature,
)
from app.models.domain import Evidence, Plant, SourceType, TruthValue


NAME_KEYS = ("Sorte", "Name", "Pflanze", "Titel")
CATEGORY_KEYS = ("Kategorie", "Typ", "Unterkategorie")
DESCRIPTION_KEYS = ("Beschreibung", "Rohbeschreibung", "Description", "Text")
RAIN_PROTECTION_KEYS = ("Regenschutz", "Dach", "Überdacht")
TAG_KEYS = ("Filter_Tags", "Besonderheiten", "Verwendung")


def split_terms(value: Any) -> list[str]:
    return [
        item.strip().casefold()
        for item in str(value or "").replace("|", ";").split(";")
        if item.strip()
    ]


def split_image_names(value: Any) -> list[str]:
    return [
        Path(item.strip()).name
        for item in str(value or "").split(",")
        if item.strip()
    ]


def add_evidence(
    evidence: list[Evidence],
    *,
    feature: PlantFeature,
    value: TruthValue,
    source: SourceType,
    quote: str,
    confidence: float,
    field_name: str | None = None,
) -> None:
    candidate = Evidence(
        feature=feature.value,
        value=value,
        source=source,
        quote=quote,
        field_name=field_name,
        confidence=confidence,
    )
    signature = (
        candidate.feature,
        candidate.value,
        candidate.source,
        candidate.quote,
        candidate.field_name,
    )
    if not any(
        (
            item.feature,
            item.value,
            item.source,
            item.quote,
            item.field_name,
        ) == signature
        for item in evidence
    ):
        evidence.append(candidate)


def first_value(row: dict[str, Any], keys: tuple[str, ...], *, preserve: bool = False) -> str:
    lowered = {str(k).strip().lower(): v for k, v in row.items()}
    for key in keys:
        value = lowered.get(key.lower())
        if value is not None and str(value).strip():
            return str(value) if preserve else str(value).strip()
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
    description = first_value(row, DESCRIPTION_KEYS, preserve=True)
    category = first_value(row, CATEGORY_KEYS) or None
    evidence = extract_text_evidence(description)

    # Tags, Besonderheiten und Verwendungszwecke sind redaktionell gepflegte
    # Positivbelege. Unbekannte Begriffe bleiben erhalten, werden aber nicht
    # eigenmächtig einem Merkmal zugeordnet.
    terms: set[str] = set()
    for key in TAG_KEYS:
        terms.update(split_terms(row.get(key)))

    for feature, aliases in FEATURE_TAGS.items():
        matches = sorted(terms & {alias.casefold() for alias in aliases})
        for match in matches:
            add_evidence(
                evidence,
                feature=feature,
                value=TruthValue.YES,
                source=SourceType.DERIVED,
                quote=match,
                field_name="Filter_Tags/Besonderheiten/Verwendung",
                confidence=0.78,
            )

    if "regenschutz" in terms:
        add_evidence(
            evidence,
            feature=PlantFeature.OUTDOOR_UNCOVERED,
            value=TruthValue.NO,
            source=SourceType.DERIVED,
            quote="regenschutz",
            field_name="Filter_Tags/Besonderheiten",
            confidence=0.82,
        )

    if "mild" in terms:
        add_evidence(
            evidence,
            feature=PlantFeature.SPICY,
            value=TruthValue.NO,
            source=SourceType.DERIVED,
            quote="mild",
            field_name="Filter_Tags/Besonderheiten",
            confidence=0.78,
        )

    # Notion-Checkboxen werden im Katalog überwiegend als Positivfelder
    # gepflegt. Ein nicht gesetztes Feld bedeutet daher UNKNOWN, nicht NO.
    for feature, field_names in POSITIVE_CHECKBOX_FIELDS.items():
        for field_name in field_names:
            if parse_checkbox(row.get(field_name)) == TruthValue.YES:
                add_evidence(
                    evidence,
                    feature=feature,
                    value=TruthValue.YES,
                    source=SourceType.STRUCTURED_FIELD,
                    quote=str(row.get(field_name)),
                    field_name=field_name,
                    confidence=0.88,
                )

    if parse_checkbox(row.get("Freiland")) == TruthValue.YES:
        add_evidence(
            evidence,
            feature=PlantFeature.OUTDOOR_UNCOVERED,
            value=TruthValue.YES,
            source=SourceType.STRUCTURED_FIELD,
            quote=str(row.get("Freiland")),
            field_name="Freiland",
            confidence=0.82,
        )

    color_value = str(row.get("Fruchtfarbe") or "").casefold()
    color_features = {
        PlantFeature.RED: ("rot",),
        PlantFeature.YELLOW: ("gelb", "gold"),
        PlantFeature.ORANGE: ("orange",),
        PlantFeature.GREEN: ("grün", "gruen"),
        PlantFeature.PURPLE: ("violett", "lila", "purpur"),
        PlantFeature.BLACK: ("schwarz",),
        PlantFeature.WHITE: ("weiß", "weiss"),
        PlantFeature.PINK: ("rosa", "pink"),
    }
    for feature, aliases in color_features.items():
        if any(alias in color_value for alias in aliases):
            add_evidence(
                evidence,
                feature=feature,
                value=TruthValue.YES,
                source=SourceType.STRUCTURED_FIELD,
                quote=color_value,
                field_name="Fruchtfarbe",
                confidence=0.9,
            )

    height_text = str(row.get("Wuchshöhe_bis_cm") or "").strip()
    try:
        height = float(height_text.replace(",", "."))
    except ValueError:
        height = 0
    if height > 0:
        if height <= 80:
            add_evidence(
                evidence,
                feature=PlantFeature.COMPACT,
                value=TruthValue.YES,
                source=SourceType.STRUCTURED_FIELD,
                quote=f"{height:g} cm",
                field_name="Wuchshöhe_bis_cm",
                confidence=0.72,
            )
        elif height >= 150:
            add_evidence(
                evidence,
                feature=PlantFeature.TALL,
                value=TruthValue.YES,
                source=SourceType.STRUCTURED_FIELD,
                quote=f"{height:g} cm",
                field_name="Wuchshöhe_bis_cm",
                confidence=0.85,
            )

    heat_text = str(row.get("Schärfegrad MAX") or "").strip()
    if heat_text:
        try:
            heat = float(heat_text.replace(",", "."))
        except ValueError:
            heat = -1
        if heat > 0:
            add_evidence(
                evidence,
                feature=PlantFeature.SPICY,
                value=TruthValue.YES,
                source=SourceType.STRUCTURED_FIELD,
                quote=heat_text,
                field_name="Schärfegrad MAX",
                confidence=0.95,
            )
        elif heat == 0:
            add_evidence(
                evidence,
                feature=PlantFeature.SPICY,
                value=TruthValue.NO,
                source=SourceType.STRUCTURED_FIELD,
                quote=heat_text,
                field_name="Schärfegrad MAX",
                confidence=0.95,
            )

    # Ein aktiv gesetztes Feld „Regenschutz“ ist ein expliziter Gegenbeleg.
    rain_value = first_value(row, RAIN_PROTECTION_KEYS)
    parsed = parse_checkbox(rain_value)
    if parsed == TruthValue.YES:
        add_evidence(
            evidence,
            feature=PlantFeature.OUTDOOR_UNCOVERED,
            value=TruthValue.NO,
            source=SourceType.STRUCTURED_FIELD,
            field_name="Regenschutz",
            quote=str(rain_value),
            confidence=0.85,
        )

    return Plant(
        id=stable_id(name),
        name=name,
        category=category,
        description=description,
        image_filenames=split_image_names(row.get("Bild")),
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
