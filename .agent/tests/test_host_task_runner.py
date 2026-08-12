#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import inspect
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "host_task_runner.py"
SPEC = importlib.util.spec_from_file_location("host_task_runner", MODULE_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def task(**updates):
    value = {
        "schema_version": 1,
        "task_id": "TEST-1",
        "mode": "TEST",
        "status": "ACTIVE",
        "branch": "main",
        "baseline_sha": "a" * 40,
        "allowed_paths": [
            ".agent/CURRENT_TASK.json", ".agent/CURRENT_TASK.md", "impl.py"
        ],
        "capabilities": {
            "commit": False, "push": False, "network_git": False,
            "kubernetes": False, "deployment": False, "database_write": False,
            "runtime_write": False, "secret_access": False,
            "package_install": False,
        },
        "max_commits": 0,
        "require_clean_start": True,
        "require_clean_finish": False,
        "architect_acceptance_required": True,
    }
    value.update(updates)
    return value


class FakeRun:
    def __init__(self, outputs=None, failures=None):
        self.outputs = outputs or {}
        self.failures = failures or set()
        self.calls = []

    def __call__(self, argv, cwd):
        key = tuple(argv)
        self.calls.append((list(argv), cwd))
        if key in self.failures:
            raise subprocess.CalledProcessError(1, argv)
        return subprocess.CompletedProcess(argv, 0, self.outputs.get(key, ""), "")


class HostTaskRunnerTests(unittest.TestCase):
    def test_valid_active_task_loads(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "task.json"
            path.write_text(json.dumps(task()), encoding="utf-8")
            self.assertEqual(runner.load_task(path)["task_id"], "TEST-1")

    def test_non_active_task_fails_closed(self):
        with self.assertRaises(runner.RunnerError):
            runner.validate_task(task(status="COMPLETE"))

    def test_baseline_ancestor_accepted_without_head_equality(self):
        fake = FakeRun()
        runner.verify_baseline_ancestor(Path("/repo"), "base", "new-head", fake)
        self.assertIn((["git", "merge-base", "--is-ancestor", "base", "new-head"], Path("/repo")), fake.calls)

    def test_unexpected_committed_handoff_path_rejected(self):
        key = ("git", "diff", "--name-only", "-z", "base..head")
        with self.assertRaises(runner.RunnerError):
            runner.committed_handoff_paths(Path("/repo"), "base", "head", FakeRun({key: "app.py\0"}))

    def test_exact_codex_argv(self):
        self.assertEqual(runner.build_codex_argv(), [
            "codex", "--ask-for-approval", "never", "--sandbox", "workspace-write",
            "exec", runner.FIXED_PROMPT,
        ])
        self.assertLess(runner.build_codex_argv().index("never"), runner.build_codex_argv().index("exec"))

    def test_command_abstraction_has_no_shell_true(self):
        source = inspect.getsource(runner.execute_command)
        self.assertNotIn("shell=True", source)

    def test_changed_path_inside_allowlist_accepted(self):
        self.assertEqual(runner.validate_changed_paths(["impl.py"], task()), ["impl.py"])

    def test_changed_path_outside_allowlist_rejected(self):
        with self.assertRaises(runner.RunnerError):
            runner.validate_changed_paths(["other.py"], task())

    def test_architect_paths_excluded_from_staging_candidates(self):
        changed = [".agent/CURRENT_TASK.json", ".agent/CURRENT_TASK.md", "impl.py"]
        self.assertEqual(runner.implementation_paths(changed, task()), ["impl.py"])

    def test_disabled_actions_fail_closed(self):
        for action in ("commit", "push", "fetch", "pull"):
            with self.subTest(action=action), self.assertRaises(runner.RunnerError):
                runner.require_capability(task(), action)

    def test_lock_contention_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runner.lock"
            with runner.InterProcessLock(path):
                with self.assertRaises(runner.RunnerError):
                    with runner.InterProcessLock(path):
                        pass
            self.assertFalse(path.exists())

    def test_deterministic_summary(self):
        expected = {
            "changed_paths": ["a", "z"], "message": "", "result": "PASS",
            "start_head": "head", "task_id": "TEST-1",
        }
        self.assertEqual(runner.make_summary("TEST-1", "head", ["z", "a", "z"], "PASS"), expected)
        self.assertEqual(json.dumps(expected, sort_keys=True), json.dumps(expected, sort_keys=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
