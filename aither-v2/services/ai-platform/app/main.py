# Aither AI Platform Service
#
# Environment variables:
#   AI_PLATFORM_DB_PATH       — SQLite path (default: /data/ai-platform.db)
#   AI_PLATFORM_IDENTITY_URL  — Identity service URL (default: http://aither-identity:8000)
#   AI_PLATFORM_GATEWAY_URL   — Gateway URL (default: http://nginx-gateway-32b.aither-inference.svc:8000)
#   AI_PLATFORM_LOG_LEVEL     — logging level (default: INFO)
#   AI_PLATFORM_CORS_ORIGIN   — CORS origin (default: *)
#   AI_PLATFORM_ENCRYPTION_KEY— for internal use (default: auto-generated from identity check)
#
# API:
#   Models:       GET/POST /api/v1/models, GET/PATCH/DELETE /api/v1/models/{id}
#   API Keys:     GET/POST /api/v1/api-keys, DELETE /api/v1/api-keys/{id}
#   Assistants:   GET/POST /api/v1/assistants, GET/PATCH/DELETE /api/v1/assistants/{id}
#   Conversations:GET/POST /api/v1/conversations, GET/DELETE /api/v1/conversations/{id}
#   Messages:     POST /api/v1/conversations/{id}/messages
#   AI:           POST /v1/chat/completions

import os
import json
import logging
import sqlite3
import secrets
import time
import hashlib
import hmac
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional
from urllib.parse import urljoin

import httpx
import prometheus_client
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, HTTPException, Depends, Request, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

# ── Configuration ──────────────────────────────────────────────

DB_PATH = os.environ.get("AI_PLATFORM_DB_PATH", "/data/ai-platform.db")
IDENTITY_URL = os.environ.get("AI_PLATFORM_IDENTITY_URL", "http://aither-identity:8000")
GATEWAY_URL = os.environ.get("AI_PLATFORM_GATEWAY_URL", "http://nginx-gateway-32b.aither-inference.svc:8000")
GATEWAY_API_KEY = os.environ.get("AI_PLATFORM_GATEWAY_API_KEY", "")
VLLM_14B_URL = os.environ.get("AI_PLATFORM_14B_URL", "http://vllm-14b-instruct.aither-inference.svc:8000")
VLLM_API_KEY = os.environ.get("VLLM_API_KEY", "")
LOG_LEVEL = os.environ.get("AI_PLATFORM_LOG_LEVEL", "INFO").upper()
CORS_ORIGIN = os.environ.get("AI_PLATFORM_CORS_ORIGIN", "http://localhost:3000")
# In production, set AI_PLATFORM_CORS_ORIGIN to the Portal Frontend URL.
# Example: AI_PLATFORM_CORS_ORIGIN=https://portal.aither.example.com

class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter."""
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "aither-ai-platform",
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "endpoint"):
            log_entry["endpoint"] = record.endpoint
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        if hasattr(record, "status_code"):
            log_entry["status_code"] = record.status_code
        return json.dumps(log_entry, default=str)

logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
log = logging.getLogger("aither-ai-platform")
log.propagate = False
_handler = logging.StreamHandler()
_handler.setFormatter(JSONFormatter())
log.addHandler(_handler)

# ── HTTP Client ────────────────────────────────────────────────

identity_client: httpx.AsyncClient | None = None
gateway_client: httpx.AsyncClient | None = None

async def get_identity_client() -> httpx.AsyncClient:
    global identity_client
    if identity_client is None:
        identity_client = httpx.AsyncClient(base_url=IDENTITY_URL, timeout=10.0)
    return identity_client

async def get_gateway_client() -> httpx.AsyncClient:
    global gateway_client
    if gateway_client is None:
        headers = {}
        if GATEWAY_API_KEY:
            headers["Authorization"] = f"Bearer {GATEWAY_API_KEY}"
        gateway_client = httpx.AsyncClient(base_url=GATEWAY_URL, timeout=300.0, headers=headers)
    return gateway_client

# ── Database ───────────────────────────────────────────────────

def get_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)  # 10s busy timeout
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

def retry_on_lock(max_retries=5, delay=0.5):
    """Decorator to retry SQLite operations on 'database is locked'."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e) and attempt < max_retries - 1:
                        last_exc = e
                        time.sleep(delay * (attempt + 1))  # Linear backoff
                        continue
                    raise
            raise last_exc  # type: ignore[misc]
        return wrapper
    return decorator

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS models (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT UNIQUE NOT NULL,
            display_name    TEXT NOT NULL,
            provider        TEXT NOT NULL DEFAULT 'local',
            endpoint        TEXT,
            model_identifier TEXT NOT NULL,
            description     TEXT DEFAULT '',
            context_window  INTEGER DEFAULT 4096,
            enabled         INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS api_keys (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            name            TEXT NOT NULL,
            key_prefix      TEXT NOT NULL,
            key_hash        TEXT NOT NULL,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            last_used_at    TEXT,
            expires_at      TEXT,
            revoked_at      TEXT
        );

        CREATE TABLE IF NOT EXISTS assistants (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id   INTEGER NOT NULL,
            name            TEXT NOT NULL,
            description     TEXT DEFAULT '',
            model_id        INTEGER NOT NULL,
            system_prompt   TEXT DEFAULT '',
            temperature     REAL DEFAULT 0.7,
            max_tokens      INTEGER DEFAULT 2048,
            enabled         INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (model_id) REFERENCES models(id)
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id   INTEGER NOT NULL,
            assistant_id    INTEGER,
            title           TEXT DEFAULT '',
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (assistant_id) REFERENCES assistants(id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role            TEXT NOT NULL CHECK(role IN ('system','user','assistant')),
            content         TEXT NOT NULL,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
        CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);
        CREATE INDEX IF NOT EXISTS idx_assistants_owner ON assistants(owner_user_id);
        CREATE INDEX IF NOT EXISTS idx_conversations_owner ON conversations(owner_user_id);
        CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
    """)
    conn.commit()
    conn.close()

# ── Models ─────────────────────────────────────────────────────

class ModelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=256)
    provider: str = Field(default="local", pattern=r"^(local|openai-compatible)$")
    endpoint: Optional[str] = None
    model_identifier: str = Field(..., min_length=1, max_length=256)
    description: str = Field(default="", max_length=2000)
    context_window: int = Field(default=4096, ge=256, le=131072)
    enabled: bool = True

class ModelUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=256)
    provider: Optional[str] = Field(None, pattern=r"^(local|openai-compatible)$")
    endpoint: Optional[str] = None
    model_identifier: Optional[str] = Field(None, min_length=1, max_length=256)
    description: Optional[str] = Field(None, max_length=2000)
    context_window: Optional[int] = Field(None, ge=256, le=131072)
    enabled: Optional[bool] = None

class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)

class APIKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    created_at: str
    last_used_at: Optional[str]
    expires_at: Optional[str]
    revoked_at: Optional[str]

class APIKeyFullResponse(APIKeyResponse):
    full_key: str

class AssistantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: str = Field(default="", max_length=2000)
    model_id: int = Field(..., ge=1)
    system_prompt: str = Field(default="", max_length=32000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=131072)

class AssistantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=256)
    description: Optional[str] = Field(None, max_length=2000)
    model_id: Optional[int] = Field(None, ge=1)
    system_prompt: Optional[str] = Field(None, max_length=32000)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=131072)
    enabled: Optional[bool] = None

class ConversationCreate(BaseModel):
    assistant_id: Optional[int] = None
    title: str = Field(default="", max_length=512)

class MessageSend(BaseModel):
    content: str = Field(..., min_length=1, max_length=64000)

class ChatCompletionRequest(BaseModel):
    model: str = Field(..., min_length=1)
    messages: list = Field(..., min_length=1)
    stream: bool = False
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=131072)

# ── Auth Helpers ───────────────────────────────────────────────

async def verify_token(token: str) -> dict:
    """Verify a bearer token against Identity service."""
    c = await get_identity_client()
    r = await c.get("/v1/identity/me", headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        METRIC_ERRORS_TOTAL.labels(type="auth_failure").inc()
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return r.json()

async def get_current_user(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        METRIC_ERRORS_TOTAL.labels(type="auth_missing").inc()
        raise HTTPException(status_code=401, detail="Authentication required")
    return await verify_token(auth[7:])

async def require_admin(user: dict = Depends(get_current_user)):
    if user.get("role") != "administrator":
        METRIC_ERRORS_TOTAL.labels(type="auth_forbidden").inc()
        raise HTTPException(status_code=403, detail="Administrator role required")
    return user

async def get_user_from_api_key(request: Request) -> Optional[dict]:
    """Try to authenticate via API Key first, fall back to Bearer token."""
    # Check API Key in Authorization header (Bearer <key>) or X-API-Key header
    auth = request.headers.get("Authorization", "")
    x_api_key = request.headers.get("X-API-Key", "")

    key_value = ""
    if auth.startswith("Bearer "):
        key_value = auth[7:]
    elif x_api_key:
        key_value = x_api_key

    if key_value and key_value.startswith("aither_"):
        return await authenticate_api_key(key_value)

    # Fall back to Bearer token auth
    return await get_current_user(request)

async def authenticate_api_key(full_key: str) -> dict:
    """Validate an API Key and return user info."""
    # Parse prefix and secret
    parts = full_key.split("_", 2)
    if len(parts) < 3:
        METRIC_ERRORS_TOTAL.labels(type="invalid_api_key_format").inc()
        raise HTTPException(status_code=401, detail="Invalid API Key format")
    prefix = f"{parts[0]}_{parts[1]}"

    key_hash = hashlib.sha256(full_key.encode()).hexdigest()

    conn = get_db()
    row = conn.execute(
        "SELECT id, user_id, revoked_at, expires_at FROM api_keys WHERE key_prefix=? AND key_hash=?",
        (prefix, key_hash),
    ).fetchone()
    conn.close()

    if row is None:
        METRIC_ERRORS_TOTAL.labels(type="invalid_api_key").inc()
        raise HTTPException(status_code=401, detail="Invalid API Key")

    if row["revoked_at"] is not None:
        METRIC_ERRORS_TOTAL.labels(type="revoked_api_key").inc()
        raise HTTPException(status_code=401, detail="API Key has been revoked")

    if row["expires_at"]:
        exp = datetime.fromisoformat(row["expires_at"])
        if exp < datetime.now(timezone.utc).replace(tzinfo=None):
            METRIC_ERRORS_TOTAL.labels(type="expired_api_key").inc()
            raise HTTPException(status_code=401, detail="API Key has expired")

    # Update last_used_at
    conn = get_db()
    conn.execute(
        "UPDATE api_keys SET last_used_at=datetime('now') WHERE id=?",
        (row["id"],),
    )
    conn.commit()
    conn.close()

    # Verify user is not disabled via Identity
    c = await get_identity_client()
    r = await c.get(f"/v1/identity/users")
    # We don't have a /users/{id} endpoint, so verify at model level
    # Return basic user info from the key
    return {"id": row["user_id"], "username": f"user-{row['user_id']}", "role": "user", "auth_method": "api_key"}

# ── Application ────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Aither AI Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/v1/ai/docs",
    openapi_url="/api/v1/ai/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN] if CORS_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Prometheus Metrics ─────────────────────────────────────────

# System metrics
METRIC_UPTIME = Gauge("uptime", "Service uptime in seconds")
METRIC_MEMORY_USAGE = Gauge("memory_usage_bytes", "Process memory usage in bytes")
METRIC_ACTIVE_REQUESTS = Gauge("active_requests", "Currently in-flight requests")
METRIC_ACTIVE_API_KEYS = Gauge("active_api_keys", "Number of non-revoked API keys")
METRIC_ACTIVE_CONVERSATIONS = Gauge("active_conversations", "Number of conversations")

# Request metrics
METRIC_HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "endpoint", "status_code"],
)
METRIC_HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

# Gateway metrics
METRIC_GATEWAY_REQUESTS = Counter(
    "gateway_requests_total",
    "Gateway proxy requests",
    labelnames=["status"],
)
METRIC_GATEWAY_ERRORS = Counter(
    "gateway_errors_total",
    "Gateway errors by type",
    labelnames=["type"],
)

# General error counter
METRIC_ERRORS_TOTAL = Counter(
    "errors_total",
    "Application errors by type",
    labelnames=["type"],
)

_start_time = time.time()


def _update_periodic_gauges():
    """Update gauges that need periodic refreshing from DB."""
    import os

    # Uptime
    METRIC_UPTIME.set(time.time() - _start_time)

    # Memory usage
    try:
        import os as _os

        with open(f"/proc/{_os.getpid()}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    # Value is in kB
                    parts = line.split()
                    if len(parts) >= 2:
                        METRIC_MEMORY_USAGE.set(int(parts[1]) * 1024)
                    break
    except Exception:
        METRIC_MEMORY_USAGE.set(0)

    # DB counters — best-effort, run in thread pool
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM api_keys WHERE revoked_at IS NULL"
        ).fetchone()
        METRIC_ACTIVE_API_KEYS.set(row["cnt"] if row else 0)

        row = conn.execute("SELECT COUNT(*) as cnt FROM conversations").fetchone()
        METRIC_ACTIVE_CONVERSATIONS.set(row["cnt"] if row else 0)
        conn.close()
    except Exception:
        pass


@app.on_event("startup")
async def start_periodic_metrics():
    """Schedule periodic metric updates every 15 seconds."""
    import asyncio

    async def _loop():
        while True:
            try:
                await asyncio.to_thread(_update_periodic_gauges)
            except Exception:
                pass
            await asyncio.sleep(15)

    asyncio.create_task(_loop())


async def metrics_middleware(request: Request, call_next):
    """Middleware that instruments request metrics."""
    import time as _time

    # Track active requests
    METRIC_ACTIVE_REQUESTS.inc()

    start = _time.monotonic()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration = _time.monotonic() - start

        # Build endpoint label — collapse path params to pattern
        endpoint = request.url.path

        METRIC_HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=response.status_code if response is not None else 500,
        ).inc()
        METRIC_HTTP_REQUEST_DURATION.labels(
            method=request.method, endpoint=endpoint
        ).observe(duration)
        METRIC_ACTIVE_REQUESTS.dec()


app.middleware("http")(metrics_middleware)


@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint."""
    # Refresh gauges before serving
    import asyncio
    await asyncio.to_thread(_update_periodic_gauges)

    # Use simple Response to avoid middleware overhead on metrics scrape
    data = generate_latest()
    from fastapi.responses import Response

    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


# ── Health ─────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "ai-platform"}

@app.get("/ready")
async def ready():
    deps = {}
    all_ok = True

    # Database
    try:
        conn = get_db()
        conn.execute("SELECT 1")
        conn.close()
        deps["database"] = "connected"
    except Exception as e:
        deps["database"] = f"error: {e}"
        all_ok = False

    # Identity
    try:
        c = await get_identity_client()
        r = await c.get("/health")
        deps["identity"] = "connected" if r.status_code == 200 else "unreachable"
        if r.status_code != 200:
            all_ok = False
    except Exception:
        deps["identity"] = "unreachable"
        all_ok = False

    if not all_ok:
        raise HTTPException(status_code=503, detail={"status": "degraded", "dependencies": deps})
    return {"status": "ok", "dependencies": deps}

@app.get("/version")
async def version():
    return {"service": "aither-ai-platform", "version": "1.0.0", "build": "stage16"}

# ── Models ─────────────────────────────────────────────────────

@app.get("/api/v1/models")
async def list_models(user: dict = Depends(get_current_user)):
    """List all enabled models (any authenticated user)."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM models ORDER BY display_name"
    ).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "display_name": r["display_name"],
            "provider": r["provider"],
            "model_identifier": r["model_identifier"],
            "description": r["description"],
            "context_window": r["context_window"],
            "enabled": bool(r["enabled"]),
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]

@app.get("/api/v1/models/{model_id}")
async def get_model(model_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    row = conn.execute("SELECT * FROM models WHERE id=?", (model_id,)).fetchone()
    conn.close()
    if row is None:
        METRIC_ERRORS_TOTAL.labels(type="model_not_found").inc()
        raise HTTPException(status_code=404, detail="Model not found")
    return {
        "id": row["id"],
        "name": row["name"],
        "display_name": row["display_name"],
        "provider": row["provider"],
        "model_identifier": row["model_identifier"],
        "description": row["description"],
        "context_window": row["context_window"],
        "enabled": bool(row["enabled"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }

@app.post("/api/v1/models", status_code=201)
async def create_model(req: ModelCreate, admin: dict = Depends(require_admin)):
    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO models (name, display_name, provider, endpoint, model_identifier, description, context_window, enabled)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (req.name, req.display_name, req.provider, req.endpoint, req.model_identifier,
             req.description, req.context_window, int(req.enabled)),
        )
        conn.commit()
        model_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        log.info("Admin '%s' created model '%s' (id=%d)", admin.get("sub"), req.name, model_id)
        return {"id": model_id, "message": f"Model '{req.name}' created"}
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=409, detail=f"Model '{req.name}' already exists")
    finally:
        conn.close()

@app.patch("/api/v1/models/{model_id}")
async def update_model(model_id: int, req: ModelUpdate, admin: dict = Depends(require_admin)):
    conn = get_db()
    row = conn.execute("SELECT * FROM models WHERE id=?", (model_id,)).fetchone()
    if row is None:
        conn.close()
        METRIC_ERRORS_TOTAL.labels(type="model_not_found").inc()
        raise HTTPException(status_code=404, detail="Model not found")

    updates = {}
    for field in ("display_name", "provider", "endpoint", "model_identifier", "description", "context_window"):
        val = getattr(req, field, None)
        if val is not None:
            updates[field] = val
    if req.enabled is not None:
        updates["enabled"] = int(req.enabled)
    updates["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    if not updates:
        conn.close()
        return {"message": "No changes"}

    set_clause = ", ".join(f"{k}=?" for k in updates)
    conn.execute(f"UPDATE models SET {set_clause} WHERE id=?", (*updates.values(), model_id))
    conn.commit()
    conn.close()
    log.info("Admin '%s' updated model id=%d", admin.get("sub"), model_id)
    return {"message": f"Model id={model_id} updated"}

@app.delete("/api/v1/models/{model_id}")
async def delete_model(model_id: int, admin: dict = Depends(require_admin)):
    """Disable a model. Physical deletion blocked if used by assistants."""
    conn = get_db()
    row = conn.execute("SELECT * FROM models WHERE id=?", (model_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Model not found")

    # Check if any enabled assistant uses this model
    used = conn.execute(
        "SELECT COUNT(*) as cnt FROM assistants WHERE model_id=? AND enabled=1",
        (model_id,),
    ).fetchone()
    if used["cnt"] > 0:
        # Disable instead of delete
        conn.execute("UPDATE models SET enabled=0, updated_at=datetime('now') WHERE id=?", (model_id,))
        conn.commit()
        conn.close()
        log.info("Admin '%s' disabled model id=%d (used by %d assistants)", admin.get("sub"), model_id, used["cnt"])
        return {"message": f"Model id={model_id} disabled — used by {used['cnt']} active assistant(s)"}

    conn.execute("DELETE FROM models WHERE id=?", (model_id,))
    conn.commit()
    conn.close()
    log.info("Admin '%s' deleted model id=%d", admin.get("sub"), model_id)
    return {"message": f"Model id={model_id} deleted"}

# ── API Keys ──────────────────────────────────────────────────

def generate_api_key(user_id: int, name: str) -> tuple:
    """Generate a new API Key. Returns (full_key, prefix, hash)."""
    raw_secret = secrets.token_urlsafe(48)
    prefix = f"aither_{secrets.token_hex(4)}"
    full_key = f"{prefix}_{raw_secret}"
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, prefix, key_hash

@app.get("/api/v1/api-keys")
async def list_api_keys(user: dict = Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute(
        """SELECT id, name, key_prefix, created_at, last_used_at, expires_at, revoked_at
           FROM api_keys WHERE user_id=? ORDER BY created_at DESC""",
        (user["id"],),
    ).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "key_prefix": r["key_prefix"],
            "created_at": r["created_at"],
            "last_used_at": r["last_used_at"],
            "expires_at": r["expires_at"],
            "revoked_at": r["revoked_at"],
        }
        for r in rows
    ]

@app.post("/api/v1/api-keys", status_code=201)
async def create_api_key(req: APIKeyCreate, user: dict = Depends(get_current_user)):
    full_key, prefix, key_hash = generate_api_key(user["id"], req.name)
    conn = get_db()
    conn.execute(
        "INSERT INTO api_keys (user_id, name, key_prefix, key_hash) VALUES (?, ?, ?, ?)",
        (user["id"], req.name, prefix, key_hash),
    )
    conn.commit()
    key_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    log.info("User '%s' created API Key id=%d (prefix=%s)", user.get("sub"), key_id, prefix)
    return {
        "id": key_id,
        "name": req.name,
        "key_prefix": prefix,
        "full_key": full_key,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "message": "Save this key — it will not be shown again",
    }

@app.delete("/api/v1/api-keys/{key_id}")
async def revoke_api_key(key_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM api_keys WHERE id=? AND user_id=?",
        (key_id, user["id"]),
    ).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="API Key not found or not owned by you")
    conn.execute(
        "UPDATE api_keys SET revoked_at=datetime('now') WHERE id=?",
        (key_id,),
    )
    conn.commit()
    conn.close()
    log.info("User '%s' revoked API Key id=%d", user.get("sub"), key_id)
    return {"message": f"API Key id={key_id} revoked"}

# ── Assistants ────────────────────────────────────────────────

@app.get("/api/v1/assistants")
async def list_assistants(user: dict = Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute(
        """SELECT a.*, m.display_name as model_name, m.name as model_name_key
           FROM assistants a LEFT JOIN models m ON a.model_id=m.id
           WHERE a.owner_user_id=? ORDER BY a.created_at DESC""",
        (user["id"],),
    ).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "description": r["description"],
            "model_id": r["model_id"],
            "model_name": r["model_name"] or r["model_name_key"],
            "system_prompt": r["system_prompt"],
            "temperature": r["temperature"],
            "max_tokens": r["max_tokens"],
            "enabled": bool(r["enabled"]),
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]

@app.post("/api/v1/assistants", status_code=201)
async def create_assistant(req: AssistantCreate, user: dict = Depends(get_current_user)):
    conn = get_db()
    # Verify model exists and is enabled
    model = conn.execute("SELECT id, enabled FROM models WHERE id=?", (req.model_id,)).fetchone()
    if model is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Model not found")
    if not model["enabled"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Model is disabled")
    try:
        conn.execute(
            """INSERT INTO assistants (owner_user_id, name, description, model_id, system_prompt, temperature, max_tokens)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user["id"], req.name, req.description, req.model_id, req.system_prompt, req.temperature, req.max_tokens),
        )
        conn.commit()
        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        log.info("User '%s' created assistant id=%d", user.get("sub"), aid)
        return {"id": aid, "message": f"Assistant '{req.name}' created"}
    finally:
        conn.close()

@app.patch("/api/v1/assistants/{assistant_id}")
async def update_assistant(assistant_id: int, req: AssistantUpdate, user: dict = Depends(get_current_user)):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM assistants WHERE id=? AND owner_user_id=?",
        (assistant_id, user["id"]),
    ).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Assistant not found or not owned by you")

    updates = {}
    for field in ("name", "description", "system_prompt", "temperature", "max_tokens"):
        val = getattr(req, field, None)
        if val is not None:
            updates[field] = val
    if req.model_id is not None:
        model = conn.execute("SELECT id, enabled FROM models WHERE id=?", (req.model_id,)).fetchone()
        if model is None:
            conn.close()
            raise HTTPException(status_code=404, detail="Model not found")
        if not model["enabled"]:
            conn.close()
            raise HTTPException(status_code=400, detail="Model is disabled")
        updates["model_id"] = req.model_id
    if req.enabled is not None:
        updates["enabled"] = int(req.enabled)
    updates["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    if not updates:
        conn.close()
        return {"message": "No changes"}

    set_clause = ", ".join(f"{k}=?" for k in updates)
    conn.execute(f"UPDATE assistants SET {set_clause} WHERE id=?", (*updates.values(), assistant_id))
    conn.commit()
    conn.close()
    return {"message": f"Assistant id={assistant_id} updated"}

@app.delete("/api/v1/assistants/{assistant_id}")
async def delete_assistant(assistant_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM assistants WHERE id=? AND owner_user_id=?",
        (assistant_id, user["id"]),
    ).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Assistant not found or not owned by you")
    conn.execute("DELETE FROM assistants WHERE id=?", (assistant_id,))
    conn.commit()
    conn.close()
    return {"message": f"Assistant id={assistant_id} deleted"}

# ── Conversations ─────────────────────────────────────────────

@app.get("/api/v1/conversations")
async def list_conversations(user: dict = Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute(
        """SELECT c.*, a.name as assistant_name
           FROM conversations c LEFT JOIN assistants a ON c.assistant_id=a.id
           WHERE c.owner_user_id=? ORDER BY c.updated_at DESC""",
        (user["id"],),
    ).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "assistant_id": r["assistant_id"],
            "assistant_name": r["assistant_name"],
            "title": r["title"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]

@app.post("/api/v1/conversations", status_code=201)
async def create_conversation(req: ConversationCreate, user: dict = Depends(get_current_user)):
    conn = get_db()
    if req.assistant_id:
        ast = conn.execute(
            "SELECT id FROM assistants WHERE id=? AND owner_user_id=?",
            (req.assistant_id, user["id"]),
        ).fetchone()
        if ast is None:
            conn.close()
            raise HTTPException(status_code=404, detail="Assistant not found or not owned by you")
    conn.execute(
        "INSERT INTO conversations (owner_user_id, assistant_id, title) VALUES (?, ?, ?)",
        (user["id"], req.assistant_id, req.title),
    )
    conn.commit()
    cid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return {"id": cid, "message": "Conversation created"}

@app.get("/api/v1/conversations/{conv_id}")
async def get_conversation(conv_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    conv = conn.execute(
        "SELECT * FROM conversations WHERE id=? AND owner_user_id=?",
        (conv_id, user["id"]),
    ).fetchone()
    if conv is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Conversation not found")
    msgs = conn.execute(
        "SELECT id, role, content, created_at FROM messages WHERE conversation_id=? ORDER BY created_at",
        (conv_id,),
    ).fetchall()
    conn.close()
    return {
        "id": conv["id"],
        "assistant_id": conv["assistant_id"],
        "title": conv["title"],
        "created_at": conv["created_at"],
        "updated_at": conv["updated_at"],
        "messages": [
            {"id": m["id"], "role": m["role"], "content": m["content"], "created_at": m["created_at"]}
            for m in msgs
        ],
    }

@app.delete("/api/v1/conversations/{conv_id}")
async def delete_conversation(conv_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM conversations WHERE id=? AND owner_user_id=?",
        (conv_id, user["id"]),
    ).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Conversation not found")
    conn.execute("DELETE FROM conversations WHERE id=?", (conv_id,))
    conn.commit()
    conn.close()
    return {"message": f"Conversation id={conv_id} deleted"}

@app.post("/api/v1/conversations/{conv_id}/messages")
async def send_message(conv_id: int, req: MessageSend, user: dict = Depends(get_current_user)):
    """Send a message and get AI response."""
    conn = get_db()
    conv = conn.execute(
        "SELECT * FROM conversations WHERE id=? AND owner_user_id=?",
        (conv_id, user["id"]),
    ).fetchone()
    if conv is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get assistant config
    assistant = None
    if conv["assistant_id"]:
        assistant = conn.execute(
            "SELECT * FROM assistants WHERE id=? AND owner_user_id=?",
            (conv["assistant_id"], user["id"]),
        ).fetchone()
        if assistant and not assistant["enabled"]:
            conn.close()
            raise HTTPException(status_code=400, detail="Assistant is disabled")
    conn.close()

    # Save user message
    conn = get_db()
    conn.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (?, 'user', ?)",
        (conv_id, req.content),
    )
    conn.execute(
        "UPDATE conversations SET updated_at=datetime('now') WHERE id=?",
        (conv_id,),
    )
    conn.commit()
    conn.close()

    # Build messages for AI
    system_prompt = assistant["system_prompt"] if assistant else ""
    model_id = assistant["model_id"] if assistant else None

    conn = get_db()
    past_msgs = conn.execute(
        "SELECT role, content FROM messages WHERE conversation_id=? ORDER BY created_at",
        (conv_id,),
    ).fetchall()
    conn.close()

    ai_messages = []
    if system_prompt:
        ai_messages.append({"role": "system", "content": system_prompt})
    for m in past_msgs:
        ai_messages.append({"role": m["role"], "content": m["content"]})

    # Get model info
    conn = get_db()
    if model_id:
        model = conn.execute("SELECT * FROM models WHERE id=?", (model_id,)).fetchone()
    else:
        # Fallback: first enabled model
        model = conn.execute("SELECT * FROM models WHERE enabled=1 ORDER BY id LIMIT 1").fetchone()
    conn.close()

    if model is None:
        raise HTTPException(status_code=503, detail="No enabled model available")

    # Call AI model
    model_id = model["model_identifier"]
    try:
        if model_id in ("qwen/Qwen-14B-Instruct", "qwen-14b"):
            # 14B supports chat natively — go directly to vLLM
            async with httpx.AsyncClient(base_url=VLLM_14B_URL, timeout=300.0) as vllm_client:
                headers = {}
                if VLLM_API_KEY:
                    headers["Authorization"] = f"Bearer {VLLM_API_KEY}"
                vllm_resp = await vllm_client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "qwen-14b",
                        "messages": ai_messages,
                        "temperature": assistant["temperature"] if assistant else 0.7,
                        "max_tokens": assistant["max_tokens"] if assistant else 2048,
                        "stream": False,
                    },
                    headers=headers,
                    timeout=300.0,
                )
                if vllm_resp.status_code != 200:
                    METRIC_GATEWAY_ERRORS.labels(type="http_error").inc()
                    log.error("vLLM 14B returned HTTP %d: %.200s", vllm_resp.status_code, vllm_resp.text[:200])
                    raise HTTPException(
                        status_code=502,
                        detail=f"AI service returned error (HTTP {vllm_resp.status_code})",
                    )
                result = vllm_resp.json()
                # Extract response content
                if "choices" in result and len(result["choices"]) > 0:
                    choice = result["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        response_content = choice["message"]["content"]
                    elif "text" in choice:
                        response_content = choice["text"]
                    else:
                        response_content = json.dumps(choice)
                else:
                    response_content = json.dumps(result)
        else:
            # For 32B (base model), use Gateway (only supports /v1/completions)
            gc = await get_gateway_client()
            gateway_payload = {
                "model": model_id,
                "prompt": ai_messages[-1]["content"] if ai_messages else "",
                "temperature": assistant["temperature"] if assistant else 0.7,
                "max_tokens": assistant["max_tokens"] if assistant else 2048,
            }
            gateway_resp = await gc.post(
                "/v1/completions",
                json=gateway_payload,
                timeout=300.0,
            )

            if gateway_resp.status_code != 200:
                METRIC_GATEWAY_ERRORS.labels(type="http_error").inc()
                log.error("Gateway returned HTTP %d: %.200s", gateway_resp.status_code, gateway_resp.text[:200])
                # Pass through 4xx client errors (e.g. 429), wrap 5xx as 502
                if 400 <= gateway_resp.status_code < 500:
                    return JSONResponse(
                        status_code=gateway_resp.status_code,
                        content=json.loads(gateway_resp.text) if gateway_resp.text else {"error": f"AI service error (HTTP {gateway_resp.status_code})"},
                    )
                raise HTTPException(
                    status_code=502,
                    detail=f"AI service returned error (HTTP {gateway_resp.status_code})",
                )

            METRIC_GATEWAY_REQUESTS.labels(status="success").inc()

            result = gateway_resp.json()

            # Extract response content
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    response_content = choice["message"]["content"]
                elif "text" in choice:
                    response_content = choice["text"]
                else:
                    response_content = json.dumps(choice)
            else:
                response_content = json.dumps(result)

    except httpx.TimeoutException:
        METRIC_GATEWAY_ERRORS.labels(type="timeout").inc()
        raise HTTPException(status_code=504, detail="AI service timed out")
    except httpx.RequestError as e:
        METRIC_GATEWAY_ERRORS.labels(type="connection").inc()
        log.error("Upstream unreachable: %s", e)
        raise HTTPException(status_code=502, detail="AI service unavailable")
    except HTTPException:
        raise
    except Exception as e:
        METRIC_GATEWAY_ERRORS.labels(type="unexpected").inc()
        log.error("Unexpected error calling AI model: %s", e)
        raise HTTPException(status_code=502, detail="AI service error")

    # Save AI response
    conn = get_db()
    conn.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (?, 'assistant', ?)",
        (conv_id, response_content),
    )
    conn.commit()
    conn.close()

    return {
        "role": "assistant",
        "content": response_content,
        "model": model["model_identifier"],
    }

# ── OpenAI-Compatible Models List ───────────────────────────

@app.get("/v1/models")
async def openai_list_models(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
):
    """OpenAI-compatible models list. Authenticated via API Key (same as chat completions)."""
    key_value = ""
    if authorization and authorization.startswith("Bearer "):
        key_value = authorization[7:]
    elif x_api_key:
        key_value = x_api_key

    if not key_value or not key_value.startswith("aither_"):
        METRIC_ERRORS_TOTAL.labels(type="missing_api_key").inc()
        raise HTTPException(status_code=401, detail="Valid API Key required (format: aither_...)")

    await authenticate_api_key(key_value)

    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, model_identifier, enabled, created_at FROM models ORDER BY id"
    ).fetchall()
    conn.close()

    now = int(time.time())
    data = []
    for r in rows:
        if not r["enabled"]:
            continue
        model_id = r["model_identifier"] or r["name"]
        created = int(datetime.fromisoformat(r["created_at"]).timestamp()) if r["created_at"] else now
        data.append({
            "id": model_id,
            "object": "model",
            "created": created,
            "owned_by": "aither",
        })

    return {"object": "list", "data": data}

# ── OpenAI-Compatible Chat Completions ────────────────────────

@app.post("/v1/chat/completions")
async def chat_completions(
    req: ChatCompletionRequest,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
):
    """OpenAI-compatible chat completions endpoint. Authenticated via API Key."""
    # Authenticate via API Key
    key_value = ""
    if authorization and authorization.startswith("Bearer "):
        key_value = authorization[7:]
    elif x_api_key:
        key_value = x_api_key

    if not key_value or not key_value.startswith("aither_"):
        METRIC_ERRORS_TOTAL.labels(type="missing_api_key").inc()
        raise HTTPException(status_code=401, detail="Valid API Key required (format: aither_...)")

    user = await authenticate_api_key(key_value)

    # Find model
    conn = get_db()
    model = conn.execute(
        "SELECT * FROM models WHERE name=? AND enabled=1",
        (req.model,),
    ).fetchone()

    if model is None:
        # Try by model_identifier
        model = conn.execute(
            "SELECT * FROM models WHERE model_identifier=? AND enabled=1",
            (req.model,),
        ).fetchone()

    if model is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Model '{req.model}' not found or disabled")

    conn.close()

    # Call upstream based on model
    model_id = model["model_identifier"]
    try:
        if model_id in ("qwen/Qwen-14B-Instruct", "qwen-14b"):
            # 14B supports chat natively — go directly to vLLM
            async with httpx.AsyncClient(base_url=VLLM_14B_URL, timeout=300.0) as vllm_client:
                headers = {}
                if VLLM_API_KEY:
                    headers["Authorization"] = f"Bearer {VLLM_API_KEY}"
                vllm_payload = {
                    "model": "qwen-14b",
                    "messages": [m.dict() if hasattr(m, 'dict') else m for m in req.messages],
                    "temperature": req.temperature if req.temperature is not None else 0.7,
                    "max_tokens": req.max_tokens if req.max_tokens is not None else 2048,
                    "stream": req.stream if req.stream is not None else False,
                }
                vllm_resp = await vllm_client.post(
                    "/v1/chat/completions",
                    json=vllm_payload,
                    headers=headers,
                    timeout=300.0,
                )
                if vllm_resp.status_code != 200:
                    METRIC_GATEWAY_ERRORS.labels(type="http_error").inc()
                    log.error("vLLM 14B returned HTTP %d: %.200s", vllm_resp.status_code, vllm_resp.text[:200])
                    # Pass through 4xx, wrap 5xx as 502
                    if 400 <= vllm_resp.status_code < 500:
                        return JSONResponse(
                            status_code=vllm_resp.status_code,
                            content=json.loads(vllm_resp.text) if vllm_resp.text else {"error": f"AI service error (HTTP {vllm_resp.status_code})"},
                        )
                    return JSONResponse(
                        status_code=502,
                        content={"error": f"AI service error (HTTP {vllm_resp.status_code})"},
                    )
                METRIC_GATEWAY_REQUESTS.labels(status="success").inc()
                return vllm_resp.json()
        else:
            # For 32B (base model), use Gateway (only supports /v1/completions)
            gc = await get_gateway_client()
            last_msg = req.messages[-1]
            if isinstance(last_msg, dict):
                prompt = last_msg.get("content", "")
            else:
                prompt = last_msg.content
            gateway_payload = {
                "model": model_id,
                "prompt": prompt,
                "temperature": req.temperature if req.temperature is not None else 0.7,
                "max_tokens": req.max_tokens if req.max_tokens is not None else 2048,
            }
            gateway_resp = await gc.post(
                "/v1/completions",
                json=gateway_payload,
                timeout=300.0,
            )
            if gateway_resp.status_code != 200:
                METRIC_GATEWAY_ERRORS.labels(type="http_error").inc()
                log.error("Gateway returned HTTP %d: %.200s", gateway_resp.status_code, gateway_resp.text[:200])
                # Pass through 4xx client errors (e.g. 429), wrap 5xx as 502
                if 400 <= gateway_resp.status_code < 500:
                    return JSONResponse(
                        status_code=gateway_resp.status_code,
                        content=json.loads(gateway_resp.text) if gateway_resp.text else {"error": f"AI service error (HTTP {gateway_resp.status_code})"},
                    )
                return JSONResponse(
                    status_code=502,
                    content={"error": f"AI service error (HTTP {gateway_resp.status_code})"},
                )
            METRIC_GATEWAY_REQUESTS.labels(status="success").inc()
            result = gateway_resp.json()
            return result

    except httpx.TimeoutException:
        METRIC_GATEWAY_ERRORS.labels(type="timeout").inc()
        raise HTTPException(status_code=504, detail="AI service timed out")
    except httpx.RequestError as e:
        METRIC_GATEWAY_ERRORS.labels(type="connection").inc()
        log.error("Upstream unreachable: %s", e)
        raise HTTPException(status_code=502, detail="AI service unavailable")

# ── Shutdown ──────────────────────────────────────────────────

@app.on_event("shutdown")
async def shutdown():
    global identity_client, gateway_client
    if identity_client:
        await identity_client.aclose()
        identity_client = None
    if gateway_client:
        await gateway_client.aclose()
        gateway_client = None
