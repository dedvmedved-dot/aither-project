#!/usr/bin/env python3
"""Fail-closed host-side task launcher (S2-A simulation only)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence


TASK_PATH = Path(".agent/CURRENT_TASK.json")
ARCHITECT_PATHS = frozenset({".agent/CURRENT_TASK.json", ".agent/CURRENT_TASK.md"})
HANDOFF_PATHS = ARCHITECT_PATHS
FIXED_PROMPT = (
    "Read AGENTS.md, .agent/CURRENT_TASK.json and .agent/CURRENT_TASK.md. "
    "Execute the current task exactly as authorized. Do not expand scope. "
    "Return the required final report and STOP."
)
REQUIRED_FIELDS: dict[str, type] = {
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
REQUIRED_CAPABILITIES = {
    "commit", "push", "network_git", "kubernetes", "deployment",
    "database_write", "runtime_write", "secret_access", "package_install",
}


class RunnerError(RuntimeError):
    """A safety or task-contract check failed."""


CommandRunner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]


def execute_command(argv: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Execute an argv directly; shell interpolation is deliberately unavailable."""
    return subprocess.run(
        list(argv), cwd=cwd, check=True, capture_output=True, text=True
    )


def resolve_repo_root(start: Path, run: CommandRunner = execute_command) -> Path:
    result = run(["git", "rev-parse", "--show-toplevel"], start)
    return Path(result.stdout.strip()).resolve()


def validate_task(task: Any) -> dict[str, Any]:
    if not isinstance(task, dict):
        raise RunnerError("task JSON must contain an object")
    for name, expected in REQUIRED_FIELDS.items():
        if name not in task or type(task[name]) is not expected:
            raise RunnerError(f"missing or invalid field: {name}")
    if task["schema_version"] != 1:
        raise RunnerError("unsupported schema_version")
    if task["status"] != "ACTIVE":
        raise RunnerError("task status is not ACTIVE")
    if any(not isinstance(value, str) or not value for value in task["allowed_paths"]):
        raise RunnerError("allowed_paths must contain non-empty strings")
    if len(task["allowed_paths"]) != len(set(task["allowed_paths"])):
        raise RunnerError("allowed_paths contains duplicates")
    capabilities = task["capabilities"]
    for name in REQUIRED_CAPABILITIES:
        if name not in capabilities or type(capabilities[name]) is not bool:
            raise RunnerError(f"missing or invalid capability: {name}")
    return task


def load_task(path: Path) -> dict[str, Any]:
    try:
        return validate_task(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunnerError(f"cannot load task: {exc}") from exc


def require_branch(repo: Path, expected: str, run: CommandRunner = execute_command) -> str:
    actual = run(["git", "branch", "--show-current"], repo).stdout.strip()
    if actual != expected:
        raise RunnerError(f"branch mismatch: expected {expected}, got {actual}")
    return actual


def require_clean_worktree(repo: Path, run: CommandRunner = execute_command) -> None:
    if run(["git", "status", "--porcelain=v1", "-z"], repo).stdout:
        raise RunnerError("worktree is not clean")


def verify_baseline_ancestor(
    repo: Path, baseline: str, head: str, run: CommandRunner = execute_command
) -> None:
    try:
        run(["git", "rev-parse", "--verify", f"{baseline}^{{commit}}"], repo)
        run(["git", "merge-base", "--is-ancestor", baseline, head], repo)
    except subprocess.CalledProcessError as exc:
        raise RunnerError("baseline is missing or is not an ancestor of launch HEAD") from exc


def committed_handoff_paths(
    repo: Path, baseline: str, head: str, run: CommandRunner = execute_command
) -> list[str]:
    output = run(["git", "diff", "--name-only", "-z", f"{baseline}..{head}"], repo).stdout
    paths = sorted(filter(None, output.split("\0")))
    unexpected = sorted(set(paths) - HANDOFF_PATHS)
    if unexpected:
        raise RunnerError(f"unexpected committed handoff paths: {unexpected}")
    return paths


def build_codex_argv(prompt: str = FIXED_PROMPT) -> list[str]:
    return [
        "codex", "--ask-for-approval", "never", "--sandbox", "workspace-write",
        "exec", prompt,
    ]


def parse_porcelain_z(output: str) -> list[str]:
    """Return paths from `git status --porcelain=v1 -z`, including rename targets."""
    entries = output.split("\0")
    paths: list[str] = []
    index = 0
    while index < len(entries) and entries[index]:
        entry = entries[index]
        if len(entry) < 4:
            raise RunnerError("invalid Git porcelain output")
        status, path = entry[:2], entry[3:]
        paths.append(path)
        if "R" in status or "C" in status:
            index += 1
            if index >= len(entries) or not entries[index]:
                raise RunnerError("invalid rename/copy porcelain output")
            paths.append(entries[index])
        index += 1
    return sorted(set(paths))


def changed_worktree_paths(
    repo: Path, run: CommandRunner = execute_command
) -> list[str]:
    output = run(["git", "status", "--porcelain=v1", "-z"], repo).stdout
    return parse_porcelain_z(output)


def validate_changed_paths(changed: Iterable[str], task: dict[str, Any]) -> list[str]:
    paths = sorted(set(changed))
    unexpected = sorted(set(paths) - set(task["allowed_paths"]))
    if unexpected:
        raise RunnerError(f"changed paths outside task allowlist: {unexpected}")
    return paths


def implementation_paths(changed: Iterable[str], task: dict[str, Any]) -> list[str]:
    paths = validate_changed_paths(changed, task)
    return [path for path in paths if path not in ARCHITECT_PATHS]


def require_capability(task: dict[str, Any], action: str) -> None:
    capability = {"fetch": "network_git", "pull": "network_git"}.get(action, action)
    if capability not in task["capabilities"] or not task["capabilities"][capability]:
        raise RunnerError(f"capability prohibits action: {action}")


def make_summary(
    task_id: str, start_head: str, changed_paths: Iterable[str], result: str,
    message: str = "",
) -> dict[str, Any]:
    return {
        "changed_paths": sorted(set(changed_paths)),
        "message": message,
        "result": result,
        "start_head": start_head,
        "task_id": task_id,
    }


class InterProcessLock(AbstractContextManager["InterProcessLock"]):
    def __init__(self, path: Path):
        self.path = path
        self._fd: int | None = None

    def __enter__(self) -> "InterProcessLock":
        try:
            self._fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.write(self._fd, f"{os.getpid()}\n".encode("ascii"))
        except FileExistsError as exc:
            raise RunnerError(f"runner lock is already held: {self.path}") from exc
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
            self.path.unlink(missing_ok=True)


def simulate(repo: Path, lock_path: Path, run: CommandRunner = execute_command) -> dict[str, Any]:
    with InterProcessLock(lock_path):
        task = load_task(repo / TASK_PATH)
        require_branch(repo, task["branch"], run)
        require_clean_worktree(repo, run)
        head = run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        verify_baseline_ancestor(repo, task["baseline_sha"], head, run)
        committed_handoff_paths(repo, task["baseline_sha"], head, run)
        return make_summary(task["task_id"], head, [], "PASS")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--lock-path", type=Path)
    parser.add_argument("--dry-run", action="store_true", required=True)
    args = parser.parse_args(argv)
    try:
        repo = resolve_repo_root(args.repo)
        lock_path = args.lock_path or repo / ".agent" / "host_task_runner.lock"
        summary = simulate(repo, lock_path)
    except (RunnerError, subprocess.CalledProcessError) as exc:
        summary = make_summary("", "", [], "BLOCKED", str(exc))
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0 if summary["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
