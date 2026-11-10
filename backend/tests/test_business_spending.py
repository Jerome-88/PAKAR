from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select

from app.business.spending import DollarBudget, SpendLedger, SpendingLimit, dollars
from app.business.tables import provider_spend_accounts, provider_spend_reservations


PRICES = {"prompt": ".1", "completion": ".5", "request": "0"}


def test_atomic_dollar_admission_and_unknown_invoices():
    budget = DollarBudget(".001", PRICES)
    def dispatch(_):
        try:
            return budget.reserve(1000, 800)[0]  # .0005 per call
        except SpendingLimit:
            return None
    with ThreadPoolExecutor(max_workers=4) as pool:
        admitted = [key for key in pool.map(dispatch, range(4)) if key]
    assert len(admitted) == 2
    assert budget.charged == Decimal(".001")
    budget.settle(admitted[0], None)
    assert budget.remaining == 0
    budget.settle(admitted[1], ".0001")
    assert budget.remaining == Decimal(".0004")
    with pytest.raises(SpendingLimit):
        budget.reserve(1000, 800)


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), "-1", None])
def test_invalid_money_is_rejected(value):
    with pytest.raises(ValueError):
        dollars(value)


def test_durable_reservations_cover_concurrent_jobs_and_billing_lag(database_url, monkeypatch):
    engine = create_engine(database_url)
    settings = SimpleNamespace(llm_base_url="https://openrouter.ai/api/v1", llm_api_key="fixture-key-not-a-credential")
    monkeypatch.setenv("PAKAR_OPENROUTER_MAX_PRICE", '{"prompt":0.1,"completion":0.5,"request":0}')
    monkeypatch.setenv("PAKAR_MAX_RUN_COST_USD", ".03")
    monkeypatch.setenv("PAKAR_CREDIT_RESERVE_USD", ".10")
    monkeypatch.setattr("app.business.spending.call_worker", lambda *a, **kw: {"remaining_usd": ".14"})
    def start(index):
        try:
            return SpendLedger.open(settings, engine, f"analysis:{index}", ".03")
        except SpendingLimit:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        admitted = [ledger for ledger in pool.map(start, range(2)) if ledger]
    assert len(admitted) == 1
    ledger = admitted[0]
    # A new process sees the held reservation even though provider billing lags.
    with pytest.raises(SpendingLimit):
        SpendLedger.open(settings, engine, "analysis:third", ".02")
    key = ledger.budget.reserve_amount(".001")
    ledger.budget.settle(key, None)
    ledger.close()
    ledger.close()  # Closing twice must not refund twice.
    with engine.connect() as connection:
        assert connection.execute(select(provider_spend_accounts.c.available_usd)).scalar_one() == Decimal(".139")
        assert connection.execute(select(provider_spend_reservations.c.charged_usd)).scalar_one() == Decimal(".001")
    with pytest.raises(SpendingLimit):
        SpendLedger.open(settings, engine, ledger.scope, ".03")
    next_run = SpendLedger.open(settings, engine, "analysis:next", ".03")
    next_run.close()
    engine.dispose()


def test_missing_price_or_credit_blocks_before_paid_inference(database_url, monkeypatch):
    engine = create_engine(database_url)
    settings = SimpleNamespace(llm_base_url="https://openrouter.ai/api/v1", llm_api_key="fixture-key")
    monkeypatch.delenv("PAKAR_OPENROUTER_MAX_PRICE", raising=False)
    def forbidden(*args, **kwargs):
        pytest.fail("Credit must not be probed before validating prices")
    monkeypatch.setattr("app.business.spending.call_worker", forbidden)
    with pytest.raises(SpendingLimit):
        SpendLedger.open(settings, engine, "missing-price", ".03")
    monkeypatch.setenv("PAKAR_OPENROUTER_MAX_PRICE", '{"prompt":0.1,"completion":0.5,"request":0}')
    monkeypatch.setenv("PAKAR_CREDIT_RESERVE_USD", ".10")
    monkeypatch.setattr("app.business.spending.call_worker", lambda *a, **kw: {"remaining_usd": ".12"})
    with pytest.raises(SpendingLimit):
        SpendLedger.open(settings, engine, "low-credit", ".03")
    engine.dispose()


def test_specialist_dollar_denial_never_dispatches(monkeypatch):
    from app.business.agents import BusinessLLM
    settings = SimpleNamespace(llm_api_key="fixture-only", llm_model="fixture-model", llm_base_url="http://127.0.0.1:9/v1", llm_structured_outputs=False)
    budget = DollarBudget(".000001", PRICES)
    llm = BusinessLLM(settings, spending=budget)
    def forbidden(*args, **kwargs):
        pytest.fail("Exhausted dollar budget must block the actual SDK call")
    monkeypatch.setattr("app.business.agents.call_worker", forbidden)
    with pytest.raises(SpendingLimit):
        llm.generate("Finance Agent", "Return bounded JSON", {"context": "test"})
    assert llm.calls == []


def test_public_sdk_marker_audit_does_not_log_internal_content():
    from app.business.information import audit_public_request
    snapshot = {"information_policy": {"public_brief": "Usulan dua rasa yang belum diuji"}, "claims": [{"id": "internal-claim-unique", "quote": "Internal secret research must never reach an external stakeholder prompt.", "source": {"document_id": "internal-document-unique"}}], "values": {"variable_cost": "71991"}}
    public = [{"role": "user", "content": snapshot["information_policy"]["public_brief"]}]
    audit = audit_public_request(snapshot, public, {})
    assert audit["public_brief_present"] and audit["protected_marker_matches"] == 0
    assert "71991" not in str(audit) and "internal-claim-unique" not in str(audit)
    with pytest.raises(ValueError, match="Internal source marker"):
        audit_public_request(snapshot, [{"role": "user", "content": "HPP 71991"}], {})


def test_terminal_job_failure_cannot_leave_analysis_running(tmp_path, database_url):
    from fastapi.testclient import TestClient
    from app.business.tables import business_analyses
    from app.database import jobs
    from app import create_app
    from test_business_api import register
    from test_business_quick import upload_only, begin, CASES
    app = create_app({"TESTING": True, "DATABASE_URL": database_url, "UPLOAD_DIR": tmp_path / "uploads", "JOB_DELAY": 0, "EMBEDDED_WORKER": False})
    with TestClient(app) as client:
        app.state.business.spawn = None
        register(client)
        project = upload_only(client, CASES[0])
        row = begin(client, project).json()
        shared = app.state.repository
        with shared.engine.connect() as connection:
            job_id = connection.execute(select(jobs.c.id).where(jobs.c.analysis_id == row["id"])).scalar_one()
        job = shared.claim_next_job("owned-worker", 60, job_id)
        assert job is not None
        assert not shared.fail_job(job_id, "wrong-worker", job["execution_token"], "not owner")
        assert shared.fail_job(job_id, "owned-worker", job["execution_token"], "publication fenced")
        with shared.engine.connect() as connection:
            result = connection.execute(select(business_analyses).where(business_analyses.c.id == row["id"])).mappings().one()
            assert result["status"] == "failed"
            assert result["result"] == {}  # Do not manufacture a review/report.
