#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path

AGENT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, AGENT / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner_live = load('runner_live', 'runner_live.py')
codex_observer = load('codex_observer', 'codex_observer.py')
systemd_runner = load('systemd_runner', 'systemd_runner.py')


class Tests(unittest.TestCase):
    def test_sanitizer(self):
        safe = runner_live.sanitize_status({'task_id': 'T', 'state': 'RUNNING',
                                            'reasoning': 'PRIVATE', 'command': 'cat token',
                                            'stdout': 'secret'})
        self.assertNotIn('reasoning', safe)
        self.assertNotIn('command', safe)
        self.assertNotIn('stdout', safe)

    def test_sanitizer_accepts_new_safe_fields(self):
        safe = runner_live.sanitize_status({'executor': 'hermes', 'repo_state': 'clean',
                                            'aither_state': 'active', 'deployed_sha': 'abc123',
                                            'progress_current': 1, 'progress_total': 5})
        self.assertEqual(safe['executor'], 'hermes')
        self.assertEqual(safe['repo_state'], 'clean')
        self.assertEqual(safe['aither_state'], 'active')
        self.assertEqual(safe['deployed_sha'], 'abc123')
        self.assertEqual(safe['progress_current'], 1)
        self.assertEqual(safe['progress_total'], 5)

    def test_sanitizer_rejects_secret_like_fields(self):
        safe = runner_live.sanitize_status({'token': 's', 'credential': 'x', 'prompt': 'p',
                                            'stdout': 'o', 'stderr': 'e', 'reasoning': 'r',
                                            'command': 'c', 'secret': 'v'})
        for key in ('token', 'credential', 'prompt', 'stdout', 'stderr', 'reasoning',
                    'command', 'secret'):
            self.assertNotIn(key, safe)

    def test_event_metadata(self):
        self.assertEqual(
            codex_observer.event_metadata('{"type":"item.completed","item":{"type":"reasoning","text":"PRIVATE"}}'),
            ('item.completed', 'reasoning'))

    def test_json_flag(self):
        old = os.environ.get('AITHER_REAL_CODEX_BIN')
        os.environ['AITHER_REAL_CODEX_BIN'] = '/opt/codex'
        try:
            argv = codex_observer.build_real_argv(['--ask-for-approval', 'never', 'exec',
                                                   '--sandbox', 'workspace-write', 'prompt'])
        finally:
            if old is None:
                os.environ.pop('AITHER_REAL_CODEX_BIN', None)
            else:
                os.environ['AITHER_REAL_CODEX_BIN'] = old
        self.assertEqual(argv[:5], ['/opt/codex', '--ask-for-approval', 'never', 'exec', '--json'])

    def test_systemd_final_status_uses_summary_identity(self):
        status = systemd_runner.build_final_status(
            {'task_id': 'H1-R4', 'executor': 'hermes', 'result': 'PASS', 'message': ''}, 0)
        self.assertEqual(status['task_id'], 'H1-R4')
        self.assertEqual(status['executor'], 'hermes')
        self.assertEqual(status['state'], 'PASS')

    def test_systemd_final_status_blocked_keeps_identity(self):
        status = systemd_runner.build_final_status(
            {'task_id': 'H1-R4', 'executor': 'hermes', 'result': 'BLOCKED',
             'message': 'invalid executor: bad'}, 1)
        self.assertEqual(status['task_id'], 'H1-R4')
        self.assertEqual(status['executor'], 'hermes')
        self.assertEqual(status['state'], 'BLOCKED')
        self.assertEqual(status['message_code'], 'EXECUTOR_FAILURE')

    def test_systemd_omits_empty_identity(self):
        status = systemd_runner.build_final_status({}, 1)
        self.assertNotIn('task_id', status)
        self.assertNotIn('executor', status)


if __name__ == '__main__':
    unittest.main(verbosity=2)
