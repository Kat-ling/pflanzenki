"""Replay captured model responses offline; never instantiate a real client."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.ai.catalogue_dialogue import consult
from app.repository import load_plants

ROOT = Path(__file__).resolve().parents[1]
LEDGER = json.loads((ROOT / "tests/fixtures/dialogue_legacy.json").read_text(encoding="utf-8"))
CASES = [c for c in LEDGER["cases"] if "result" in c]
CALLS = [c for c in LEDGER["calls"] if c["status"] == "completed"]


def replay(index):
    response = SimpleNamespace(status="completed", output_text=CALLS[index]["output_text"])
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: response))
    interpreter = SimpleNamespace(client=client, model="captured-offline", categories=[])
    return consult(interpreter, load_plants(Path(__file__).parent / "fixtures/catalogue_legacy.json"), CASES[index]["question"], [])


@pytest.mark.parametrize("index", range(6))
def test_captured_response_still_selects_locally(index):
    result = replay(index)
    assert result["selection_mode"] == "local"
    assert result["plan"] == CASES[index]["result"]["plan"]
    if CASES[index]["id"] == "numeric":
        assert result["recommendations"] == []
        assert len(result["unknown"]) == 249
    else:
        assert [p["plant_id"] for p in result["recommendations"]] == [
            p["plant_id"] for p in CASES[index]["result"]["recommendations"]]
    if CASES[index]["id"] == "unknown":
        assert len(result["unknown"]) == 104
        assert "Woas I ned." in result["answer"]


if __name__ == "__main__":
    results = []
    for i, case in enumerate(CASES):
        result = replay(i)
        results.append({"id": case["id"], "recommendations": [p["plant_name"] for p in result["recommendations"]],
                        "unknown": len(result["unknown"]), "excluded": len(result["excluded"])})
    (ROOT / "docs/LIVE_MODEL_OFFLINE_REPLAY.json").write_text(
        json.dumps({"mode": "offline replay of captured responses", "extractor_version": "4", "cases": results},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
