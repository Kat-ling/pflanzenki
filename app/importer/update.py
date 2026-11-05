"""Update the catalogue from a Notion export, with a preview and safety checks.

python -m app.importer.update EXPORT.zip --vorschau   shows what would change
python -m app.importer.update EXPORT.zip              applies the change
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from app.importer.cli import write_catalog_files
from app.importer.csv_importer import first_value, NAME_KEYS, parse_csv_text, row_to_plant
from app.importer.privacy import find_personal_hints, load_privacy_rules, sanitize_row
from app.models.domain import Plant
from app.repository import load_plants

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
RULES_FILE = "data/privacy_rules.local.json"
INPUT_FILE = "data/input/notion_pflanzen.csv"
CATALOGUE_FILE = "data/normalized/plants.json"
IMAGE_DIRECTORY = "static/images"
# More than this share disappearing usually means an incomplete export.
LARGE_REMOVAL_SHARE = 0.25


@dataclass
class CatalogueUpdate:
    plants: list[Plant]
    csv_text: str
    new_images: dict[str, bytes]
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    missing_images: list[str] = field(default_factory=list)
    unused_images: list[str] = field(default_factory=list)


def is_blank(row: dict) -> bool:
    return not any(str(value or "").strip() for value in row.values())


def to_csv(rows: list[dict]) -> str:
    buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return buffer.getvalue()


def duplicates(names: list[str]) -> list[str]:
    seen, repeated = set(), []
    for name in names:
        key = name.casefold()
        if key in seen and name not in repeated:
            repeated.append(name)
        seen.add(key)
    return repeated


def compare(update: CatalogueUpdate, old: list[Plant], allow_large_removal: bool) -> None:
    previous = {p.id: p for p in old}
    current = {p.id: p for p in update.plants}
    update.added = sorted(p.name for key, p in current.items() if key not in previous)
    update.removed = sorted(p.name for key, p in previous.items() if key not in current)
    update.changed = sorted(p.name for key, p in current.items() if key in previous and (
        p.raw_fields != previous[key].raw_fields or p.image_filenames != previous[key].image_filenames))
    removed = len(update.removed)
    if not allow_large_removal and old and removed / len(old) > LARGE_REMOVAL_SHARE:
        update.problems.append(
            f"{removed} von {len(old)} Sorten würden entfallen. Ist der Export vollständig? "
            "Falls ja, mit --viele-entfernen bestätigen.")


def check_images(update: CatalogueUpdate, root: Path) -> None:
    directory = root / IMAGE_DIRECTORY
    existing = {path.name for path in directory.iterdir()} if directory.exists() else set()
    needed = {name for plant in update.plants for name in plant.image_filenames}
    update.new_images = {name: data for name, data in update.new_images.items() if name in needed}
    update.missing_images = sorted(needed - existing - set(update.new_images))
    update.unused_images = sorted(existing - needed)


def check_gaps(update: CatalogueUpdate) -> None:
    for label, gaps in (("ohne Kategorie", [p.name for p in update.plants if not p.category]),
                        ("ohne Beschreibung", [p.name for p in update.plants if not p.description.strip()])):
        if gaps:
            update.notes.append(f"{len(gaps)} Sorten {label}: " + ", ".join(sorted(gaps)))


def prepare_update(csv_text: str, root: str | Path, new_images: dict[str, bytes] | None = None,
                   allow_large_removal: bool = False, allow_personal_hints: bool = False) -> CatalogueUpdate:
    """Checks everything and writes nothing."""
    root = Path(root)
    rules = load_privacy_rules(root / RULES_FILE)
    rows = [sanitize_row(row, rules) for row in parse_csv_text(csv_text) if not is_blank(row)]
    named = [row for row in rows if first_value(row, NAME_KEYS)]
    problems = []
    if not rows:
        problems.append("Der Export enthält keine Sorten.")
    if len(named) != len(rows):
        problems.append(f"{len(rows) - len(named)} Zeilen ohne Name.")
    names = [str(first_value(row, NAME_KEYS)).strip() for row in named]
    problems += [f"Doppelter Name: {name}" for name in duplicates(names)]
    if not allow_personal_hints:
        problems += [f"Möglicher Personenbezug: {hint}" for hint in find_personal_hints(rows)]

    plants = [row_to_plant(row) for row in {str(first_value(r, NAME_KEYS)).strip().casefold(): r
                                            for r in named}.values()]
    update = CatalogueUpdate(plants, to_csv(rows), dict(new_images or {}), problems=problems)
    path = root / CATALOGUE_FILE
    compare(update, load_plants(path) if path.exists() else [], allow_large_removal)
    check_images(update, root)
    check_gaps(update)
    return update


def apply_update(update: CatalogueUpdate, root: str | Path) -> None:
    if update.problems:
        raise ValueError("Der Import wurde nicht ausgeführt: " + "; ".join(update.problems))
    root = Path(root)
    directory = root / IMAGE_DIRECTORY
    if update.new_images:
        directory.mkdir(parents=True, exist_ok=True)
    source = {root / INPUT_FILE: update.csv_text.encode("utf-8")}
    write_catalog_files(update.plants, root / CATALOGUE_FILE, extra_files=source)
    for name, data in update.new_images.items():
        (directory / name).write_bytes(data)


def select_catalog_csv(names: list[str]) -> str:
    candidates = [name for name in names
                  if name.casefold().endswith(".csv") and not name.casefold().endswith("_all.csv")]
    preferred = [name for name in candidates if "pflanzenkatalog" in Path(name).name.casefold()]
    selected = preferred or candidates
    if len(selected) != 1:
        raise ValueError("Im Notion-ZIP konnte die Katalog-CSV nicht eindeutig bestimmt werden.")
    return selected[0]


def read_source(path: str | Path) -> tuple[str, dict[str, bytes]]:
    path = Path(path)
    if path.suffix.casefold() != ".zip":
        return path.read_text(encoding="utf-8-sig"), {}
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        text = archive.read(select_catalog_csv(names)).decode("utf-8-sig")
        return text, {Path(name).name: archive.read(name) for name in names
                      if Path(name).suffix.casefold() in IMAGE_EXTENSIONS}


def import_notion_zip(zip_path: str | Path, project_root: str | Path) -> tuple[int, int, list[str]]:
    text, images = read_source(zip_path)
    update = prepare_update(text, project_root, images)
    apply_update(update, project_root)
    return len(update.plants), len(update.new_images), update.missing_images


def listing(title: str, names: list[str]) -> str:
    return f"{title}: {len(names)}" + "".join(f"\n  - {name}" for name in names)


def print_report(update: CatalogueUpdate) -> None:
    print(f"{len(update.plants)} Sorten im Export.")
    print(listing("Neu", update.added))
    print(listing("Entfällt", update.removed))
    print(listing("Geändert", update.changed))
    print(listing("Fehlende Bilder", update.missing_images))
    print(listing("Nicht mehr verwendete Bilder (bleiben liegen)", update.unused_images))
    for note in update.notes:
        print(f"Hinweis: {note}")
    for problem in update.problems:
        print(f"STOPP: {problem}")


def main(arguments: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Katalog aus einem Notion-Export aktualisieren.")
    parser.add_argument("quelle", help="Notion-ZIP oder CSV-Datei")
    parser.add_argument("--root", default=".", help="Projektordner")
    parser.add_argument("--vorschau", action="store_true", help="nur anzeigen, nichts ändern")
    parser.add_argument("--viele-entfernen", action="store_true", help="große Löschung bestätigen")
    parser.add_argument("--hinweise-ignorieren", action="store_true",
                        help="Treffer der Personenbezug-Prüfung ausdrücklich zulassen")
    options = parser.parse_args(arguments)

    text, images = read_source(options.quelle)
    update = prepare_update(text, options.root, images, options.viele_entfernen, options.hinweise_ignorieren)
    print_report(update)
    if update.problems:
        print("Nichts geändert.")
        return 1
    if options.vorschau:
        print("Vorschau: Nichts geändert.")
        return 0
    apply_update(update, options.root)
    print("Katalog aktualisiert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
