"""Aither API Gateway — proxy to vLLM with JWT RS256, Redis rate limiting, and billing."""
import os, json, time, uuid, traceback, threading
from urllib.request import Request, urlopen
from http.server import HTTPServer, BaseHTTPRequestHandler
import redis
import jwt as pyjwt
import psycopg2
import psycopg2.pool
from security import check_security

VLLM_URL = os.environ.get("VLLM_URL", "http://vllm:8000")
REDIS_URL = os.environ.get("REDIS_URL", "redis")
RATE_LIMIT_RPM = int(os.environ.get("RATE_LIMIT_RPM", "300"))
RATE_LIMIT_TPM = int(os.environ.get("RATE_LIMIT_TPM", "100000"))
PG_URL = os.environ.get("PG_URL", "postgresql://aither@postgres:5432/aither")
TOKEN_COST = int(os.environ.get("TOKEN_COST", "1"))  # tokens to reserve per request token

r = redis.Redis(host=REDIS_URL, port=6379, decode_responses=True, socket_connect_timeout=2)
db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, PG_URL)
# Ensure usage_records table exists
_conn = db_pool.getconn()
try:
    with _conn:
        with _conn.cursor() as _cur:
            _cur.execute('''
                CREATE TABLE IF NOT EXISTS usage_records (
                    id SERIAL PRIMARY KEY,
                    org_id UUID NOT NULL,
                    request_id VARCHAR(8),
                    model VARCHAR(64),
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    total_tokens INTEGER NOT NULL DEFAULT 0,
                    status VARCHAR(16) NOT NULL DEFAULT %s,
                    latency_ms INTEGER,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            ''', ('success',))
            _cur.execute("CREATE INDEX IF NOT EXISTS idx_usage_org_time ON usage_records (org_id, created_at DESC)")
            _cur.execute("CREATE INDEX IF NOT EXISTS idx_usage_model ON usage_records (model)")
finally:
    db_pool.putconn(_conn)

# Load public key
PUBLIC_KEY = os.environ.get("JWT_PUBLIC_KEY", "")
if not PUBLIC_KEY:
    for path in ["/app/delegation/public.pem", "./delegation/public.pem"]:
        try:
            with open(path) as f:
                PUBLIC_KEY = f.read()
            break
        except:
            pass

print(f"Gateway: public key {'loaded' if PUBLIC_KEY else 'MISSING'} ({len(PUBLIC_KEY)} chars)", flush=True)

def billing_op(org_id: str, operation: str, amount: int, reference: str = ""):
    """Execute a billing operation in a transaction. Returns (success, balance_after, error)."""
    conn = db_pool.getconn()
    try:
        with conn:
            with conn.cursor() as cur:
                if operation == "reserve":
                    # Auto-create billing account if missing
                    cur.execute(
                        "INSERT INTO billing_accounts (org_id, balance, reserved) VALUES (%s, 1000000, 0) ON CONFLICT (org_id) DO NOTHING",
                        (org_id,))
                    # Check balance, then reserve
                    cur.execute(
                        "SELECT balance, reserved FROM billing_accounts WHERE org_id=%s FOR UPDATE",
                        (org_id,))
                    row = cur.fetchone()
                    if not row:
                        return False, 0, "org not found"
                    balance, reserved = row
                    if balance < reserved + amount:
                        return False, balance, f"insufficient balance: {balance}, reserved: {reserved}, need: {amount}"
                    cur.execute(
                        "UPDATE billing_accounts SET reserved = reserved + %s, updated_at = now() WHERE org_id = %s",
                        (amount, org_id))
                    cur.execute(
                        "INSERT INTO billing_ledger (org_id, amount, operation, reference, balance_after) VALUES (%s,%s,%s,%s,%s)",
                        (org_id, amount, "reserve", reference, balance - amount))
                    return True, balance - amount, ""

                elif operation == "settle":
                    cur.execute(
                        "UPDATE billing_accounts SET balance = balance - %s, reserved = reserved - %s, updated_at = now() WHERE org_id = %s RETURNING balance",
                        (amount, amount, org_id))
                    row = cur.fetchone()
                    if not row:
                        return False, 0, "org not found"
                    new_balance = row[0]
                    cur.execute(
                        "INSERT INTO billing_ledger (org_id, amount, operation, reference, balance_after) VALUES (%s,%s,%s,%s,%s)",
                        (org_id, amount, "settle", reference, new_balance))
                    return True, new_balance, ""

                elif operation == "refund":
                    cur.execute(
                        "UPDATE billing_accounts SET reserved = reserved - %s, updated_at = now() WHERE org_id = %s AND reserved >= %s RETURNING balance",
                        (amount, org_id, amount))
                    row = cur.fetchone()
                    if not row:
                        return False, 0, "insufficient reserved"
                    new_balance = row[0]
                    cur.execute(
                        "INSERT INTO billing_ledger (org_id, amount, operation, reference, balance_after) VALUES (%s,%s,%s,%s,%s)",
                        (org_id, amount, "refund", reference, new_balance))
                    return True, new_balance, ""

    except Exception as e:
        conn.rollback()
        return False, 0, str(e)
    finally:
        db_pool.putconn(conn)


def get_balance(org_id: str):
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT balance, reserved FROM billing_accounts WHERE org_id=%s", (org_id,))
            row = cur.fetchone()
            if row:
                return {"balance": row[0], "reserved": row[1]}
            return None
    finally:
        db_pool.putconn(conn)


class Gateway(BaseHTTPRequestHandler):
    vllm_url = VLLM_URL  # default, overridden per-request by model routing

    def _check_jwt(self):
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        token = auth[7:]
        try:
            if PUBLIC_KEY:
                return pyjwt.decode(token, PUBLIC_KEY, algorithms=["RS256"],
                                    options={"verify_exp": True, "verify_iss": False})
        except pyjwt.ExpiredSignatureError:
            return "expired"
        except:
            pass
        return {"legacy_key": token}

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"status": "ok", "billing": "enabled"})
            return
        if self.path.startswith("/v1/billing/"):
            # Get balance for org
            auth = self.headers.get("Authorization", "")
            token = auth[7:] if auth.startswith("Bearer ") else ""
            if not token or not PUBLIC_KEY:
                self._json(401, {"error": "unauthorized"})
                return
            try:
                payload = pyjwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])
                org_id = payload.get("org_id")
                if not org_id:
                    self._json(400, {"error": "no org_id in token"})
                    return
                bal = get_balance(org_id)
                if bal:
                    self._json(200, {"org_id": org_id, **bal})
                else:
                    self._json(404, {"error": "org not found"})
            except Exception as e:
                self._json(401, {"error": str(e)})
            return
        if self.path == "/v1/models":
            status, body, ct = self._proxy("GET", self.path)
            self.send_response(status)
            self.send_header("Content-Type", ct)
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/v1/usage/"):
            auth = self.headers.get("Authorization", "")
            token = auth[7:] if auth.startswith("Bearer ") else ""
            if not token or not PUBLIC_KEY:
                self._json(401, {"error": "unauthorized"})
                return
            try:
                payload = pyjwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])
                org_id = payload.get("org_id")
            except Exception as e:
                self._json(401, {"error": str(e)})
                return
            conn = db_pool.getconn()
            try:
                with conn.cursor() as cur:
                    if self.path == "/v1/usage/":
                        # Summary
                        cur.execute(
                            "SELECT count(*), coalesce(sum(amount),0) FROM billing_ledger "
                            "WHERE org_id=%s AND operation='settle'", (org_id,))
                        cnt, total = cur.fetchone()
                        cnt, total = cnt or 0, total or 0
                        # Requests today
                        today = time.strftime("%Y-%m-%d")
                        rcount = int(r.get(f"usage:{org_id}:{today}") or 0)
                        self._json(200, {
                            "org_id": org_id,
                            "total_tokens": int(total),
                            "total_requests": cnt,
                            "requests_today": rcount,
                        })
                    elif self.path == "/v1/usage/stats" or self.path.startswith("/v1/usage/stats?"):
                        days = 7
                        if "?" in self.path:
                            for kv in self.path.split("?", 1)[1].split("&"):
                                if kv.startswith("days="):
                                    try: days = min(int(kv[6:]), 90)
                                    except: pass
                        cur.execute(
                            "SELECT date(created_at) as day, model,"
                            " count(*) as requests,"
                            " coalesce(sum(input_tokens),0) as input_tk,"
                            " coalesce(sum(output_tokens),0) as output_tk,"
                            " coalesce(sum(total_tokens),0) as total_tk,"
                            " count(*) FILTER (WHERE status='error') as errors"
                            " FROM usage_records"
                            " WHERE org_id=%s AND created_at >= now() - interval %s"
                            " GROUP BY day, model ORDER BY day DESC, model",
                            (org_id, str(days) + " days"))
                        rows = cur.fetchall()
                        self._json(200, {"org_id": org_id, "days": days, "stats": [
                            {"day": str(r[0]), "model": r[1], "requests": r[2],
                             "input_tokens": int(r[3]), "output_tokens": int(r[4]),
                             "total_tokens": int(r[5]), "errors": r[6]}
                            for r in rows
                        ]})
                    elif self.path.startswith("/v1/usage/history"):
                        limit = 20
                        if "?" in self.path:
                            for kv in self.path.split("?", 1)[1].split("&"):
                                if kv.startswith("limit="):
                                    try: limit = min(int(kv[6:]), 100)
                                    except: pass
                        cur.execute(
                            "SELECT amount, operation, reference, balance_after, created_at "
                            "FROM billing_ledger WHERE org_id=%s ORDER BY id DESC LIMIT %s",
                            (org_id, limit))
                        rows = cur.fetchall()
                        self._json(200, {"org_id": org_id, "ledger": [
                            {"amount": r[0], "operation": r[1], "reference": r[2],
                             "balance_after": r[3], "created_at": r[4].isoformat()}
                            for r in rows
                        ]})
            finally:
                db_pool.putconn(conn)
            return
        self._json(404, {"error": "not found"})

    def _proxy(self, method, path, body=None):
        url = f"{self.vllm_url}{path}"
        headers = {"Content-Type": "application/json"}
        data = body.encode() if body else None
        req = Request(url, data=data, headers=headers, method=method)
        try:
            resp = urlopen(req, timeout=120)
            return resp.status, resp.read(), resp.headers.get("Content-Type", "application/json")
        except Exception as e:
            return 502, str(e).encode(), "text/plain"

    def do_POST(self):
        if self.path == "/health":
            self._json(200, {"status": "ok"})
            return

        if not self.path.startswith("/v1/"):
            self._json(404, {"error": "not found"})
            return

        # Validate JWT
        payload = self._check_jwt()
        if payload is None:
            self._json(401, {"error": "valid delegation token required"})
            return
        if payload == "expired":
            self._json(401, {"error": "delegation token expired"})
            return

        org_id = payload.get("org_id", "unknown")

        # Rate limit (RPM + TPM)
        now = int(time.time())
        window = now // 60
        body_len = int(self.headers.get("Content-Length", 0))
        token_est = max(body_len // 4, 100)
        try:
            rpm = r.incr(f"rl:{org_id}:rpm:{window}")
            if rpm == 1: r.expire(f"rl:{org_id}:rpm:{window}", 120)
            tpm = r.incrby(f"rl:{org_id}:tpm:{window}", token_est)
            if tpm <= token_est: r.expire(f"rl:{org_id}:tpm:{window}", 120)
            if rpm > RATE_LIMIT_RPM or tpm > RATE_LIMIT_TPM:
                self._json(429, {"error": "rate_limit_exceeded", "rpm": rpm, "tpm": tpm,
                    "rpm_limit": RATE_LIMIT_RPM, "tpm_limit": RATE_LIMIT_TPM})
                return
        except Exception as e:
            pass  # Redis down: let request through

        # Read body
        length = int(self.headers.get("Content-Length", 0))
        body_str = self.rfile.read(length).decode() if length else "{}"

        # Parse request to estimate tokens
        try:
            req_data = json.loads(body_str)
            max_tokens = req_data.get("max_tokens", 256)
            input_tokens = len(req_data.get("messages", [])) * 20  # rough estimate
            reserve_amount = (max_tokens + input_tokens) * TOKEN_COST
            # Multi-model routing
            model = req_data.get("model", "qwen")
            if "saiga" in model.lower():
                self.vllm_url = os.environ.get("VLLM_SAIGA_URL", "http://vllm-saiga:8000") or "http://vllm-saiga:8000"
                req_data["model"] = "/models/saiga_llama3_8b"
            else:
                self.vllm_url = os.environ.get("VLLM_URL", "http://vllm:8000") or "http://vllm:8000"
                req_data["model"] = "/models/Qwen2.5-14B-Instruct"
            body_str = json.dumps(req_data)

            # Security check: prompt injection + DLP
            messages = req_data.get("messages", [])
            secure, reason = check_security(messages)
            if not secure:
                self._json(403, {"error": "security_violation", "reason": reason})
                return

        except:
            max_tokens = 256
            reserve_amount = 300

        ref = str(uuid.uuid4())[:8]

        # Reserve tokens
        ok, bal, err = billing_op(org_id, "reserve", reserve_amount, ref)
        if not ok:
            self._json(402, {
                "error": "insufficient_balance",
                "detail": err,
                "required": reserve_amount,
                "balance": bal,
            })
            return

        # Proxy to vLLM
        try:
            status, resp_body, ct = self._proxy("POST", self.path, body_str)
        except Exception as e:
            billing_op(org_id, "refund", reserve_amount, ref)
            self._json(502, {"error": "vllm_error", "detail": str(e)})
            return

        # Count actual tokens
        actual_tokens = reserve_amount  # fallback
        try:
            resp_data = json.loads(resp_body.decode())
            if "usage" in resp_data:
                actual_tokens = resp_data["usage"].get("total_tokens", reserve_amount)
        except:
            pass

        if status == 200:
            # Cap settle at reserved amount (actual can exceed estimate)
            settle_amount = min(actual_tokens, reserve_amount)
            billing_op(org_id, "settle", settle_amount, ref)
            # Insert usage record to PostgreSQL
            try:
                conn = db_pool.getconn()
                try:
                    with conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                "INSERT INTO usage_records"
                                " (org_id, request_id, model, input_tokens, output_tokens, total_tokens, status, latency_ms)"
                                " VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                                (org_id, ref, req_data.get("model","?"),
                                 resp_data.get("usage",{}).get("prompt_tokens",0),
                                 resp_data.get("usage",{}).get("completion_tokens",0),
                                 actual_tokens, "success", None))
                finally:
                    db_pool.putconn(conn)
            except Exception as e:
                print(f"Usage record error: {e}", flush=True)
            # Track daily usage in Redis
            today = time.strftime("%Y-%m-%d")
            r.incr(f"usage:{org_id}:{today}")
            r.incrby(f"usage:tk:{org_id}:{today}", actual_tokens)
            r.expire(f"usage:{org_id}:{today}", 86400 * 2)
            r.expire(f"usage:tk:{org_id}:{today}", 86400 * 2)
        else:
            billing_op(org_id, "refund", reserve_amount, ref)
            # Insert error usage record
            try:
                conn = db_pool.getconn()
                try:
                    with conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                "INSERT INTO usage_records"
                                " (org_id, request_id, model, input_tokens, output_tokens, total_tokens, status, latency_ms)"
                                " VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                                (org_id, ref, req_data.get("model","?"), 0, 0, 0, "error", None))
                finally:
                    db_pool.putconn(conn)
            except Exception as e:
                print(f"Usage record error: {e}", flush=True)

        self.send_response(status)
        self.send_header("Content-Type", ct)
        self.end_headers()
        self.wfile.write(resp_body)

    def log_message(self, format, *args):
        pass


# ── Reservation Reaper (background) ────────────────────────────────────

REAP_INTERVAL = int(os.environ.get("REAP_INTERVAL", "60"))
STUCK_THRESHOLD = int(os.environ.get("STUCK_THRESHOLD", "300"))


def reap_stuck():
    """Find and refund stuck reservations."""
    conn = db_pool.getconn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT r.id, r.org_id, r.reference, r.amount, r.created_at
                    FROM billing_ledger r
                    LEFT JOIN billing_ledger s
                        ON s.reference = r.reference AND s.operation = 'settle'
                    LEFT JOIN billing_ledger f
                        ON f.reference = r.reference AND f.operation = 'refund'
                    WHERE r.operation = 'reserve'
                      AND s.id IS NULL
                      AND f.id IS NULL
                      AND r.created_at < now() - interval '%s seconds'
                    ORDER BY r.created_at
                """ % STUCK_THRESHOLD)
                stuck = cur.fetchall()
                if not stuck:
                    return 0
                refunded = 0
                for (lid, org_id, ref, amount, created_at) in stuck:
                    # Release reserved tokens
                    cur.execute(
                        """UPDATE billing_accounts
                           SET reserved = reserved - %s, updated_at = now()
                           WHERE org_id = %s AND reserved >= %s
                           RETURNING balance""",
                        (amount, org_id, amount))
                    row = cur.fetchone()
                    if not row:
                        continue  # reserved < amount, skip
                    new_balance = row[0]
                    # Record refund with correct amount and balance
                    cur.execute(
                        """INSERT INTO billing_ledger
                           (org_id, amount, operation, reference, balance_after)
                           VALUES (%s, %s, 'refund', %s, %s)""",
                        (org_id, amount, ref, new_balance))
                    refunded += 1
                return refunded
    except Exception as e:
        conn.rollback()
        print(f"[Reaper] Error: {e}", flush=True)
        return -1
    finally:
        db_pool.putconn(conn)


def reaper_loop():
    while True:
        time.sleep(REAP_INTERVAL)
        try:
            count = reap_stuck()
            if count > 0:
                print(f"[Reaper] Refunded {count} stuck reservation(s)", flush=True)
        except Exception as e:
            print(f"[Reaper] Loop error: {e}", flush=True)


if __name__ == "__main__":
    print(f"[Reaper] Starting (interval={REAP_INTERVAL}s, threshold={STUCK_THRESHOLD}s)", flush=True)
    threading.Thread(target=reaper_loop, daemon=True).start()
    port = int(os.environ.get("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), Gateway)
    print(f"Gateway listening on :{port}", flush=True)
    server.serve_forever()
