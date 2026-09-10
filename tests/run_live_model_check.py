"""Opt-in paid smoke test; never collected by pytest. No automatic retries.

Default is dry-run. --live spends against a persistent conservative ledger.
The model/prices and euro reserve were reviewed for this specific test run.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.ai.catalogue_dialogue import consult
from app.ai.dialogue_models import ChatMessage, DialoguePlan
from app.ai.interpreter_factory import create_query_interpreter
from app.repository import load_plants

LEDGER = ROOT / "docs/LIVE_MODEL_TEST_RESULTS.json"
MODEL = "gpt-5-mini"
USD_LIMIT = 0.10  # 0.20 EUR at conservative 2 EUR/USD; below 0.25 EUR authorization.
MAX_CALLS = 8  # Six cases, with at most two explicitly reviewed failed attempts.
CASES = [
    ("freiland_large", "Welche Tomate eignet sich für Freiland und hat große Früchte?"),
    ("correction", "Doch lieber kleine Früchte, alles andere bleibt."),
    ("alternatives", "Ich suche Tomaten mit (roten und kleinen Früchten) oder (gelben und großen Früchten)."),
    ("negation", "Welche Paprika sind süß und nicht scharf?"),
    ("numeric", "Welche Pflanzen sind höchstens 80 cm hoch?"),
    ("unknown", "Welche Tomate hat nachweislich weniger als fünf Kerne pro Frucht?"),
]


def save(data):
    temporary = LEDGER.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(LEDGER)


def load_ledger():
    if LEDGER.exists():
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    return {"authorized_eur": 0.25, "usd_reserve_limit": USD_LIMIT,
            "eur_per_usd_safety_factor": 2, "model": MODEL,
            "pricing_source": "https://developers.openai.com/api/docs/models/gpt-5-mini",
            "pricing_usd_per_million": {"input": 0.25, "cached_input": 0.025, "output": 2.0},
            "calls": [], "cases": [], "stopped": False}


class GuardedClient:
    def __init__(self, client, ledger, dry_run=False):
        self.client, self.ledger, self.dry_run = client, ledger, dry_run
        self.responses = self

    def with_options(self, **options):
        if options != {"timeout": 30.0, "max_retries": 0}:
            raise ValueError("Unexpected request limits")
        self.client = self.client.with_options(**options)
        return self

    def create(self, **kwargs):
        if kwargs.get("model") != MODEL or kwargs.get("max_output_tokens") != 4000 or kwargs.get("store") is not False:
            raise ValueError("Unexpected model or output limit")
        if str(self.client.base_url) != "https://api.openai.com/v1/":
            raise ValueError("Live test requires the official OpenAI endpoint")
        # UTF-8 byte length overestimates ordinary text tokenization. Include
        # schema/instructions and a further 2,048 tokens of protocol headroom.
        size = len(json.dumps(kwargs, ensure_ascii=False).encode("utf-8"))
        reserve = (size + 2048) * 0.25 / 1_000_000 + 4000 * 2 / 1_000_000
        used = sum(c["reserved_usd"] for c in self.ledger["calls"])
        if len(self.ledger["calls"]) >= MAX_CALLS or used + reserve > USD_LIMIT:
            raise ValueError("Live-test budget/call limit reached")
        if self.dry_run:
            print(json.dumps({"dry_run": True, "input_bytes_including_schema": size,
                              "reserved_usd": round(reserve, 6), "model": MODEL}), flush=True)
            raise RuntimeError("Dry-run complete: no request sent")
        call = {"timestamp": datetime.now(timezone.utc).isoformat(), "reserved_usd": reserve,
                "input_bytes_including_schema": size, "status": "reserved"}
        self.ledger["calls"].append(call)
        save(self.ledger)  # Reserve before network I/O; unknown spend is never treated as zero.
        started = monotonic()
        try:
            response = self.client.responses.create(**kwargs)
            call["status"] = response.status
            call["response_id"] = response.id
            call["returned_model"] = response.model
            call["output_text"] = response.output_text
            call["usage"] = response.usage.model_dump() if response.usage else None
            if response.usage:
                usage = response.usage
                cached = getattr(usage.input_tokens_details, "cached_tokens", 0) or 0
                call["estimated_usd"] = ((usage.input_tokens - cached) * .25 + cached * .025 + usage.output_tokens * 2) / 1_000_000
            call["incomplete_reason"] = getattr(response.incomplete_details, "reason", None)
            return response
        except Exception as exc:
            call["status"] = "error"
            call["error_class"] = type(exc).__name__
            call["http_status"] = getattr(exc, "status_code", None)
            call["network_cause_class"] = type(exc.__cause__).__name__ if exc.__cause__ else None
            body = getattr(exc, "body", None)
            if isinstance(body, dict):
                error = body.get("error", body)
                if isinstance(error, dict):
                    call["provider_code"] = error.get("code")
                    call["provider_param"] = error.get("param")
            raise
        finally:
            call["duration_seconds"] = round(monotonic() - started, 3)
            save(self.ledger)


def run(live=False, resume_reviewed=False):
    ledger = load_ledger()
    if live and ledger["stopped"] and not resume_reviewed:
        print("Previous run stopped. Review results before any further live request.")
        return
    if live and resume_reviewed:
        ledger["stopped"] = False
        ledger.setdefault("reviewed_resumptions", []).append(datetime.now(timezone.utc).isoformat())
        save(ledger)
    interpreter = create_query_interpreter()
    if getattr(interpreter, "model", None) != MODEL:
        raise ValueError("Configured model differs from budgeted model")
    original_client = interpreter.client
    interpreter.client = GuardedClient(original_client, ledger, dry_run=not live)
    plants = load_plants()
    first_result = next((c.get("result") for c in ledger["cases"] if c["id"] == "freiland_large"), None)
    try:
        for case_id, question in CASES:
            if any(c["id"] == case_id and c.get("result") for c in ledger["cases"]):
                continue
            history, previous, visible = [], None, []
            if case_id == "correction":
                if not first_result:
                    raise ValueError("Correction requires a successful initial response")
                previous = DialoguePlan.model_validate(first_result["plan"])
                history = [ChatMessage(role="user", content=CASES[0][1]),
                           ChatMessage(role="assistant", content=first_result["answer"])]
                visible = [{"plant_id": p["plant_id"], "name": p["plant_name"]}
                           for p in first_result["recommendations"][:3]]
            started = monotonic()
            case = {"id": case_id, "question": question}
            try:
                result = consult(interpreter, plants, question, history, previous, visible)
                # Keep model plan and local IDs/verdicts, not a duplicate of the full catalogue.
                case["result"] = {k: result[k] for k in ["answer", "intent", "plan", "selection_mode", "total_matches"]}
                for key in ["recommendations", "unknown", "excluded"]:
                    case["result"][key] = [{"plant_id": p["plant_id"], "plant_name": p["plant_name"]} for p in result[key]]
                if case_id == "freiland_large":
                    first_result = case["result"]
            except Exception as exc:
                if not live:
                    return
                case["error_class"] = type(exc).__name__
                case["cause_class"] = type(exc.__cause__).__name__ if exc.__cause__ else None
                ledger["stopped"] = True
            case["duration_seconds"] = round(monotonic() - started, 3)
            ledger["cases"].append(case)
            save(ledger)
            print(json.dumps({"case": case_id, "duration_seconds": case["duration_seconds"],
                              "error_class": case.get("error_class"),
                              "plan": case.get("result", {}).get("plan"),
                              "matches": case.get("result", {}).get("total_matches")}, ensure_ascii=False), flush=True)
            if ledger["stopped"]:
                break
    finally:
        original_client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Spend against explicitly authorized test budget")
    parser.add_argument("--resume-reviewed", action="store_true", help="Resume after manual error review; retain all budget reservations")
    args = parser.parse_args()
    try:
        run(args.live, args.resume_reviewed)
    except Exception as exc:
        # No raw provider errors, environment values or key material on stdout.
        print("Test stopped:", type(exc).__name__)
        sys.exit(1)
