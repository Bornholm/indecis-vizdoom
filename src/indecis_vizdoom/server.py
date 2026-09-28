"""Starts indecis-serve for the duration of a run."""

from __future__ import annotations

import contextlib
import subprocess
import time
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class Served:
    url: str
    pid: int

    def memory(self) -> tuple[float, float]:
        """Resident and private (anonymous) memory of the server, in MB.
        The rest of the resident memory is the memory-mapped model file,
        shared with the page cache: the system can reclaim it."""
        fields = {}
        with open(f"/proc/{self.pid}/status") as f:
            for line in f:
                key, _, value = line.partition(":")
                if key in ("VmRSS", "RssAnon"):
                    fields[key] = int(value.split()[0]) / 1024
        return fields.get("VmRSS", 0.0), fields.get("RssAnon", 0.0)
from dataclasses import dataclass


@dataclass(frozen=True)
class Served:
    url: str
    pid: int

    def memory(self) -> tuple[float, float]:
        """Resident and private (anonymous) memory of the server, in MB.
        The rest of the resident memory is the model file, memory-mapped:
        shared with the page cache, the system can reclaim it."""
        fields = {}
        with open(f"/proc/{self.pid}/status") as f:
            for line in f:
                key, _, value = line.partition(":")
                if key in ("VmRSS", "RssAnon"):
                    fields[key] = int(value.split()[0]) / 1024
        return fields.get("VmRSS", 0.0), fields.get("RssAnon", 0.0)


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
        yield Served(url, proc.pid)
    finally:
        proc.terminate()
        proc.wait()
