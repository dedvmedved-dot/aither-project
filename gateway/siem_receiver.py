#!/usr/bin/env python3
"""
Aither SIEM Receiver — Production Implementation. CHANGE-0022-C3.

Features:
- Persistent event storage (SQLite + JSON file backup)
- Authentication on query API (admin key / API token)
- Retention policy (configurable, default 90 days)
- Backup/forwarding support (JSON file + syslog relay)
- 16 required event types
- No pip install at startup (pre-built image, deps baked in)
"""
import os
import sys
import json
import signal
import socket
import sqlite3
import threading
import time
import hashlib
import gzip
import shutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta

# ── Configuration ────────────────────────────────────────────────────────────
LISTEN_HOST = os.environ.get("SIEM_LISTEN_HOST", "0.0.0.0")
UDP_PORT = int(os.environ.get("SIEM_UDP_PORT", "1514"))   # non-privileged port for K8s
HTTP_PORT = int(os.environ.get("SIEM_HTTP_PORT", "8080"))
RING_SIZE = int(os.environ.get("SIEM_RING_SIZE", "50000"))
RETENTION_DAYS = int(os.environ.get("SIEM_RETENTION_DAYS", "90"))
DB_PATH = os.environ.get("SIEM_DB_PATH", "/data/siem/events.db")
BACKUP_DIR = os.environ.get("SIEM_BACKUP_DIR", "/data/siem/backups")
FORWARD_ENABLED = os.environ.get("SIEM_FORWARD_ENABLED", "false").lower() == "true"
FORWARD_HOST = os.environ.get("SIEM_FORWARD_HOST", "")
FORWARD_PORT = int(os.environ.get("SIEM_FORWARD_PORT", "514"))
ADMIN_API_KEY = os.environ.get("SIEM_ADMIN_KEY", os.environ.get("ADMIN_KEY", ""))
QUERY_AUTH_ENABLED = os.environ.get("SIEM_QUERY_AUTH", "true").lower() == "true"
BACKUP_INTERVAL = int(os.environ.get("SIEM_BACKUP_INTERVAL", "3600"))  # seconds

# ── All 16 required event types ─────────────────────────────────────────────
EXPECTED_TYPES = {
    "auth_success", "auth_failure", "scope_denied", "rate_limit_exceeded",
    "security_input_block", "security_output_block",
    "billing_reserve", "billing_settle", "billing_refund",
    "admin_drain", "admin_undrain",
    "upstream_timeout", "upstream_error",
    "dependency_failure", "vault_failure", "rag_access_denied",
}

# ── Global state ─────────────────────────────────────────────────────────────
events: deque = deque(maxlen=RING_SIZE)
counters: dict = defaultdict(int)
lock = threading.Lock()
db_conn: sqlite3.Connection = None
db_lock = threading.Lock()
START_TIME = time.time()
_forward_sock = None


def init_db():
    """Initialize SQLite database with proper schema and indices."""
    global db_conn
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    db_conn.execute("PRAGMA journal_mode=WAL")
    db_conn.execute("PRAGMA synchronous=NORMAL")
    
    db_conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            source TEXT NOT NULL,
            raw_data TEXT NOT NULL,
            event_hash TEXT NOT NULL
        )
    """)
    db_conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events (event_type)")
    db_conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events (timestamp)")
    db_conn.execute("CREATE INDEX IF NOT EXISTS idx_events_hash ON events (event_hash)")
    db_conn.commit()
    print(f"[SIEM] Database initialized: {DB_PATH}", flush=True)


def store_event(etype: str, source: str, raw: str, ts: str, evt_hash: str):
    """Persist event to SQLite with deduplication (by hash)."""
    try:
        with db_lock:
            # Dedup: skip if same hash within 1 minute
            cur = db_conn.execute(
                "SELECT id FROM events WHERE event_hash=? AND timestamp > datetime(?, '-1 minutes')",
                (evt_hash, ts))
            if cur.fetchone():
                return
            db_conn.execute(
                "INSERT INTO events (timestamp, event_type, source, raw_data, event_hash) VALUES (?,?,?,?,?)",
                (ts, etype, source, raw[:2000], evt_hash))
            db_conn.commit()
    except Exception as e:
        print(f"[SIEM] DB write error: {e}", flush=True)


def run_retention():
    """Delete events older than retention period."""
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)).isoformat()
        with db_lock:
            cur = db_conn.execute("DELETE FROM events WHERE timestamp < ?", (cutoff,))
            deleted = cur.rowcount
            db_conn.commit()
            if deleted > 0:
                print(f"[SIEM] Retention: deleted {deleted} events older than {RETENTION_DAYS}d", flush=True)
    except Exception as e:
        print(f"[SIEM] Retention error: {e}", flush=True)


def backup_events():
    """Backup events to compressed JSON file."""
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"siem_backup_{ts}.json.gz")
        
        with db_lock:
            cur = db_conn.execute(
                "SELECT timestamp, event_type, source, raw_data FROM events ORDER BY id DESC LIMIT 100000")
            rows = cur.fetchall()
        
        events_list = [
            {"timestamp": r[0], "event_type": r[1], "source": r[2], "raw": r[3]}
            for r in rows
        ]
        
        with gzip.open(backup_file, 'wt', encoding='utf-8') as f:
            json.dump(events_list, f, ensure_ascii=False)
        
        print(f"[SIEM] Backup: {len(events_list)} events → {backup_file}", flush=True)
        
        # Cleanup old backups (keep last 30)
        backups = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.startswith("siem_backup_")],
            reverse=True)
        for old in backups[30:]:
            os.remove(os.path.join(BACKUP_DIR, old))
    except Exception as e:
        print(f"[SIEM] Backup error: {e}", flush=True)


def classify_event(msg: str) -> str:
    """Extract event type from CEF or JSON message."""
    msg_lower = msg.lower()
    # Try JSON first
    try:
        data = json.loads(msg)
        if "event_type" in data:
            return data["event_type"]
    except (json.JSONDecodeError, TypeError):
        pass
    # Try CEF: look for event name in message
    for etype in sorted(EXPECTED_TYPES, key=len, reverse=True):
        if etype in msg_lower:
            return etype
    return "unknown"


def forward_event(msg: str):
    """Forward event to external SIEM via UDP syslog."""
    global _forward_sock
    if not FORWARD_ENABLED or not FORWARD_HOST:
        return
    try:
        if _forward_sock is None:
            _forward_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        _forward_sock.sendto(msg.encode()[:4096], (FORWARD_HOST, FORWARD_PORT))
    except Exception as e:
        print(f"[SIEM] Forward error: {e}", flush=True)


# ── UDP Listener ─────────────────────────────────────────────────────────────
def udp_listener():
    """Listen for CEF syslog and JSON events on UDP."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((LISTEN_HOST, UDP_PORT))
    print(f"[SIEM] UDP listener bound to {LISTEN_HOST}:{UDP_PORT}", flush=True)

    while True:
        try:
            data, addr = sock.recvfrom(4096)
            msg = data.decode("utf-8", errors="replace").strip()
            if not msg:
                continue

            ts = datetime.now(timezone.utc).isoformat()
            etype = classify_event(msg)
            evt_hash = hashlib.sha256(msg.encode()).hexdigest()[:16]
            
            evt = {
                "timestamp": ts,
                "event_type": etype,
                "source": f"{addr[0]}:{addr[1]}",
                "raw": msg[:1000],
                "id": evt_hash,
            }

            with lock:
                events.append(evt)
                counters[etype] += 1
                counters["total"] += 1

            # Persistent storage
            store_event(etype, f"{addr[0]}:{addr[1]}", msg, ts, evt_hash)
            
            # Forward to external SIEM
            forward_event(msg)

            if etype != "unknown":
                print(f"[SIEM] [{etype}] from {addr[0]}:{addr[1]}", flush=True)
        except Exception as e:
            print(f"[SIEM] UDP error: {e}", flush=True)


# ── HTTP Handler with Authentication ─────────────────────────────────────────
class SiemHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress access logs
    
    def _check_auth(self) -> bool:
        """Check API key authentication for query endpoints."""
        if not QUERY_AUTH_ENABLED:
            return True
        if not ADMIN_API_KEY:
            return True  # No key configured → allow (dev mode)
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
            if token == ADMIN_API_KEY:
                return True
        # Also check x-api-key header
        x_key = self.headers.get("X-API-Key", "")
        if x_key and x_key == ADMIN_API_KEY:
            return True
        return False

    def _json(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _auth_json(self, code: int, data: dict):
        if not self._check_auth():
            return self._json(401, {"error": "authentication_required"})
        return self._json(code, data)

    def do_GET(self):
        path = self.path.rstrip("/")

        if path == "/health":
            with lock:
                total = counters.get("total", 0)
            return self._json(200, {
                "status": "ok",
                "service": "aither-siem",
                "change": "CHANGE-0022-C3",
                "total_events": total,
                "ring_size": RING_SIZE,
                "uptime_seconds": int(time.time() - START_TIME),
                "db_path": DB_PATH,
                "retention_days": RETENTION_DAYS,
            })

        if path == "/ready":
            status = "ok"
            checks = {"udp": "ok", "db": "ok"}
            if not db_conn:
                checks["db"] = "not_initialized"
                status = "degraded"
            return self._json(200 if status == "ok" else 503, {
                "status": status, "checks": checks})

        # All query endpoints require auth
        if path == "/events":
            if not self._check_auth():
                return self._json(401, {"error": "authentication_required"})
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
            if not self._check_auth():
                return self._json(401, {"error": "authentication_required"})
            with lock:
                c = dict(counters)
            return self._json(200, {"counters": c})

        if path.startswith("/events/type/"):
            if not self._check_auth():
                return self._json(401, {"error": "authentication_required"})
            etype = path.split("/events/type/")[1]
            with lock:
                filtered = [e for e in events if e["event_type"] == etype][-50:]
            return self._json(200, {
                "event_type": etype,
                "total": counters.get(etype, 0),
                "recent": filtered,
            })

        if path == "/events/summary":
            if not self._check_auth():
                return self._json(401, {"error": "authentication_required"})
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
                "expected_total": len(EXPECTED_TYPES),
                "covered_total": len(covered),
            })

        if path == "/events/search":
            if not self._check_auth():
                return self._json(401, {"error": "authentication_required"})
            # Simple search by event_type query param
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            etype = qs.get("type", [None])[0]
            limit = min(int(qs.get("limit", ["100"])[0]), 1000)
            
            if etype:
                with db_lock:
                    cur = db_conn.execute(
                        "SELECT timestamp, event_type, source, raw_data FROM events "
                        "WHERE event_type=? ORDER BY id DESC LIMIT ?",
                        (etype, limit))
                    rows = cur.fetchall()
                return self._json(200, {
                    "event_type": etype,
                    "count": len(rows),
                    "events": [
                        {"timestamp": r[0], "event_type": r[1], "source": r[2], "raw": r[3][:500]}
                        for r in rows
                    ]
                })
            return self._json(400, {"error": "type parameter required"})

        return self._json(404, {"error": "not_found"})

    def do_POST(self):
        # Ingest JSON events via HTTP (authenticated)
        if self.path == "/ingest":
            if not self._check_auth():
                return self._json(401, {"error": "authentication_required"})
            try:
                length = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(length))
                event_type = data.get("event_type", "unknown")
                ts = datetime.now(timezone.utc).isoformat()
                raw = json.dumps(data, ensure_ascii=False)
                evt_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]
                
                evt = {
                    "timestamp": ts,
                    "event_type": event_type,
                    "source": "http",
                    "raw": raw[:1000],
                    "id": evt_hash,
                }
                with lock:
                    events.append(evt)
                    counters[event_type] += 1
                    counters["total"] += 1
                
                store_event(event_type, "http", raw, ts, evt_hash)
                forward_event(raw)
                
                return self._json(201, {"status": "accepted", "id": evt["id"]})
            except Exception as e:
                return self._json(400, {"error": str(e)})
        
        # Manual backup trigger
        if self.path == "/admin/backup":
            if not self._check_auth():
                return self._json(401, {"error": "authentication_required"})
            backup_events()
            return self._json(200, {"status": "backup_completed"})
        
        # Manual retention trigger
        if self.path == "/admin/retention":
            if not self._check_auth():
                return self._json(401, {"error": "authentication_required"})
            run_retention()
            return self._json(200, {"status": "retention_completed"})
        
        return self._json(404, {"error": "not_found"})


# ── Background Tasks ─────────────────────────────────────────────────────────
def retention_loop():
    """Run retention policy periodically."""
    while True:
        time.sleep(3600)  # every hour
        try:
            run_retention()
        except Exception as e:
            print(f"[SIEM] Retention loop error: {e}", flush=True)


def backup_loop():
    """Run backups periodically."""
    while True:
        time.sleep(BACKUP_INTERVAL)
        try:
            backup_events()
        except Exception as e:
            print(f"[SIEM] Backup loop error: {e}", flush=True)


# ── Main ─────────────────────────────────────────────────────────────────────
def shutdown(sig, frame):
    print("[SIEM] Shutting down...", flush=True)
    if db_conn:
        db_conn.close()
    sys.exit(0)


signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)


def main():
    print("=" * 60, flush=True)
    print("Aither SIEM Receiver — Production (CHANGE-0022-C3)", flush=True)
    print(f"UDP: {LISTEN_HOST}:{UDP_PORT}", flush=True)
    print(f"HTTP: {LISTEN_HOST}:{HTTP_PORT}", flush=True)
    print(f"Ring buffer: {RING_SIZE} events", flush=True)
    print(f"Retention: {RETENTION_DAYS} days", flush=True)
    print(f"DB: {DB_PATH}", flush=True)
    print(f"Backup dir: {BACKUP_DIR}", flush=True)
    print(f"Forward: {'enabled → ' + FORWARD_HOST + ':' + str(FORWARD_PORT) if FORWARD_ENABLED else 'disabled'}", flush=True)
    print(f"Query auth: {'enabled' if QUERY_AUTH_ENABLED else 'disabled'}", flush=True)
    print(f"Expected types: {len(EXPECTED_TYPES)}", flush=True)
    print("=" * 60, flush=True)

    # Initialize database
    init_db()

    # Start background threads
    threading.Thread(target=udp_listener, daemon=True).start()
    threading.Thread(target=retention_loop, daemon=True).start()
    threading.Thread(target=backup_loop, daemon=True).start()

    # Start HTTP server
    httpd = HTTPServer((LISTEN_HOST, HTTP_PORT), SiemHTTPHandler)
    print(f"[SIEM] HTTP server listening on {LISTEN_HOST}:{HTTP_PORT}", flush=True)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        if db_conn:
            db_conn.close()


if __name__ == "__main__":
    main()
