"""Aither API Gateway — proxy to vLLM with JWT RS256, Redis rate limiting, and billing."""
import os, json, time, uuid, traceback
from urllib.request import Request, urlopen
from http.server import HTTPServer, BaseHTTPRequestHandler
import redis
import jwt as pyjwt
import psycopg2
import psycopg2.pool

VLLM_URL = os.environ.get("VLLM_URL", "http://vllm:8000")
REDIS_URL = os.environ.get("REDIS_URL", "redis")
RATE_LIMIT = int(os.environ.get("RATE_LIMIT", "60"))
PG_URL = os.environ.get("PG_URL", "postgresql://aither@postgres:5432/aither")
TOKEN_COST = int(os.environ.get("TOKEN_COST", "1"))  # tokens to reserve per request token

r = redis.Redis(host=REDIS_URL, port=6379, decode_responses=True, socket_connect_timeout=2)
db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, PG_URL)

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
        url = f"{VLLM_URL}{path}"
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

        # Rate limit
        now = int(time.time())
        window = now // 60
        count = r.incr(f"ratelimit:{org_id}:{window}")
        if count == 1:
            r.expire(f"ratelimit:{org_id}:{window}", 120)
        if count > RATE_LIMIT:
            self._json(429, {"error": "rate limit exceeded"})
            return

        # Read body
        length = int(self.headers.get("Content-Length", 0))
        body_str = self.rfile.read(length).decode() if length else "{}"

        # Parse request to estimate tokens
        try:
            req_data = json.loads(body_str)
            max_tokens = req_data.get("max_tokens", 256)
            input_tokens = len(req_data.get("messages", [])) * 20  # rough estimate
            reserve_amount = (max_tokens + input_tokens) * TOKEN_COST
            req_data["model"] = "/models/Qwen2.5-14B-Instruct"
            body_str = json.dumps(req_data)
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
            billing_op(org_id, "settle", actual_tokens, ref)
            # Track daily usage in Redis
            today = time.strftime("%Y-%m-%d")
            r.incr(f"usage:{org_id}:{today}")
            r.expire(f"usage:{org_id}:{today}", 86400 * 2)
        else:
            billing_op(org_id, "refund", reserve_amount, ref)

        self.send_response(status)
        self.send_header("Content-Type", ct)
        self.end_headers()
        self.wfile.write(resp_body)

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), Gateway)
    print(f"Gateway listening on :{port}", flush=True)
    server.serve_forever()
