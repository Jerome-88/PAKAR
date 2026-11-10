"""Hard process boundaries for external calls; SDK timeouts are not deadlines."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path


class BudgetExceeded(ValueError):
    pass


class RunCancelled(ValueError):
    pass


class ExternalCallError(RuntimeError):
    def __init__(self, message, *, worker_error_type=None, status_code=None, failure_kind=None, failure_terms=None, retry_after_seconds=None):
        super().__init__(message)
        self.worker_error_type = worker_error_type
        self.status_code = status_code
        self.failure_kind = failure_kind
        self.failure_terms = failure_terms
        self.retry_after_seconds = retry_after_seconds


class RunDeadline:
    def __init__(self, seconds, *, cancelled=None):
        self.started = time.monotonic()
        self.seconds = float(seconds)
        self.expires = self.started + self.seconds
        self.finalization_reserve = min(2.0, self.seconds / 10)
        self.cancelled = cancelled

    def remaining(self):
        if self.cancelled and self.cancelled():
            raise RunCancelled("Analysis cancelled or lease lost")
        remaining = self.expires - self.finalization_reserve - time.monotonic()
        if remaining <= 0:
            raise BudgetExceeded("Analysis work deadline reached")
        return remaining


def call_worker(operation, payload, timeout, *, cancelled=None):
    """Credentials travel over stdin, never command arguments or diagnostics.

    A synchronous SDK/read can stall despite its socket timeout. The isolated
    worker has no child processes; killing and reaping it terminates that wait.
    """
    if timeout <= 0:
        raise BudgetExceeded("External call has no remaining time")
    if cancelled and cancelled():
        raise RunCancelled("Analysis cancelled or lease lost")
    expires = time.monotonic() + timeout
    process = subprocess.Popen(
        [sys.executable, str(Path(__file__).with_name("call_worker.py"))],
        cwd=Path(__file__).resolve().parents[2],
        env=os.environ | {"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "PYTHON_DOTENV_DISABLED": "1", "PAKAR_PARENT_PID": str(os.getpid())},
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, encoding="utf-8",
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    encoded = json.dumps({"operation": operation, "payload": payload}, ensure_ascii=False)
    try:
        while True:
            if cancelled and cancelled():
                raise RunCancelled("Analysis cancelled or lease lost")
            remaining = expires - time.monotonic()
            if remaining <= 0:
                raise BudgetExceeded("External call deadline reached")
            try:
                output, _ = process.communicate(input=encoded, timeout=min(0.1, remaining))
                break
            except subprocess.TimeoutExpired:
                encoded = None
        if process.returncode or len(output) > 8_000_000:
            raise ExternalCallError("External worker did not return a bounded response")
        envelope = json.loads(output)
        if not envelope.get("ok"):
            # Only a worker-defined class/code is returned, never exception text
            # that might contain a BPS key URL or provider request context.
            raise ExternalCallError(f"External call failed ({envelope.get('error_type', 'unknown')})",
                worker_error_type=envelope.get("error_type"), status_code=envelope.get("status_code"), failure_kind=envelope.get("failure_kind"), failure_terms=envelope.get("failure_terms"), retry_after_seconds=envelope.get("retry_after_seconds"))
        return envelope["data"]
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=2)

