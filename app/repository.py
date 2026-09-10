from __future__ import annotations

import json
from pathlib import Path
from app.models.domain import Plant


DEFAULT_DATA = Path(__file__).resolve().parents[1] / "data" / "normalized" / "plants.json"
DEFAULT_CATEGORIES = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "normalized"
    / "categories.json"
)


def load_plants(path: str | Path = DEFAULT_DATA) -> list[Plant]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Plant.model_validate(item) for item in raw]


def load_categories(path: str | Path = DEFAULT_CATEGORIES) -> list[str]:
    category_path = Path(path)
    if category_path.exists():
        raw = json.loads(category_path.read_text(encoding="utf-8"))
        return [str(item) for item in raw]

    return sorted(
        {
            plant.category
            for plant in load_plants()
            if plant.category
        },
        key=str.casefold,
    )
