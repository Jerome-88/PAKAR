from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert, select, update

from app.business.tables import business_analyses, business_chat_turns, business_documents, provider_spend_accounts, provider_spend_reservations
from app.business.repository import utcnow
from test_business_api import make_app, register, create_project, upload, wait


def test_delete_completed_project_cleans_files_and_results_but_keeps_credit_ledger(tmp_path, database_url):
    app = make_app(tmp_path, database_url)
    runtime_root = tmp_path / "runtime"
    with TestClient(app) as client:
        app.state.business.settings = replace(app.state.business.settings, oasis_data_dir=runtime_root)
        register(client)
        project = upload(client, create_project(client))
        base = f"/api/v1/business/projects/{project['id']}"
        run = client.post(base + "/quick-analysis", json={"expected_revision": project["revision"], "engine": "fixture", "rounds": 2, "max_personas": 4, "customer_count": 2}).json()
        run = wait(client, run["id"])
        assert run["status"] == "completed"
        runtime_id = "business-" + "a" * 32
        runtime = runtime_root / runtime_id
        runtime.mkdir(parents=True)
        (runtime / "business.db").write_text("synthetic trace")
        outside = tmp_path / "outside"
        outside.mkdir()
        result = run["result"] | {"runtime_calls": [{"runtime_id": runtime_id}, {"runtime_id": "../../outside"}]}
        with app.state.business.shared.engine.begin() as db:
            key = db.execute(select(business_documents.c.storage_key).where(business_documents.c.project_id == project["id"])).scalar_one()
            db.execute(update(business_analyses).where(business_analyses.c.id == run["id"]).values(result=result))
            db.execute(insert(provider_spend_accounts).values(id="retained-account", available_usd="0.1"))
            db.execute(insert(provider_spend_reservations).values(id="analysis:" + run["id"], account_id="retained-account", ceiling_usd="0.1", charged_usd="0.001"))
        assert app.state.business.storage.exists(key)
        response = client.delete(base)
        assert response.status_code == 200, response.text
        assert response.json() == {"status": "deleted", "cleanup_pending": False}
        assert client.get(base).status_code == 404
        assert client.get(f"/api/v1/business/analyses/{run['id']}").status_code == 404
        assert not app.state.business.storage.exists(key)
        assert not runtime.exists() and outside.exists()
        with app.state.business.shared.engine.connect() as db:
            assert db.execute(select(provider_spend_reservations.c.id)).scalar_one() == "analysis:" + run["id"]


@pytest.mark.parametrize("kind", ["analysis", "chat"])
def test_delete_rejects_active_work_without_removing_project_or_uploads(tmp_path, database_url, kind):
    app = make_app(tmp_path, database_url)
    with TestClient(app) as client:
        register(client)
        project = upload(client, create_project(client))
        with app.state.business.shared.engine.begin() as db:
            if kind == "analysis":
                db.execute(insert(business_analyses).values(id="active-analysis", project_id=project["id"], status="running", stage="simulation", input_snapshot={"config": {"engine": "fixture"}, "revision": project["revision"]}, result={}, created_at=utcnow(), updated_at=utcnow()))
            else:
                db.execute(insert(business_chat_turns).values(id="active-chat", project_id=project["id"], sequence=1, status="queued", request={}, input_snapshot={}, created_at=utcnow(), updated_at=utcnow(), idempotency_key="active"))
        response = client.delete(f"/api/v1/business/projects/{project['id']}")
        assert response.status_code == 409
        assert client.get(f"/api/v1/business/projects/{project['id']}").status_code == 200


def test_delete_cannot_cross_account_boundary(tmp_path, database_url):
    app = make_app(tmp_path, database_url)
    with TestClient(app) as client:
        register(client, "first@example.com")
        project = create_project(client)
        register(client, "second@example.com")
        assert client.delete(f"/api/v1/business/projects/{project['id']}").status_code == 404
