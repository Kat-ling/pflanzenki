"""Exercise the paid-test guard without any external client or network."""
from types import SimpleNamespace

import pytest

import run_live_model_check as runner


def kwargs():
    return dict(model="gpt-5-mini", max_output_tokens=4000, store=False, input="probe")


def test_dry_run_never_dispatches_or_reserves(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "LEDGER", tmp_path / "ledger.json")
    client = SimpleNamespace(base_url="https://api.openai.com/v1/")
    ledger = runner.load_ledger()
    with pytest.raises(RuntimeError, match="no request sent"):
        runner.GuardedClient(client, ledger, dry_run=True).create(**kwargs())
    assert ledger["calls"] == []
    assert not runner.LEDGER.exists()


@pytest.mark.parametrize("change", ["budget", "count", "model"])
def test_limits_reject_before_dispatch(tmp_path, monkeypatch, change):
    monkeypatch.setattr(runner, "LEDGER", tmp_path / "ledger.json")
    ledger = runner.load_ledger()
    args = kwargs()
    if change == "budget":
        ledger["calls"] = [{"reserved_usd": runner.USD_LIMIT}]
    elif change == "count":
        ledger["calls"] = [{"reserved_usd": 0}] * runner.MAX_CALLS
    else:
        args["model"] = "other-model"
    client = SimpleNamespace(base_url="https://api.openai.com/v1/")
    with pytest.raises(ValueError):
        runner.GuardedClient(client, ledger).create(**args)
    assert not runner.LEDGER.exists()


def test_unknown_spend_stays_reserved_and_error_is_sanitized(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "LEDGER", tmp_path / "ledger.json")
    ledger = runner.load_ledger()
    def dispatch(**args):
        assert runner.LEDGER.exists()
        assert ledger["calls"][0]["status"] == "reserved"
        raise RuntimeError("private provider body")
    client = SimpleNamespace(base_url="https://api.openai.com/v1/", responses=SimpleNamespace(create=dispatch))
    with pytest.raises(RuntimeError):
        runner.GuardedClient(client, ledger).create(**kwargs())
    assert ledger["calls"][0]["reserved_usd"] > 0
    assert "estimated_usd" not in ledger["calls"][0]
    assert "private provider body" not in runner.LEDGER.read_text()
