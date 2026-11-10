import json
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from fastapi.testclient import TestClient

from app.business.contracts import Finding
from test_business_api import create_project, make_app, prepare, register, wait


def test_paired_review_api_uses_real_sdk_with_local_provider_and_preserves_conflicting_source(tmp_path, database_url, monkeypatch):
    calls = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            context = json.loads(body["messages"][-1]["content"])
            role = context["role"]
            calls.append({"role": role, "peers": [p["author"] for p in context["peer_findings"]], "body": body})
            finding = Finding(id="candidate", author=role, title=f"{role}: local validation", category="evidence", severity="MEDIUM", origin="evidence", claim_ids=[context["claims"][0]["id"]], evidence_ids=["local-conflict"], reasoning="Official figures conflict; demand remains unknown", evidence_gaps=["Source reconciliation"], next_validation="Check survey scope", owner_suggestion="Analyst").model_dump(mode="json")
            content = {"findings": [finding], "disagreements": ["A prior hypothesis still needs validation"]}
            response = {"id": f"local-{role}", "model": body["model"], "object": "chat.completion", "created": 1,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": json.dumps(content)}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 100, "total_tokens": 200, "cost": 0}}
            raw = json.dumps(response).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        app = make_app(tmp_path, database_url)
        with TestClient(app) as client:
            register(client)
            project = prepare(client, create_project(client))
            service = app.state.business
            service.settings = replace(service.settings, llm_api_key="local-test-only", llm_base_url=f"http://127.0.0.1:{server.server_port}/v1", llm_structured_outputs=True)
            runtime_caps = []
            class Runtime:
                def run_business_simulation(self, run_id, snapshot, receive, **kwargs):
                    runtime_caps.append(snapshot["config"]["max_seconds"])
                    return service._fixture_simulation(run_id, snapshot, lambda stage, payload: None)
            service.oasis = Runtime()
            source = {"id": "local-conflict", "status": "CONFLICTING", "value": None, "reason": "Local source conflict fixture"}
            monkeypatch.setattr(service.evidence, "retrieve", lambda *a, **k: [source])
            response = client.post(f"/api/v1/business/projects/{project['id']}/analyses", json={"expected_revision": project["revision"], "engine": "oasis", "public_brief": "Konsep usaha untuk diskusi customer; biaya internal tidak dibagikan.", "rounds": 2, "max_personas": 24, "max_tokens": 100000, "max_seconds": 60, "review_concurrency": 2})
            assert response.status_code == 202
            row = wait(client, response.json()["id"])
            assert row["status"] == "completed", row["result"]
            assert row["input_snapshot"]["review_policy"] == "paired-v2"
            assert 30 < runtime_caps[0] < 40
            assert len(calls) == 4 and len({c["role"] for c in calls}) == 4
            assert all(c["body"]["max_tokens"] == 1100 for c in calls)
            assert row["result"]["usage"]["call_count"] == 4
            assert row["result"]["usage"]["actual_tokens"] == 800
            assert row["result"]["usage"]["cost"] == 0
            execution = row["result"]["review_execution"]
            assert execution["concurrency"] == 2 and len(execution["waves"]) == 2
            assert len(row["result"]["disagreements"]) == 4
            assert all(f["status"] == "NEEDS_VALIDATION" for f in row["result"]["findings"])
            assert row["result"]["evidence"][0]["value"] is None
            assert any("konflik" in limitation for limitation in row["result"]["limitations"])
            report = client.get(f"/api/v1/business/analyses/{row['id']}/report").json()
            assert len(report["sections"]) == 8
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
