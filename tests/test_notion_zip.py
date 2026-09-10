import csv
import io
import json
import zipfile

from app.importer.notion_zip import import_notion_zip


def test_notion_zip_imports_catalog_and_referenced_images(tmp_path):
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=["Name", "Kategorie", "Beschreibung", "Bild"],
    )
    writer.writeheader()
    writer.writerow({
        "Name": "Gold Rush",
        "Kategorie": "Zucchini",
        "Beschreibung": "Gelbe Zucchini.",
        "Bild": "gold.jpg",
    })

    zip_path = tmp_path / "notion.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "Pflanzenkatalog abc.csv",
            buffer.getvalue().encode("utf-8-sig"),
        )
        archive.writestr("gold.jpg", b"test-image")

    project_root = tmp_path / "project"
    plants, images, missing = import_notion_zip(
        zip_path,
        project_root,
    )

    assert (plants, images, missing) == (1, 1, [])
    imported_csv = (
        project_root / "data" / "input" / "notion_pflanzen.csv"
    ).read_bytes()
    assert b"\r" not in imported_csv
    assert not imported_csv.startswith(b"\xef\xbb\xbf")
    assert (
        project_root / "static" / "images" / "gold.jpg"
    ).read_bytes() == b"test-image"
    normalized = json.loads(
        (
            project_root / "data" / "normalized" / "plants.json"
        ).read_text(encoding="utf-8")
    )
    assert normalized[0]["image_filenames"] == ["gold.jpg"]
