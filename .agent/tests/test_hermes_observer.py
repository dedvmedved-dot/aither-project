#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import socket
import tempfile
import threading
import unittest
import sys
from pathlib import Path

AGENT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AGENT))


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, AGENT / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hermes_observer = load('hermes_observer', 'hermes_observer.py')


def _serve(path, response, *, delay=0.0, read_signal=True):
    """Run a fake H2 bridge on `path`. Returns (thread, received, ready)."""
    received = {}
    ready = threading.Event()

    def run():
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(path)
        listener.listen(1)
        ready.set()
        conn, _ = listener.accept()
        if delay:
            import time
            time.sleep(delay)
        if read_signal:
            received['signal'] = conn.recv(16)
        if response is not None:
            conn.sendall(response)
        conn.close()
        listener.close()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread, received, ready


class Tests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix='hermes-bridge-')
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _path(self):
        return str(self.dir / 'bridge.sock')

    def test_socket_path_env_override(self):
        old = os.environ.get('AITHER_HERMES_SOCKET')
        os.environ['AITHER_HERMES_SOCKET'] = '/tmp/override.sock'
        try:
            self.assertEqual(hermes_observer.socket_path(), '/tmp/override.sock')
        finally:
            if old is None:
                os.environ.pop('AITHER_HERMES_SOCKET', None)
            else:
                os.environ['AITHER_HERMES_SOCKET'] = old

    def test_sends_only_fixed_run_signal(self):
        path = self._path()
        thread, received, ready = _serve(path, b'PASS\n')
        ready.wait(5)
        hermes_observer.send_run(path=path, timeout=5)
        thread.join(5)
        self.assertEqual(received.get('signal'), b'RUN\n')

    def test_success_response(self):
        path = self._path()
        thread, _, ready = _serve(path, b'PASS\n')
        ready.wait(5)
        self.assertEqual(hermes_observer.send_run(path=path, timeout=5), 'PASS')
        thread.join(5)

    def test_blocked_response_is_fail_closed(self):
        self.assertTrue(hermes_observer.is_fail_closed('BLOCKED_EXECUTOR'))
        self.assertTrue(hermes_observer.is_fail_closed('FAIL_TIMEOUT'))
        self.assertFalse(hermes_observer.is_fail_closed('PASS'))

    def test_main_returns_nonzero_on_blocked(self):
        path = self._path()
        thread, _, ready = _serve(path, b'BLOCKED_EXECUTOR\n')
        ready.wait(5)
        old = os.environ.get('AITHER_HERMES_SOCKET')
        old_factory = hermes_observer.make_publisher
        os.environ['AITHER_HERMES_SOCKET'] = path
        events = []
        hermes_observer.make_publisher = lambda *args: events.append
        try:
            self.assertEqual(hermes_observer.main([]), 1)
        finally:
            hermes_observer.make_publisher = old_factory
            if old is None:
                os.environ.pop('AITHER_HERMES_SOCKET', None)
            else:
                os.environ['AITHER_HERMES_SOCKET'] = old
        thread.join(5)

    def test_main_returns_zero_on_success(self):
        path = self._path()
        thread, _, ready = _serve(path, b'PASS\n')
        ready.wait(5)
        old = os.environ.get('AITHER_HERMES_SOCKET')
        old_factory = hermes_observer.make_publisher
        os.environ['AITHER_HERMES_SOCKET'] = path
        events = []
        hermes_observer.make_publisher = lambda *args: events.append
        try:
            self.assertEqual(hermes_observer.main([]), 0)
        finally:
            hermes_observer.make_publisher = old_factory
            if old is None:
                os.environ.pop('AITHER_HERMES_SOCKET', None)
            else:
                os.environ['AITHER_HERMES_SOCKET'] = old
        thread.join(5)

    def test_rejects_arbitrary_args(self):
        self.assertEqual(hermes_observer.main(['--prompt', 'x']), 2)

    def test_timeout_fails_closed(self):
        path = self._path()
        thread, _, ready = _serve(path, None, delay=2.0)
        ready.wait(5)
        with self.assertRaises(socket.timeout):
            hermes_observer.send_run(path=path, timeout=0.3)
        thread.join(5)

    def test_connection_failure_fails_closed(self):
        with self.assertRaises(OSError):
            hermes_observer.send_run(path=self._path(), timeout=0.1)

    def test_bounded_response(self):
        path = self._path()
        thread, _, ready = _serve(path, b'A' * 10000)
        ready.wait(5)
        result = hermes_observer.send_run(path=path, timeout=5, max_response=100)
        self.assertLessEqual(len(result), 100)
        thread.join(5)

    def test_no_direct_hermes_cli_and_no_shell(self):
        src = (AGENT / 'hermes_observer.py').read_text(encoding='utf-8')
        self.assertNotIn('/usr/local/lib/hermes-agent/venv/bin/hermes', src)
        self.assertNotIn('shell=True', src)
        self.assertNotIn('os.system', src)
        self.assertNotIn(' eval(', src)
        self.assertNotIn(' exec(', src)


if __name__ == '__main__':
    unittest.main(verbosity=2)
