import json
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.business.tables import business_chat_turns
from app.database import jobs
from app.business.repository import utcnow
from test_business_api import make_app, register, create_project, upload


@pytest.fixture
def workspace(tmp_path, database_url):
    app = make_app(tmp_path, database_url)
    with TestClient(app) as client:
        register(client)
        project = upload(client, create_project(client))
        app.state.business.settings = replace(app.state.business.settings, embedded_worker=False, llm_api_key="local-test-only", llm_base_url="http://127.0.0.1:1/v1", llm_structured_outputs=True)
        yield app, client, project


def project_path(project):
    return f"/api/v1/business/projects/{project['id']}"


def save_idea(client, project, text="Dua rasa dipilih melalui dua ruang tube.", *, key="idea-create", idea=None, version=0, documents=None, source_turn_ids=None):
    path = project_path(project) + "/ideas" + (f"/{idea}/revisions" if idea else "")
    return client.post(path, headers={"Idempotency-Key": key}, json={"expected_revision": project["revision"], "expected_version": version, "title": "Pasta gigi dua rasa", "text": text, "document_ids": documents or [], "source_turn_ids": source_turn_ids or []})


def send(client, project, *, key="chat-send", idea=None, analysis=None, target="facilitator", message="Apa kelemahan ide ini dari dokumen yang diberikan?"):
    return client.post(project_path(project) + "/conversation", headers={"Idempotency-Key": key}, json={"expected_revision": project["revision"], "content": message, "target": target, "idea_revision_id": idea, "analysis_id": analysis})


def local_provider(monkeypatch, calls, *, bad_reference=False):
    def complete(operation, payload, timeout, **kwargs):
        request = payload["request"]
        context = json.loads(request["messages"][-1]["content"])
        calls.append(context)
        reply = {"answer": "Data ini belum membuktikan manfaat produk; uji apakah perubahan warna memberi nilai bagi pelanggan.", "questions": ["Bagaimana rasa dipilih dari tube?"], "source_ids": ["invented"] if bad_reference else [context["sources"][0]["id"]] if context["sources"] else [], "suggested_revision": None}
        return {"content": json.dumps(reply), "usage": {"total_tokens": 300, "prompt_tokens": 200, "completion_tokens": 100, "cost": 0.00001}, "finish_reason": "stop", "provider": "local-test", "model": "local-test", "id": "local-generation"}
    monkeypatch.setattr("app.business.agents.call_worker", complete)


def test_idea_revisions_are_immutable_idempotent_and_conflict_on_stale_versions(workspace):
    app, client, project = workspace
    first = save_idea(client, project)
    assert first.status_code == 201, first.text
    old = first.json()
    assert save_idea(client, project).json()["id"] == old["id"]
    assert save_idea(client, project, text="Changed content").status_code == 409
    project = client.get(project_path(project)).json()
    updated = save_idea(client, project, text="Dua ruang terpisah dan nozzle yang dapat dipilih.", key="idea-revise", idea=old["idea_id"], version=1)
    assert updated.status_code == 201, updated.text
    assert updated.json()["version"] == 2
    assert save_idea(client, project, key="stale", idea=old["idea_id"], version=1).status_code == 409
    history = client.get(project_path(project) + f"/ideas/{old['idea_id']}/revisions").json()["items"]
    assert [r["version"] for r in history] == [2, 1] and history[1] == old
    assert history[0]["content"]["provenance"] == "user_proposed_assumption"


def test_chat_calls_one_selected_role_once_and_refresh_or_duplicate_does_not_dispatch(workspace, monkeypatch):
    app, client, project = workspace
    calls = []; local_provider(monkeypatch, calls)
    idea = save_idea(client, project).json()
    project = client.get(project_path(project)).json()
    row = send(client, project, idea=idea["id"], target="finance")
    assert row.status_code == 202, row.text
    turn = row.json()
    assert send(client, project, idea=idea["id"], target="finance").json()["id"] == turn["id"]
    assert send(client, project, key="different-active", idea=idea["id"]).status_code == 409
    assert not calls
    assert app.state.workflow.run_once(turn["job_id"])
    for _ in range(2):
        state = client.get(project_path(project) + "/conversation").json()
    saved = state["turns"][0]
    assert saved["status"] == "completed" and saved["response"]["responder"] == "Finance Agent"
    assert len(calls) == 1 and calls[0]["idea"]["id"] == idea["id"]
    assert saved["response"]["citations"][0]["kind"] == "idea_assumption"
    assert saved["response"]["usage"][0]["phase"] == "conversation"
    assert send(client, project, idea=idea["id"], target="finance").json()["id"] == turn["id"]
    assert len(calls) == 1
    assert client.get(project_path(project)).json()["analyses"] == []


def test_unknown_model_citations_fail_without_retry_and_keep_message_and_billing(workspace, monkeypatch):
    app, client, project = workspace
    calls = []; local_provider(monkeypatch, calls, bad_reference=True)
    row = send(client, project).json()
    assert not app.state.workflow.run_once(row["job_id"])
    saved = client.get(project_path(project) + "/conversation").json()["turns"][0]
    assert saved["status"] == "failed" and saved["request"]["content"]
    assert "answer" not in saved["response"] and saved["response"]["usage"][0]["cost"] == 0.00001
    assert not app.state.workflow.run_once() and len(calls) == 1


def test_queued_chat_cancel_and_expired_lease_fence_old_worker(workspace, monkeypatch):
    app, client, project = workspace
    calls = []; local_provider(monkeypatch, calls)
    row = send(client, project).json()
    assert client.post(project_path(project) + f"/conversation/{row['id']}/cancel").status_code == 200
    assert not app.state.workflow.run_once(row["job_id"]) and not calls
    row = send(client, project, key="expired-chat").json()
    repo = app.state.repository
    job = repo.claim_next_job("expired-worker", 60, row["job_id"])
    with repo.engine.begin() as db:
        db.execute(update(jobs).where(jobs.c.id == job["id"]).values(lease_expires_at=utcnow() - timedelta(seconds=1)))
    repo.requeue_expired_jobs()
    with pytest.raises(RuntimeError, match="lease"):
        app.state.business.conversation.repository.publish(job, "expired-worker", "completed", {"answer": "late"})
    saved = client.get(project_path(project) + "/conversation").json()["turns"][-1]
    assert saved["status"] == "failed" and saved["response"]["error_type"] == "LeaseExpired"
    assert not repo.claim_next_job("replacement", 60, row["job_id"])


def test_document_ideas_are_separate_and_only_selected_revision_enters_new_runs(workspace):
    app, client, project = workspace
    path = project_path(project)
    uploaded = client.post(path + "/documents", data={"purpose": "idea"}, files=[("files", ("idea.txt", b"Produk baru menggunakan dua ruang untuk rasa berbeda.", "text/plain"))])
    assert uploaded.status_code == 201
    project = uploaded.json(); document = project["documents"][-1]
    assert document["content"]["purpose"] == "idea"
    original = save_idea(client, project, documents=[document["id"]]).json()
    project = client.get(path).json()
    first = client.post(path + "/quick-analysis", headers={"Idempotency-Key": "first-idea-run"}, json={"expected_revision": project["revision"], "engine": "fixture", "rounds": 2, "idea_revision_id": original["id"]}).json()
    frozen = deepcopy(first["input_snapshot"])
    assert frozen["idea"]["id"] == original["id"]
    assert any(c["source"].get("idea_revision_id") == original["id"] for c in frozen["claims"])
    assert app.state.workflow.run_once(first["job_id"])
    project = client.get(path).json()
    changed = save_idea(client, project, text="Desain baru memakai satu rasa saja.", key="changed-idea", idea=original["idea_id"], version=1).json()
    project = client.get(path).json()
    second = client.post(path + "/quick-analysis", headers={"Idempotency-Key": "second-idea-run"}, json={"expected_revision": project["revision"], "engine": "fixture", "rounds": 2, "idea_revision_id": changed["id"]}).json()
    assert second["input_snapshot"]["idea"]["text"] == changed["content"]["text"]
    assert not any(c["source"]["document_id"] == document["id"] for c in second["input_snapshot"]["claims"])
    assert client.get(f"/api/v1/business/analyses/{first['id']}").json()["input_snapshot"]["idea"] == frozen["idea"]


def test_cross_user_access_sources_and_ideas_are_rejected(workspace, tmp_path, database_url):
    app, client, project = workspace
    idea = save_idea(client, project).json()
    # Different account in the same application has no project access.
    client.post("/api/auth/logout")
    register(client, "other-business@example.com")
    assert client.get(project_path(project) + "/conversation").status_code == 404
    assert client.get(project_path(project) + f"/ideas/{idea['idea_id']}/revisions").status_code == 404
    other = create_project(client)
    assert send(client, other, idea=idea["id"]).status_code == 404
    assert save_idea(client, other, documents=[project["documents"][0]["id"]]).status_code == 409


def test_chat_snapshot_uses_frozen_idea_and_never_silently_applies_ai_proposal(workspace, monkeypatch):
    app, client, project = workspace
    calls = []; local_provider(monkeypatch, calls)
    idea = save_idea(client, project).json(); project = client.get(project_path(project)).json()
    queued = send(client, project, idea=idea["id"]).json()
    assert save_idea(client, project, text="Konsep berbeda untuk versi berikutnya.", key="newer", idea=idea["idea_id"], version=1).status_code == 201
    assert app.state.workflow.run_once(queued["job_id"])
    assert calls[0]["idea"]["version"] == 1 and calls[0]["sources"][0]["text"] == idea["content"]["text"]
    revisions = client.get(project_path(project) + f"/ideas/{idea['idea_id']}/revisions").json()["items"]
    assert len(revisions) == 2


def test_no_key_chat_is_unavailable_but_local_ideas_can_be_saved(workspace):
    app, client, project = workspace
    app.state.business.settings = replace(app.state.business.settings, llm_api_key="")
    assert send(client, project).status_code == 503
    assert save_idea(client, project).status_code == 201
    with app.state.repository.engine.connect() as db:
        assert db.execute(select(business_chat_turns)).first() is None


def test_saved_analysis_context_contains_conditional_calculation_and_rejects_other_project(workspace, monkeypatch):
    app, client, project = workspace
    calls = []; local_provider(monkeypatch, calls)
    run = client.post(project_path(project) + "/quick-analysis", headers={"Idempotency-Key": "calculation-run"}, json={"expected_revision": project["revision"], "engine": "fixture", "rounds": 2}).json()
    assert app.state.workflow.run_once(run["job_id"])
    project = client.get(project_path(project)).json()
    queued = send(client, project, target="finance", analysis=run["id"], message="Berapa BEP dan apa input perhitungan yang masih belum tersedia?").json()
    assert app.state.workflow.run_once(queued["job_id"])
    calc = next(s for s in calls[0]["sources"] if s["kind"] == "conditional_calculation")
    assert '"break_even_units_monthly": "2000"' in calc["text"]
    assert any(s["kind"] == "synthetic_stance_summary" for s in calls[0]["sources"])
    assert calls[0]["prompt_version"] == "project-chat-1.1"
    assert len(calls[0]["sources"]) <= 14
    other = create_project(client)
    assert send(client, other, key="wrong-project-analysis", analysis=run["id"]).status_code == 409


def test_result_chat_sources_match_explicit_positions_without_inventing_votes(workspace):
    from app.business.conversation import dialogue_sources
    report = {"appendix": {"personas": [{"id": key, "name": key, "role": "customer"} for key in ("a", "b", "c", "missing")], "events": [
        {"id": "e2", "actor_id": "b", "target_id": "a", "round": 2, "kind": "reply_message", "content": "Perlu uji mekanisme", "stance_update": {"after": "conditional", "reason": "Syarat dari pesan"}},
        {"id": "e1", "actor_id": "a", "target_id": "all", "round": 1, "kind": "post_message", "content": "Manfaat belum terbukti", "stance_update": {"after": "oppose", "reason": "Posisi lama"}},
        {"id": "rejected", "actor_id": "b", "target_id": "a", "round": 3, "kind": "action_rejected", "rationale": "Pesan ditolak", "stance_update": {"after": "oppose", "reason": "Tidak dipakai"}},
        {"id": "financial", "actor_id": "missing", "target_id": "a", "round": 1, "kind": "accept_terms", "rationale": "Menerima syarat harga", "state_after": {"position": "terms_accepted"}},
    ], "stances": {"a": {"stance": "support", "stance_reason": "Posisi akhir tersimpan"}, "c": {"stance": "undecided", "stance_reason": "Belum ada bukti"}}}}
    before = deepcopy(report)
    sources = dialogue_sources("saved", report)
    assert report == before
    summary = sources[0]["text"]
    assert all(part in summary for part in ("4 persona aktif", "Mendukung: 1", "Menolak: 0", "Bersyarat: 1", "Belum memutuskan: 1", "Belum tercatat: 1"))
    assert next(s for s in sources if s["id"] == "saved:stance:a")["text"].endswith("Posisi akhir tersimpan.")
    assert not any(s["id"] == "rejected" for s in sources)
    assert any(s["id"] == "e2" and s["kind"] == "synthetic_interaction" for s in sources)
    report["appendix"]["stances"]["b"] = {"stance": "invalid"}
    assert "Belum tercatat: 2" in dialogue_sources("saved", report)[0]["text"]


def test_result_chat_history_stays_with_selected_analysis(workspace, monkeypatch):
    app, client, project = workspace
    calls = []; local_provider(monkeypatch, calls)
    runs = []
    for index in range(2):
        response = client.post(project_path(project) + "/quick-analysis", headers={"Idempotency-Key": f"history-run-{index}"}, json={"expected_revision": project["revision"], "engine": "fixture", "rounds": 2})
        assert response.status_code == 202, response.text
        run = response.json()
        assert app.state.workflow.run_once(run["job_id"])
        runs.append(run)
        project = client.get(project_path(project)).json()
    before = client.get(f"/api/v1/business/analyses/{runs[0]['id']}").json()
    for index in (0, 1, 0):
        queued = send(client, project, key=f"history-chat-{len(calls)}", analysis=runs[index]["id"], message=f"Bahas hasil {index}, konteks tersimpan").json()
        assert app.state.workflow.run_once(queued["job_id"])
    assert not calls[1]["history"]
    assert len(calls[2]["history"]) == 1
    assert calls[2]["history"][0]["user"] == "Bahas hasil 0, konteks tersimpan"
    after = client.get(f"/api/v1/business/analyses/{runs[0]['id']}").json()
    assert before["input_snapshot"] == after["input_snapshot"] and before["result"] == after["result"]


def test_cancelled_in_flight_answer_is_discarded_but_known_billing_is_kept(workspace, monkeypatch):
    app, client, project = workspace
    queued = send(client, project).json()
    owner = project["owner_user_id"]
    def completed_after_cancel(operation, payload, timeout, **kwargs):
        app.state.business.conversation.repository.cancel(project["id"], queued["id"], owner)
        return {"content": json.dumps({"answer": "Late answer", "questions": [], "source_ids": [], "suggested_revision": None}), "usage": {"total_tokens": 50, "cost": 0.0001}, "finish_reason": "stop"}
    monkeypatch.setattr("app.business.agents.call_worker", completed_after_cancel)
    assert not app.state.workflow.run_once(queued["job_id"])
    saved = client.get(project_path(project) + "/conversation").json()["turns"][0]
    assert saved["status"] == "cancelled" and "answer" not in saved["response"]
    assert saved["response"]["usage"][0]["cost"] == 0.0001
    assert saved["response"]["billing_status"] == "provider_reported"
