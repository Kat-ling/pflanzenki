import json

import pytest

from app.importer.catalogue_facts import (
    build_bundle, bundle_report, digest, source_is_valid, write_bundle,
)
from app.importer.cli import write_catalog_files
from app.importer.csv_importer import row_to_plant
from app.models.catalogue_facts import FactBundle, PropertyDefinition


def prepare(fields):
    return build_bundle([row_to_plant({"Name": "Probe", **fields})]).plants[0]


def test_freiland_does_not_imply_no_roof():
    plant = prepare({"Freiland": "Yes", "Beschreibung": "Nur mit Regenschutz geeignet."})
    assert ("site.outdoor", True) in [(f.property_id, f.value) for f in plant.facts]
    assert ("site.uncovered", False) in [(f.property_id, f.value) for f in plant.facts]
    assert plant.facts[0].semantic_status == "unreviewed"
    assert plant.source_fields["Beschreibung"] == "Nur mit Regenschutz geeignet."


@pytest.mark.parametrize("value", ["", "No", "false", "0", "unchecked"])
def test_empty_or_unchecked_positive_is_not_negative(value):
    plant = prepare({"Freiland": value})
    assert not plant.facts
    assert any(i.field == "Freiland" for i in plant.issues)


def test_numeric_zero_exception_and_units():
    plant = prepare({"Schärfegrad MAX": "0", "Wuchshöhe_bis_cm": "0",
                     "Ernte_von_Monat": "0"})
    assert [(f.property_id, f.value) for f in plant.facts] == [("fruit.heat", 0.0)]
    height = prepare({"Wuchshöhe_bis_cm": "70,5"}).facts[0]
    assert (height.value, height.unit, height.semantics) == (70.5, "cm", "upper_bound")
    assert height.source.quote == "70,5"


@pytest.mark.parametrize("value", ["NaN", "inf", "-1", "13", "2.5", "Juni"])
def test_invalid_months_are_not_facts(value):
    plant = prepare({"Ernte_von_Monat": value})
    assert not plant.facts
    assert any(i.field == "Ernte_von_Monat" and i.reason == "invalid_value" for i in plant.issues)


def test_sources_are_exact_unicode_and_full_field_not_normalized():
    text = "  Gelb und grün – bei Reife rot.\nWeitere Einschränkung.  "
    plant = prepare({"Fruchtfarbe": text, "Unbekanntes Feld": "Neue Eigenschaft"})
    fact = plant.facts[0]
    assert fact.value == text
    assert fact.source.quote == text
    assert fact.source.end == len(text)
    assert source_is_valid(fact.source, plant.source_fields)
    assert not source_is_valid(fact.source, {"Fruchtfarbe": text.strip()})
    assert not source_is_valid(fact.source.model_copy(update={"end": 9999}), plant.source_fields)
    assert plant.source_fields["Unbekanntes Feld"] == "Neue Eigenschaft"


def test_registry_can_extend_without_feature_enum():
    definition = PropertyDefinition(property_id="fruit.storage_note", field="Lagerhinweis",
                                    value_type="text", semantics="verbatim_unparsed")
    bundle = build_bundle([row_to_plant({"Name": "A", "Lagerhinweis": "Kühl lagern."})], [definition])
    assert bundle.plants[0].facts[0].property_id == "fruit.storage_note"
    assert bundle.plants[0].facts[0].source.field == "Lagerhinweis"


def test_duplicate_ids_reject_import_before_output_changes(tmp_path):
    output = tmp_path / "plants.json"
    output.write_text("existing", encoding="utf-8")
    with pytest.raises(ValueError, match="Doppelte Pflanzen-IDs"):
        write_catalog_files([row_to_plant({"Name": "A"})] * 2, output)
    assert output.read_text() == "existing"
    assert not (tmp_path / "catalogue_facts.json").exists()


def test_revision_changes_when_description_changes_or_plant_is_deleted():
    plants = [row_to_plant({"Name": "A", "Beschreibung": "Alt"}), row_to_plant({"Name": "B"})]
    initial = build_bundle(plants)
    plants[0] = row_to_plant({"Name": "A", "Beschreibung": "Neu"})
    updated = build_bundle(plants)
    assert initial.catalogue_revision != updated.catalogue_revision
    assert initial.plants[0].content_hash != updated.plants[0].content_hash
    assert initial.plants[1] == updated.plants[1]
    assert len(build_bundle(plants[:1]).plants) == 1


def test_bundle_roundtrip_and_identical_import_does_not_write(tmp_path):
    bundle = build_bundle([row_to_plant({"Name": "A", "Freiland": "Yes"})])
    output = tmp_path / "catalogue_facts.json"
    write_bundle(bundle, output)
    first_stat = output.stat()
    assert FactBundle.model_validate_json(output.read_bytes()) == bundle
    write_bundle(bundle, output)
    assert output.stat().st_mtime_ns == first_stat.st_mtime_ns
    assert bundle.registry_hash == digest([d.model_dump() for d in bundle.registry])


def test_failed_atomic_replace_preserves_previous_bundle(tmp_path, monkeypatch):
    from pathlib import Path
    output = tmp_path / "catalogue_facts.json"
    output.write_text("previous", encoding="utf-8")
    def fail(*args):
        raise OSError("simulated disk error")
    monkeypatch.setattr(Path, "replace", fail)
    with pytest.raises(OSError, match="disk error"):
        write_bundle(build_bundle([]), output)
    assert output.read_text() == "previous"
    assert list(tmp_path.iterdir()) == [output]


def test_csv_writer_includes_source_bundle_and_keeps_originals(tmp_path):
    plant = row_to_plant({"Name": "A", "Beschreibung": "Nicht ohne Dach.",
                         "Freiland": "Yes", "Bild": "a.jpg"})
    original = plant.model_dump(mode="json")
    write_catalog_files([plant], tmp_path / "plants.json")
    assert json.loads((tmp_path / "plants.json").read_text(encoding="utf-8")) == [original]
    bundle = FactBundle.model_validate_json((tmp_path / "catalogue_facts.json").read_bytes())
    assert bundle.plants[0].source_fields == plant.raw_fields
    assert bundle_report(bundle)["facts_by_property"]["site.outdoor"] == 1
    assert bundle_report(bundle)["facts_by_property"]["site.uncovered"] == 1


def test_real_catalogue_sources_and_ids_are_complete():
    from app.repository import load_plants
    plants = load_plants()
    bundle = build_bundle(plants)
    assert len(bundle.plants) == len(plants)
    for original, prepared in zip(plants, bundle.plants):
        assert prepared.plant_id == original.id
        for key, value in original.raw_fields.items():
            if value is not None and str(value).strip():
                assert prepared.source_fields[key] == str(value)
        assert all(source_is_valid(f.source, prepared.source_fields) for f in prepared.facts)
