#!/usr/bin/env python3
"""
Aither SIEM Receiver — CHANGE-0022-C2 R7-R5-EMG-GW-R4.

Simple Python HTTP+UDP server that:
- Listens on UDP port 514 for CEF-formatted syslog events from Gateway siem.py
- Listens on HTTP port 8080 for JSON health-check and event query API
- Classifies events into 12 required types
- Stores recent events in memory (ring buffer)
- Exposes /health, /events, /events/count, /events/type/{name} endpoints

Deployed as aither-siem service in aither-inference namespace.
"""
import os
import sys
import json
import signal
import socket
import threading
import time
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import defaultdict, deque
from datetime import datetime, timezone

# ── Configuration ────────────────────────────────────────────────────────────
LISTEN_HOST = os.environ.get("SIEM_LISTEN_HOST", "0.0.0.0")
UDP_PORT = int(os.environ.get("SIEM_UDP_PORT", "514"))
HTTP_PORT = int(os.environ.get("SIEM_HTTP_PORT", "8080"))
RING_SIZE = int(os.environ.get("SIEM_RING_SIZE", "10000"))

# ── Event store ──────────────────────────────────────────────────────────────
events: deque = deque(maxlen=RING_SIZE)
counters: dict = defaultdict(int)
lock = threading.Lock()

# ── Expected event types ─────────────────────────────────────────────────────
EXPECTED_TYPES = {
    "auth_failure", "rate_limit_exceeded", "security_input_block",
    "security_output_block", "billing_reserve", "billing_settle",
    "billing_refund", "admin_drain", "admin_undrain",
    "upstream_timeout", "dependency_failure",
}

def classify_event(msg: str) -> str:
    """Extract event type from CEF message."""
    msg_lower = msg.lower()
    for etype in sorted(EXPECTED_TYPES, key=len, reverse=True):
        if etype in msg_lower:
            return etype
    return "unknown"

# ── UDP Listener ─────────────────────────────────────────────────────────────
def udp_listener():
    """Listen for CEF syslog events on UDP."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((LISTEN_HOST, UDP_PORT))
        print(f"[SIEM] UDP listener bound to {LISTEN_HOST}:{UDP_PORT}", flush=True)
    except PermissionError:
        print(f"[SIEM] WARNING: cannot bind UDP {UDP_PORT} (requires root/cap_net_bind_service). Using port 1514.", flush=True)
        sock.bind((LISTEN_HOST, 1514))

    while True:
        try:
            data, addr = sock.recvfrom(4096)
            msg = data.decode("utf-8", errors="replace").strip()
            if not msg:
                continue

            ts = datetime.now(timezone.utc).isoformat()
            etype = classify_event(msg)
            evt = {
                "timestamp": ts,
                "event_type": etype,
                "source": f"{addr[0]}:{addr[1]}",
                "raw": msg[:1000],
                "id": hashlib.sha256(msg.encode()).hexdigest()[:16],
            }

            with lock:
                events.append(evt)
                counters[etype] += 1
                counters["total"] += 1

            if etype != "unknown":
                print(f"[SIEM] [{etype}] from {addr[0]}:{addr[1]}", flush=True)
        except Exception as e:
            print(f"[SIEM] UDP error: {e}", flush=True)

# ── HTTP Handler ─────────────────────────────────────────────────────────────
class SiemHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress access logs

    def _json(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.rstrip("/")

        if path == "/health":
            with lock:
                total = counters.get("total", 0)
            return self._json(200, {
                "status": "ok",
                "service": "aither-siem",
                "change": "CHANGE-0022-C2",
                "total_events": total,
                "ring_size": RING_SIZE,
                "uptime_seconds": int(time.time() - START_TIME),
            })

        if path == "/events":
            with lock:
                recent = list(events)[-100:]
            counts_by_type = defaultdict(int)
            for e in recent:
                counts_by_type[e["event_type"]] += 1
            return self._json(200, {
                "count": len(recent),
                "events": recent,
                "type_summary": dict(counts_by_type),
            })

        if path == "/events/count":
            with lock:
                c = dict(counters)
            return self._json(200, {"counters": c})

        if path.startswith("/events/type/"):
            etype = path.split("/events/type/")[1]
            with lock:
                filtered = [e for e in events if e["event_type"] == etype][-50:]
            return self._json(200, {
                "event_type": etype,
                "total": counters.get(etype, 0),
                "recent": filtered,
            })

        if path == "/events/summary":
            with lock:
                c = dict(counters)
            covered = set(c.keys()) - {"total", "unknown"}
            missing = EXPECTED_TYPES - covered
            return self._json(200, {
                "total": c.get("total", 0),
                "covered_types": sorted(covered),
                "missing_types": sorted(missing),
                "all_expected_present": len(missing) == 0,
                "counters": c,
            })

        return self._json(404, {"error": "not_found"})

    def do_POST(self):
        # Ingest JSON events via HTTP (alternative to UDP)
        if self.path == "/ingest":
            try:
                length = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(length))
                event_type = data.get("event_type", "unknown")
                ts = datetime.now(timezone.utc).isoformat()
                evt = {
                    "timestamp": ts,
                    "event_type": event_type,
                    "source": "http",
                    "raw": json.dumps(data, ensure_ascii=False),
                    "id": hashlib.sha256(json.dumps(data).encode()).hexdigest()[:16],
                }
                with lock:
                    events.append(evt)
                    counters[event_type] += 1
                    counters["total"] += 1
                return self._json(201, {"status": "accepted", "id": evt["id"]})
            except Exception as e:
                return self._json(400, {"error": str(e)})
        return self._json(404, {"error": "not_found"})


# ── Main ─────────────────────────────────────────────────────────────────────
START_TIME = time.time()

def shutdown(sig, frame):
    print("[SIEM] Shutting down...", flush=True)
    sys.exit(0)

signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)

def main():
    print("=" * 50, flush=True)
    print("Aither SIEM Receiver — CHANGE-0022-C2", flush=True)
    print(f"UDP: {LISTEN_HOST}:{UDP_PORT}", flush=True)
    print(f"HTTP: {LISTEN_HOST}:{HTTP_PORT}", flush=True)
    print(f"Ring buffer: {RING_SIZE} events", flush=True)
    print(f"Expected types: {sorted(EXPECTED_TYPES)}", flush=True)
    print("=" * 50, flush=True)

    # Start UDP listener in background thread
    udp_thread = threading.Thread(target=udp_listener, daemon=True)
    udp_thread.start()

    # Start HTTP server
    httpd = HTTPServer((LISTEN_HOST, HTTP_PORT), SiemHTTPHandler)
    print(f"[SIEM] HTTP server listening on {LISTEN_HOST}:{HTTP_PORT}", flush=True)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
