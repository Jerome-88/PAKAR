import json
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.business.agents import BusinessLLM
from app.business.budget import BudgetExceeded
from app.business.preparation import contextual_personas
from app.business.service import BusinessService
from test_business_api import make_app, register, wait


CASES = json.loads((Path(__file__).resolve().parents[2] / "docs/evaluation/business-cases.v0.json").read_text(encoding="utf-8"))["cases"]


def upload_only(client, case):
    response = client.post("/api/v1/business/projects", json=case["context"])
    assert response.status_code == 201
    project = response.json()
    response = client.post(f"/api/v1/business/projects/{project['id']}/documents", files=[("files", ("proposal.txt", case["proposal"].encode(), "text/plain"))])
    assert response.status_code == 201, response.text
    return response.json()


def begin(client, project, **options):
    return client.post(f"/api/v1/business/projects/{project['id']}/quick-analysis", headers={"Idempotency-Key": "one-explicit-user-action"}, json={"expected_revision": project["revision"], "public_brief": "Konsep produk untuk diskusi stakeholder; informasi internal tidak dibagikan.", "engine": "fixture", "interaction_mode": "pairwise", "max_personas": 4, "rounds": 2, **options})


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_upload_to_report_without_manual_review_preserves_sources_and_context(tmp_path, database_url, case):
    with TestClient(make_app(tmp_path, database_url)) as client:
        register(client)
        project = upload_only(client, case)
        assert not project["personas"] and all(c["review_status"] == "pending" for c in project["claims"])
        response = begin(client, project)
        assert response.status_code == 202, response.text
        row = wait(client, response.json()["id"])
        assert row["status"] == "completed", row["result"].get("error")
        snapshot = row["input_snapshot"]
        assert snapshot["input_mode"] == "automatic-v1"
        assert snapshot["preparation"]["generator"] == "document-context-v1"
        assert 2 <= len(snapshot["personas"]) <= 4
        assert all(not p["reviewed"] for p in snapshot["personas"])
        roles = {p["role"] for p in snapshot["personas"]}
        assert {"operator", "customer"} <= roles
        if case["id"] == "services-dki-v0":
            assert "employee" in roles
        assert "community" not in roles and "regulator" not in roles
        assert row["result"]["simulation"]["calculation"]["break_even_units_monthly"] == case["expected_calculations"]["baseline_break_even_units_monthly"]
        report = client.get(f"/api/v1/business/analyses/{row['id']}/report").json()
        assert len(report["sections"]) == 8
        assert all(c["input_acceptance"] == "automatic_document_assumption" and not c["human_reviewed"] and c["quote"] for c in report["assumptions"])
        assert report["appendix"]["calculation"]["profit_monthly"] is None
        assert any("tanpa review manusia" in f["reasoning"] for f in report["findings"])
        assert report["appendix"]["provenance"]["human_reviewed"] is False
        saved = client.get(f"/api/v1/business/projects/{project['id']}").json()
        assert {p["id"] for p in saved["personas"]} == {p["id"] for p in snapshot["personas"]}
        assert all(c["review_status"] == "pending" for c in saved["claims"])
        # Repeating the same explicit request cannot generate/pay for another job,
        # including after the preparation checkpoint changes the project revision.
        repeated = begin(client, project)
        assert repeated.status_code == 202 and repeated.json()["id"] == row["id"]
        assert begin(client, project, rounds=3).status_code == 409
        events = client.get(f"/api/v1/business/analyses/{row['id']}/events").json()["items"]
        assert {"preparing", "personas_ready", "completed"} <= {e["type"] for e in events}


def test_ambiguous_prices_are_retained_as_quotes_but_not_guessed_for_calculation(tmp_path, database_url):
    case = {**CASES[0], "proposal": CASES[0]["proposal"] + "\nHarga jual Rp25.000 per unit."}
    with TestClient(make_app(tmp_path, database_url)) as client:
        register(client)
        project = upload_only(client, case)
        row = wait(client, begin(client, project).json()["id"])
        assert row["status"] == "completed"
        assert row["input_snapshot"]["values"]["selling_price"] is None
        assert row["result"]["simulation"]["calculation"]["break_even_units_monthly"] is None
        assert len([c for c in row["input_snapshot"]["claims"] if c["variable"] == "selling_price"]) == 2
        assert any("nilai ganda" in line for line in row["result"]["limitations"])


def test_discovery_timeout_falls_back_without_retry_or_marking_human_review_done(tmp_path, database_url, monkeypatch):
    app = make_app(tmp_path, database_url)
    calls = []

    def timeout(self, context, claims, existing, **kwargs):
        calls.append(kwargs)
        raise BudgetExceeded("upstream test context must not leak")

    class LocalRuntime:
        def run_business_simulation(self, identity, snapshot, receive, cancelled=None):
            return BusinessService._fixture_simulation(identity, snapshot, lambda *a: None)

    monkeypatch.setattr(BusinessLLM, "discover", timeout)
    monkeypatch.setattr("app.business.service.run_paired_reviews", lambda *a: {"failures": [], "disagreements": [], "waves": []})
    with TestClient(app) as client:
        register(client)
        project = upload_only(client, CASES[0])
        app.state.business.settings = replace(app.state.business.settings, llm_api_key="local-test-only")
        app.state.business.oasis = LocalRuntime()
        app.state.business.evidence.retrieve = lambda *a, **k: [{"id": "local", "status": "UNAVAILABLE"}]
        row = wait(client, begin(client, project, engine="oasis").json()["id"])
        assert row["status"] == "completed", row["result"].get("error")
        assert len(calls) == 1 and calls[0]["call_seconds"] <= 25
        assert row["input_snapshot"]["preparation"]["discovery_failure_type"] == "BudgetExceeded"
        assert row["input_snapshot"]["preparation"]["generator"] == "document-context-v1"
        assert all(not p["reviewed"] for p in row["input_snapshot"]["personas"])
        assert any("bukan hasil discovery LLM" in line for line in row["result"]["limitations"])
        assert "upstream test context" not in json.dumps(row)


def test_discovery_assigns_ids_server_side_and_rejects_invented_source_ids(tmp_path, database_url, monkeypatch):
    from app.config import Settings
    llm = BusinessLLM(Settings.load({"TESTING": True, "DATABASE_URL": database_url}))
    claims = [{"id": "claim-1", "quote": "Supplier memasok bahan kedai.", "normalized_text": "Supplier memasok bahan kedai."}]
    payload = {"personas": [{"name": "Pengelola kedai", "role": "operator", "goals": ["Memeriksa biaya"], "constraints": [], "claim_ids": ["claim-1"], "rationale": "Hipotesis konteks kedai"}, {"name": "Pemasok bahan", "role": "supplier", "goals": ["Menilai pasokan"], "constraints": [], "claim_ids": ["claim-1"], "rationale": "Disebut dalam dokumen"}]}
    captured = []
    monkeypatch.setattr(llm, "generate", lambda *a, **k: (captured.append(k) or payload))
    personas = llm.discover(CASES[0]["context"], claims, [])
    assert len({p["id"] for p in personas}) == 3
    assert all(p["id"].startswith("persona_") and not p["reviewed"] for p in personas)
    assert captured[0]["response_schema"]["properties"]["personas"]["maxItems"] == 4
    payload["personas"][1]["claim_ids"] = ["invented-source"]
    with pytest.raises(ValueError, match="di luar dokumen"):
        llm.discover(CASES[0]["context"], claims, [])


def test_grounding_removes_invented_people_and_unsupported_roles_but_keeps_model_goals():
    from app.business.preparation import ground_personas
    claims = [{"id": "supplier-claim", "quote": "Supplier memasok bahan. Kompetitor dapat mengubah harga."}]
    proposed = [{"id": "model-operator", "name": "Hendro", "role": "operator", "goals": ["Memeriksa margin kedai"], "constraints": []}, {"id": "model-partner", "name": "Ibu Tuti", "role": "partner", "goals": ["Tujuan tanpa sumber"], "constraints": []}]
    personas = ground_personas(CASES[0]["context"], claims, proposed)
    assert {p["role"] for p in personas} == {"operator", "customer", "supplier", "competitor"}
    assert not any(word in p["name"] or word in p["discovery_rationale"] for p in personas for word in ["Hendro", "Tuti"])
    operator = next(p for p in personas if p["role"] == "operator")
    assert operator["id"] == "model-operator" and operator["goals"] == ["Memeriksa margin kedai"]
    assert operator["provenance"]["goals"] == "llm_hypothesis"
    assert all(target in {p["id"] for p in personas} for p in personas for target in p["relationships"])
    funding = contextual_personas(CASES[0]["context"], [{"id": "funding", "quote": "Investor menyediakan pendanaan untuk ekspansi."}])
    assert "investor" in {p["role"] for p in funding}
    investor = next(p for p in funding if p["role"] == "investor")
    assert investor["provenance"]["claim_ids"] == ["funding"] and not investor["reviewed"]


def test_manual_discovery_timeout_is_a_safe_504_instead_of_uncaught_500(tmp_path, database_url, monkeypatch):
    app = make_app(tmp_path, database_url)
    with TestClient(app) as client:
        register(client)
        project = upload_only(client, CASES[0])
        def fail(*a):
            raise BudgetExceeded("secret upstream context")
        monkeypatch.setattr(app.state.business, "discover", fail)
        response = client.post(f"/api/v1/business/projects/{project['id']}/stakeholder-discovery", json={"expected_revision": project["revision"]})
        assert response.status_code == 504 and response.json()["error"]["code"] == "discovery_timeout"
        assert "secret upstream" not in response.text


def test_preparation_checkpoint_is_fenced_and_cannot_rewrite_frozen_personas(tmp_path, database_url, monkeypatch):
    from copy import deepcopy
    from sqlalchemy import select
    from app.database import jobs
    from app.business.tables import business_personas
    app = make_app(tmp_path, database_url)
    with TestClient(app) as client:
        register(client)
        project = upload_only(client, CASES[0])
        monkeypatch.setattr(app.state.business, "_spawn", lambda *a: None)
        row = begin(client, project).json()
        with app.state.repository.engine.connect() as db:
            job_id = db.execute(select(jobs.c.id).where(jobs.c.analysis_id == row["id"])).scalar_one()
        job = app.state.repository.claim_next_job("preparer", 60, job_id)
        snapshot = deepcopy(row["input_snapshot"])
        snapshot["personas"] = contextual_personas(snapshot["context"], snapshot["claims"])
        snapshot["preparation"] = {"status": "completed", "generator": "document-context-v1", "human_reviewed": False}
        repository = app.state.business.repository
        with pytest.raises(RuntimeError, match="lease lost"):
            repository.publish(dict(job, execution_token="stale"), "preparer", "personas_ready", {}, prepared_snapshot=snapshot)
        assert repository.analysis(row["id"])["input_snapshot"]["personas"] == []
        repository.publish(job, "preparer", "personas_ready", {}, prepared_snapshot=snapshot)
        with pytest.raises(RuntimeError, match="already frozen"):
            repository.publish(job, "preparer", "personas_ready", {}, prepared_snapshot=snapshot)
        assert repository.analysis(row["id"])["input_snapshot"] == snapshot
        with app.state.repository.engine.connect() as db:
            ids = db.execute(select(business_personas.c.id).where(business_personas.c.project_id == project["id"])).scalars().all()
        assert set(ids) == {p["id"] for p in snapshot["personas"]}
        app.state.repository.finish_job(job["id"], "preparer", job["execution_token"], {"analysis_id": row["id"]})
