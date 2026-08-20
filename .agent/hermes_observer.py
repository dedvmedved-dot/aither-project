#!/usr/bin/env python3
"""Aither -> Hermes H2 root socket-bridge client (governed executor observer).

Writes exactly ``RUN`` to the accepted H2 root bridge socket and reads only the
bridge's response. Never invokes the Hermes binary directly, never accepts a
prompt or command from the caller, never uses shell/eval/exec.
"""

from __future__ import annotations

import os
import socket
import sys
import time
import json
from pathlib import Path
from typing import Any, Callable

from runner_live import publish_status, repo_root, utc_now

DEFAULT_SOCKET = "/run/aither-hermes/execute.sock"
SOCKET_ENV = "AITHER_HERMES_SOCKET"              # test-only socket path override
TIMEOUT_ENV = "AITHER_HERMES_TIMEOUT"            # hard timeout, seconds
MAX_RESPONSE_ENV = "AITHER_HERMES_MAX_RESPONSE"  # bounded response, bytes
HEARTBEAT_ENV = "AITHER_HERMES_HEARTBEAT_SECONDS"

FIXED_SIGNAL = b"RUN\n"
DEFAULT_TIMEOUT = 3600.0
DEFAULT_MAX_RESPONSE = 65536
DEFAULT_HEARTBEAT = 30.0

Publisher = Callable[[dict[str, Any]], None]


def socket_path() -> str:
    return os.environ.get(SOCKET_ENV, DEFAULT_SOCKET)


def timeout_seconds() -> float:
    try:
        return float(os.environ.get(TIMEOUT_ENV, str(DEFAULT_TIMEOUT)))
    except ValueError:
        return DEFAULT_TIMEOUT


def max_response_bytes() -> int:
    try:
        return int(os.environ.get(MAX_RESPONSE_ENV, str(DEFAULT_MAX_RESPONSE)))
    except ValueError:
        return DEFAULT_MAX_RESPONSE


def heartbeat_seconds() -> float:
    try:
        value = float(os.environ.get(HEARTBEAT_ENV, str(DEFAULT_HEARTBEAT)))
        return value if value > 0 else DEFAULT_HEARTBEAT
    except ValueError:
        return DEFAULT_HEARTBEAT


def load_task_id(repo: Path) -> str:
    try:
        data = json.loads((repo / ".agent/CURRENT_TASK.json").read_text(encoding="utf-8"))
        value = data.get("task_id", "")
        return value if isinstance(value, str) else ""
    except (OSError, json.JSONDecodeError):
        return ""


def status_payload(*, task_id: str, state: str, phase: str, started_at: str,
                   last_event_at: str, start_monotonic: float,
                   last_event_monotonic: float, response_bytes: int = 0,
                   process_alive: bool = True) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "state": state,
        "phase": phase,
        "started_at": started_at,
        "heartbeat_at": utc_now(),
        "last_event_at": last_event_at,
        "silent_seconds": max(0, int(time.monotonic() - last_event_monotonic)),
        "process_alive": process_alive,
        "event_count": response_bytes,
    }


def make_publisher(repo: Path, task_id: str, started_at: str,
                   start_monotonic: float) -> Publisher:
    """Return a best-effort publisher; observability failure cannot alter H2."""
    last_event_at = started_at
    last_event_monotonic = start_monotonic

    def publish(event: dict[str, Any]) -> None:
        nonlocal last_event_at, last_event_monotonic
        if event.get("advance_event", True):
            last_event_at = utc_now()
            last_event_monotonic = time.monotonic()
        payload = status_payload(
            task_id=task_id, state=str(event["state"]), phase=str(event["phase"]),
            started_at=started_at, last_event_at=last_event_at,
            start_monotonic=start_monotonic,
            last_event_monotonic=last_event_monotonic,
            response_bytes=int(event.get("response_bytes", 0)),
            process_alive=bool(event.get("process_alive", True)),
        )
        try:
            publish_status(repo, payload, remote=True)
        except Exception:
            pass

    return publish


def send_run(path: str | None = None, timeout: float | None = None,
             max_response: int | None = None, *, publisher: Publisher | None = None,
             heartbeat: float | None = None) -> str:
    """Send the fixed RUN signal and return the stripped bridge response.

    Raises ``socket.timeout`` on a hard timeout and ``OSError`` on connect/send
    failures. The response is truncated to ``max_response`` bytes.
    """
    path = path if path is not None else socket_path()
    timeout = timeout if timeout is not None else timeout_seconds()
    max_response = max_response if max_response is not None else max_response_bytes()
    heartbeat = heartbeat if heartbeat is not None else heartbeat_seconds()
    deadline = time.monotonic() + timeout
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(max(0.001, deadline - time.monotonic()))
        sock.connect(path)
        if publisher:
            publisher({"state": "RUNNING", "phase": "H2_CONNECTED"})
        sock.sendall(FIXED_SIGNAL)
        sock.shutdown(socket.SHUT_WR)
        if publisher:
            publisher({"state": "RUNNING", "phase": "HERMES_RUNNING"})
        chunks: list[bytes] = []
        received = 0
        next_heartbeat = time.monotonic() + heartbeat
        while received < max_response:
            now = time.monotonic()
            remaining = deadline - now
            if remaining <= 0:
                raise socket.timeout("Hermes bridge hard timeout")
            sock.settimeout(max(0.001, min(remaining, next_heartbeat - now)))
            try:
                data = sock.recv(min(4096, max_response - received))
            except socket.timeout:
                if time.monotonic() >= deadline:
                    raise
                if publisher:
                    publisher({"state": "RUNNING", "phase": "HERMES_HEARTBEAT",
                               "response_bytes": received, "advance_event": False})
                next_heartbeat = time.monotonic() + heartbeat
                continue
            if not data:
                break
            chunks.append(data)
            received += len(data)
        response = b"".join(chunks).decode("utf-8", errors="replace")
    return response.strip()


def is_fail_closed(response: str) -> bool:
    upper = response.upper()
    return upper.startswith("BLOCKED_") or upper.startswith("FAIL")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv:
        # The bridge client accepts no prompt and no command from the caller.
        sys.stderr.write("BLOCKED_ARGS\n")
        return 2
    repo = repo_root(Path.cwd())
    started_at = utc_now()
    start_monotonic = time.monotonic()
    publisher = make_publisher(repo, load_task_id(repo), started_at, start_monotonic)
    publisher({"state": "RUNNING", "phase": "H2_DISPATCH"})
    try:
        response = send_run(publisher=publisher)
    except socket.timeout:
        publisher({"state": "BLOCKED", "phase": "H2_TIMEOUT", "process_alive": False})
        sys.stderr.write("BLOCKED_TIMEOUT\n")
        return 1
    except OSError:
        publisher({"state": "BLOCKED", "phase": "H2_CONNECT_FAILED", "process_alive": False})
        sys.stderr.write("BLOCKED_CONNECT\n")
        return 1
    if not response:
        publisher({"state": "BLOCKED", "phase": "H2_EMPTY", "process_alive": False})
        sys.stderr.write("BLOCKED_EMPTY\n")
        return 1
    if is_fail_closed(response):
        publisher({"state": "BLOCKED", "phase": "H2_FAIL_RESPONSE", "process_alive": False})
        sys.stdout.write(response + "\n")
        return 1
    publisher({"state": "COMPLETED", "phase": "H2_COMPLETED", "process_alive": False})
    sys.stdout.write(response + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
