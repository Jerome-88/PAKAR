import json
import sys
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update, delete

from app.business.budget import BudgetExceeded
from app.business.contracts import SwarmAction
from app.business.recovery import replay_committed
from app.business.swarm import SwarmSimulation, swarm_fixture_action
from app.business.tables import business_analyses, business_events
from app.database import jobs
from app.oasis_direct import DirectOasisEngine
from test_business_api import make_app, register, wait
from test_business_quick import CASES, upload_only


def configure_local_live(app, monkeypatch):
    service = app.state.business
    service.settings = replace(service.settings, llm_api_key="local-test-only")
    def no_discovery(*a, **k):
        raise BudgetExceeded("No model call in this test")
    monkeypatch.setattr("app.business.service.BusinessLLM.discover", no_discovery)
    service.evidence.retrieve = lambda *a, **k: [{"id": "local", "status": "UNAVAILABLE"}]
    reviewed = []
    def review(*a):
        reviewed.append(True)
        return {"failures": [], "disagreements": [], "waves": []}
    monkeypatch.setattr("app.business.service.run_paired_reviews", review)
    return service, reviewed


class InterruptedRuntime:
    def run_business_simulation(self, identity, snapshot, receive, cancelled=None):
        sim = SwarmSimulation(identity, snapshot["personas"], snapshot["values"], snapshot["config"]["max_events"])
        for actor in sim.turn_order()[:3]:
            receive({"kind": "interaction", "event": sim.apply(swarm_fixture_action(sim, actor, 1), 1)})
        receive({"kind": "usage", "call": {"call_id": "unfinished", "status": "started", "tokens": None, "cost": None}})
        raise BudgetExceeded("Runtime phase deadline")


def begin_live(client, project, **kwargs):
    r = client.post(f"/api/v1/business/projects/{project['id']}/quick-analysis", json={"expected_revision": project["revision"], "engine": "oasis", "public_brief": "Konsep usaha untuk diskusi customer. Biaya internal tidak dibagikan.", "discussion_policy": "round-robin-v1", **kwargs})
    assert r.status_code == 202, r.text
    return wait(client, r.json()["id"])


def test_runtime_phase_timeout_keeps_real_committed_messages_and_uses_reserved_review_time(tmp_path, database_url, monkeypatch):
    app = make_app(tmp_path, database_url)
    with TestClient(app) as client:
        register(client)
        service, reviewed = configure_local_live(app, monkeypatch)
        service.oasis = InterruptedRuntime()
        row = begin_live(client, upload_only(client, CASES[0]))
        assert row["status"] == "partial" and row["result"]["report"]
        sim = row["result"]["simulation"]
        assert len(sim["events"]) == 3 and len(sim["threads"]) == 1
        assert sim["stop_reason"] == "runtime_time_budget"
        assert row["result"]["runtime_recovery"]["new_model_calls"] == 0
        assert reviewed == [True]  # Work continues in the already reserved phase.
        assert sim["usage"]["reserved_tokens_upper_bound"] == 65000
        assert row["result"]["usage"]["cost"] is None
        assert len(client.get(f"/api/v1/business/analyses/{row['id']}/report").json()["sections"]) == 8
        with app.state.repository.engine.connect() as db:
            job = db.execute(select(jobs).where(jobs.c.analysis_id == row["id"])).mappings().one()
        assert job["max_attempts"] == 1 and job["attempts"] == 1 and job["status"] == "completed"


def test_historical_timeout_report_is_a_read_projection_without_rewriting_raw_data_or_model_calls(tmp_path, database_url, monkeypatch):
    app = make_app(tmp_path, database_url)
    with TestClient(app) as client:
        register(client)
        service, reviewed = configure_local_live(app, monkeypatch)
        service.oasis = InterruptedRuntime()
        row = begin_live(client, upload_only(client, CASES[0]))
        failed = {"stop_reason": "time_budget", "error": "Original timeout", "runtime_calls": row["result"]["runtime_calls"], "evidence": row["result"]["evidence"], "elapsed_seconds": 182.8}
        with app.state.repository.engine.begin() as db:
            db.execute(update(business_analyses).where(business_analyses.c.id == row["id"]).values(status="failed", stage="failed", result=failed))
        base = f"/api/v1/business/analyses/{row['id']}"
        view = client.get(base).json()
        assert view["status"] == "partial" and "error" not in view["result"]
        assert view["result"]["recovery"]["original_execution_status"] == "failed"
        assert view["result"]["recovery"]["specialist_review"] == "not_run"
        assert view["result"]["recovery"]["new_model_calls"] == 0
        assert len(client.get(base + "/report").json()["sections"]) == 8
        assert client.get(base + "/export").status_code == 200
        assert reviewed == [True]  # Reading/exporting does not run reviewers again.
        with app.state.repository.engine.connect() as db:
            saved = db.execute(select(business_analyses).where(business_analyses.c.id == row["id"])).mappings().one()
        assert saved["status"] == "failed" and saved["result"] == failed
        with app.state.repository.engine.begin() as db:
            db.execute(update(business_analyses).where(business_analyses.c.id == row["id"]).values(status="cancelled"))
        assert client.get(base).json()["status"] == "cancelled"
        register(client, "different-owner@example.com")
        assert client.get(base).status_code == 404


def test_actual_killed_runtime_process_still_yields_a_partial_report_without_live_retry(tmp_path, database_url, monkeypatch):
    app = make_app(tmp_path, database_url)
    bridge = tmp_path / "committed_then_blocked.py"
    bridge.write_text('''import json,sys,time
p=json.load(sys.stdin);s=p["snapshot"]
print(json.dumps({"kind":"interaction","event":s["config"]["local_test_event"]}),flush=True)
time.sleep(30)
''', encoding="utf-8")
    class BlockedRuntime(DirectOasisEngine):
        def run_business_simulation(self, identity, snapshot, callback, cancelled=None):
            payload = deepcopy(snapshot)
            sim = SwarmSimulation(identity, snapshot["personas"], snapshot["values"], snapshot["config"]["max_events"])
            actor = sim.turn_order()[0]
            payload["config"]["local_test_event"] = sim.apply(swarm_fixture_action(sim, actor, 1), 1)
            return super().run_business_simulation(identity, payload, callback, cancelled=cancelled)
    with TestClient(app) as client:
        register(client)
        service, reviewed = configure_local_live(app, monkeypatch)
        runtime = BlockedRuntime(tmp_path, tmp_path / "runtime")
        runtime.runtime_python, runtime.bridge = sys.executable, bridge
        service.oasis = runtime
        row = begin_live(client, upload_only(client, CASES[0]), max_seconds=12)
        assert row["status"] == "partial" and len(row["result"]["simulation"]["events"]) == 1
        assert row["result"]["report"] and reviewed == [True]
        assert row["result"]["elapsed_seconds"] < 12


def test_replay_rejects_gaps_or_tampered_state_and_preserves_private_business_transactions():
    from test_business_swarm import make_sim, action
    sim = make_sim()
    supplier = next(p.id for p in sim.personas.values() if p.role == "supplier")
    operator = next(p.id for p in sim.personas.values() if p.role == "operator")
    offer = sim.apply(action(sim, supplier, kind="offer_terms", target_id=operator, amount="15000", content="", visibility="participants"), 1)
    sim.apply(action(sim, operator, kind="accept_terms", target_id=supplier, parent_event_ids=[offer["id"]], content="", visibility="participants"), 1)
    snapshot = {"personas": [p.model_dump(mode="json") for p in sim.personas.values()], "values": sim.initial_values, "config": {"interaction_mode": "swarm", "max_events": 50}}
    replayed = replay_committed(snapshot, sim.events)
    assert replayed["calculation"] == sim.snapshot()["calculation"]
    assert replayed["events"] == sim.events
    with pytest.raises(ValueError):
        replay_committed(snapshot, sim.events[1:])
    bad = deepcopy(sim.events)
    bad[0]["state_after"]["offered_cost"] = "1"
    with pytest.raises(ValueError, match="State pemulihan"):
        replay_committed(snapshot, bad)


def test_cancelled_discussion_requires_explicit_review_and_preserves_source_without_replaying_personas(tmp_path, database_url, monkeypatch):
    app = make_app(tmp_path, database_url)
    with TestClient(app) as client:
        register(client)
        service, reviewed = configure_local_live(app, monkeypatch)
        service.oasis = InterruptedRuntime()
        row = begin_live(client, upload_only(client, CASES[0]))
        # Construct the durable state of cancellation during the discussion phase.
        with app.state.repository.engine.begin() as db:
            db.execute(update(business_analyses).where(business_analyses.c.id == row['id']).values(status='cancelled', stage='cancelled', result={}))
            db.execute(delete(business_events).where(business_events.c.analysis_id == row['id'], business_events.c.type.not_in(['interaction', 'simulation'])))
        base = f"/api/v1/business/analyses/{row['id']}"
        frozen_events = service.repository.events(row['id'])
        assert client.get(base).json()['status'] == 'cancelled'
        assert client.post(base + '/specialist-review', json={}, headers={'Idempotency-Key':'no-explicit-recovery'}).status_code == 409
        class NoMorePersonaCalls:
            def run_business_simulation(self, *a, **k):
                raise AssertionError('Recovery must never repeat stakeholder inference')
        service.oasis = NoMorePersonaCalls()
        reviewed.clear()
        response = client.post(base + '/specialist-review', json={'recover_cancelled':True}, headers={'Idempotency-Key':'explicit-recovery'})
        assert response.status_code == 202, response.text
        recovered = wait(client, response.json()['id'])
        assert recovered['status'] == 'partial' and recovered['result']['report']
        assert recovered['result']['simulation']['events'] == row['result']['simulation']['events']
        seed = recovered['input_snapshot']['review_source']
        assert seed['recovered_cancelled'] and seed['original_execution_status'] == 'cancelled'
        assert seed['evidence'] == [] and seed['committed_events_sha256']
        assert reviewed == [True]
        assert client.post(base + '/specialist-review', json={'recover_cancelled':True}, headers={'Idempotency-Key':'explicit-recovery'}).json()['id'] == recovered['id']
        assert client.get(base).json()['status'] == 'cancelled'
        assert service.repository.analysis(row['id'])['result'] == {}
        assert service.repository.events(row['id']) == frozen_events
        register(client, 'another-recovery-owner@example.com')
        assert client.post(base + '/specialist-review', json={'recover_cancelled':True}, headers={'Idempotency-Key':'wrong-owner'}).status_code == 404


def test_cancelled_review_recovery_refuses_possible_previously_dispatched_review(tmp_path, database_url, monkeypatch):
    app = make_app(tmp_path, database_url)
    with TestClient(app) as client:
        register(client)
        service, reviewed = configure_local_live(app, monkeypatch)
        service.oasis = InterruptedRuntime()
        row = begin_live(client, upload_only(client, CASES[0]))
        with app.state.repository.engine.begin() as db:
            db.execute(update(business_analyses).where(business_analyses.c.id == row['id']).values(status='cancelled', stage='cancelled', result={}))
        response = client.post(f"/api/v1/business/analyses/{row['id']}/specialist-review", json={'recover_cancelled':True}, headers={'Idempotency-Key':'possible-paid-duplicate'})
        assert response.status_code == 409
        assert reviewed == [True]
