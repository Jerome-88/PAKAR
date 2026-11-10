from copy import deepcopy

from fastapi.testclient import TestClient

from app.business.contracts import SwarmAction
from app.business.reviews import compact_context
from test_business_api import make_app, register, wait
from test_business_quick import CASES, upload_only


def start(client, project):
    response = client.post(f"/api/v1/business/projects/{project['id']}/quick-analysis", json={"expected_revision": project["revision"], "engine": "fixture"})
    assert response.status_code == 202, response.text
    return wait(client, response.json()["id"])


def test_automatic_swarm_reports_conversation_stance_and_scenario_without_rewriting_baseline(tmp_path, database_url):
    with TestClient(make_app(tmp_path, database_url)) as client:
        register(client)
        row = start(client, upload_only(client, CASES[0]))
        assert row["status"] == "completed", row["result"].get("error")
        snapshot, result = row["input_snapshot"], row["result"]
        customers = {p["id"] for p in snapshot["personas"] if p["role"] == "customer"}
        assert len(customers) == 4 and len(snapshot["personas"]) <= 8
        assert snapshot["interaction_policy"] == "reactive-v2"
        assert snapshot["config"]["discussion_policy"] == "reactive-v2"
        assert result["action_validation"]["rejected"] == 0
        events = result["simulation"]["events"]
        assert any(e["kind"] == "reply_message" and e["actor_id"] in customers and e["target_id"] in customers for e in events)
        assert len({s["stance"] for s in result["simulation"]["stances"].values()}) > 1
        report = client.get(f"/api/v1/business/analyses/{row['id']}/report").json()
        assert len(report["sections"]) == 8 and report["appendix"]["stances"]
        assert any("Perubahan sikap" in f["title"] and f["interaction_chain"] for f in report["findings"])
        assert any(d["author"] == "Jejak diskusi swarm" for d in report["contradictions"])
        exported = client.get(f"/api/v1/business/analyses/{row['id']}/export").text
        assert "Posisi dan perubahan sikap sintetis" in exported and "Membalas pesan" in exported
        payload, schema = compact_context("Risk Agent", snapshot, result["simulation"], result["evidence"], result["findings"])
        assert payload["stances"] and any(e.get("content") for e in payload["events"])
        assert set(schema["properties"]["findings"]["items"]["properties"]["event_ids"]["items"]["enum"]) <= {e["id"] for e in payload["events"]}
        before = deepcopy(row)
        response = client.post(f"/api/v1/business/analyses/{row['id']}/scenarios", json={"shock": {"kind": "competitor_price_cut", "magnitude_percent": 20, "response_strategy": "match_price", "effective_round": 2, "duration_rounds": 2, "region": snapshot["context"]["region"]}})
        assert response.status_code == 202, response.text
        scenario = wait(client, response.json()["id"])
        assert scenario["status"] == "completed"
        assert scenario["input_snapshot"]["personas"] == snapshot["personas"]
        assert scenario["result"]["simulation"]["calculation"]["break_even_units_monthly"] == "3000"
        assert client.get(f"/api/v1/business/analyses/{row['id']}").json() == before


def test_quiet_round_is_not_consensus_and_does_not_skip_a_future_shock(tmp_path, database_url, monkeypatch):
    def abstain(sim, actor_id, round_number):
        state = sim.states[actor_id]
        return SwarmAction(actor_id=actor_id, target_id="all", kind="abstain", expected_version=state["version"], rationale="Tidak ada informasi baru untuk ditambahkan", stance=state["stance"], stance_reason=state["stance_reason"])
    monkeypatch.setattr("app.business.service.swarm_fixture_action", abstain)
    with TestClient(make_app(tmp_path, database_url)) as client:
        register(client)
        row = start(client, upload_only(client, CASES[0]))
        assert row["status"] == "completed" and row["result"]["simulation"]["stop_reason"] == "discussion_quiet"
        assert len(row["result"]["simulation"]["events"]) == len(row["input_snapshot"]["personas"])
        assert all(s["stance"] == "undecided" for s in row["result"]["simulation"]["stances"].values())
        response = client.post(f"/api/v1/business/analyses/{row['id']}/scenarios", json={"shock": {"kind": "supplier_cost_increase", "magnitude_percent": 20, "effective_round": 2, "duration_rounds": 2, "region": row["input_snapshot"]["context"]["region"]}})
        scenario = wait(client, response.json()["id"])
        assert any(e["kind"] == "shock" and e["round"] == 2 for e in scenario["result"]["simulation"]["events"])
        project = client.get(f"/api/v1/business/projects/{row['project_id']}").json()
        response = client.post(f"/api/v1/business/projects/{project['id']}/quick-analysis", json={"expected_revision": project["revision"], "engine": "fixture", "max_events": 3})
        bounded = wait(client, response.json()["id"])
        assert bounded["status"] == "partial" and bounded["result"]["simulation"]["stop_reason"] == "event_budget"
