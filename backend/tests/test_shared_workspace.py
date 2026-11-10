import io
import time

from fastapi.testclient import TestClient

from app import create_app
from app.business.agents import BusinessLLM
from app.config import Settings


CONTEXT = {"name": "Ruang kerja bersama", "industry": "FMCG", "region": "Indonesia", "target_customer": "Calon pembeli", "decision_question": "Apa yang perlu diuji?", "data_classification": "synthetic"}


def app_for(tmp_path, database_url, **overrides):
    return create_app({"TESTING": True, "AUTH_REQUIRED": False, "DATABASE_URL": database_url,
                       "UPLOAD_DIR": tmp_path / "uploads", "JOB_DELAY": 0,
                       "LLM_API_KEY": "local-test-key", "LLM_BASE_URL": "http://127.0.0.1:9/v1", **overrides})


def completed(client, url):
    until = time.monotonic() + 15
    while time.monotonic() < until:
        value = client.get(url).json()
        if value["status"] not in {"queued", "running"}:
            assert value["status"] == "completed", value
            return value
        time.sleep(0.03)
    raise AssertionError("Fixture job did not complete")


def test_shared_mode_is_default_outside_explicit_auth_configuration(monkeypatch):
    monkeypatch.delenv("AUTH_REQUIRED")
    assert Settings.load({"TESTING": True}).auth_required is False


def test_no_cookie_intake_analysis_and_persistent_chat(tmp_path, database_url, monkeypatch):
    calls = []

    def answer(self, role, instruction, payload, *args, **kwargs):
        calls.append(role)
        return {"answer": "Jawaban fixture: manfaat produk tetap perlu diuji.", "questions": [], "source_ids": [], "suggested_revision": None}

    monkeypatch.setattr(BusinessLLM, "generate", answer)
    with TestClient(app_for(tmp_path, database_url)) as client:
        identity = client.get("/api/auth/me")
        assert identity.status_code == 200
        assert identity.json()["user"]["shared"] is True
        assert "set-cookie" not in identity.headers
        client.cookies.set("pakar_session", "expired-cookie-is-irrelevant")
        assert client.get("/api/auth/me").json() == identity.json()
        project = client.post("/api/v1/business/projects", json=CONTEXT).json()
        base = f"/api/v1/business/projects/{project['id']}"
        uploaded = client.post(base + "/documents", files=[("files", ("idea.txt", io.BytesIO(b"Konsep produk untuk customer; supplier perlu memeriksa spesifikasi bersama operator."), "text/plain"))])
        assert uploaded.status_code == 201
        project = uploaded.json()
        started = client.post(base + "/quick-analysis", json={"expected_revision": project["revision"], "engine": "fixture", "rounds": 2, "interaction_mode": "swarm", "customer_count": 2, "max_personas": 4})
        assert started.status_code == 202, started.text
        run_url = f"/api/v1/business/analyses/{started.json()['id']}"
        result = completed(client, run_url)
        assert client.get(run_url + "/report").status_code == 200
        assert client.get(run_url + "/export").status_code == 200
        project = client.get(base).json()
        sent = client.post(base + "/conversation", headers={"Idempotency-Key": "shared-chat"}, json={"content": "Apa yang perlu diuji?", "target": "facilitator", "expected_revision": project["revision"], "analysis_id": result["id"]})
        assert sent.status_code == 202, sent.text
        until = time.monotonic() + 15
        while time.monotonic() < until:
            turn = client.get(base + "/conversation").json()["turns"][-1]
            if turn["status"] not in {"queued", "running"}:
                break
            time.sleep(0.03)
        assert turn["status"] == "completed", turn
        assert len(calls) == 1
        assert client.get(run_url).json()["result"] == result["result"]
        assert client.post("/api/auth/register", json={"name": "Unused", "email": "unused@example.com", "password": "testing-password"}).status_code == 409
    with TestClient(app_for(tmp_path, database_url)) as fresh:
        assert fresh.get("/api/auth/me").json() == identity.json()
        assert fresh.get(base + "/conversation").json()["turns"][-1]["response"]["answer"].startswith("Jawaban fixture")
        assert len(fresh.get("/api/v1/business/projects").json()["items"]) == 1


def test_older_owners_remain_readable_and_editable_without_reassigning_them(tmp_path, database_url):
    old_projects = []
    with TestClient(app_for(tmp_path, database_url, AUTH_REQUIRED=True)) as private:
        for index in range(2):
            registered = private.post("/api/auth/register", json={"name": f"Owner {index}", "email": f"owner-{index}@example.com", "password": "testing-password"})
            assert registered.status_code == 201
            project = private.post("/api/v1/business/projects", json={**CONTEXT, "name": f"Existing {index}"}).json()
            old_projects.append(project)
            private.post("/api/auth/logout")
    with TestClient(app_for(tmp_path, database_url)) as public:
        assert {p["id"] for p in public.get("/api/v1/business/projects").json()["items"]} == {p["id"] for p in old_projects}
        for project in old_projects:
            base = f"/api/v1/business/projects/{project['id']}"
            loaded = public.get(base)
            assert loaded.status_code == 200
            assert loaded.json()["owner_user_id"] == project["owner_user_id"]
            saved = public.post(base + "/ideas", headers={"Idempotency-Key": "public-revision"}, json={"title": "Ide bersama", "text": "Produk yang perlu diuji ke calon pembeli.", "expected_revision": project["revision"], "expected_version": 0})
            assert saved.status_code == 201, saved.text
            assert public.get(base + "/conversation").json()["ideas"][0]["title"] == "Ide bersama"
        assert public.get("/api/v1/business/projects/missing").status_code == 404
        assert public.get("/api/v1/business/analyses/missing").status_code == 404
    with TestClient(app_for(tmp_path, database_url, AUTH_REQUIRED=True)) as private_again:
        assert private_again.get("/api/v1/business/projects").status_code == 401
        disabled = private_again.post("/api/auth/login", json={"email": "workspace@pakar.invalid", "password": "testing-password"})
        assert disabled.status_code == 401
