import sys

from fastapi.testclient import TestClient

from app import oasis_direct_bridge
from app.legacy_branding import LEGACY_OASIS_RUNTIME_ENV, LEGACY_SESSION_COOKIE
from test_auth import make_app, register


def test_old_session_survives_rename_but_cannot_override_new_cookie(tmp_path, database_url):
    with TestClient(make_app(tmp_path, database_url, SESSION_COOKIE_NAME="pakar_session")) as client:
        user_id = register(client).json()["user"]["id"]
        token = client.cookies.get("pakar_session")
        client.cookies.clear()
        client.cookies.set(LEGACY_SESSION_COOKIE, token)
        assert client.get("/api/auth/me").json()["user"]["id"] == user_id
        client.cookies.set("pakar_session", "invalid-new-token")
        assert client.get("/api/auth/me").status_code == 401
        client.cookies.set("pakar_session", "")
        assert client.get("/api/auth/me").status_code == 401


def test_logout_clears_and_revokes_both_cookie_names(tmp_path, database_url):
    app = make_app(tmp_path, database_url, SESSION_COOKIE_NAME="pakar_session")
    with TestClient(app) as client:
        register(client)
        legacy_token = client.cookies.get("pakar_session")
        login = client.post("/api/auth/login", json={"email": "user@example.com", "password": "kata-sandi-kuat"})
        assert any(LEGACY_SESSION_COOKIE in value and "Max-Age=0" in value for value in login.headers.get_list("set-cookie"))
        new_token = client.cookies.get("pakar_session")
        client.cookies.set(LEGACY_SESSION_COOKIE, legacy_token)
        assert client.post("/api/auth/logout", headers={"Origin": "https://evil.example"}).status_code == 403
        assert app.state.repository.user_for_session(legacy_token)
        response = client.post("/api/auth/logout")
        assert response.status_code == 200
        assert not app.state.repository.user_for_session(legacy_token)
        assert not app.state.repository.user_for_session(new_token)
        cleared = response.headers.get_list("set-cookie")
        assert len(cleared) == 2
        assert all("Max-Age=0" in value for value in cleared)


def test_custom_session_namespace_does_not_accept_legacy_cookie(tmp_path, database_url):
    with TestClient(make_app(tmp_path, database_url, SESSION_COOKIE_NAME="custom_session")) as client:
        register(client)
        token = client.cookies.get("custom_session")
        client.cookies.clear()
        client.cookies.set(LEGACY_SESSION_COOKIE, token)
        assert client.get("/api/auth/me").status_code == 401


def test_runtime_path_accepts_old_launcher_and_prefers_new_name(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.delenv("PAKAR_OASIS_RUNTIME_PATH", raising=False)
    monkeypatch.setenv(LEGACY_OASIS_RUNTIME_ENV, str(tmp_path / "existing"))
    assert oasis_direct_bridge.configure_runtime() == (tmp_path / "existing").resolve()
    monkeypatch.setenv("PAKAR_OASIS_RUNTIME_PATH", str(tmp_path / "pakar"))
    assert oasis_direct_bridge.configure_runtime() == (tmp_path / "pakar").resolve()
