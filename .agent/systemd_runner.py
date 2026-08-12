#!/usr/bin/env python3
"""Systemd entrypoint that makes every supervisor poll externally observable."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from runner_live import publish_status, repo_root, utc_now


def task_id(repo: Path) -> str:
    try:
        data = json.loads((repo / ".agent/CURRENT_TASK.json").read_text(encoding="utf-8"))
        value = data.get("task_id", "")
        return value if isinstance(value, str) else ""
    except (OSError, json.JSONDecodeError):
        return ""


def main() -> int:
    repo = repo_root(Path.cwd())
    current_task = task_id(repo)
    publish_status(repo, {
        "task_id": current_task,
        "state": "SUPERVISOR_POLL",
        "phase": "HOST_RUNNER_START",
        "pid": 0,
        "heartbeat_at": utc_now(),
        "process_alive": True,
    }, remote=True, min_remote_interval_seconds=60)

    cp = subprocess.run(
        [sys.executable, str(repo / ".agent/host_task_runner.py"), "--run-once"],
        cwd=repo, text=True, capture_output=True,
    )
    summary = {}
    try:
        lines = [line for line in cp.stdout.splitlines() if line.strip()]
        if lines:
            parsed = json.loads(lines[-1])
            if isinstance(parsed, dict):
                summary = parsed
    except json.JSONDecodeError:
        summary = {}
    result = summary.get("result") if isinstance(summary.get("result"), str) else "BLOCKED"
    message = summary.get("message") if isinstance(summary.get("message"), str) else ""
    message_code = ""
    if result == "IDLE":
        state, phase = "IDLE", "HOST_RUNNER_IDLE"
    elif cp.returncode == 0 and result == "PASS":
        state, phase = "PASS", "HOST_RUNNER_COMPLETE"
    else:
        state, phase = "BLOCKED", "HOST_RUNNER_FAILED"
        if "worktree is not clean" in message:
            message_code = "DIRTY_WORKTREE"
        elif "baseline" in message:
            message_code = "BASELINE_CHECK"
        elif "remote moved" in message:
            message_code = "REMOTE_RACE"
        elif "agent capability" in message:
            message_code = "CAPABILITY_BLOCK"
        else:
            message_code = "RUNNER_ERROR"
    publish_status(repo, {
        "task_id": current_task,
        "state": state,
        "phase": phase,
        "pid": 0,
        "heartbeat_at": utc_now(),
        "process_alive": False,
        "runner_result": result,
        "exit_code": cp.returncode,
        "message_code": message_code,
    }, remote=True, min_remote_interval_seconds=0 if state != "IDLE" else 300)
    if cp.stdout:
        sys.stdout.write(cp.stdout)
    if cp.stderr:
        sys.stderr.write(cp.stderr)
    return cp.returncode


if __name__ == "__main__":
    raise SystemExit(main())
