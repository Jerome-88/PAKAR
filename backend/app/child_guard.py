"""Exit external-call children when their owning worker process disappears.

This module is stdlib-only and starts before SDK/runtime imports. A Windows
process handle tracks the original process even if its PID is later reused.
"""
from __future__ import annotations

import os
import threading


def watch_parent():
    raw = os.environ.get("PAKAR_PARENT_PID")
    if not raw:
        return
    parent = int(raw)
    if parent <= 0:
        raise ValueError("Invalid worker parent PID")
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x00100000, False, parent)
        if not handle:
            os._exit(75)
        def alive():
            return kernel.WaitForSingleObject(handle, 0) == 258
    else:
        def alive():
            return os.getppid() == parent

    def monitor():
        pause = threading.Event()
        try:
            while alive():
                pause.wait(0.2)
            # The SDK/runtime may be synchronously blocked. Exiting the whole
            # child also stops its background threads and open HTTP connection.
            os._exit(75)
        finally:
            if os.name == "nt":
                kernel.CloseHandle(handle)
    threading.Thread(target=monitor, name="pakar-parent-guard", daemon=True).start()
