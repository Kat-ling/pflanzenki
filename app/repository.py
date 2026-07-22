from __future__ import annotations

import json
from pathlib import Path
from app.models.domain import Plant


DEFAULT_DATA = Path(__file__).resolve().parents[1] / "data" / "normalized" / "plants.json"


def load_plants(path: str | Path = DEFAULT_DATA) -> list[Plant]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Plant.model_validate(item) for item in raw]
