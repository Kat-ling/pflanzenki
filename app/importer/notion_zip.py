from __future__ import annotations

import csv
import io
import sys
import zipfile
from pathlib import Path

from app.importer.cli import write_catalog_files
from app.importer.csv_importer import import_csv, split_image_names


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


def select_catalog_csv(names: list[str]) -> str:
    candidates = [
        name
        for name in names
        if name.casefold().endswith(".csv")
        and not name.casefold().endswith("_all.csv")
    ]
    preferred = [
        name
        for name in candidates
        if "pflanzenkatalog" in Path(name).name.casefold()
    ]
    selected = preferred or candidates
    if len(selected) != 1:
        raise ValueError(
            "Im Notion-ZIP konnte die Katalog-CSV nicht eindeutig "
            "bestimmt werden."
        )
    return selected[0]


def import_notion_zip(
    zip_path: str | Path,
    project_root: str | Path,
) -> tuple[int, int, list[str]]:
    zip_path = Path(zip_path)
    project_root = Path(project_root)
    input_path = project_root / "data" / "input" / "notion_pflanzen.csv"
    output_path = project_root / "data" / "normalized" / "plants.json"
    image_directory = project_root / "static" / "images"

    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        csv_name = select_catalog_csv(names)
        csv_bytes = archive.read(csv_name)
        csv_text = csv_bytes.decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(csv_text)))

        input_path.parent.mkdir(parents=True, exist_ok=True)
        normalized_csv = csv_text.replace("\r\n", "\n").replace("\r", "\n")
        input_path.write_text(normalized_csv, encoding="utf-8", newline="\n")
        image_directory.mkdir(parents=True, exist_ok=True)

        members_by_name = {
            Path(name).name: name
            for name in names
            if Path(name).suffix.casefold() in IMAGE_EXTENSIONS
        }
        requested_images = {
            image_name
            for row in rows
            for image_name in split_image_names(row.get("Bild"))
        }
        missing: list[str] = []
        copied = 0

        for image_name in sorted(requested_images):
            member = members_by_name.get(image_name)
            if member is None:
                missing.append(image_name)
                continue
            (image_directory / image_name).write_bytes(archive.read(member))
            copied += 1

    plants = import_csv(input_path)
    write_catalog_files(plants, output_path)
    return len(plants), copied, missing


def main() -> None:
    if len(sys.argv) not in {2, 3}:
        raise SystemExit(
            "Usage: python -m app.importer.notion_zip NOTION_EXPORT.zip "
            "[PROJECT_ROOT]"
        )

    project_root = Path(sys.argv[2]) if len(sys.argv) == 3 else Path.cwd()
    plants, images, missing = import_notion_zip(sys.argv[1], project_root)
    print(f"{plants} Pflanzen und {images} Bilder importiert.")
    if missing:
        print("Fehlende Bilddateien: " + ", ".join(missing))


if __name__ == "__main__":
    main()
