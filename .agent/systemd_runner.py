#!/usr/bin/env python3
"""Systemd entrypoint that makes every supervisor poll externally observable."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from runner_live import publish_status, repo_root, utc_now


def build_final_status(summary: dict, returncode: int) -> dict:
    """Build the final sanitized live status from a host-runner summary.

    Uses the summary's task_id/executor rather than any stale pre-fetch value.
    Does not expose raw stdout/stderr.
    """
    result = summary.get("result") if isinstance(summary.get("result"), str) else "BLOCKED"
    message = summary.get("message") if isinstance(summary.get("message"), str) else ""
    message_code = ""
    if result == "IDLE":
        state, phase = "IDLE", "HOST_RUNNER_IDLE"
    elif returncode == 0 and result == "PASS":
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
        elif "executor" in message:
            message_code = "EXECUTOR_FAILURE"
        else:
            message_code = "RUNNER_ERROR"
    status = {
        "state": state,
        "phase": phase,
        "process_alive": False,
        "runner_result": result,
        "exit_code": returncode,
        "message_code": message_code,
    }
    task_id_value = summary.get("task_id")
    if isinstance(task_id_value, str) and task_id_value:
        status["task_id"] = task_id_value
    executor_value = summary.get("executor")
    if isinstance(executor_value, str) and executor_value:
        status["executor"] = executor_value
    return status


def main() -> int:
    repo = repo_root(Path.cwd())
    # Initial pre-sync poll: task identity is intentionally omitted until the
    # host-runner summary provides the synchronized task_id/executor.
    publish_status(repo, {
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
    status = build_final_status(summary, cp.returncode)
    status["task_id"] = status.get("task_id", "")
    status["heartbeat_at"] = utc_now()
    status["pid"] = 0
    publish_status(repo, status, remote=True,
                   min_remote_interval_seconds=0 if status.get("state") != "IDLE" else 300)
    if cp.stdout:
        sys.stdout.write(cp.stdout)
    if cp.stderr:
        sys.stderr.write(cp.stderr)
    return cp.returncode


if __name__ == "__main__":
    raise SystemExit(main())
