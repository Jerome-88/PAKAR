import json
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread
from types import SimpleNamespace

import pytest

from app.business.agents import BusinessLLM
from app.business.budget import BudgetExceeded, RunCancelled, RunDeadline, call_worker
from app.business.usage import summarize_calls
from app.oasis_direct import DirectOasisEngine


def test_one_work_deadline_reserves_finalization_and_observes_cancellation(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr("app.business.budget.time.monotonic", lambda: clock[0])
    cancelled = Event()
    budget = RunDeadline(10, cancelled=cancelled.is_set)
    assert budget.remaining() == 9
    clock[0] += 4
    assert budget.remaining() == 5  # A new phase does not get a new 10 seconds.
    cancelled.set()
    with pytest.raises(RunCancelled):
        budget.remaining()
    cancelled.clear()
    clock[0] = 109.0
    with pytest.raises(BudgetExceeded):
        budget.remaining()


@pytest.mark.parametrize("cancel", [False, True])
def test_sdk_worker_is_killed_and_reaped_when_sync_provider_stalls(monkeypatch, cancel):
    entered, release, cancelled = Event(), Event(), Event()
    processes = []
    original = subprocess.Popen
    def capture(*args, **kwargs):
        process = original(*args, **kwargs)
        processes.append(process)
        return process
    monkeypatch.setattr("app.business.budget.subprocess.Popen", capture)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            entered.set()
            if cancel:
                cancelled.set()
            release.wait(30)
            try:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"{}")
            except OSError:
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    payload = {"api_key": "never-print-this-test-secret", "model": "local-model", "base_url": f"http://127.0.0.1:{server.server_port}/v1", "timeout": 60,
               "request": {"model": "local-model", "messages": [{"role": "user", "content": "local only"}], "max_tokens": 10, "timeout": 60}}
    started = time.monotonic()
    try:
        with pytest.raises(RunCancelled if cancel else BudgetExceeded) as error:
            call_worker("llm_completion", payload, 10, cancelled=cancelled.is_set)
        assert time.monotonic() - started < 13
        assert entered.is_set(), "Exercise a blocked SDK call, not just interpreter startup"
        assert len(processes) == 1 and processes[0].poll() is not None
        assert payload["api_key"] not in str(error.value)
        assert payload["api_key"] not in str(processes[0].args)
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize("cancel", [False, True])
def test_business_stream_deadline_cleans_stalled_runtime_without_extra_thirty_seconds(tmp_path, monkeypatch, cancel):
    bridge = tmp_path / "blocked_bridge.py"
    bridge.write_text('import json,sys,time\njson.load(sys.stdin)\nprint(json.dumps({"kind":"tick"}),flush=True)\ntime.sleep(30)\n', encoding="utf-8")
    engine = DirectOasisEngine(tmp_path, tmp_path / "data")
    engine.runtime_python, engine.bridge = sys.executable, bridge
    cancelled = Event()
    processes = []
    original = subprocess.Popen
    def capture(*args, **kwargs):
        process = original(*args, **kwargs)
        processes.append(process)
        return process
    monkeypatch.setattr("app.oasis_direct.subprocess.Popen", capture)
    def receive(message):
        if cancel:
            cancelled.set()
    started = time.monotonic()
    with pytest.raises(RunCancelled if cancel else BudgetExceeded):
        engine.run_business_simulation("test", {"config": {"max_seconds": 0.7}}, receive, cancelled=cancelled.is_set)
    assert time.monotonic() - started < 3.5
    assert len(processes) == 1 and processes[0].poll() is not None


def test_failed_or_expired_specialist_does_not_release_reservation_or_dispatch_again(monkeypatch):
    calls = []
    def timeout(*args, **kwargs):
        calls.append(args)
        raise BudgetExceeded("local timeout")
    monkeypatch.setattr("app.business.agents.call_worker", timeout)
    settings = SimpleNamespace(llm_api_key="test", llm_model="local", llm_base_url="http://127.0.0.1:1/v1", llm_structured_outputs=False, provider_timeout_seconds=10)
    llm = BusinessLLM(settings, max_tokens=4000)
    with pytest.raises(BudgetExceeded):
        llm.generate("Finance Agent", "review", {})
    reserved = llm.tokens
    assert reserved > 0 and llm.calls[0]["status"] == "failed"
    llm.deadline = time.monotonic() - 1
    with pytest.raises(BudgetExceeded):
        llm.generate("Risk Agent", "review", {})
    assert llm.tokens == reserved and len(calls) == 1
    assert llm.calls[0]["cost"] is None


def test_unknown_cost_and_missing_tokens_are_not_reported_as_zero():
    report = summarize_calls([{"cost": 0.001, "tokens": 30}, {"cost": None, "tokens": None}])
    assert report["cost"] is None and report["actual_tokens"] is None
    assert report["reported_cost_subtotal"] == 0.001 and report["cost_status"] == "partial"
    assert summarize_calls([])["cost"] is None
    assert summarize_calls([{"cost": float("nan")}])["cost"] is None


def test_stream_deadline_also_covers_child_that_never_reads_large_stdin(tmp_path):
    bridge = tmp_path / "blocked_before_input.py"
    bridge.write_text('import time\ntime.sleep(30)\n', encoding="utf-8")
    engine = DirectOasisEngine(tmp_path, tmp_path / "data")
    engine.runtime_python, engine.bridge = sys.executable, bridge
    started = time.monotonic()
    with pytest.raises(BudgetExceeded):
        engine.run_business_simulation("large-input", {"config": {"max_seconds": 0.5}, "context": "x" * 300000}, lambda _: None)
    assert time.monotonic() - started < 3.5

