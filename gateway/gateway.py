"""Aither API Gateway — proxy to vLLM with JWT RS256, Redis rate limiting, and billing."""
import os, json, time, uuid, traceback, threading, hashlib
from urllib.request import Request, urlopen
from http.server import HTTPServer, BaseHTTPRequestHandler
import redis
import jwt as pyjwt
import psycopg2
import psycopg2.pool
from security import check_security
from security_egress import check_egress
from vault import vault_validate_key
from hybrid_rag import hybrid_query, wiki_ingest, wiki_status
from wiki_graph import get_wiki_graph
from admin import (
    admin_queues, admin_models, admin_drain, admin_undrain,
    admin_health, admin_org_detail, admin_reaper, is_model_drained,
)
from metrics import metrics, metrics_summary

VLLM_URL = os.environ.get("VLLM_URL", "http://vllm:8000")
REDIS_URL = os.environ.get("REDIS_URL", "redis")
RATE_LIMIT_RPM = int(os.environ.get("RATE_LIMIT_RPM", "300"))
RATE_LIMIT_TPM = int(os.environ.get("RATE_LIMIT_TPM", "100000"))
PG_URL = os.environ.get("PG_URL", "postgresql://aither@postgres:5432/aither")
TOKEN_COST = int(os.environ.get("TOKEN_COST", "1"))  # tokens to reserve per request token

r = redis.Redis(host=REDIS_URL, port=6379, decode_responses=True, socket_connect_timeout=2)
db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, PG_URL)

# ── Tier-based rate limiting ──

def _get_org_tier(org_id: str) -> str:
    """Get organisation's tier, cached in Redis (60s)."""
    tier = r.get(f"org_tier:{org_id}")
    if tier:
        return tier
    tier = "free"
    try:
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT tier FROM billing_accounts WHERE org_id = %s", (org_id,))
                row = cur.fetchone()
                if row:
                    tier = row[0]
        finally:
            db_pool.putconn(conn)
    except:
        pass
    r.set(f"org_tier:{org_id}", tier, ex=60)
    return tier


def _get_tier_limits(tier_id: str) -> dict:
    """Get tier limits from Redis cache or PostgreSQL."""
    cached = r.hgetall(f"tier:{tier_id}")
    if cached:
        return {
            "rpm": int(cached.get("rpm", RATE_LIMIT_RPM)),
            "tpm": int(cached.get("tpm", RATE_LIMIT_TPM)),
            "daily": int(cached["daily"]) if cached.get("daily") else None,
            "models": cached.get("models", "").split(",") if cached.get("models") else [],
            "rag": cached.get("rag") == "1",
        }
    # Cache miss: query PostgreSQL
    limits = {"rpm": RATE_LIMIT_RPM, "tpm": RATE_LIMIT_TPM, "daily": None, "models": [], "rag": False}
    try:
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT rpm_limit, tpm_limit, daily_request_limit, models, rag_enabled "
                    "FROM subscription_tiers WHERE tier_id = %s", (tier_id,))
                row = cur.fetchone()
                if row:
                    limits = {"rpm": row[0], "tpm": row[1], "daily": row[2],
                              "models": row[3] if row[3] else [], "rag": row[4]}
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        print(f"Tier lookup failed: {e}", flush=True)
    # Cache in Redis (60s)
    try:
        r.hset(f"tier:{tier_id}", mapping={
            "rpm": str(limits["rpm"]), "tpm": str(limits["tpm"]),
            "daily": str(limits["daily"] or ""),
            "models": ",".join(limits["models"]),
            "rag": "1" if limits["rag"] else "0",
        })
        r.expire(f"tier:{tier_id}", 60)
    except:
        pass
    return limits
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


CHROMA_URL = os.environ.get("CHROMA_URL", "http://chromadb:8000")
_rag_chroma = None
_rag_ef = None

def _get_ef():
    global _rag_ef
    if _rag_ef is None:
        from chromadb.utils import embedding_functions
        _rag_ef = embedding_functions.ONNXMiniLM_L6_V2()
    return _rag_ef

def _get_chroma():
    global _rag_chroma
    if _rag_chroma is None:
        import chromadb
        _rag_chroma = chromadb.HttpClient(host=CHROMA_URL.split("://")[1].split(":")[0],
                                          port=int(CHROMA_URL.split(":")[-1]))
    return _rag_chroma

def rag_ingest(documents: list) -> dict:
    """Ingest documents into ChromaDB. Each doc: {id, text, metadata?}"""
    chroma = _get_chroma()
    ef = _get_ef()
    coll = chroma.get_or_create_collection("documents")
    ids, texts, metadatas = [], [], []
    for doc in documents:
        ids.append(doc.get("id", str(uuid.uuid4())[:8]))
        texts.append(doc["text"])
        metadatas.append(doc.get("metadata", {"source": "unknown"}))
    embeddings = ef(texts)
    coll.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    return {"ingested": len(documents), "ids": ids}

def rag_query(query: str, top_k: int = 5) -> list:
    """Query ChromaDB for relevant documents."""
    chroma = _get_chroma()
    ef = _get_ef()
    coll = chroma.get_or_create_collection("documents")
    count = coll.count()
    if count == 0:
        return []
    q_embedding = ef(["query: " + query])
    results = coll.query(query_embeddings=q_embedding, n_results=min(top_k, count))
    return [{"id": id_, "text": doc, "metadata": meta,
             "score": round(1 - float(dist), 4) if dist is not None else 0}
            for id_, doc, meta, dist in zip(
                results["ids"][0], results["documents"][0],
                results["metadatas"][0] if results["metadatas"] else [{}]*len(results["ids"][0]),
                results.get("distances", [[1]]*len(results["ids"][0]))[0])]


class Gateway(BaseHTTPRequestHandler):
    vllm_url = VLLM_URL  # default, overridden per-request by model routing

    def _check_jwt(self):
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        token = auth[7:]
                # ── API Key auth (ak-...) ──────────────────────────────
        if token.startswith("ak-"):
            # 🆕 Try Vault first (corporate key management)
            vault_result = vault_validate_key(token, redis_module=redis)
            if vault_result.get("valid"):
                return {
                    "org_id": vault_result["org_id"],
                    "user_id": vault_result.get("user_id", ""),
                    "api_key": True,
                    "key_name": vault_result.get("key_name", "vault"),
                    "vault_policies": vault_result.get("policies", {}),
                }

            # Fallback: local PostgreSQL (for non-Vault keys / dev mode)
            conn = db_pool.getconn()
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT org_id, user_id, name FROM portal_api_keys"
                            " WHERE api_key=%s AND status='active'"
                            " AND (expires_at IS NULL OR expires_at > now())",
                            (token,))
                        row = cur.fetchone()
                        if row:
                            cur.execute(
                                "UPDATE portal_api_keys SET last_used_at=now() WHERE api_key=%s",
                                (token,))
                            return {"org_id": str(row[0]), "user_id": str(row[1]),
                                    "api_key": True, "key_name": row[2]}
            except Exception as e:
                print(f"[API Key] lookup error: {e}", flush=True)
            finally:
                db_pool.putconn(conn)
            return None

        # ── JWT RS256 auth ─────────────────────────────────────
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

    ADMIN_KEY = os.environ.get("ADMIN_KEY", "")

    def _check_admin(self):
        """Check admin access via API key or JWT. Returns True if authorized."""
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
            # Admin API key from env
            if self.ADMIN_KEY and token == self.ADMIN_KEY:
                return True
            # JWT with admin role (HS256 — no cryptography needed)
            try:
                jwt_secret = os.environ.get("JWT_SECRET", os.environ.get("ADMIN_SECRET", "aither-admin-secret"))
                payload = pyjwt.decode(token, jwt_secret, algorithms=["HS256"],
                                      options={"verify_exp": True, "verify_iss": False})
                if payload.get("role") == "admin":
                    return True
            except Exception as e:
                print(f"[admin] JWT decode failed: {e}", flush=True)
        self._json(403, {"error": "admin access required"})
        return False

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"status": "ok", "billing": "enabled"})
            return
        if self.path == "/metrics":
            body = metrics.prometheus_text()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            self.wfile.write(body.encode())
            return
        # ── Admin Management API ─────────────────────────────────
        if self.path == "/admin/queues":
            if not self._check_admin(): return
            try:
                data = admin_queues(r)
                self._json(200, data)
            except Exception as e:
                self._json(500, {"error": str(e)})
            return
        if self.path == "/admin/models":
            if not self._check_admin(): return
            try:
                from catalog import _registry
                models = admin_models(_registry, r)
                self._json(200, {"models": models})
            except Exception as e:
                self._json(500, {"error": str(e)})
            return
        if self.path == "/admin/health":
            if not self._check_admin(): return
            try:
                from catalog import _registry
                data = admin_health(db_pool, r, _registry)
                self._json(200, data)
            except Exception as e:
                self._json(500, {"error": str(e)})
            return
        if self.path == "/admin/reaper":
            if not self._check_admin(): return
            try:
                data = admin_reaper(r)
                self._json(200, data)
            except Exception as e:
                self._json(500, {"error": str(e)})
            return
        if self.path == "/admin/metrics":
            if not self._check_admin(): return
            try:
                data = metrics_summary()
                self._json(200, data)
            except Exception as e:
                self._json(500, {"error": str(e)})
            return
        if self.path.startswith("/admin/orgs/"):
            if not self._check_admin(): return
            org_id = self.path.split("/admin/orgs/")[1].split("?")[0]
            try:
                data = admin_org_detail(org_id, db_pool, r)
                self._json(200, data)
            except Exception as e:
                self._json(500, {"error": str(e)})
            return
        # ─────────────────────────────────────────────────────────
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

        # ── Admin drain/undrain ─────────────────────────────────
        if self.path.startswith("/admin/models/") and self.path.endswith("/drain"):
            model_name = self.path.split("/admin/models/")[1].split("/drain")[0]
            if not self._check_admin(): return
            try:
                data = admin_drain(model_name, r)
                self._json(200, data)
            except Exception as e:
                self._json(500, {"error": str(e)})
            return
        if self.path.startswith("/admin/models/") and self.path.endswith("/undrain"):
            model_name = self.path.split("/admin/models/")[1].split("/undrain")[0]
            if not self._check_admin(): return
            try:
                data = admin_undrain(model_name, r)
                self._json(200, data)
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        if not self.path.startswith("/v1/"):
            self._json(404, {"error": "not found"})
            return

        # ── RAG endpoints ─────────────────────────────────────
        if self.path == "/v1/rag/ingest":
            payload = self._check_jwt()
            if payload is None:
                self._json(401, {"error": "valid token required"})
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                body_str = self.rfile.read(length).decode() if length else "{}"
                req_data = json.loads(body_str)
                docs = req_data.get("documents", [])
                if not docs:
                    self._json(400, {"error": "documents array required"})
                    return
                result = rag_ingest(docs)
                self._json(200, result)
            except Exception as e:
                self._json(500, {"error": "ingest_failed", "detail": str(e)})
            return

        if self.path == "/v1/rag/query":
            payload = self._check_jwt()
            if payload is None:
                self._json(401, {"error": "valid token required"})
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                body_str = self.rfile.read(length).decode() if length else "{}"
                req_data = json.loads(body_str)
                query = req_data.get("query", "")
                top_k = req_data.get("top_k", 5)
                if not query:
                    self._json(400, {"error": "query required"})
                    return
                # Tier check: RAG access
                _payload = self._check_jwt()
                if _payload and _payload != "expired":
                    _oid = _payload.get("org_id", "unknown")
                    _tier = _get_org_tier(_oid)
                    _limits = _get_tier_limits(_tier)
                    if not _limits["rag"]:
                        self._json(403, {"error": "rag_not_available", "tier": _tier})
                        return
                results = rag_query(query, top_k)
                self._json(200, {"query": query, "results": results})
            except Exception as e:
                self._json(500, {"error": "query_failed", "detail": str(e)})
            return

        # ── Hybrid RAG endpoints ──────────────────────────────
        if self.path == "/v1/rag/hybrid-query":
            payload = self._check_jwt()
            if payload is None:
                self._json(401, {"error": "valid token required"})
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                body_str = self.rfile.read(length).decode() if length else "{}"
                req_data = json.loads(body_str)
                query = req_data.get("query", "")
                top_k = req_data.get("top_k", 5)
                wiki_radius = req_data.get("wiki_radius", 1)
                if not query:
                    self._json(400, {"error": "query required"})
                    return
                _oid = payload.get("org_id", "unknown")
                _tier = _get_org_tier(_oid)
                _limits = _get_tier_limits(_tier)
                if not _limits["rag"]:
                    self._json(403, {"error": "rag_not_available", "tier": _tier})
                    return
                results = hybrid_query(query, top_k=top_k, wiki_radius=wiki_radius)
                self._json(200, {"query": query, "results": results, "mode": "hybrid"})
            except Exception as e:
                traceback.print_exc()
                self._json(500, {"error": "hybrid_query_failed", "detail": str(e)})
            return

        if self.path == "/v1/rag/wiki-ingest":
            payload = self._check_jwt()
            if payload is None:
                self._json(401, {"error": "valid token required"})
                return
            try:
                result = wiki_ingest()
                self._json(200, result)
            except Exception as e:
                traceback.print_exc()
                self._json(500, {"error": "wiki_ingest_failed", "detail": str(e)})
            return

        if self.path == "/v1/rag/status":
            payload = self._check_jwt()
            if payload is None:
                self._json(401, {"error": "valid token required"})
                return
            try:
                status = wiki_status()
                self._json(200, status)
            except Exception as e:
                self._json(500, {"error": "status_failed", "detail": str(e)})
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

        # --- Tier-based rate limiting + model access + RAG access ---
        tier = _get_org_tier(org_id)
        limits = _get_tier_limits(tier)
        now = int(time.time())
        window = now // 60
        body_len = int(self.headers.get("Content-Length", 0))
        token_est = max(body_len // 4, 100)
        try:
            rpm = r.incr(f"rl:{org_id}:rpm:{window}")
            if rpm == 1: r.expire(f"rl:{org_id}:rpm:{window}", 120)
            tpm = r.incrby(f"rl:{org_id}:tpm:{window}", token_est)
            if tpm <= token_est: r.expire(f"rl:{org_id}:tpm:{window}", 120)
            if rpm > limits["rpm"] or tpm > limits["tpm"]:
                self._json(429, {"error": "rate_limit_exceeded", "tier": tier, "rpm": rpm, "tpm": tpm,
                    "rpm_limit": limits["rpm"], "tpm_limit": limits["tpm"]})
                return
            # Daily request limit
            if limits["daily"]:
                today = time.strftime("%Y-%m-%d")
                daily = r.incr(f"rl:{org_id}:daily:{today}")
                if daily == 1: r.expire(f"rl:{org_id}:daily:{today}", 86400 * 2)
                if daily > limits["daily"]:
                    self._json(429, {"error": "daily_limit_exceeded", "tier": tier,
                        "daily": daily, "daily_limit": limits["daily"]})
                    return
        except Exception as e:
            pass  # Redis down: let request through

        # Read body
        length = int(self.headers.get("Content-Length", 0))
        body_str = self.rfile.read(length).decode() if length else "{}"

        # Parse request to estimate tokens
        req_data = {}
        try:
            req_data = json.loads(body_str)
            max_tokens = req_data.get("max_tokens", 256)
            input_tokens = len(req_data.get("messages", [])) * 20  # rough estimate
            reserve_amount = (max_tokens + input_tokens) * TOKEN_COST
            # Multi-model routing with cost-aware selection
            from routing import select_model, check_fallback
            messages = req_data.get("messages", [])
            explicit_model = req_data.get("model", None)
            # If user passed an explicit model_id (not vLLM path), use it for routing
            if explicit_model and "/models/" not in explicit_model:
                model_id, vllm_url, model_path, reason = select_model(messages, explicit_model)
            else:
                model_id, vllm_url, model_path, reason = select_model(messages)
            # Apply routing
            self.vllm_url = check_fallback(vllm_url)
            req_data["model"] = model_path
            body_str = json.dumps(req_data)
            print(f"[Route] {reason} → {self.vllm_url}{req_data['model']} (chars={sum(len(m.get('content','')) for m in messages)})", flush=True)

            # Tier check: model access
            if limits["models"]:
                if model_id not in limits["models"] and f"qwen2.5-{model_id}" not in [m.split("/")[-1] for m in limits["models"]]:
                    allowed_list = ", ".join(limits["models"])
                    self._json(403, {"error": "model_not_available", "tier": tier,
                        "requested": model_id, "allowed": limits["models"]})
                    return

            # Drain check (admin-controlled model availability)
            if is_model_drained(model_id, r):
                metrics.incr_drain_block(model_id)
                self._json(503, {"error": "model_drained", "model": model_id,
                    "detail": "Модель временно недоступна. Попробуйте другую модель."})
                return

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
            metrics.incr_billing_error(org_id, err[:50] if err else "unknown")
            self._json(402, {
                "error": "insufficient_balance",
                "detail": err,
                "required": reserve_amount,
                "balance": bal,
            })
            return

        metrics.incr_active()

        # Proxy to vLLM (measure TTFT)
        ttft_start = time.time()
        try:
            status, resp_body, ct = self._proxy("POST", self.path, body_str)
        except Exception as e:
            metrics.decr_active()
            metrics.incr_request(model_id, org_id, "error")
            billing_op(org_id, "refund", reserve_amount, ref)
            self._json(502, {"error": "vllm_error", "detail": str(e)})
            return
        ttft_seconds = time.time() - ttft_start
        metrics.decr_active()

        # Record TTFT
        metrics.observe_ttft(model_id, ttft_seconds)

        # Count actual tokens
        actual_tokens = reserve_amount  # fallback
        resp_data = {}
        try:
            resp_data = json.loads(resp_body.decode())
            if "usage" in resp_data:
                actual_tokens = resp_data["usage"].get("total_tokens", reserve_amount)
        except:
            pass

        # ── EGRESS Security Check (DSP/PII/System Leak) ──────────────
        request_hash = hashlib.sha256(body_str.encode()).hexdigest()[:16] if body_str else ""
        egress_ok, egress_reason, egress_audit = check_egress(
            resp_data,
            org_id=str(org_id),
            request_id=ref,
            model=req_data.get("model", "unknown"),
            request_hash=request_hash,
            db_pool=db_pool,
        )
        if not egress_ok:
            # Block response, refund, log incident
            billing_op(org_id, "refund", reserve_amount, ref)
            # Insert blocked usage record
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
                                 0, 0, 0, "blocked_egress", None))
                finally:
                    db_pool.putconn(conn)
            except Exception as e:
                print(f"Usage record error: {e}", flush=True)
            self._json(403, {
                "error": "content_filtered",
                "reason": "Ответ содержит информацию ограниченного распространения и был отфильтрован",
                "code": egress_reason,
            })
            return

        if status == 200:
            # Cap settle at reserved amount (actual can exceed estimate)
            settle_amount = min(actual_tokens, reserve_amount)
            billing_op(org_id, "settle", settle_amount, ref)
            # Track metrics
            metrics.incr_request(model_id, org_id, "success")
            metrics.incr_tokens(model_id, org_id, "total", actual_tokens)
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
            metrics.incr_request(model_id, org_id, "error")
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
            # Track in Redis for admin API
            try:
                r.set("admin:reaper:last_run", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
                if count >= 0:
                    r.set("admin:reaper:last_refunded", str(count))
            except:
                pass
        except Exception as e:
            print(f"[Reaper] Loop error: {e}", flush=True)


if __name__ == "__main__":
    print(f"[Reaper] Starting (interval={REAP_INTERVAL}s, threshold={STUCK_THRESHOLD}s)", flush=True)
    threading.Thread(target=reaper_loop, daemon=True).start()
    # Pre-load ONNX embedding model at startup (avoids blocking first RAG request)
    print("[Init] Pre-loading ONNX embedding model...", flush=True)
    try:
        ef = _get_ef()
        _ = ef(["warmup"])
        print("[Init] ONNX embedding model ready", flush=True)
    except Exception as e:
        print(f"[Init] ONNX warmup failed (will retry on first request): {e}", flush=True)
    # Pre-load wiki graph at startup
    print("[Init] Loading wiki graph...", flush=True)
    try:
        wg = get_wiki_graph()
        print(f"[Init] Wiki graph loaded: {wg.page_count} pages", flush=True)
    except Exception as e:
        print(f"[Init] Wiki graph load failed (will retry on first request): {e}", flush=True)
    port = int(os.environ.get("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), Gateway)
    print(f"Gateway listening on :{port}", flush=True)
    server.serve_forever()
