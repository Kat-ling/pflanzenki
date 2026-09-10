from __future__ import annotations

import json
import sys
from pathlib import Path

from app.feature_catalog import FEATURE_DESCRIPTIONS, PlantFeature
from app.importer.csv_importer import import_csv
from app.models.domain import Plant
from app.importer.catalogue_facts import build_bundle, bundle_report, write_bundle


def write_catalog_files(
    plants: list[Plant],
    output: str | Path,
) -> None:
    # Validate IDs and source references before touching any output file.
    facts = build_bundle(plants)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            [plant.model_dump(mode="json") for plant in plants],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    categories = sorted(
        {plant.category for plant in plants if plant.category},
        key=str.casefold,
    )
    (output.parent / "categories.json").write_text(
        json.dumps(categories, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output.parent / "features.json").write_text(
        json.dumps(
            [
                {
                    "id": feature.value,
                    "description": FEATURE_DESCRIPTIONS[feature],
                }
                for feature in PlantFeature
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    write_bundle(facts, output.parent / "catalogue_facts.json")
    report = bundle_report(facts)
    print(f"{report['facts']} Originalbelege vorbereitet (einschließlich unklarer Angaben).")
    print(f"Prüfstatus: {report['semantic_status']}")
    print(f"{len(plants)} Pflanzen nach {output} geschrieben.")
    print(
        f"{len(categories)} Kategorien und "
        f"{len(PlantFeature)} Merkmale aktualisiert."
    )


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(
            "Usage: python -m app.importer.cli INPUT.csv OUTPUT.json"
        )
    plants = import_csv(sys.argv[1])
    write_catalog_files(plants, sys.argv[2])


if __name__ == "__main__":
    main()
