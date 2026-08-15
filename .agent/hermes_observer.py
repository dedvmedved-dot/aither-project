#!/usr/bin/env python3
"""Aither -> Hermes H2 root socket-bridge client (governed executor observer).

Writes exactly ``RUN`` to the accepted H2 root bridge socket and reads only the
bridge's response. Never invokes the Hermes binary directly, never accepts a
prompt or command from the caller, never uses shell/eval/exec.
"""

from __future__ import annotations

import os
import socket
import sys

DEFAULT_SOCKET = "/run/aither-hermes/execute.sock"
SOCKET_ENV = "AITHER_HERMES_SOCKET"              # test-only socket path override
TIMEOUT_ENV = "AITHER_HERMES_TIMEOUT"            # hard timeout, seconds
MAX_RESPONSE_ENV = "AITHER_HERMES_MAX_RESPONSE"  # bounded response, bytes

FIXED_SIGNAL = b"RUN\n"
DEFAULT_TIMEOUT = 3600.0
DEFAULT_MAX_RESPONSE = 65536


def socket_path() -> str:
    return os.environ.get(SOCKET_ENV, DEFAULT_SOCKET)


def timeout_seconds() -> float:
    try:
        return float(os.environ.get(TIMEOUT_ENV, str(DEFAULT_TIMEOUT)))
    except ValueError:
        return DEFAULT_TIMEOUT


def max_response_bytes() -> int:
    try:
        return int(os.environ.get(MAX_RESPONSE_ENV, str(DEFAULT_MAX_RESPONSE)))
    except ValueError:
        return DEFAULT_MAX_RESPONSE


def send_run(path: str | None = None, timeout: float | None = None,
             max_response: int | None = None) -> str:
    """Send the fixed RUN signal and return the stripped bridge response.

    Raises ``socket.timeout`` on a hard timeout and ``OSError`` on connect/send
    failures. The response is truncated to ``max_response`` bytes.
    """
    path = path if path is not None else socket_path()
    timeout = timeout if timeout is not None else timeout_seconds()
    max_response = max_response if max_response is not None else max_response_bytes()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        sock.connect(path)
        sock.sendall(FIXED_SIGNAL)
        sock.shutdown(socket.SHUT_WR)
        chunks: list[bytes] = []
        received = 0
        while received < max_response:
            data = sock.recv(min(4096, max_response - received))
            if not data:
                break
            chunks.append(data)
            received += len(data)
        response = b"".join(chunks).decode("utf-8", errors="replace")
    return response.strip()


def is_fail_closed(response: str) -> bool:
    upper = response.upper()
    return upper.startswith("BLOCKED_") or upper.startswith("FAIL")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv:
        # The bridge client accepts no prompt and no command from the caller.
        sys.stderr.write("BLOCKED_ARGS\n")
        return 2
    try:
        response = send_run()
    except socket.timeout:
        sys.stderr.write("BLOCKED_TIMEOUT\n")
        return 1
    except OSError:
        sys.stderr.write("BLOCKED_CONNECT\n")
        return 1
    if not response:
        sys.stderr.write("BLOCKED_EMPTY\n")
        return 1
    if is_fail_closed(response):
        sys.stdout.write(response + "\n")
        return 1
    sys.stdout.write(response + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
