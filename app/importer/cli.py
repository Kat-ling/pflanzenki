from __future__ import annotations

import json
from pathlib import Path

from app.feature_catalog import FEATURE_DESCRIPTIONS, PlantFeature
from app.models.domain import Plant
from app.importer.catalogue_facts import build_bundle, bundle_report


def write_staged(files: dict[Path, bytes]) -> None:
    """All files are written beside their target first, then swapped in together."""
    staged = {path: path.with_name(path.name + ".staged") for path in files}
    try:
        for path, content in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            staged[path].write_bytes(content)
        for path, temporary in staged.items():
            temporary.replace(path)
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)


def as_json(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")


def write_catalog_files(
    plants: list[Plant],
    output: str | Path,
    extra_files: dict[Path, bytes] | None = None,
) -> None:
    # Validate IDs and source references before touching any output file.
    facts = build_bundle(plants)
    output = Path(output)
    categories = sorted(
        {plant.category for plant in plants if plant.category},
        key=str.casefold,
    )
    features = [
        {"id": feature.value, "description": FEATURE_DESCRIPTIONS[feature]}
        for feature in PlantFeature
    ]
    write_staged({
        output: as_json([plant.model_dump(mode="json") for plant in plants]),
        output.parent / "categories.json": as_json(categories),
        output.parent / "features.json": as_json(features),
        output.parent / "catalogue_facts.json": (facts.model_dump_json(indent=2) + "\n").encode("utf-8"),
        **(extra_files or {}),
    })
    report = bundle_report(facts)
    print(f"{report['facts']} Originalbelege vorbereitet (einschließlich unklarer Angaben).")
    print(f"Prüfstatus: {report['semantic_status']}")
    print(f"{len(plants)} Pflanzen nach {output} geschrieben.")
    print(
        f"{len(categories)} Kategorien und "
        f"{len(PlantFeature)} Merkmale aktualisiert."
    )


def main() -> None:
    raise SystemExit(
        "Dieser Befehl wurde ersetzt, damit jeder Import die Prüfungen durchläuft: "
        "python -m app.importer.update QUELLE"
    )


if __name__ == "__main__":
    main()
