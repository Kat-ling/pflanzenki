"""Adding, changing and removing varieties through a Notion export."""
import csv
import io
import json
import zipfile

import pytest

from app.importer.update import apply_update, main, prepare_update
from app.repository import load_plants


def table(*rows):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["Name", "Kategorie", "Beschreibung", "Bild"], lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


def row(name, description="Text.", category="Tomate", image=""):
    return {"Name": name, "Kategorie": category, "Beschreibung": description, "Bild": image}


def install(root, *rows):
    apply_update(prepare_update(table(*rows), root, allow_large_removal=True), root)


def test_report_names_added_removed_and_changed_varieties(tmp_path):
    install(tmp_path, row("Alt"), row("Bleibt"), row("Geändert"), row("Vierte"))
    update = prepare_update(table(row("Bleibt"), row("Geändert", "Neu."), row("Vierte"), row("Neu")), tmp_path)
    assert update.added == ["Neu"]
    assert update.removed == ["Alt"]
    assert update.changed == ["Geändert"]
    assert update.problems == []


def test_preview_changes_nothing(tmp_path):
    install(tmp_path, row("Alt"))
    before = (tmp_path / "data/normalized/plants.json").read_bytes()
    prepare_update(table(row("Alt"), row("Neu")), tmp_path)
    assert (tmp_path / "data/normalized/plants.json").read_bytes() == before


def test_removed_variety_disappears_from_all_catalogue_files(tmp_path):
    install(tmp_path, row("Vergriffen", category="Lauch"), row("A"), row("B"), row("C"))
    apply_update(prepare_update(table(row("A"), row("B"), row("C")), tmp_path), tmp_path)
    normalized = tmp_path / "data/normalized"
    assert [p.name for p in load_plants(normalized / "plants.json")] == ["A", "B", "C"]
    assert json.loads((normalized / "categories.json").read_text(encoding="utf-8")) == ["Tomate"]
    assert "Vergriffen" not in (normalized / "catalogue_facts.json").read_text(encoding="utf-8")
    assert "Vergriffen" not in (tmp_path / "data/input/notion_pflanzen.csv").read_text(encoding="utf-8")


def test_new_category_is_available_without_code_change(tmp_path):
    install(tmp_path, row("A"), row("B"), row("C"))
    update = prepare_update(table(row("A"), row("B"), row("C"), row("Neu", category="Pastinake")), tmp_path)
    apply_update(update, tmp_path)
    categories = json.loads((tmp_path / "data/normalized/categories.json").read_text(encoding="utf-8"))
    assert "Pastinake" in categories


def test_partial_export_is_blocked_before_writing(tmp_path):
    install(tmp_path, *[row(f"S{i}") for i in range(10)])
    update = prepare_update(table(row("S1")), tmp_path)
    assert any("9 von 10" in problem for problem in update.problems)
    with pytest.raises(ValueError):
        apply_update(update, tmp_path)
    assert len(load_plants(tmp_path / "data/normalized/plants.json")) == 10


def test_intended_large_removal_can_be_confirmed(tmp_path):
    install(tmp_path, *[row(f"S{i}") for i in range(10)])
    update = prepare_update(table(row("S1")), tmp_path, allow_large_removal=True)
    assert update.problems == []


@pytest.mark.parametrize("rows, message", [
    ([row(""), row("A")], "ohne Name"),
    ([row("A"), row("A")], "Doppelt"),
    ([row("Tomate (von Erika)")], "Personenbezug"),
])
def test_bad_rows_block_the_import(tmp_path, rows, message):
    update = prepare_update(table(*rows), tmp_path)
    assert any(message in problem for problem in update.problems)


def test_blank_rows_from_notion_are_ignored(tmp_path):
    update = prepare_update(table(row("A"), row("", "", "")), tmp_path)
    assert update.problems == []
    assert [p.name for p in update.plants] == ["A"]


def test_gaps_are_reported_without_blocking(tmp_path):
    update = prepare_update(table(row("A", "", "", "fehlt.jpg")), tmp_path)
    assert update.problems == []
    assert any("Beschreibung" in note for note in update.notes)
    assert any("Kategorie" in note for note in update.notes)
    assert update.missing_images == ["fehlt.jpg"]


def test_images_of_removed_varieties_are_reported_and_kept(tmp_path):
    images = tmp_path / "static/images"
    images.mkdir(parents=True)
    (images / "alt.jpg").write_bytes(b"x")
    update = prepare_update(table(row("Neu", image="neu.jpg")), tmp_path, new_images={"neu.jpg": b"y"})
    apply_update(update, tmp_path)
    assert update.unused_images == ["alt.jpg"]
    assert (images / "alt.jpg").exists() and (images / "neu.jpg").read_bytes() == b"y"


def test_written_csv_contains_no_cloud_link_or_private_term(tmp_path):
    image = "https://cloud.example/privat/a.jpg"
    (tmp_path / "data").mkdir()
    (tmp_path / "data/privacy_rules.local.json").write_text(
        json.dumps({"replacements": [{"find": " von Erika", "replace": ""}]}), encoding="utf-8")
    apply_update(prepare_update(table(row("Tomate von Erika", image=image)), tmp_path), tmp_path)
    text = (tmp_path / "data/input/notion_pflanzen.csv").read_text(encoding="utf-8")
    assert "cloud.example" not in text and "Erika" not in text
    plant = load_plants(tmp_path / "data/normalized/plants.json")[0]
    assert plant.name == "Tomate" and plant.image_filenames == ["a.jpg"]


def test_failed_write_keeps_the_previous_catalogue(tmp_path, monkeypatch):
    from pathlib import Path
    install(tmp_path, row("Alt"))
    path = tmp_path / "data/normalized/plants.json"
    before = path.read_bytes()
    update = prepare_update(table(row("Alt"), row("Neu")), tmp_path)
    def fail(*args, **kwargs):
        raise OSError("Datenträger voll")
    monkeypatch.setattr(Path, "write_bytes", fail)
    with pytest.raises(OSError):
        apply_update(update, tmp_path)
    assert path.read_bytes() == before
    assert not list(path.parent.glob("*.staged"))


def test_command_preview_and_apply(tmp_path, capsys):
    export = tmp_path / "export.zip"
    with zipfile.ZipFile(export, "w") as archive:
        archive.writestr("Pflanzenkatalog.csv", table(row("Neu", image="a.jpg")).encode("utf-8-sig"))
        archive.writestr("a.jpg", b"x")
    root = tmp_path / "projekt"
    assert main([str(export), "--root", str(root), "--vorschau"]) == 0
    assert "Neu" in capsys.readouterr().out
    assert not (root / "data").exists()
    assert main([str(export), "--root", str(root)]) == 0
    assert (root / "static/images/a.jpg").exists()


def test_command_reports_blocked_import(tmp_path, capsys):
    source = tmp_path / "katalog.csv"
    source.write_text(table(row("Tomate (von Erika)")), encoding="utf-8")
    assert main([str(source), "--root", str(tmp_path / "p")]) == 1
    assert "Personenbezug" in capsys.readouterr().out
