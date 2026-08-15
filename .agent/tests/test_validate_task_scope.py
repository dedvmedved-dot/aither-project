#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

AGENT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, AGENT / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load('validate_task_scope', 'validate_task_scope.py')


def base_task(**updates):
    value = {
        'schema_version': 1, 'task_id': 'T', 'mode': 'M', 'status': 'ACTIVE',
        'branch': 'aither-v2', 'baseline_sha': 'a' * 40,
        'allowed_paths': ['impl.py'],
        'capabilities': {}, 'max_commits': 1,
        'require_clean_start': True, 'require_clean_finish': True,
        'architect_acceptance_required': True,
    }
    value.update(updates)
    return value


class Tests(unittest.TestCase):
    def test_architect_handoff_plus_committed_impl_pass(self):
        ua = validator.classify_unauthorized(
            committed={'.agent/CURRENT_TASK.json', '.agent/CURRENT_TASK.md', 'impl.py'},
            worktree=set(), untracked=set(), allowed={'impl.py'})
        self.assertEqual(ua, [])

    def test_committed_allowed_impl_alone_pass(self):
        ua = validator.classify_unauthorized(
            committed={'impl.py'}, worktree=set(), untracked=set(), allowed={'impl.py'})
        self.assertEqual(ua, [])

    def test_unexpected_committed_fails(self):
        ua = validator.classify_unauthorized(
            committed={'app.py'}, worktree=set(), untracked=set(), allowed={'impl.py'})
        self.assertIn('app.py', ua)

    def test_architect_handoff_committed_pass(self):
        ua = validator.classify_unauthorized(
            committed={'.agent/CURRENT_TASK.json', '.agent/CURRENT_TASK.md'},
            worktree=set(), untracked=set(), allowed={'impl.py'})
        self.assertEqual(ua, [])

    def test_architect_path_in_worktree_fails(self):
        ua = validator.classify_unauthorized(
            committed=set(), worktree={'.agent/CURRENT_TASK.md'},
            untracked=set(), allowed={'impl.py'})
        self.assertIn('.agent/CURRENT_TASK.md', ua)

    def test_architect_path_in_untracked_fails(self):
        ua = validator.classify_unauthorized(
            committed=set(), worktree=set(),
            untracked={'.agent/CURRENT_TASK.json'}, allowed={'impl.py'})
        self.assertIn('.agent/CURRENT_TASK.json', ua)

    def test_unexpected_untracked_fails(self):
        ua = validator.classify_unauthorized(
            committed=set(), worktree=set(), untracked={'bad.txt'}, allowed={'impl.py'})
        self.assertIn('bad.txt', ua)

    def test_allowed_worktree_impl_pass(self):
        ua = validator.classify_unauthorized(
            committed=set(), worktree={'impl.py'}, untracked=set(), allowed={'impl.py'})
        self.assertEqual(ua, [])

    def test_duplicate_allowlist_fails(self):
        with self.assertRaises(SystemExit):
            validator.validate_task(base_task(allowed_paths=['impl.py', 'impl.py']))

    def test_malformed_allowlist_fails(self):
        with self.assertRaises(SystemExit):
            validator.validate_task(base_task(allowed_paths=['']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
