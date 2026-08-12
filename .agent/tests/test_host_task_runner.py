#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import inspect
import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / 'host_task_runner.py'
SPEC = importlib.util.spec_from_file_location('host_task_runner', MODULE_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def base_task(**updates):
    value = {
        'schema_version': 1,
        'task_id': 'TEST-1',
        'mode': 'TEST',
        'status': 'ACTIVE',
        'branch': 'aither-v2',
        'baseline_sha': 'a' * 40,
        'allowed_paths': ['impl.txt'],
        'capabilities': {
            'source_write': True,
            'agent_exec': True,
            'network_git': False,
            'kubernetes': False,
            'deployment': False,
            'database_write': False,
            'runtime_write': False,
            'secret_access': False,
            'package_install': False,
        },
        'host_capabilities': {'sync': True, 'commit': True, 'push': True},
        'max_commits': 1,
        'require_clean_start': True,
        'require_clean_finish': True,
        'architect_acceptance_required': True,
        'validation_commands': [],
        'commit_message': 'test: governed agent result',
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
        self.calls.append((list(argv), Path(cwd)))
        if key in self.failures:
            raise subprocess.CalledProcessError(1, argv)
        return subprocess.CompletedProcess(argv, 0, self.outputs.get(key, ''), '')


class HostRunnerTests(unittest.TestCase):
    def setUp(self):
        self.old_codex_bin = os.environ.get('CODEX_BIN')

    def tearDown(self):
        if self.old_codex_bin is None:
            os.environ.pop('CODEX_BIN', None)
        else:
            os.environ['CODEX_BIN'] = self.old_codex_bin

    def test_active_task_validation(self):
        self.assertEqual(runner.validate_task(base_task())['task_id'], 'TEST-1')

    def test_non_active_fails(self):
        with self.assertRaises(runner.RunnerError):
            runner.validate_task(base_task(status='DONE'))

    def test_agent_exec_required_boolean(self):
        task = base_task()
        del task['capabilities']['agent_exec']
        with self.assertRaises(runner.RunnerError):
            runner.validate_task(task)
        with self.assertRaises(runner.RunnerError):
            runner.validate_task(base_task(capabilities={**base_task()['capabilities'], 'agent_exec': 'yes'}))

    def test_host_capabilities_required(self):
        task = base_task()
        del task['host_capabilities']['push']
        with self.assertRaises(runner.RunnerError):
            runner.validate_task(task)

    def test_validation_commands_are_argv_lists(self):
        with self.assertRaises(runner.RunnerError):
            runner.validate_task(base_task(validation_commands=['shell command']))

    def test_exact_codex_argv(self):
        os.environ.pop('CODEX_BIN', None)
        self.assertEqual(runner.build_codex_argv(), [
            'codex', '--ask-for-approval', 'never', '--sandbox', 'workspace-write',
            'exec', runner.FIXED_PROMPT,
        ])

    def test_codex_path_can_be_pinned_by_environment(self):
        os.environ['CODEX_BIN'] = '/opt/codex/bin/codex'
        self.assertEqual(runner.build_codex_argv()[0], '/opt/codex/bin/codex')

    def test_no_shell_true(self):
        self.assertNotIn('shell=True', inspect.getsource(runner.execute_command))

    def test_untracked_files_all(self):
        command = ('git', 'status', '--porcelain=v1', '-z', '--untracked-files=all')
        fake = FakeRun({command: '?? dir/a.py\0?? dir/b.py\0'})
        self.assertEqual(runner.changed_worktree_paths(Path('/repo'), fake), ['dir/a.py', 'dir/b.py'])
        self.assertEqual(fake.calls[0][0], list(command))

    def test_unauthorized_path_rejected(self):
        with self.assertRaises(runner.RunnerError):
            runner.validate_changed_paths(['bad.txt'], base_task())

    def test_architect_tamper_rejected(self):
        task = base_task(allowed_paths=['impl.txt', '.agent/CURRENT_TASK.md'])
        with self.assertRaises(runner.RunnerError):
            runner.validate_changed_paths(['.agent/CURRENT_TASK.md'], task)

    def test_source_write_false_rejects_changes(self):
        caps = {**base_task()['capabilities'], 'source_write': False}
        with self.assertRaises(runner.RunnerError):
            runner.validate_changed_paths(['impl.txt'], base_task(capabilities=caps))

    def test_agent_exec_false_blocks(self):
        caps = {**base_task()['capabilities'], 'agent_exec': False}
        with self.assertRaises(runner.RunnerError):
            runner.require_agent_capability(base_task(capabilities=caps), 'agent_exec')

    def test_host_push_false_blocks(self):
        with self.assertRaises(runner.RunnerError):
            runner.require_host_capability(base_task(host_capabilities={'sync': True, 'commit': True, 'push': False}), 'push')

    def test_baseline_equality_not_required(self):
        fake = FakeRun()
        runner.verify_baseline_ancestor(Path('/repo'), 'base', 'later', fake)
        self.assertIn((['git', 'merge-base', '--is-ancestor', 'base', 'later'], Path('/repo')), fake.calls)

    def test_unexpected_handoff_path_rejected(self):
        cmd = ('git', 'diff', '--name-only', '-z', 'base..head')
        with self.assertRaises(runner.RunnerError):
            runner.committed_handoff_paths(Path('/repo'), 'base', 'head', FakeRun({cmd: 'app.py\0'}))

    def test_summary_deterministic(self):
        summary = runner.make_summary('T', 'H', ['z', 'a'], ['z'], 'PASS', commit_sha='C')
        self.assertEqual(summary['changed_paths'], ['a', 'z'])
        self.assertEqual(summary['implementation_paths'], ['z'])
        self.assertEqual(json.dumps(summary, sort_keys=True), json.dumps(summary, sort_keys=True))

    def test_flock_contention_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'lock'
            with runner.InterProcessLock(path):
                with self.assertRaises(runner.RunnerError):
                    with runner.InterProcessLock(path):
                        pass

    def _git(self, cwd: Path, *args: str) -> str:
        return subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()

    def _fixture(self, codex_body: str):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        remote = root / 'remote.git'
        work = root / 'work'
        self._git(root, 'init', '--bare', str(remote))
        self._git(root, 'clone', str(remote), str(work))
        self._git(work, 'checkout', '-b', 'aither-v2')
        self._git(work, 'config', 'user.name', 'Test Agent')
        self._git(work, 'config', 'user.email', 'agent@example.invalid')
        (work / '.agent').mkdir()
        (work / '.agent' / 'CURRENT_TASK.json').write_text('{}\n')
        (work / '.agent' / 'CURRENT_TASK.md').write_text('bootstrap\n')
        (work / '.agent' / 'validate_task_scope.py').write_text('raise SystemExit(0)\n')
        (work / 'AGENTS.md').write_text('test\n')
        self._git(work, 'add', '.')
        self._git(work, 'commit', '-m', 'baseline')
        baseline = self._git(work, 'rev-parse', 'HEAD')
        task = base_task(baseline_sha=baseline)
        (work / '.agent' / 'CURRENT_TASK.json').write_text(json.dumps(task, indent=2) + '\n')
        (work / '.agent' / 'CURRENT_TASK.md').write_text('task\n')
        self._git(work, 'add', '.agent/CURRENT_TASK.json', '.agent/CURRENT_TASK.md')
        self._git(work, 'commit', '-m', 'publish task')
        task_head = self._git(work, 'rev-parse', 'HEAD')
        self._git(work, 'push', '-u', 'origin', 'aither-v2')
        fake = root / 'fake-codex'
        fake.write_text('#!/bin/sh\nset -eu\n' + codex_body + '\n')
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        os.environ['CODEX_BIN'] = str(fake)
        return temp, work, remote, baseline, task_head

    def test_end_to_end_success_commit_push_and_idempotence(self):
        temp, work, remote, baseline, task_head = self._fixture("printf 'ok\\n' > impl.txt")
        with temp:
            result = runner.run_once(work, execute_agent=True)
            self.assertEqual(result['result'], 'PASS')
            self.assertEqual(result['implementation_paths'], ['impl.txt'])
            self.assertTrue(result['commit_sha'])
            self.assertEqual(self._git(work, 'status', '--porcelain'), '')
            remote_head = subprocess.run(['git', '--git-dir', str(remote), 'rev-parse', 'refs/heads/aither-v2'], check=True, capture_output=True, text=True).stdout.strip()
            self.assertEqual(remote_head, result['commit_sha'])
            again = runner.run_once(work, execute_agent=True)
            self.assertEqual(again['result'], 'IDLE')
            self.assertEqual(self._git(work, 'rev-parse', 'HEAD'), result['commit_sha'])

    def test_end_to_end_unauthorized_path_restores_and_does_not_push(self):
        temp, work, remote, baseline, task_head = self._fixture("printf 'bad\\n' > bad.txt")
        with temp:
            with self.assertRaises(runner.RunnerError):
                runner.run_once(work, execute_agent=True)
            self.assertEqual(self._git(work, 'status', '--porcelain'), '')
            self.assertEqual(self._git(work, 'rev-parse', 'HEAD'), task_head)
            remote_head = subprocess.run(['git', '--git-dir', str(remote), 'rev-parse', 'refs/heads/aither-v2'], check=True, capture_output=True, text=True).stdout.strip()
            self.assertEqual(remote_head, task_head)

    def test_end_to_end_architect_tamper_restores(self):
        temp, work, remote, baseline, task_head = self._fixture("printf 'tamper\\n' > .agent/CURRENT_TASK.md")
        with temp:
            with self.assertRaises(runner.RunnerError):
                runner.run_once(work, execute_agent=True)
            self.assertEqual(self._git(work, 'status', '--porcelain'), '')
            self.assertEqual(self._git(work, 'rev-parse', 'HEAD'), task_head)

    def test_dry_run_never_invokes_codex(self):
        temp, work, remote, baseline, task_head = self._fixture("exit 99")
        with temp:
            result = runner.run_once(work, execute_agent=False)
            self.assertEqual(result['result'], 'PASS')
            self.assertEqual(result['message'], 'dry-run')
            self.assertEqual(self._git(work, 'rev-parse', 'HEAD'), task_head)


if __name__ == '__main__':
    unittest.main(verbosity=2)
