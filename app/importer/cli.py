from __future__ import annotations

import json
import sys
from pathlib import Path
from app.importer.csv_importer import import_csv


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python -m app.importer.cli INPUT.csv OUTPUT.json")
    plants = import_csv(sys.argv[1])
    output = Path(sys.argv[2])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps([p.model_dump(mode="json") for p in plants], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"{len(plants)} Pflanzen nach {output} geschrieben.")


if __name__ == "__main__":
    main()
