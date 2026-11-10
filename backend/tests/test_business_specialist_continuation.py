import json
from copy import deepcopy
from dataclasses import replace

from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.business.reviews import ROLES, run_paired_reviews
from app.business.tables import business_analyses, business_projects
from app.database import jobs
from test_business_api import make_app, register, wait
from test_business_partial_recovery import configure_local_live, InterruptedRuntime, begin_live
from test_business_quick import upload_only, CASES


def test_explicit_retry_recovers_frozen_discussion_after_review_worker_dies(tmp_path, database_url, monkeypatch):
    app = make_app(tmp_path, database_url)
    with TestClient(app) as client:
        register(client)
        service, source = saved_timeout(client, app, monkeypatch)
        monkeypatch.setattr("app.business.service.run_paired_reviews", run_paired_reviews)
        calls = []
        def completion(operation, payload, *args, **kwargs):
            calls.append(operation)
            return {"id": "local-only", "content": '{"findings":[],"disagreements":[]}', "finish_reason": "stop", "usage": {"total_tokens": 200}}
        monkeypatch.setattr("app.business.agents.call_worker", completion)
        first = client.post(f"/api/v1/business/analyses/{source['id']}/specialist-review", json={}, headers={"Idempotency-Key": "first-review"})
        finished = wait(client, first.json()["id"])
        with app.state.repository.engine.begin() as db:
            db.execute(update(business_analyses).where(business_analyses.c.id == finished["id"]).values(status="failed", stage="failed", result={"error": "Review worker stopped"}))
        failed_before = deepcopy(service.repository.analysis(finished["id"]))
        def forbidden(*args, **kwargs):
            raise AssertionError("Persona simulation and evidence retrieval must not repeat")
        service.oasis.run_business_simulation = forbidden
        service.evidence.retrieve = forbidden
        url = f"/api/v1/business/analyses/{finished['id']}/specialist-review"
        assert client.post(url, json={}, headers={"Idempotency-Key": "no-explicit-retry"}).status_code == 409
        started = client.post(url, json={"retry_failed": True}, headers={"Idempotency-Key": "resume-interrupted-review"})
        assert started.status_code == 202
        recovered = wait(client, started.json()["id"])
        assert recovered["result"]["simulation"] == source["result"]["simulation"]
        assert recovered["input_snapshot"]["review_source"]["interrupted_review"] is True
        assert len(calls) == 8
        assert service.repository.analysis(finished["id"]) == failed_before


def saved_timeout(client, app, monkeypatch):
    service, _ = configure_local_live(app, monkeypatch)
    service.oasis = InterruptedRuntime()
    original = begin_live(client, upload_only(client, CASES[0]))
    raw = {"stop_reason": "time_budget", "evidence": original["result"]["evidence"], "runtime_calls": original["result"]["runtime_calls"], "error": "Original timeout"}
    with app.state.repository.engine.begin() as db:
        db.execute(update(business_analyses).where(business_analyses.c.id == original["id"]).values(status="failed", result=raw))
    return service, client.get(f"/api/v1/business/analyses/{original['id']}").json()


def test_four_specialists_reuse_frozen_discussion_without_restarting_runtime_or_double_billing(tmp_path, database_url, monkeypatch):
    app = make_app(tmp_path, database_url)
    with TestClient(app) as client:
        register(client)
        service, source = saved_timeout(client, app, monkeypatch)
        raw_before = deepcopy(service.repository.analysis(source["id"]))
        monkeypatch.setattr("app.business.service.run_paired_reviews", run_paired_reviews)
        def forbidden(*args, **kwargs):
            raise AssertionError("Continuation must not fetch evidence, discover personas or run OASIS")
        service.evidence.retrieve = forbidden
        service.oasis.run_business_simulation = forbidden
        monkeypatch.setattr("app.business.service.BusinessLLM.discover", forbidden)
        calls = []
        def local_completion(operation, payload, *args, **kwargs):
            assert operation == "llm_completion"
            context = json.loads(payload["request"]["messages"][-1]["content"])
            calls.append(context)
            assert {e["id"] for e in context["events"]} == {e["id"] for e in source["result"]["simulation"]["events"]}
            return {"id": "local-only", "content": '{"findings":[],"disagreements":[]}', "finish_reason": "stop", "usage": {"total_tokens": 200, "cost": 0.00001}}
        monkeypatch.setattr("app.business.agents.call_worker", local_completion)
        # New project edits must not silently change the original frozen inputs.
        with app.state.repository.engine.begin() as db:
            db.execute(update(business_projects).where(business_projects.c.id == source["project_id"]).values(revision=99))
        url = f"/api/v1/business/analyses/{source['id']}/specialist-review"
        response = client.post(url, json={}, headers={"Idempotency-Key": "continue-once"})
        assert response.status_code == 202, response.text
        result = wait(client, response.json()["id"])
        assert result["status"] == "partial"  # Incomplete discussion is still incomplete.
        assert result["id"] != source["id"] and result["baseline_id"] is None
        assert result["input_snapshot"]["personas"] == source["input_snapshot"]["personas"]
        assert result["input_snapshot"]["revision"] == source["input_snapshot"]["revision"]
        assert result["result"]["simulation"] == source["result"]["simulation"]
        assert result["result"]["evidence"] == source["result"]["evidence"]
        assert sorted(c["role"] for c in calls) == sorted(ROLES)
        assert result["result"]["usage"]["call_count"] == 4
        assert result["result"]["usage"]["actual_tokens"] == 800
        assert result["result"]["continuation"]["usage_scope"] == "new_specialist_calls_only"
        assert len([c for c in result["result"]["agent_runs"] if c.get("phase") == "specialist" and c["status"] == "completed"]) == 4
        for key in ("continue-once", "different-key-same-source"):
            repeated = client.post(url, json={}, headers={"Idempotency-Key": key})
            assert repeated.status_code == 202 and repeated.json()["id"] == result["id"]
        assert len(calls) == 4
        assert client.post(url, json={"max_seconds": 200}, headers={"Idempotency-Key": "continue-once"}).status_code == 409
        assert client.post(url, json={"max_seconds": 200}, headers={"Idempotency-Key": "different-budget"}).status_code == 409
        assert client.post(url, json={}).status_code == 422
        assert service.repository.analysis(source["id"]) == raw_before
        followup = client.get(f"/api/v1/business/analyses/{source['id']}").json()["review_followup"]
        assert followup == {"id": result["id"], "status": "partial"}
        report = client.get(f"/api/v1/business/analyses/{result['id']}/report").json()
        assert len(report["sections"]) == 8
        assert report["appendix"]["provenance"]["source_analysis_id"] == source["id"]
        assert client.get(f"/api/v1/business/analyses/{result['id']}/export").status_code == 200
        with app.state.repository.engine.connect() as db:
            job = db.execute(select(jobs).where(jobs.c.analysis_id == result["id"])).mappings().one()
        assert job["max_attempts"] == 1 and job["attempts"] == 1
        # Scenario execution must not accidentally reuse the continuation seed.
        service.spawn = None
        scenario = client.post(f"/api/v1/business/analyses/{result['id']}/scenarios", json={"shock": {"kind": "competitor_price_cut", "region": result["input_snapshot"]["context"]["region"]}}, headers={"Idempotency-Key": "scenario"})
        assert scenario.status_code == 202, scenario.text
        assert "review_source" not in scenario.json()["input_snapshot"]
        register(client, "other-owner@example.com")
        assert client.post(url, json={}, headers={"Idempotency-Key": "other"}).status_code == 404


def test_continuation_rejects_model_changes_and_repeat_specialist_runs(tmp_path, database_url, monkeypatch):
    app = make_app(tmp_path, database_url)
    with TestClient(app) as client:
        register(client)
        service, source = saved_timeout(client, app, monkeypatch)
        url = f"/api/v1/business/analyses/{source['id']}/specialist-review"
        service.settings = replace(service.settings, llm_model="different-model")
        assert client.post(url, json={}, headers={"Idempotency-Key": "wrong-model"}).status_code == 409
        service.settings = replace(service.settings, llm_model=source["input_snapshot"]["model"])
        raw = deepcopy(service.repository.analysis(source["id"])["result"])
        raw["simulation"] = source["result"]["simulation"]
        raw["agent_runs"] = [{"role": ROLES[0], "phase": "specialist", "status": "failed"}]
        with app.state.repository.engine.begin() as db:
            db.execute(update(business_analyses).where(business_analyses.c.id == source["id"]).values(status="partial", result=raw))
        assert client.post(url, json={}, headers={"Idempotency-Key": "already-started"}).status_code == 409


def test_explicit_failed_only_resume_inherits_accepted_reviews_and_bills_only_missing_roles(tmp_path, database_url, monkeypatch):
    app = make_app(tmp_path, database_url)
    with TestClient(app) as client:
        register(client)
        service, source = saved_timeout(client, app, monkeypatch)
        result = deepcopy(source["result"])
        result.pop("recovery", None)
        result["agent_runs"] = [{"role": role, "phase": "specialist", "status": "completed" if i < 2 else "failed", "tokens": 100, "cost": 0.001} for i, role in enumerate(ROLES)]
        result["disagreements"] = [{"author": ROLES[0], "summary": "Earlier accepted market uncertainty"}]
        with app.state.repository.engine.begin() as db:
            db.execute(update(business_analyses).where(business_analyses.c.id == source["id"]).values(status="partial", result=result))
        original = deepcopy(service.repository.analysis(source["id"]))
        monkeypatch.setattr("app.business.service.run_paired_reviews", run_paired_reviews)
        calls = []
        def completion(operation, payload, *args, **kwargs):
            context = json.loads(payload["request"]["messages"][-1]["content"])
            calls.append(context["role"])
            return {"id": "local", "content": '{"findings":[],"disagreements":[]}', "usage": {"total_tokens": 200, "cost": 0.00001}}
        monkeypatch.setattr("app.business.agents.call_worker", completion)
        url = f"/api/v1/business/analyses/{source['id']}/specialist-review"
        assert client.post(url, json={}, headers={"Idempotency-Key": "default-stays-protected"}).status_code == 409
        started = client.post(url, json={"retry_failed": True}, headers={"Idempotency-Key": "explicit-failed-only"})
        assert started.status_code == 202, started.text
        resumed = wait(client, started.json()["id"])
        assert calls == list(ROLES[2:])
        inherited = [entry for entry in resumed["result"]["agent_runs"] if entry.get("phase") == "inherited_specialist"]
        assert [entry["role"] for entry in inherited] == list(ROLES[:2])
        assert all(entry["source_analysis_id"] == source["id"] for entry in inherited)
        assert resumed["result"]["usage"]["call_count"] == 2 and resumed["result"]["usage"]["actual_tokens"] == 400
        assert result["disagreements"][0] in resumed["result"]["disagreements"]
        assert service.repository.analysis(source["id"]) == original
        duplicate = client.post(url, json={"retry_failed": True}, headers={"Idempotency-Key": "another-key"})
        assert duplicate.status_code == 202 and duplicate.json()["id"] == resumed["id"]
        assert len(calls) == 2
