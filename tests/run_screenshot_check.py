"""Three opt-in screenshot turns using the remaining original test budget."""
import json
import sys
from pathlib import Path
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests import run_live_model_check as guard
from app.ai.catalogue_answer import consult
from app.ai.dialogue_models import ChatMessage
from app.ai.interpreter_factory import create_query_interpreter
from app.repository import load_plants

QUESTIONS = ["Welche Cocktailtomaten gibt es?", "Ich suche Tomaten mit kleinen Früchten",
             "Du wirst doch Tomaten nennen können, die - geschützt oder ohne Schutz - kleine Früchte haben, in der Größe von Cocktailtomaten."]


def run():
    original = guard.load_ledger()
    guard.LEDGER = ROOT / "docs/SCREENSHOT_MODEL_RESULTS.json"
    guard.MAX_CALLS = 4  # One carried-forward accounting entry plus three calls.
    if guard.LEDGER.exists() and "--resume" not in sys.argv:
        raise ValueError("Results already exist; no automatic rerun")
    prior = sum(c.get("estimated_usd", c["reserved_usd"]) for c in original["calls"])
    ledger = {"authorized_eur": .25, "usd_reserve_limit": guard.USD_LIMIT,
              "eur_per_usd_safety_factor": 2,
              "calls": [{"status": "prior_accounting", "reserved_usd": prior,
                         "source": "LIVE_MODEL_TEST_RESULTS.json"}], "cases": []}
    if guard.LEDGER.exists():
        ledger = json.loads(guard.LEDGER.read_text(encoding="utf-8"))
    interpreter = create_query_interpreter()
    client = interpreter.client
    interpreter.client = guard.GuardedClient(client, ledger, dry_run="--live" not in sys.argv)
    history, visible = [], []
    try:
        for question in QUESTIONS:
            previous = next((c for c in ledger["cases"] if c["question"] == question), None)
            if previous:
                result = previous["result"]
                history.extend([ChatMessage(role="user", content=question), ChatMessage(role="assistant", content=result["answer"])])
                visible = [{"plant_id": p["plant_id"], "name": p["plant_name"]} for p in result["recommendations"][:3]]
                continue
            started = monotonic()
            try:
                result = consult(interpreter, load_plants(), question, history, None, visible)
            except Exception as exc:
                if "--live" in sys.argv:
                    ledger["error_class"] = type(exc).__name__
                    guard.save(ledger)
                print("Stopped:", type(exc).__name__)
                break
            ledger["cases"].append({"question": question, "duration_seconds": round(monotonic()-started, 3), "result": result})
            guard.save(ledger)
            print(json.dumps({"answer": result["answer"], "understood": result["understood_request"],
                              "names": [p["plant_name"] for p in result["recommendations"]],
                              "seconds": ledger["cases"][-1]["duration_seconds"]}, ensure_ascii=True), flush=True)
            history.extend([ChatMessage(role="user", content=question), ChatMessage(role="assistant", content=result["answer"])])
            visible = [{"plant_id": p["plant_id"], "name": p["plant_name"]} for p in result["recommendations"][:3]]
    finally:
        client.close()


if __name__ == "__main__":
    run()
