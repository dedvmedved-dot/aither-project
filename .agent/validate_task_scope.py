#!/usr/bin/env python3
"""Validate repository changes against .agent/CURRENT_TASK.json."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "schema_version": int,
    "task_id": str,
    "mode": str,
    "status": str,
    "branch": str,
    "baseline_sha": str,
    "allowed_paths": list,
    "capabilities": dict,
    "max_commits": int,
    "require_clean_start": bool,
    "require_clean_finish": bool,
    "architect_acceptance_required": bool,
}

ARCHITECT_PATHS = frozenset({".agent/CURRENT_TASK.json", ".agent/CURRENT_TASK.md"})


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def fail(message: str) -> None:
    print(f"ERROR={message}")
    print("RESULT=FAIL")
    raise SystemExit(1)


def validate_task(task: Any) -> dict[str, Any]:
    if not isinstance(task, dict):
        fail("CURRENT_TASK.json must contain an object")
    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in task:
            fail(f"missing required field: {field}")
        if not isinstance(task[field], expected_type):
            fail(f"invalid type for field: {field}")
    if not task["task_id"] or not task["branch"] or not task["baseline_sha"]:
        fail("task_id, branch, and baseline_sha must be non-empty")
    if task["schema_version"] != 1:
        fail("unsupported schema_version")
    if task["max_commits"] < 0:
        fail("max_commits must be non-negative")
    allowed = task["allowed_paths"]
    if not all(isinstance(path, str) and path for path in allowed):
        fail("allowed_paths must contain non-empty strings")
    if len(allowed) != len(set(allowed)):
        fail("allowed_paths contains duplicates")
    return task


def classify_unauthorized(committed, worktree, untracked, allowed) -> list[str]:
    """Return sorted unauthorized paths.

    committed  = paths in the committed baseline..HEAD range (Architect handoff
                 plus any committed result implementation paths).
    worktree   = uncommitted modified paths (staged + unstaged).
    untracked  = untracked paths.
    allowed    = task allowed_paths (executor implementation allowlist).

    A committed path is authorized when it is an Architect task-control path
    OR a current allowed_paths implementation path. Worktree/untracked paths
    are authorized only when in allowed_paths.
    """
    allowed = set(allowed)
    unauthorized = (
        {path for path in committed if path not in ARCHITECT_PATHS and path not in allowed}
        | {path for path in worktree if path not in allowed}
        | {path for path in untracked if path not in allowed}
    )
    return sorted(unauthorized)


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    task_path = repo / ".agent" / "CURRENT_TASK.json"
    try:
        task = validate_task(json.loads(task_path.read_text(encoding="utf-8")))
        git_root = Path(run_git(repo, "rev-parse", "--show-toplevel")).resolve()
        if git_root != repo:
            fail("validator is not located at repository root/.agent")

        if os.environ.get("GITHUB_ACTIONS") == "true":
            if os.environ.get("GITHUB_EVENT_NAME") == "pull_request":
                branch = os.environ.get("GITHUB_BASE_REF", "")
                if not branch:
                    fail("GITHUB_BASE_REF must be non-empty for pull_request")
            else:
                branch = os.environ.get("GITHUB_REF_NAME", "")
                if not branch:
                    fail("GITHUB_REF_NAME must be non-empty in GitHub Actions")
        else:
            branch = run_git(repo, "branch", "--show-current")
        if branch != task["branch"]:
            fail(f"branch mismatch: expected {task['branch']}, got {branch}")

        baseline = run_git(repo, "rev-parse", "--verify", f"{task['baseline_sha']}^{{commit}}")
        head = run_git(repo, "rev-parse", "HEAD")

        committed_output = run_git(repo, "diff", "--name-only", f"{baseline}..{head}")
        worktree_output = run_git(repo, "diff", "--name-only", "HEAD")
        untracked_output = run_git(repo, "ls-files", "--others", "--exclude-standard")
        committed = {path for path in committed_output.splitlines() if path}
        worktree = {path for path in worktree_output.splitlines() if path}
        untracked = {path for path in untracked_output.splitlines() if path}
        changed = sorted(committed | worktree | untracked)
        unauthorized = classify_unauthorized(committed, worktree, untracked, task["allowed_paths"])
    except (OSError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        fail(str(exc).replace("\n", " "))

    print(f"TASK_ID={task['task_id']}")
    print(f"BRANCH={branch}")
    print(f"BASELINE={baseline}")
    print(f"HEAD={head}")
    print(f"CHANGED_PATHS={len(changed)}")
    print(f"UNAUTHORIZED_PATHS={len(unauthorized)}")
    for path in unauthorized:
        print(f"UNAUTHORIZED={path}")
    print(f"RESULT={'FAIL' if unauthorized else 'PASS'}")
    return 1 if unauthorized else 0


if __name__ == "__main__":
    sys.exit(main())
