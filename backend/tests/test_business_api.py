import io
import time

from fastapi.testclient import TestClient

from app import create_app


CONTEXT = {"name": "Ekspansi Kedai Jakarta", "industry": "F&B", "region": "Jakarta", "target_customer": "Pekerja kantor", "decision_question": "Apakah ekspansi tetap layak saat biaya supplier meningkat?", "data_classification": "synthetic"}
SOURCE = """Rencana ekspansi kedai untuk pelanggan pekerja kantor di Jakarta.
Harga jual Rp30.000 per unit.
Biaya variabel Rp12.000 per unit.
Biaya tetap Rp36.000.000 per bulan.
Target permintaan belum pernah diuji melalui riset customer.
Supplier utama memasok bahan harian kepada pengelola bisnis.
"""


def make_app(tmp_path, database_url):
    return create_app({"TESTING": True, "DATABASE_URL": database_url, "UPLOAD_DIR": tmp_path / "uploads", "JOB_DELAY": 0})


def register(client, email="business@example.com"):
    response = client.post("/api/auth/register", json={"name": "Business Analyst", "email": email, "password": "testing-password"})
    assert response.status_code == 201


def create_project(client):
    response = client.post("/api/v1/business/projects", json=CONTEXT)
    assert response.status_code == 201, response.text
    return response.json()


def upload(client, project):
    response = client.post(f"/api/v1/business/projects/{project['id']}/documents", files=[("files", ("proposal.txt", io.BytesIO(SOURCE.encode()), "text/plain"))])
    assert response.status_code == 201, response.text
    return response.json()


def prepare(client, project):
    base = f"/api/v1/business/projects/{project['id']}"
    project = upload(client, project)
    project = client.post(base + "/claims/approve", json={"expected_revision": project["revision"]}).json()
    response = client.post(base + "/stakeholder-discovery", json={"expected_revision": project["revision"]})
    assert response.status_code == 200, response.text
    project = response.json()
    for persona in project["personas"]:
        result = client.patch(base + f"/personas/{persona['id']}", json={"expected_revision": persona["revision"], "reviewed": True})
        assert result.status_code == 200, result.text
    return client.get(base).json()


def wait(client, analysis_id):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        row = client.get(f"/api/v1/business/analyses/{analysis_id}").json()
        if row["status"] not in {"queued", "running"}:
            return row
        time.sleep(0.05)
    raise AssertionError("Business analysis did not finish")


def test_live_attempt_deadline_fails_truthfully_and_does_not_queue_paid_retry(tmp_path, database_url, monkeypatch):
    import sys
    from dataclasses import replace
    from app.business.budget import RunDeadline
    from app.oasis_direct import DirectOasisEngine
    from app.database import jobs
    from sqlalchemy import select

    app = make_app(tmp_path, database_url)
    with TestClient(app) as client:
        register(client)
        project = prepare(client, create_project(client))
        bridge = tmp_path / "blocked_business.py"
        bridge.write_text('import json,sys,time\njson.load(sys.stdin)\nprint(json.dumps({"kind":"tick"}),flush=True)\ntime.sleep(30)\n', encoding="utf-8")
        runtime = DirectOasisEngine(tmp_path, tmp_path / "runtime")
        runtime.runtime_python, runtime.bridge = sys.executable, bridge
        service = app.state.business
        service.oasis = runtime
        service.settings = replace(service.settings, llm_api_key="local-test-only")
        monkeypatch.setattr("app.business.service.RunDeadline", lambda seconds, **kwargs: RunDeadline(0.5, **kwargs))
        monkeypatch.setattr(service.evidence, "retrieve", lambda *a, **k: [{"id": "local-source", "status": "UNAVAILABLE"}])
        started = time.monotonic()
        response = client.post(f"/api/v1/business/projects/{project['id']}/analyses", json={"expected_revision": project["revision"], "engine": "oasis", "public_brief": "Konsep usaha untuk diskusi customer; biaya internal tidak dibagikan.", "rounds": 2, "max_seconds": 10})
        assert response.status_code == 202
        row = wait(client, response.json()["id"])
        assert row["status"] == "failed" and row["result"]["stop_reason"] == "time_budget"
        assert "batas waktu" in row["result"]["error"]
        assert time.monotonic() - started < 4
        with app.state.repository.engine.connect() as connection:
            job = connection.execute(select(jobs).where(jobs.c.analysis_id == row["id"])).mappings().one()
            assert job["max_attempts"] == 1 and job["attempts"] == 1
            assert job["status"] != "queued"


def test_business_upload_review_analysis_scenario_export_and_baseline_isolation(tmp_path, database_url):
    with TestClient(make_app(tmp_path, database_url)) as client:
        register(client)
        project = prepare(client, create_project(client))
        response = client.post(f"/api/v1/business/projects/{project['id']}/analyses", json={"expected_revision": project["revision"], "engine": "fixture"})
        assert response.status_code == 202, response.text
        baseline = wait(client, response.json()["id"])
        assert baseline["status"] == "completed", baseline
        assert baseline["result"]["simulation"]["calculation"]["break_even_units_monthly"] == "2000"
        assert any(f["category"] == "interaction" for f in baseline["result"]["findings"])
        assert all(f["status"] == "NEEDS_VALIDATION" for f in baseline["result"]["findings"])
        assert baseline["result"]["provenance"]["execution_kind"] == "fixture"
        assert baseline["result"]["report"]["version"] == "pakar-report-v2"
        assert "appendix" not in baseline["result"]["report"]
        assert baseline["input_snapshot"]["response_mode"] == "json_object"
        assert baseline["input_snapshot"]["review_policy"] == "paired-v2"
        report = client.get(f"/api/v1/business/analyses/{baseline['id']}/report")
        assert report.status_code == 200
        baseline_report = report.json()
        assert [s["title"] for s in baseline_report["sections"]] == ["Executive Summary", "Assumption Register", "Top Blind Spots", "Evidence Table", "Contradictions", "Scenario Impact", "Recommended Validation Tasks", "Limitations"]
        assert baseline_report["summary"]["validation_status"] == "NEEDS_VALIDATION"
        assert all(t["status"] == "PROPOSED" and t["owner"] for t in baseline_report["validation_tasks"])
        assert any(f["interaction_chain"] for f in baseline_report["findings"] if f["category"] == "interaction")
        assert "storage_key" not in str(baseline_report)
        assert baseline["result"]["evidence"][0]["status"] == "UNAVAILABLE"
        created = client.post(f"/api/v1/business/analyses/{baseline['id']}/scenarios", json={"shock": {"kind": "competitor_price_cut", "magnitude_percent": 20, "effective_round": 2, "duration_rounds": 3, "region": "Jakarta", "response_strategy": "match_price"}})
        assert created.status_code == 202, created.text
        scenario = wait(client, created.json()["id"])
        assert scenario["status"] == "completed", scenario
        assert scenario["input_snapshot"]["response_mode"] == baseline["input_snapshot"]["response_mode"]
        scenario_report = client.get(f"/api/v1/business/analyses/{scenario['id']}/report").json()
        assert scenario_report["scenario"]["baseline_id"] == baseline["id"]
        report_break_even = next(m for m in scenario_report["scenario"]["metrics"] if m["metric"] == "break_even_units_monthly")
        assert report_break_even["before"] == "2000" and report_break_even["after"] == "3000" and report_break_even["delta"] == "1000"
        comparison = client.get(f"/api/v1/business/analyses/{scenario['id']}/comparison")
        assert comparison.status_code == 200
        metric = next(m for m in comparison.json()["metrics"] if m["metric"] == "break_even_units_monthly")
        assert metric["before"] == "2000" and metric["after"] == "3000" and metric["delta"] == "1000"
        assert client.get(f"/api/v1/business/analyses/{baseline['id']}").json()["result"] == baseline["result"]
        exported = client.get(f"/api/v1/business/analyses/{scenario['id']}/export")
        assert exported.status_code == 200 and "attachment" in exported.headers["content-disposition"]
        assert "Recommended Validation Tasks" in exported.text
        assert "calculation trail" in exported.text.lower()
        assert "<pre>" not in exported.text
        assert "3.000" in exported.text
        assert "Geser tabel untuk melihat kolom Delta" in exported.text
        assert 'role="region" tabindex="0"' in exported.text
        events = client.get(f"/api/v1/business/analyses/{baseline['id']}/events").json()["items"]
        assert any(e["type"] == "interaction" for e in events)
        assert len({e["sequence"] for e in events}) == len(events)


def test_rejected_persona_action_marks_an_otherwise_finished_run_partial(tmp_path, database_url, monkeypatch):
    from app.business.service import BusinessService
    original = BusinessService._fixture_simulation

    def with_rejected_action(run_id, snapshot, publish):
        result = original(run_id, snapshot, publish)
        result["events"].append({"id": run_id + ":rejected-action", "kind": "action_rejected", "actor_id": snapshot["personas"][0]["id"], "target_id": snapshot["personas"][1]["id"], "parent_event_ids": [], "rationale": "Fixture of a model proposing a stale state version", "origin": "simulation", "state_unchanged": True})
        return result

    monkeypatch.setattr(BusinessService, "_fixture_simulation", staticmethod(with_rejected_action))
    with TestClient(make_app(tmp_path, database_url)) as client:
        register(client)
        project = prepare(client, create_project(client))
        response = client.post(f"/api/v1/business/projects/{project['id']}/analyses", json={"expected_revision": project["revision"], "engine": "fixture"})
        assert response.status_code == 202
        row = wait(client, response.json()["id"])
        assert row["stage"] == "completed" and row["status"] == "partial"
        assert row["result"]["report"]
        assert row["result"]["action_validation"]["rejected"] == 1
        assert any("ditolak validator" in message for message in row["result"]["limitations"])


def test_claim_source_span_review_conflicts_and_unknown_values(tmp_path, database_url):
    with TestClient(make_app(tmp_path, database_url)) as client:
        register(client)
        project = upload(client, create_project(client))
        assert "storage_key" not in str(project)
        price = next(c for c in project["claims"] if c["variable"] == "selling_price")
        assert price["value"] == "30000" and price["unit"] == "IDR/unit"
        source = project["documents"][0]["content"]["chunks"][0]["text"]
        locator = price["source"]["locator"]
        assert source[locator["char_start"]:locator["char_end"]] == price["quote"]
        assert price["evidence_status"] == "UNAVAILABLE"
        url = f"/api/v1/business/projects/{project['id']}/claims/{price['id']}"
        changed = client.patch(url, json={"expected_revision": 1, "value": None, "review_status": "approved"})
        assert changed.status_code == 200 and changed.json()["value"] is None
        assert client.patch(url, json={"expected_revision": 1, "value": "10000"}).status_code == 409
        assert client.patch(url, json={"expected_revision": 2, "evidence_status": "VERIFIED"}).status_code == 422


def test_business_resources_are_private_to_owner(tmp_path, database_url):
    app = make_app(tmp_path, database_url)
    with TestClient(app) as client:
        assert client.get("/api/v1/business/projects").status_code == 401
        assert client.get("/api/v1/business/analyses/unknown/report").status_code == 401
        register(client)
        project = upload(client, create_project(client))
        client.post("/api/auth/logout")
        register(client, "outsider@example.com")
        assert client.get(f"/api/v1/business/projects/{project['id']}").status_code == 404
        assert client.get("/api/v1/business/projects").json()["items"] == []
        assert client.patch(f"/api/v1/business/projects/{project['id']}/claims/{project['claims'][0]['id']}", json={"expected_revision": 1, "review_status": "approved"}).status_code == 404


def test_analysis_requires_review_and_live_engine_never_silently_falls_back(tmp_path, database_url):
    with TestClient(make_app(tmp_path, database_url)) as client:
        register(client)
        project = upload(client, create_project(client))
        response = client.post(f"/api/v1/business/projects/{project['id']}/analyses", json={"expected_revision": project["revision"], "engine": "fixture"})
        assert response.status_code == 409 and "claim" in response.json()["message"]
        project = prepare(client, create_project(client))
        response = client.post(f"/api/v1/business/projects/{project['id']}/analyses", json={"expected_revision": project["revision"], "engine": "oasis"})
        assert response.status_code == 409 and "OASIS" in response.json()["message"]


def test_project_creation_is_idempotent_and_rejects_key_reuse(tmp_path, database_url):
    with TestClient(make_app(tmp_path, database_url)) as client:
        register(client)
        headers = {"Idempotency-Key": "same-business-request"}
        first = client.post("/api/v1/business/projects", json=CONTEXT, headers=headers)
        second = client.post("/api/v1/business/projects", json=CONTEXT, headers=headers)
        assert first.json()["id"] == second.json()["id"]
        assert client.post("/api/v1/business/projects", json=CONTEXT | {"name": "Different"}, headers=headers).status_code == 409


def test_discovery_ids_and_relationships_are_isolated_between_projects(tmp_path, database_url):
    with TestClient(make_app(tmp_path, database_url)) as client:
        register(client)
        first = prepare(client, create_project(client))
        second = prepare(client, create_project(client))
        first_ids = {p["id"] for p in first["personas"]}
        second_ids = {p["id"] for p in second["personas"]}
        assert not first_ids & second_ids
        assert all(set(p["relationships"]) <= second_ids for p in second["personas"])


def test_parse_failure_can_be_excluded_without_rewriting_old_sources(tmp_path, database_url):
    with TestClient(make_app(tmp_path, database_url)) as client:
        register(client)
        project = upload(client, create_project(client))
        base = f"/api/v1/business/projects/{project['id']}"
        response = client.post(base + "/documents", files=[("files", ("unreadable.txt", b"\x00binary", "text/plain"))])
        assert response.status_code == 201
        project = response.json()
        invalid = next(d for d in project["documents"] if d["status"] == "parse_failed")
        excluded = client.post(base + f"/documents/{invalid['id']}/exclude", json={"expected_revision": project["revision"]})
        assert excluded.status_code == 200
        assert next(d for d in excluded.json()["documents"] if d["id"] == invalid["id"])["status"] == "excluded"


def test_cancellation_cannot_be_changed_back_into_retry_by_late_worker(tmp_path, database_url):
    from sqlalchemy import insert, select
    from app.business.repository import utcnow
    from app.database import jobs
    from app.business.tables import business_analyses
    with TestClient(make_app(tmp_path, database_url)) as client:
        register(client)
        project = create_project(client)
        shared = client.app.state.repository
        with shared.engine.begin() as db:
            db.execute(insert(business_analyses).values(id="cancel-test", project_id=project["id"], status="queued", stage="queued", input_snapshot={}, result={}, created_at=utcnow(), updated_at=utcnow()))
            db.execute(insert(jobs).values(id="cancel-job", analysis_id="cancel-test", stage="business", status="queued", config={}, created_at=utcnow(), updated_at=utcnow(), available_at=utcnow()))
        job = shared.claim_next_job("worker-test", job_id="cancel-job")
        assert client.post("/api/v1/business/analyses/cancel-test/cancel").status_code == 200
        assert not shared.fail_job(job["id"], "worker-test", job["execution_token"], "late error", retry_delay=1)
        with shared.engine.connect() as db:
            assert db.execute(select(jobs.c.status).where(jobs.c.id == job["id"])).scalar_one() == "cancelled"
