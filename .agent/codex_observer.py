#!/usr/bin/env python3
"""Observed Codex CLI launcher for headless Aither execution."""
from __future__ import annotations

import json
import os
import selectors
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Sequence

from runner_live import publish_status, repo_root, utc_now

HEARTBEAT_SECONDS = int(os.environ.get("AITHER_HEARTBEAT_SECONDS", "30"))
STALL_WARNING_SECONDS = int(os.environ.get("AITHER_STALL_WARNING_SECONDS", "600"))
HARD_TIMEOUT_SECONDS = int(os.environ.get("AITHER_HARD_TIMEOUT_SECONDS", "3600"))


def build_real_argv(wrapper_argv: Sequence[str]) -> list[str]:
    real = os.environ.get("AITHER_REAL_CODEX_BIN", "").strip()
    if not real:
        raise RuntimeError("AITHER_REAL_CODEX_BIN is not set")
    args = list(wrapper_argv)
    try:
        exec_index = args.index("exec")
    except ValueError as exc:
        raise RuntimeError("observed Codex launcher only supports exec") from exc
    if "--json" not in args[exec_index + 1:]:
        args.insert(exec_index + 1, "--json")
    return [real, *args]


def load_task_id(repo: Path) -> str:
    try:
        data = json.loads((repo / ".agent/CURRENT_TASK.json").read_text(encoding="utf-8"))
        value = data.get("task_id", "")
        return value if isinstance(value, str) else ""
    except (OSError, json.JSONDecodeError):
        return ""


def event_metadata(line: str) -> tuple[str, str]:
    """Return event/item type only. Never surface model text or command content."""
    try:
        event: Any = json.loads(line)
    except json.JSONDecodeError:
        return "invalid-jsonl", ""
    if not isinstance(event, dict):
        return "invalid-event", ""
    event_type = event.get("type", "unknown")
    if not isinstance(event_type, str):
        event_type = "unknown"
    item_type = ""
    item = event.get("item")
    if isinstance(item, dict) and isinstance(item.get("type"), str):
        item_type = item["type"]
    return event_type[:80], item_type[:80]


def status_payload(*, task_id: str, state: str, phase: str, pid: int,
                   started_at: str, last_event_at: str, event_count: int,
                   last_event_type: str, last_item_type: str,
                   start_monotonic: float, last_event_monotonic: float,
                   exit_code: int | None = None) -> dict[str, Any]:
    now_mono = time.monotonic()
    silent = max(0, int(now_mono - last_event_monotonic))
    payload: dict[str, Any] = {
        "task_id": task_id,
        "state": state,
        "phase": phase,
        "pid": pid,
        "started_at": started_at,
        "heartbeat_at": utc_now(),
        "last_event_at": last_event_at,
        "event_count": event_count,
        "last_event_type": last_event_type,
        "last_item_type": last_item_type,
        "silent_seconds": silent,
        "stall_warning": silent >= STALL_WARNING_SECONDS,
        "process_alive": exit_code is None,
    }
    if exit_code is not None:
        payload["exit_code"] = exit_code
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    wrapper_argv = list(sys.argv[1:] if argv is None else argv)
    repo = repo_root(Path.cwd())
    task_id = load_task_id(repo)
    real_argv = build_real_argv(wrapper_argv)
    started_at = utc_now()
    start_mono = time.monotonic()
    last_event_mono = start_mono
    last_event_at = started_at
    event_count = 0
    last_event_type = "process.start"
    last_item_type = ""
    next_heartbeat = start_mono

    stderr_path = repo / ".git" / "codex-observer.stderr.log"
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    with stderr_path.open("w", encoding="utf-8") as stderr_file:
        process = subprocess.Popen(
            real_argv,
            cwd=repo,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=stderr_file,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        assert process.stdout is not None
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        publish_status(repo, status_payload(
            task_id=task_id, state="RUNNING", phase="CODEX_EXEC", pid=process.pid,
            started_at=started_at, last_event_at=last_event_at,
            event_count=event_count, last_event_type=last_event_type,
            last_item_type=last_item_type, start_monotonic=start_mono,
            last_event_monotonic=last_event_mono,
        ), remote=True)
        next_heartbeat = time.monotonic() + HEARTBEAT_SECONDS

        while True:
            now = time.monotonic()
            if now - start_mono >= HARD_TIMEOUT_SECONDS:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=10)
                except Exception:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except Exception:
                        pass
                publish_status(repo, status_payload(
                    task_id=task_id, state="BLOCKED", phase="HARD_TIMEOUT", pid=process.pid,
                    started_at=started_at, last_event_at=last_event_at,
                    event_count=event_count, last_event_type=last_event_type,
                    last_item_type=last_item_type, start_monotonic=start_mono,
                    last_event_monotonic=last_event_mono, exit_code=124,
                ), remote=True)
                return 124

            events = selector.select(timeout=1.0)
            for key, _ in events:
                line = key.fileobj.readline()
                if not line:
                    try:
                        selector.unregister(key.fileobj)
                    except Exception:
                        pass
                    continue
                event_count += 1
                last_event_mono = time.monotonic()
                last_event_at = utc_now()
                last_event_type, last_item_type = event_metadata(line)
                publish_status(repo, status_payload(
                    task_id=task_id, state="RUNNING", phase="CODEX_EXEC", pid=process.pid,
                    started_at=started_at, last_event_at=last_event_at,
                    event_count=event_count, last_event_type=last_event_type,
                    last_item_type=last_item_type, start_monotonic=start_mono,
                    last_event_monotonic=last_event_mono,
                ), remote=True, min_remote_interval_seconds=5)

            now = time.monotonic()
            if now >= next_heartbeat:
                publish_status(repo, status_payload(
                    task_id=task_id, state="RUNNING", phase="CODEX_EXEC", pid=process.pid,
                    started_at=started_at, last_event_at=last_event_at,
                    event_count=event_count, last_event_type=last_event_type,
                    last_item_type=last_item_type, start_monotonic=start_mono,
                    last_event_monotonic=last_event_mono,
                ), remote=True)
                next_heartbeat = now + HEARTBEAT_SECONDS

            rc = process.poll()
            if rc is not None and not selector.get_map():
                state = "CODEX_COMPLETED" if rc == 0 else "CODEX_FAILED"
                publish_status(repo, status_payload(
                    task_id=task_id, state=state, phase="CODEX_EXIT", pid=process.pid,
                    started_at=started_at, last_event_at=last_event_at,
                    event_count=event_count, last_event_type=last_event_type,
                    last_item_type=last_item_type, start_monotonic=start_mono,
                    last_event_monotonic=last_event_mono, exit_code=rc,
                ), remote=True)
                return rc


if __name__ == "__main__":
    raise SystemExit(main())
