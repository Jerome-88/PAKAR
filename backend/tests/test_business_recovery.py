import json
import os
import subprocess
import sys
import time
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event, Thread

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.business.repository import utcnow
from app.database import jobs
from app.repository import Repository
from test_business_api import create_project, make_app, prepare, register


def test_worker_crash_stops_blocked_child_and_recovers_live_job_without_paid_retry(tmp_path, database_url):
    entered, release = Event(), Event()
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            requests.append(True)
            entered.set()
            release.wait(30)
            try:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"{}")
            except OSError: pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    controller = tmp_path / "crashing_worker.py"
    controller.write_text('''import json,sys
from pathlib import Path
from app.repository import Repository
from app.business import budget
p=json.load(sys.stdin)
r=Repository(p["database_url"])
j=r.claim_next_job("crash-test-worker",60,p["job_id"])
assert j is not None
original=budget.subprocess.Popen
def capture(*args,**kwargs):
 child=original(*args,**kwargs)
 Path(p["child_pid_path"]).write_text(str(child.pid))
 return child
budget.subprocess.Popen=capture
budget.call_worker("llm_completion",p["request"],60)
''', encoding="utf-8")
    process, child_pid = None, None
    try:
        app = make_app(tmp_path, database_url)
        with TestClient(app) as client:
            register(client)
            project = prepare(client, create_project(client))
            service = app.state.business
            snapshot = {"context": project["context"], "revision": project["revision"], "config": {"engine": "oasis"}}
            row = service.repository.enqueue(project["id"], project["owner_user_id"], snapshot)
            payload = {"database_url": database_url, "job_id": row["job_id"], "child_pid_path": str(tmp_path / "child.pid"),
                "request": {"api_key": "local-test-only", "model": "local", "base_url": f"http://127.0.0.1:{server.server_port}/v1", "timeout": 60,
                "request": {"model": "local", "messages": [{"role": "user", "content": "local crash test"}], "max_tokens": 10}}}
            process = subprocess.Popen([sys.executable, str(controller)], cwd=Path(__file__).resolve().parents[1],
                env=os.environ | {"PYTHONPATH": str(Path(__file__).resolve().parents[1])},
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
            process.stdin.write(json.dumps(payload))
            process.stdin.close()
            assert entered.wait(18), "Local SDK request must be active before terminating its owner"
            child_pid = int((tmp_path / "child.pid").read_text())
            # Track the actual child lifetime, not a reusable PID, on Windows.
            if os.name == "nt":
                import ctypes
                from ctypes import wintypes
                kernel = ctypes.WinDLL("kernel32", use_last_error=True)
                kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
                kernel.OpenProcess.restype = wintypes.HANDLE
                kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
                handle = kernel.OpenProcess(0x00100000, False, child_pid)
                assert handle
            with app.state.repository.engine.connect() as db:
                claimed = dict(db.execute(select(jobs).where(jobs.c.id == row["job_id"])).mappings().one())
            process.kill()
            process.wait(timeout=2)
            if os.name == "nt":
                try:
                    assert kernel.WaitForSingleObject(handle, 3000) == 0, "Orphaned SDK child must exit with its worker"
                finally:
                    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
                    kernel.CloseHandle(handle)
            else:
                limit = time.monotonic() + 3
                while time.monotonic() < limit:
                    try:
                        os.kill(child_pid, 0)
                        stat = Path(f"/proc/{child_pid}/stat")
                        if stat.exists() and stat.read_text().split()[2] == "Z": break
                    except ProcessLookupError: break
                    time.sleep(0.05)
                else: pytest.fail("Orphaned SDK child is still running")
            with app.state.repository.engine.begin() as db:
                db.execute(update(jobs).where(jobs.c.id == row["job_id"]).values(lease_expires_at=utcnow() - timedelta(seconds=1)))
            reopened = Repository(database_url)
            try:
                reopened.requeue_expired_jobs()
                assert reopened.claim_next_job("replacement-worker", job_id=row["job_id"]) is None
                assert service.repository.analysis(row["id"])["status"] == "failed"
                assert reopened.job_status(row["job_id"]) == "failed"
                with pytest.raises(RuntimeError, match="lease lost"):
                    service.repository.publish(claimed, "crash-test-worker", "completed", {}, result={"invalid": True}, status="completed")
                assert not reopened.renew_job_lease(row["job_id"], "crash-test-worker", claimed["execution_token"], 60)
                assert len(requests) == 1
            finally: reopened.close()
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=2)
        release.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
