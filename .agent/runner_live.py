#!/usr/bin/env python3
"""Safe live-status publisher for the Aither host supervisor.

Writes a local status file under Git metadata and, when possible, force-moves the
single lightweight tag ``runner-live`` to an orphan commit containing
``runner-status.json``. The status schema intentionally excludes prompts,
reasoning text, command text, stdout/stderr, secrets, and file contents.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LIVE_STATE_NAME = "runner-live.json"
REMOTE_REF = "refs/tags/runner-live"
SAFE_KEYS = frozenset({
    "schema_version", "task_id", "state", "phase", "pid", "started_at",
    "heartbeat_at", "last_event_at", "event_count", "last_event_type",
    "last_item_type", "silent_seconds", "stall_warning", "process_alive",
    "exit_code", "runner_result", "head_sha", "message_code",
})
MAX_STRING = 160


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def git(repo: Path, *argv: str, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *argv], cwd=repo, input=input_text, text=True,
        capture_output=True, check=check,
    )


def repo_root(start: Path) -> Path:
    cp = git(start, "rev-parse", "--show-toplevel")
    return Path(cp.stdout.strip()).resolve()


def git_path(repo: Path, name: str) -> Path:
    cp = git(repo, "rev-parse", "--git-path", name)
    path = Path(cp.stdout.strip())
    return (path if path.is_absolute() else repo / path).resolve()


def sanitize_status(status: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {"schema_version": 1}
    for key in SAFE_KEYS:
        if key == "schema_version" or key not in status:
            continue
        value = status[key]
        if value is None or isinstance(value, (bool, int, float)):
            safe[key] = value
        elif isinstance(value, str):
            safe[key] = value[:MAX_STRING]
    safe.setdefault("heartbeat_at", utc_now())
    return safe


def load_local(repo: Path) -> dict[str, Any]:
    path = git_path(repo, LIVE_STATE_NAME)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def write_local(repo: Path, status: dict[str, Any]) -> Path:
    path = git_path(repo, LIVE_STATE_NAME)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(sanitize_status(status), sort_keys=True, separators=(",", ":")) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
    return path


def _write_local_with_push_epoch(repo: Path, status: dict[str, Any], epoch: float) -> None:
    path = git_path(repo, LIVE_STATE_NAME)
    data = sanitize_status(status)
    data["_last_remote_push_epoch"] = epoch
    payload = json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def push_remote(repo: Path, status: dict[str, Any]) -> bool:
    """Publish sanitized status without touching index, worktree, or task branch."""
    safe = sanitize_status(status)
    payload = json.dumps(safe, sort_keys=True, separators=(",", ":")) + "\n"
    try:
        blob = git(repo, "hash-object", "-w", "--stdin", input_text=payload).stdout.strip()
        tree_spec = f"100644 blob {blob}\trunner-status.json\n"
        tree = git(repo, "mktree", input_text=tree_spec).stdout.strip()
        env = os.environ.copy()
        env.update({
            "GIT_AUTHOR_NAME": "Aither Runner",
            "GIT_AUTHOR_EMAIL": "runner@aither.local",
            "GIT_COMMITTER_NAME": "Aither Runner",
            "GIT_COMMITTER_EMAIL": "runner@aither.local",
        })
        commit = subprocess.run(
            ["git", "commit-tree", tree], cwd=repo,
            input="Aither runner live status\n", text=True,
            capture_output=True, check=True, env=env,
        ).stdout.strip()
        subprocess.run(
            ["git", "push", "--force", "origin", f"{commit}:{REMOTE_REF}"],
            cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=True,
        )
        _write_local_with_push_epoch(repo, safe, time.time())
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def publish_status(repo: Path, status: dict[str, Any], *, remote: bool = True,
                   min_remote_interval_seconds: int = 0) -> dict[str, Any]:
    repo = repo_root(repo)
    safe = sanitize_status(status)
    previous = load_local(repo)
    last_push = previous.get("_last_remote_push_epoch")
    write_local(repo, safe)
    if isinstance(last_push, (int, float)):
        _write_local_with_push_epoch(repo, safe, float(last_push))
    if remote:
        previous_after = load_local(repo)
        last_epoch = previous_after.get("_last_remote_push_epoch")
        due = min_remote_interval_seconds <= 0 or not isinstance(last_epoch, (int, float)) or time.time() - float(last_epoch) >= min_remote_interval_seconds
        if due:
            push_remote(repo, safe)
    return safe
