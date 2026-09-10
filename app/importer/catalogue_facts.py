"""Deterministic, offline facts and complete source corpus for local selection.

One atomic sidecar contains both registry and facts so their versions cannot
be mixed. Existing v0.5 recommendation evidence is deliberately not reused.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
import re
from pathlib import Path
import tempfile

from app.models.catalogue_facts import (
    CatalogueFact, FactBundle, ImportIssue, PreparedPlant,
    PropertyDefinition, SourceReference,
)
from app.models.domain import Plant

SCHEMA_VERSION = "2"
EXTRACTOR_VERSION = "4"

# Data rather than a feature enum. Additional reviewed field definitions can
# be supplied to build_bundle; unknown fields remain in the source corpus.
DEFAULT_REGISTRY = [
    PropertyDefinition(property_id=key, field=field, value_type="boolean",
                       semantics="explicit_positive", positive_only=True)
    for key, field in [
        ("site.outdoor", "Freiland"),
        ("site.container", "Balkon / Topf"),
        ("site.greenhouse_or_roof", "Gewächshaus / unter Dach"),
        ("site.protected", "Geschützter Standort"),
        ("site.warm", "Warmer Standort"),
        ("care.drought_tolerant", "Trockenheitsverträglich"),
        ("plant.climbing", "Rankend"),
        ("plant.overwinterable", "Überwinterbar"),
        ("plant.winter_hardy", "Winterhart"),
        ("plant.robust_or_resistant", "Robust/Resistent"),
    ]
] + [
    PropertyDefinition(property_id="plant.height", field="Wuchshöhe_bis_cm",
                       value_type="number", semantics="upper_bound", unit="cm", minimum=0.0),
    PropertyDefinition(property_id="fruit.heat", field="Schärfegrad MAX",
                       value_type="number", semantics="upper_bound", minimum=0.0),
    PropertyDefinition(property_id="harvest.start_month", field="Ernte_von_Monat",
                       value_type="number", semantics="calendar_month", minimum=1.0, maximum=12.0),
    PropertyDefinition(property_id="harvest.end_month", field="Ernte_bis_Monat",
                       value_type="number", semantics="calendar_month", minimum=1.0, maximum=12.0),
    PropertyDefinition(property_id="fruit.color", field="Fruchtfarbe",
                       value_type="text", semantics="verbatim_unparsed"),
]

from app.importer.text_facts import TEXT_REGISTRY, extract_description

DEFAULT_REGISTRY += [d for d in TEXT_REGISTRY
                     if d.property_id not in {p.property_id for p in DEFAULT_REGISTRY}]


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def original_fields(plant: Plant) -> dict[str, str]:
    return {str(k): str(v) for k, v in plant.raw_fields.items()
            if v is not None and str(v).strip()}


def source_is_valid(source: SourceReference, fields: dict[str, str]) -> bool:
    text = fields.get(source.field)
    return (text is not None and source.field_hash == digest(text)
            and 0 <= source.start < source.end <= len(text)
            and text[source.start:source.end] == source.quote)


def parse_value(text: str, definition: PropertyDefinition):
    cleaned = text.strip()
    if not cleaned:
        return None, "missing"
    if definition.value_type == "text":
        return text, None
    if definition.value_type == "boolean":
        token = cleaned.casefold()
        if token in {"1", "true", "yes", "ja", "x", "✓", "checked"}:
            return True, None
        if token in {"0", "false", "no", "nein", "unchecked"}:
            return (None, "unchecked_positive") if definition.positive_only else (False, None)
        return None, "invalid_value"
    try:
        value = float(cleaned.replace(",", "."))
    except ValueError:
        return None, "invalid_value"
    if not math.isfinite(value):
        return None, "invalid_value"
    if value == 0 and definition.property_id != "fruit.heat":
        return None, "placeholder_zero"
    if ((definition.minimum is not None and value < definition.minimum)
            or (definition.maximum is not None and value > definition.maximum)
            or (definition.semantics == "calendar_month" and not value.is_integer())):
        return None, "invalid_value"
    return value, None


def prepare_plant(plant: Plant, registry: list[PropertyDefinition]) -> PreparedPlant:
    fields = original_fields(plant)
    facts, issues = [], []
    for definition in registry:
        if definition.field == "Beschreibung":
            continue  # Description rules require sentence context, not checkbox parsing.
        text = fields.get(definition.field, "")
        value, reason = parse_value(text, definition)
        if reason:
            issues.append(ImportIssue(field=definition.field, reason=reason))
            continue
        source = SourceReference(field=definition.field, field_hash=digest(text),
                                 start=0, end=len(text), quote=text)
        facts.append(CatalogueFact(
            fact_id=digest([plant.id, definition.model_dump(), source.model_dump(), value]),
            plant_id=plant.id, property_id=definition.property_id, value=value,
            unit=definition.unit, semantics=definition.semantics, source=source,
        ))
    allowed = {d.property_id for d in registry}
    facts.extend(f for f in extract_description(plant.id, fields) if f.property_id in allowed)
    # Legacy imports sometimes copied fruit dimensions or planting distances
    # into the height column. A matching unrelated measurement is not proof
    # of plant height. Keep both original sources and abstain pending review.
    from app.importer.text_facts import sentences
    height_facts = [f for f in facts if f.property_id == "plant.height"
                    and f.origin == "structured_field"]
    for field in ("Beschreibung", "Rohbeschreibung", "Description", "Text"):
        description = fields.get(field, "")
        for sentence in sentences(description):
            fragment = sentence.group()
            if (not re.search(r"frucht|früchte|köpfe|kopf|abstand|\d\s*[x×]\s*\d", fragment, re.I)
                    or re.search(r"hoch|höhe", fragment, re.I)):
                continue
            numbers = [float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[.,]\d+)?", fragment)]
            if not re.search(r"\bcm\b", fragment, re.I) or not any(f.value in numbers for f in height_facts):
                continue
            source = SourceReference(field=field, field_hash=digest(description),
                                     start=sentence.start(), end=sentence.end(), quote=fragment)
            facts.append(CatalogueFact(
                fact_id=digest([plant.id, "height_object_uncertain", source.model_dump()]),
                plant_id=plant.id, property_id="plant.height", value="height object uncertain",
                unit="cm", semantics="upper_bound", source=source,
                origin="description_rule", semantic_status="ambiguous",
            ))
    return PreparedPlant(plant_id=plant.id, content_hash=digest(plant.model_dump(mode="json")),
                         facts=facts, issues=issues, source_fields=fields)


def build_bundle(plants: list[Plant], registry: list[PropertyDefinition] | None = None) -> FactBundle:
    registry = DEFAULT_REGISTRY if registry is None else registry
    if len({p.id for p in plants}) != len(plants):
        raise ValueError("Doppelte Pflanzen-IDs: Faktenbestand wurde nicht aktiviert.")
    if len({p.property_id for p in registry}) != len(registry):
        raise ValueError("Doppelte Eigenschafts-IDs in der Registry.")
    prepared = [prepare_plant(p, registry) for p in plants]
    bundle = FactBundle(
        schema_version=SCHEMA_VERSION, extractor_version=EXTRACTOR_VERSION,
        registry_hash=digest([d.model_dump() for d in registry]),
        catalogue_revision=digest([p.model_dump(mode="json") for p in plants]),
        registry=registry, plants=prepared,
    )
    for plant in bundle.plants:
        if not all(source_is_valid(f.source, plant.source_fields) for f in plant.facts):
            raise ValueError("Ungültige Originalquelle im Faktenbestand.")
    return bundle


def bundle_report(bundle: FactBundle) -> dict:
    return {
        "catalogue_revision": bundle.catalogue_revision,
        "plants": len(bundle.plants),
        "facts": sum(len(p.facts) for p in bundle.plants),
        "facts_by_property": dict(sorted(Counter(
            f.property_id for p in bundle.plants for f in p.facts).items())),
        "issues_by_reason": dict(sorted(Counter(
            issue.reason for p in bundle.plants for issue in p.issues).items())),
        "semantic_status": dict(Counter(f.semantic_status for p in bundle.plants for f in p.facts)),
        "text_extraction": "conservative rules; unparsed mentions remain unknown",
    }


def write_bundle(bundle: FactBundle, output: str | Path) -> None:
    """Atomic sidecar replacement; identical imports leave the file untouched."""
    output = Path(output)
    content = (bundle.model_dump_json(indent=2) + "\n").encode("utf-8")
    if output.exists() and output.read_bytes() == content:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        temporary.replace(output)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main() -> None:
    """Build a sidecar without rewriting the existing catalogue or images."""
    import argparse
    from app.repository import load_plants

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Existing normalized plants.json")
    parser.add_argument("output", type=Path, help="New catalogue_facts.json sidecar")
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error("Input and sidecar output must be different files.")
    bundle = build_bundle(load_plants(args.input))
    write_bundle(bundle, args.output)
    print(json.dumps(bundle_report(bundle), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
