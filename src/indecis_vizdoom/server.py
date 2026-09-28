"""Starts indecis-serve for the duration of a run."""

from __future__ import annotations

import contextlib
import subprocess
import time
import urllib.request


@contextlib.contextmanager
def indecis_serve(binary: str, models: dict[str, str], addr: str = "127.0.0.1:8090"):
    args = [binary, "-addr", addr]
    for name, path in models.items():
        args += ["-model", f"{name}={path}"]
    proc = subprocess.Popen(args, stderr=subprocess.DEVNULL)
    url = f"http://{addr}"
    try:
        deadline = time.monotonic() + 60
        while True:
            try:
                urllib.request.urlopen(url + "/healthz", timeout=1).read()
                break
            except OSError:
                if proc.poll() is not None:
                    raise RuntimeError(f"indecis-serve exited with status {proc.returncode}")
                if time.monotonic() > deadline:
                    raise RuntimeError("indecis-serve did not start within 60 s")
                time.sleep(0.2)
        yield url
    finally:
        proc.terminate()
        proc.wait()
