# Aither Identity Service
#
# Environment variables:
#   IDENTITY_SECRET_KEY         — JWT signing key (required)
#   IDENTITY_ADMIN_USER         — bootstrap admin username (default: admin)
#   IDENTITY_ADMIN_PASS         — bootstrap admin password hash (bcrypt) (required on first run)
#   IDENTITY_DB_PATH            — SQLite path (default: /data/identity.db)
#   IDENTITY_TOKEN_TTL          — JWT token TTL in seconds (default: 86400 = 24h)
#   IDENTITY_LOG_LEVEL          — logging level (default: INFO)
#
#   OAuth (optional — set CLIENT_ID + CLIENT_SECRET to enable each provider):
#   OAUTH_GITHUB_CLIENT_ID      — GitHub OAuth App Client ID
#   OAUTH_GITHUB_CLIENT_SECRET  — GitHub OAuth App Client Secret
#   OAUTH_GOOGLE_CLIENT_ID      — Google OAuth Client ID
#   OAUTH_GOOGLE_CLIENT_SECRET  — Google OAuth Client Secret
#   OAUTH_YANDEX_CLIENT_ID      — Yandex OAuth Client ID
#   OAUTH_YANDEX_CLIENT_SECRET  — Yandex OAuth Client Secret
#   OAUTH_REDIRECT_BASE         — Base URL for OAuth callbacks (default: http://localhost:8000)
#
#   LDAP (optional — set LDAP_ENABLED=true to enable):
#   LDAP_ENABLED                — "true" to enable LDAP auth
#   LDAP_SERVER                 — LDAP server URL (e.g. ldap://ldap.example.com:389)
#   LDAP_BASE_DN                — Base DN for user search (e.g. dc=example,dc=com)
#   LDAP_USER_DN_TEMPLATE       — Template for user DN (e.g. uid={username},ou=people,dc=example,dc=com)
#
# API:
#   POST /v1/identity/auth              — login (username/password)
#   POST /v1/identity/logout            — logout (token revocation)
#   GET  /v1/identity/me                — current user info
#   GET  /v1/identity/users             — list users (admin only)
#   POST /v1/identity/users             — create user (admin only)
#   POST /v1/identity/bootstrap         — create initial admin (one-shot)
#   GET  /v1/identity/auth/providers    — list available auth providers
#   GET  /v1/identity/auth/oauth/{provider}        — OAuth redirect
#   GET  /v1/identity/auth/oauth/{provider}/callback — OAuth callback
#   POST /v1/identity/auth/ldap         — LDAP authentication

import asyncio
import os
import json
import logging
import re
import sqlite3
import secrets
import time
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlencode

import bcrypt
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response, JSONResponse

# ── Configuration ──────────────────────────────────────────────

SECRET_KEY = os.environ.get("IDENTITY_SECRET_KEY", "")
ADMIN_USER = os.environ.get("IDENTITY_ADMIN_USER", "admin")
ADMIN_PASS_HASH = os.environ.get("IDENTITY_ADMIN_PASS", "")
DB_PATH = os.environ.get("IDENTITY_DB_PATH", "/data/identity.db")
TOKEN_TTL = int(os.environ.get("IDENTITY_TOKEN_TTL", "86400"))
LOG_LEVEL = os.environ.get("IDENTITY_LOG_LEVEL", "INFO").upper()

# OAuth config
OAUTH_REDIRECT_BASE = os.environ.get("OAUTH_REDIRECT_BASE", "http://localhost:8000").rstrip("/")
OAUTH_CALLBACK_PATH = os.environ.get("OAUTH_CALLBACK_PATH", "/v1/identity/auth/oauth")
OAUTH_PROVIDERS_CONFIG = {
    "github": {
        "name": "GitHub",
        "client_id": os.environ.get("OAUTH_GITHUB_CLIENT_ID", ""),
        "client_secret": os.environ.get("OAUTH_GITHUB_CLIENT_SECRET", ""),
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "userinfo_emails_url": "https://api.github.com/user/emails",
        "scope": "read:user user:email",
    },
    "google": {
        "name": "Google",
        "client_id": os.environ.get("OAUTH_GOOGLE_CLIENT_ID", ""),
        "client_secret": os.environ.get("OAUTH_GOOGLE_CLIENT_SECRET", ""),
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "userinfo_emails_url": None,
        "scope": "openid email profile",
    },
    "yandex": {
        "name": "Yandex",
        "client_id": os.environ.get("OAUTH_YANDEX_CLIENT_ID", ""),
        "client_secret": os.environ.get("OAUTH_YANDEX_CLIENT_SECRET", ""),
        "authorize_url": "https://oauth.yandex.ru/authorize",
        "token_url": "https://oauth.yandex.ru/token",
        "userinfo_url": "https://login.yandex.ru/info",
        "userinfo_emails_url": None,
        "scope": "login:email login:info",
    },
}

# LDAP config
LDAP_ENABLED = os.environ.get("LDAP_ENABLED", "").lower() == "true"
LDAP_SERVER = os.environ.get("LDAP_SERVER", "")
LDAP_BASE_DN = os.environ.get("LDAP_BASE_DN", "")
LDAP_USER_DN_TEMPLATE = os.environ.get("LDAP_USER_DN_TEMPLATE", "")

if not SECRET_KEY or not SECRET_KEY.strip():
    raise RuntimeError("IDENTITY_SECRET_KEY is required")

# ── Logging ────────────────────────────────────────────────────

class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter."""
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "aither-identity",
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
log = logging.getLogger("aither-identity")
log.propagate = False
_handler = logging.StreamHandler()
_handler.setFormatter(JSONFormatter())
log.addHandler(_handler)

security = HTTPBearer(auto_error=False)

# ── Database ───────────────────────────────────────────────────

def get_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            role        TEXT NOT NULL DEFAULT 'user',
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            disabled    INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            token_hash  TEXT UNIQUE NOT NULL,
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            expires_at  TEXT NOT NULL,
            revoked     INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS oauth_accounts (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL,
            provider         TEXT NOT NULL,
            provider_user_id TEXT NOT NULL,
            email            TEXT,
            created_at       TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(provider, provider_user_id)
        );

        CREATE TABLE IF NOT EXISTS organisations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT UNIQUE NOT NULL,
            tier        TEXT NOT NULL DEFAULT 'free',
            status      TEXT NOT NULL DEFAULT 'active',
            balance     INTEGER NOT NULL DEFAULT 0,
            quota_daily INTEGER NOT NULL DEFAULT 1000,
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()

    # Migration: add org_id to users if missing
    cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    if "org_id" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN org_id INTEGER DEFAULT NULL REFERENCES organisations(id)")
        conn.commit()

    # Migration: add scopes to users if missing
    if "scopes" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN scopes TEXT DEFAULT ''")
        conn.commit()

    # Migration: add email to users if missing
    cols2 = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    if "email" not in cols2:
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT DEFAULT ''")
        conn.commit()

    # Ensure default organisation exists (for bootstrap only — not auto-assigned)
    org = conn.execute("SELECT id FROM organisations WHERE name='default'").fetchone()
    if not org:
        conn.execute("INSERT INTO organisations (name, tier, status) VALUES ('default', 'free', 'active')")
        conn.commit()
        org = conn.execute("SELECT id FROM organisations WHERE name='default'").fetchone()

    # NO automatic org assignment — users without org are PENDING ENTITLEMENT
    # Old fallback removed: UPDATE users SET org_id=? WHERE org_id IS NULL

    conn.close()

# ── Utilities ──────────────────────────────────────────────────

def hash_token(token: str) -> str:
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()

def generate_token() -> str:
    return secrets.token_urlsafe(48)

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

# ── Password Policy ────────────────────────────────────────────
# Minimum 16 characters.
# Must contain: uppercase (A-Z), lowercase (a-z), digit (0-9), special char.
_PASSWORD_SPECIAL = r"~!@#$%^&*+\-/.,\\{}[\]();:_?<>\"'"

def validate_password(password: str) -> str | None:
    """Return error message if password fails policy, None if valid."""
    if len(password) < 16:
        return "Пароль должен содержать не менее 16 символов"
    if not re.search(r"[A-Z]", password):
        return "Пароль должен содержать хотя бы одну заглавную букву (A-Z)"
    if not re.search(r"[a-z]", password):
        return "Пароль должен содержать хотя бы одну строчную букву (a-z)"
    if not re.search(r"[0-9]", password):
        return "Пароль должен содержать хотя бы одну цифру (0-9)"
    if not re.search(r"[~!@#$%^&*+\-/.,\\{}[\]();:_?<>\"']", password):
        return "Пароль должен содержать хотя бы один спецсимвол (~!@#$%^&*+-/.,\\{}[]();:_?<>\"')"
    return None

def make_jwt(user_id: int, username: str, role: str, org_id: int | None = None, scopes: str = "", disabled: bool = False, tier: str = "") -> str:
    """Simple HMAC-based stateless token."""
    token = generate_token()
    payload = json.dumps({
        "uid": user_id,
        "sub": username,
        "role": role,
        "org_id": org_id,
        "scopes": scopes,
        "disabled": disabled,
        "tier": tier,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_TTL,
        "jti": token,
    }, separators=(',', ':'))
    import hmac
    sig = hmac.new(SECRET_KEY.encode(), payload.encode(), "sha256").hexdigest()
    return f"{payload}.{sig}"

def verify_jwt(token_str: str):
    """Returns payload dict or None."""
    try:
        if "." not in token_str:
            return None
        payload_b64, sig = token_str.rsplit(".", 1)
        import hmac
        expected = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), "sha256").hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(payload_b64)
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None

def create_session(conn, user_id: int, token: str):
    conn.execute(
        "INSERT INTO sessions (user_id, token_hash, expires_at) VALUES (?, ?, datetime('now', '+{} seconds'))".format(TOKEN_TTL),
        (user_id, hash_token(token)),
    )

def get_or_create_oauth_user(conn, provider: str, provider_user_id: str, email: str = None) -> int:
    """Find existing OAuth-linked user or create a new one. Returns user_id."""
    row = conn.execute(
        "SELECT user_id FROM oauth_accounts WHERE provider=? AND provider_user_id=?",
        (provider, provider_user_id),
    ).fetchone()
    if row:
        return row["user_id"]

    # Try to find by email if provided
    username = f"{provider}_{provider_user_id}"
    if email:
        username = email.split("@")[0]
        # Check uniqueness
        existing = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if existing:
            username = f"{username}_{provider}"

    try:
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, 'user')",
            (username, ""),
        )
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO oauth_accounts (user_id, provider, provider_user_id, email) VALUES (?, ?, ?, ?)",
            (user_id, provider, provider_user_id, email),
        )
        log.info("OAuth: created user '%s' (provider=%s, id=%s)", username, provider, provider_user_id)
        return user_id
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail=f"Username '{username}' already exists")

# ── OAuth Client ───────────────────────────────────────────────

from authlib.integrations.httpx_client import AsyncOAuth2Client  # noqa: E402

def get_oauth_client(provider: str) -> AsyncOAuth2Client:
    cfg = OAUTH_PROVIDERS_CONFIG.get(provider)
    if not cfg or not cfg["client_id"]:
        raise HTTPException(status_code=400, detail=f"OAuth provider '{provider}' is not configured")
    redirect_uri = f"{OAUTH_REDIRECT_BASE}{OAUTH_CALLBACK_PATH}/{provider}/callback"
    return AsyncOAuth2Client(
        client_id=cfg["client_id"],
        client_secret=cfg["client_secret"],
        redirect_uri=redirect_uri,
        scope=cfg["scope"],
    )

# ── LDAP Client ────────────────────────────────────────────────

def ldap_authenticate(username: str, password: str) -> dict | None:
    """Authenticate user against LDAP. Returns user dict or None."""
    if not LDAP_ENABLED:
        return None
    try:
        import ldap3
        server = ldap3.Server(LDAP_SERVER, get_info=ldap3.ALL)
        user_dn = LDAP_USER_DN_TEMPLATE.format(username=username)
        conn = ldap3.Connection(server, user=user_dn, password=password, auto_bind=True)
        conn.search(
            search_base=LDAP_BASE_DN,
            search_filter=f"(uid={username})",
            attributes=["uid", "mail", "cn", "givenName", "sn"],
        )
        if conn.entries:
            entry = conn.entries[0]
            return {
                "username": str(entry.uid) if hasattr(entry, "uid") else username,
                "email": str(entry.mail) if hasattr(entry, "mail") else None,
                "display_name": str(entry.cn) if hasattr(entry, "cn") else username,
            }
        conn.unbind()
    except Exception as e:
        log.warning("LDAP auth failed for '%s': %s", username, str(e))
    return None

# ── Models ─────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str = ""

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"
    org_id: int | None = None
    scopes: str = ""

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: str
    disabled: bool
    org_id: int | None = None
    scopes: str = ""

class MeResponse(BaseModel):
    id: int
    username: str
    role: str
    org_id: int | None = None
    org_name: str | None = None
    org_status: str | None = None
    tier: str | None = None
    scopes: str = ""
    disabled: bool = False

class TokenResponse(BaseModel):
    token: str
    user: MeResponse

class StatusResponse(BaseModel):
    service: str
    version: str
    status: str

class ProviderInfo(BaseModel):
    id: str
    name: str
    enabled: bool

class LdapLoginRequest(BaseModel):
    username: str
    password: str

# ── Dependencies ───────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = verify_jwt(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Check session: must exist, not revoked, not expired
    conn = get_db()
    try:
        token_hash_val = hash_token(credentials.credentials)
        session = conn.execute(
            "SELECT id, revoked, expires_at FROM sessions WHERE token_hash=?",
            (token_hash_val,),
        ).fetchone()
        if not session:
            raise HTTPException(status_code=401, detail="Session not found")
        if session["revoked"]:
            raise HTTPException(status_code=401, detail="Session revoked")
        if session["expires_at"] < datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"):
            raise HTTPException(status_code=401, detail="Session expired")

        # Load CURRENT (not stale token) rights from DB
        row = conn.execute(
            """SELECT u.id as uid, u.username, u.role, u.disabled, u.org_id,
                      COALESCE(u.scopes,'') as scopes, o.tier, o.status as org_status
               FROM users u LEFT JOIN organisations o ON u.org_id=o.id
               WHERE u.id=?""",
            (payload["uid"],),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="User not found")
        if row["disabled"]:
            # Revoke all sessions for disabled user
            conn.execute("UPDATE sessions SET revoked=1 WHERE user_id=? AND revoked=0", (payload["uid"],))
            conn.commit()
            raise HTTPException(status_code=403, detail="Account disabled")

        # Detect role change: revoke all sessions if role no longer matches token
        if row["role"] != payload.get("role"):
            conn.execute("UPDATE sessions SET revoked=1 WHERE user_id=? AND revoked=0", (payload["uid"],))
            conn.commit()
            raise HTTPException(status_code=401, detail="Role changed — session revoked, please re-authenticate")

        # Build fresh payload with current DB values
        fresh = {
            "uid": row["uid"],
            "sub": row["username"],
            "role": row["role"],
            "disabled": bool(row["disabled"]),
            "org_id": row["org_id"],
            "scopes": row["scopes"],
            "tier": row["tier"],
            "org_status": row["org_status"],
            "iat": payload.get("iat"),
            "exp": payload.get("exp"),
            "jti": payload.get("jti"),
        }
        return fresh
    finally:
        conn.close()

async def require_admin(user: dict = Depends(get_current_user)):
    if user.get("role") != "administrator":
        raise HTTPException(status_code=403, detail="Administrator role required")
    return user

# ── Application ────────────────────────────────────────────────

import traceback  # noqa: E402

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    async def update_gauges():
        while True:
            try:
                import psutil
                memory_usage_bytes.set(psutil.Process().memory_info().rss)
            except Exception:
                pass
            try:
                conn = get_db()
                row = conn.execute(
                    "SELECT COUNT(*) as cnt FROM sessions WHERE revoked=0"
                ).fetchone()
                active_users.set(row["cnt"])
                conn.close()
            except Exception:
                pass
            await asyncio.sleep(15)
    task = asyncio.create_task(update_gauges())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="Aither Identity Service",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/v1/identity/docs",
    openapi_url="/v1/identity/openapi.json",
)

# ── Global exception handler (log full tracebacks) ─────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error("Unhandled exception on %s %s: %s\n%s",
              request.method, request.url.path, str(exc),
              traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )

# ── Prometheus Metrics ─────────────────────────────────────────

uptime_info = Info("identity", "Aither Identity Service metadata")
uptime_info.info({"version": "1.0.0", "service": "aither-identity"})

uptime = Gauge("identity_start_time_seconds", "Service start time (Unix timestamp)")
uptime.set(time.time())

http_requests_total = Counter(
    "identity_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "identity_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

active_requests = Gauge("identity_active_requests", "Currently active requests")

memory_usage_bytes = Gauge(
    "identity_memory_usage_bytes", "Current memory usage in bytes"
)

active_users = Gauge(
    "identity_active_users", "Number of currently active (non-revoked) sessions"
)

errors_total = Counter(
    "identity_errors_total", "Total errors by type", ["type"]
)

# ── Middleware ─────────────────────────────────────────────────

@app.middleware("http")
async def metrics_middleware(request, call_next):
    active_requests.inc()
    start = time.time()
    status_code = 200
    try:
        response = await call_next(request)
        status_code = response.status_code
    except HTTPException as exc:
        status_code = exc.status_code
        errors_total.labels(type="http_exception").inc()
        raise
    except Exception as exc:
        status_code = 500
        errors_total.labels(type="internal").inc()
        raise
    finally:
        duration = time.time() - start
        endpoint = request.url.path
        http_requests_total.labels(
            method=request.method, endpoint=endpoint, status_code=status_code
        ).inc()
        http_request_duration_seconds.labels(
            method=request.method, endpoint=endpoint
        ).observe(duration)
        active_requests.dec()
    return response

# ── Metrics Endpoint ───────────────────────────────────────────

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# ── Routes: Health ─────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "identity"}

@app.get("/ready")
async def ready():
    try:
        conn = get_db()
        conn.execute("SELECT 1")
        conn.close()
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {e}")

@app.get("/version")
async def version():
    return {"service": "aither-identity", "version": "1.0.0", "build": "stage15"}

# ── Routes: Auth Providers ─────────────────────────────────────

@app.get("/v1/identity/auth/providers")
async def list_providers():
    """List all available authentication providers (OAuth + LDAP + local)."""
    providers = [
        ProviderInfo(id="local", name="Local (Username/Password)", enabled=True),
    ]
    for pid, cfg in OAUTH_PROVIDERS_CONFIG.items():
        enabled = bool(cfg["client_id"] and cfg["client_secret"])
        providers.append(ProviderInfo(id=pid, name=cfg["name"], enabled=enabled))
    providers.append(ProviderInfo(id="ldap", name="LDAP", enabled=LDAP_ENABLED))
    return {"providers": [p.model_dump() for p in providers]}

# ── Routes: OAuth ──────────────────────────────────────────────

@app.get("/v1/identity/auth/oauth/{provider}")
async def oauth_login(provider: str):
    """Initiate OAuth login flow — redirect to provider."""
    if provider not in OAUTH_PROVIDERS_CONFIG:
        raise HTTPException(status_code=404, detail=f"Unknown OAuth provider: {provider}")
    cfg = OAUTH_PROVIDERS_CONFIG[provider]
    if not cfg["client_id"]:
        raise HTTPException(status_code=400, detail=f"OAuth provider '{provider}' is not configured")

    redirect_uri = f"{OAUTH_REDIRECT_BASE}{OAUTH_CALLBACK_PATH}/{provider}/callback"
    client = AsyncOAuth2Client(
        client_id=cfg["client_id"],
        redirect_uri=redirect_uri,
        scope=cfg["scope"],
    )
    state = secrets.token_urlsafe(32)
    auth_url, _state = client.create_authorization_url(cfg["authorize_url"], state=state)
    log.info("OAuth redirect: provider=%s state=%s", provider, state[:8])
    return RedirectResponse(url=auth_url)


@app.get("/v1/identity/auth/oauth/{provider}/callback")
async def oauth_callback(request: Request, provider: str, code: str = None, state: str = None, error: str = None):
    """OAuth callback — exchange code for token and create/find user."""
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    if provider not in OAUTH_PROVIDERS_CONFIG:
        raise HTTPException(status_code=404, detail=f"Unknown OAuth provider: {provider}")
    cfg = OAUTH_PROVIDERS_CONFIG[provider]
    if not cfg["client_id"]:
        raise HTTPException(status_code=400, detail=f"OAuth provider '{provider}' is not configured")

    redirect_uri = f"{OAUTH_REDIRECT_BASE}{OAUTH_CALLBACK_PATH}/{provider}/callback"

    # Exchange code for token using raw httpx (handles provider quirks)
    import httpx as _httpx  # noqa: E402
    try:
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "redirect_uri": redirect_uri,
        }
        token_headers = {"Accept": "application/json"}
        async with _httpx.AsyncClient(timeout=15.0) as token_client:
            token_resp = await token_client.post(cfg["token_url"], data=token_data, headers=token_headers)
            token_body = token_resp.text
            try:
                token = token_resp.json()
            except Exception:
                log.error("OAuth token response not JSON for %s: %s", provider, token_body[:200])
                raise HTTPException(status_code=401, detail=f"Token exchange failed: {token_body[:100]}")

            if "error" in token:
                err = token.get("error_description", token["error"])
                raise HTTPException(status_code=401, detail=f"OAuth error: {err}")

            access_token = token.get("access_token")
            if not access_token:
                raise HTTPException(status_code=401, detail="No access_token in response")

            # Fetch user info
            user_headers = {"Authorization": f"Bearer {access_token}"}
            user_resp = await token_client.get(cfg["userinfo_url"], headers=user_headers)
            userinfo = user_resp.json()

            provider_user_id = str(userinfo.get("id", userinfo.get("sub", "")))
            email = userinfo.get("email", userinfo.get("default_email", ""))

            # GitHub: email may be private — fetch from /user/emails
            if not email and cfg.get("userinfo_emails_url"):
                try:
                    emails_resp = await token_client.get(cfg["userinfo_emails_url"], headers=user_headers)
                    emails = emails_resp.json()
                    primary = next((e for e in emails if e.get("primary")), emails[0] if emails else None)
                    if primary:
                        email = primary.get("email", "")
                except Exception:
                    pass
    except Exception as e:
        log.error("OAuth callback error for %s: %s", provider, str(e))
        raise HTTPException(status_code=401, detail=f"OAuth error: {str(e)}")

    # Get or create user
    conn = get_db()
    try:
        user_id = get_or_create_oauth_user(conn, provider, provider_user_id, email)
        row = conn.execute(
            "SELECT u.id, u.username, u.role, u.disabled, u.org_id, COALESCE(u.scopes,'') as scopes, o.tier, o.name as org_name, o.status as org_status FROM users u LEFT JOIN organisations o ON u.org_id=o.id WHERE u.id=?",
            (user_id,),
        ).fetchone()
        if row["disabled"]:
            raise HTTPException(status_code=403, detail="Account disabled")
        token_str = make_jwt(row["id"], row["username"], row["role"],
                            org_id=row["org_id"], scopes=row["scopes"], disabled=bool(row["disabled"]), tier=row["tier"])
        create_session(conn, row["id"], token_str)
        conn.commit()
        log.info("OAuth login: provider=%s user='%s'", provider, row["username"])
        # Redirect to portal SPA with token — use OAUTH_REDIRECT_BASE (preserves port)
        redirect_url = f"{OAUTH_REDIRECT_BASE}/?aither_token={token_str}"
        log.info("OAuth redirect: %s", redirect_url)
        return RedirectResponse(url=redirect_url)
    finally:
        conn.close()

# ── Routes: LDAP ───────────────────────────────────────────────

@app.post("/v1/identity/auth/ldap")
async def ldap_login(req: LdapLoginRequest):
    """Authenticate via LDAP and return a bearer token."""
    if not LDAP_ENABLED:
        raise HTTPException(status_code=400, detail="LDAP authentication is not enabled")

    ldap_user = ldap_authenticate(req.username, req.password)
    if not ldap_user:
        log.warning("LDAP login failed for '%s'", req.username)
        raise HTTPException(status_code=401, detail="Invalid LDAP credentials")

    # Find or create local user — LDAP auto-creation REMOVED (PENDING ENTITLEMENT)
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT u.id, u.username, u.role, u.disabled, u.org_id, COALESCE(u.scopes,'') as scopes, o.tier FROM users u LEFT JOIN organisations o ON u.org_id=o.id WHERE u.username=?",
            (ldap_user["username"],),
        ).fetchone()
        if not row:
            # PENDING ENTITLEMENT: user must be provisioned by admin before login
            conn.close()
            raise HTTPException(
                status_code=403,
                detail="PENDING ENTITLEMENT: LDAP user requires admin provisioning (org, scopes, tier)"
            )

        if row["disabled"]:
            conn.close()
            raise HTTPException(status_code=403, detail="Account disabled")

        token_str = make_jwt(row["id"], row["username"], row["role"],
                            org_id=row["org_id"], scopes=row["scopes"], disabled=bool(row["disabled"]), tier=row["tier"])
        create_session(conn, row["id"], token_str)
        conn.commit()
        log.info("LDAP login: user='%s'", row["username"])
        return TokenResponse(
            token=token_str,
            user=MeResponse(id=row["id"], username=row["username"], role=row["role"]),
        )
    finally:
        conn.close()

# ── Routes: Bootstrap ──────────────────────────────────────────

@app.post("/v1/identity/bootstrap", status_code=201)
async def bootstrap():
    """Create the initial administrator account. Only works once."""
    conn = get_db()
    existing = conn.execute("SELECT COUNT(*) as cnt FROM users WHERE role='administrator'").fetchone()
    if existing["cnt"] > 0:
        conn.close()
        raise HTTPException(status_code=400, detail="Bootstrap already completed — administrator exists")

    if not ADMIN_PASS_HASH:
        conn.close()
        raise HTTPException(status_code=400, detail="IDENTITY_ADMIN_PASS environment variable not set")

    try:
        # Get or create default org for bootstrap admin
        org = conn.execute("SELECT id FROM organisations WHERE name='default'").fetchone()
        if not org:
            conn.execute("INSERT INTO organisations (name, tier, status) VALUES ('default', 'free', 'active')")
            conn.commit()
            org = conn.execute("SELECT id FROM organisations WHERE name='default'").fetchone()

        conn.execute(
            "INSERT INTO users (username, password, role, org_id, scopes) VALUES (?, ?, 'administrator', ?, 'model:14b:chat,model:32b:chat-adapter,model:32b:completion,rag:query,rag:ingest')",
            (ADMIN_USER, ADMIN_PASS_HASH, org["id"]),
        )
        conn.commit()
        log.info("Bootstrap: created initial administrator '%s'", ADMIN_USER)
        return {"message": f"Administrator '{ADMIN_USER}' created successfully"}
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=409, detail="User already exists")
    finally:
        conn.close()

# ── Routes: Local Auth ─────────────────────────────────────────

@app.post("/v1/identity/auth")
async def login(req: LoginRequest):
    """Authenticate a user and return a bearer token."""
    conn = get_db()
    row = conn.execute(
        "SELECT u.id, u.username, u.password, u.role, u.disabled, u.org_id, COALESCE(u.scopes,'') as scopes, o.tier, o.name as org_name, o.status as org_status FROM users u LEFT JOIN organisations o ON u.org_id=o.id WHERE u.username=?",
        (req.username,),
    ).fetchone()
    conn.close()

    if row is None:
        log.warning("Login failed: unknown user '%s'", req.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if row["disabled"]:
        raise HTTPException(status_code=403, detail="Account disabled")

    if not verify_password(req.password, row["password"]):
        log.warning("Login failed: wrong password for '%s'", req.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = make_jwt(row["id"], row["username"], row["role"],
                     org_id=row["org_id"], scopes=row["scopes"], disabled=bool(row["disabled"]), tier=row["tier"])

    conn = get_db()
    create_session(conn, row["id"], token)
    conn.commit()
    conn.close()

    log.info("Login: user '%s' (role=%s)", row["username"], row["role"])
    return TokenResponse(
        token=token,
        user=MeResponse(
            id=row["id"], username=row["username"], role=row["role"],
            org_id=row["org_id"], org_name=row["org_name"],
            org_status=row["org_status"], tier=row["tier"],
            scopes=row["scopes"], disabled=bool(row["disabled"]),
        ),
    )

# ── Routes: Session Management ─────────────────────────────────

@app.post("/v1/identity/logout")
async def logout(
    user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Revoke the current token by hashing the full token (matches session)."""
    token_hash_val = hash_token(credentials.credentials)
    conn = get_db()
    conn.execute(
        "UPDATE sessions SET revoked=1 WHERE token_hash=?",
        (token_hash_val,),
    )
    conn.commit()
    conn.close()
    log.info("Logout: user '%s' (token revoked)", user.get("sub"))
    return {"message": "Logged out"}

@app.get("/v1/identity/me")
async def me(user: dict = Depends(get_current_user)):
    """Get current user information including org, tier, and scopes."""
    conn = get_db()
    row = conn.execute(
        """SELECT u.id, u.username, u.role, u.disabled, u.org_id,
                  COALESCE(u.scopes,'') as scopes,
                  o.name as org_name, o.status as org_status, o.tier
           FROM users u
           LEFT JOIN organisations o ON u.org_id=o.id
           WHERE u.id=?""",
        (user["uid"],),
    ).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=401, detail="User not found")
    if row["disabled"]:
        raise HTTPException(status_code=403, detail="Account disabled")
    if row["org_id"] and row["org_status"] != "active":
        raise HTTPException(status_code=403, detail="Organisation is not active")
    # tier must be present for active organisations
    if row["org_id"] and not row["tier"]:
        raise HTTPException(status_code=403, detail="entitlement_missing: organisation tier not configured")
    return MeResponse(
        id=row["id"],
        username=row["username"],
        role=row["role"],
        org_id=row["org_id"],
        org_name=row["org_name"],
        org_status=row["org_status"],
        tier=row["tier"],
        scopes=row["scopes"],
        disabled=bool(row["disabled"]),
    )


@app.get("/v1/identity/users/lookup")
async def lookup_user_by_email(email: str = ""):
    """Look up user by email (public — for password reset)."""
    if not email:
        raise HTTPException(status_code=400, detail="email parameter required")
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, username, email FROM users WHERE email=? AND disabled=0",
            (email.strip(),),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        return {"id": row["id"], "username": row["username"], "email": row["email"]}
    finally:
        conn.close()


# ── Routes: User Management ────────────────────────────────────

@app.get("/v1/identity/users")
async def list_users(admin: dict = Depends(require_admin)):
    """List all users (admin only)."""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, username, role, created_at, disabled FROM users ORDER BY id"
    ).fetchall()
    conn.close()
    return [
        UserResponse(id=r["id"], username=r["username"], role=r["role"],
                     created_at=r["created_at"], disabled=bool(r["disabled"]))
        for r in rows
    ]

@app.post("/v1/identity/register", status_code=201)
async def register_user(req: RegisterRequest):
    """Public self-registration — creates a user with default org and basic scopes.
    No admin token required. Password must meet policy (≥16, upper, lower, digit, special)."""
    if len(req.username.strip()) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    pw_err = validate_password(req.password)
    if pw_err:
        raise HTTPException(status_code=400, detail=pw_err)

    pw_hash = hash_password(req.password)
    conn = get_db()
    try:
        # Assign default org (free tier, basic scopes)
        org = conn.execute("SELECT id FROM organisations WHERE name='default' AND status='active'").fetchone()
        org_id = org["id"] if org else None

        conn.execute(
            "INSERT INTO users (username, password, role, org_id, scopes, email) VALUES (?, ?, 'user', ?, 'model:14b:chat,rag:query', ?)",
            (req.username.strip(), pw_hash, org_id, req.email.strip()),
        )
        conn.commit()
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        log.info("Self-registration: user='%s' email='%s' id=%d", req.username, req.email, user_id)
        return {
            "id": user_id,
            "username": req.username.strip(),
            "role": "user",
            "message": "User registered successfully"
        }
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=409, detail="Username already taken")
    finally:
        conn.close()


class ResetPasswordRequest(BaseModel):
    username: str
    new_password: str


@app.post("/v1/identity/reset-password")
async def reset_password(req: ResetPasswordRequest):
    """Public password reset — updates password for given username.
    Requires password to meet policy (≥16, upper, lower, digit, special)."""
    pw_err = validate_password(req.new_password)
    if pw_err:
        raise HTTPException(status_code=400, detail=pw_err)
    conn = get_db()
    try:
        row = conn.execute("SELECT id FROM users WHERE username=?", (req.username.strip(),)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        pw_hash = hash_password(req.new_password)
        conn.execute("UPDATE users SET password=? WHERE id=?", (pw_hash, row["id"]))
        # Revoke all existing sessions for this user
        conn.execute("UPDATE sessions SET revoked=1 WHERE user_id=? AND revoked=0", (row["id"],))
        conn.commit()
        log.info("Password reset: user='%s' id=%d", req.username, row["id"])
        return {"message": "Password updated successfully"}
    finally:
        conn.close()


@app.post("/v1/identity/users", status_code=201)
async def create_user(req: UserCreate, admin: dict = Depends(require_admin)):
    """Create a new user (admin only). Requires org_id and scopes."""
    if req.role not in ("administrator", "user", "operator"):
        raise HTTPException(status_code=400, detail="Role must be 'administrator', 'operator' or 'user'")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if not req.org_id:
        raise HTTPException(status_code=400, detail="org_id is required")
    if not req.scopes or not req.scopes.strip():
        raise HTTPException(status_code=400, detail="scopes is required (comma-separated)")

    pw_hash = hash_password(req.password)
    conn = get_db()
    try:
        # Validate organisation exists and is active
        org = conn.execute(
            "SELECT id, status FROM organisations WHERE id=?", (req.org_id,)
        ).fetchone()
        if not org:
            raise HTTPException(status_code=400, detail=f"Organisation {req.org_id} does not exist")
        if org["status"] != "active":
            raise HTTPException(status_code=400, detail=f"Organisation {req.org_id} is not active")

        conn.execute(
            "INSERT INTO users (username, password, role, org_id, scopes) VALUES (?, ?, ?, ?, ?)",
            (req.username, pw_hash, req.role, req.org_id, req.scopes.strip()),
        )
        conn.commit()
        log.info("Admin '%s' created user '%s' role='%s' org=%d scopes='%s'",
                 admin.get("sub"), req.username, req.role, req.org_id, req.scopes)
        return {"message": f"User '{req.username}' created with role '{req.role}'"}
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=409, detail=f"User '{req.username}' already exists")
    finally:
        conn.close()

@app.patch("/v1/identity/users/{user_id}/role")
async def patch_user_role(
    user_id: int,
    request: Request,
    admin: dict = Depends(require_admin),
):
    """Change a user's role (admin only). Cannot demote the last administrator."""
    body = await request.json()
    new_role = body.get("role")
    if new_role not in ("administrator", "user"):
        raise HTTPException(status_code=400, detail="Role must be 'administrator' or 'user'")

    conn = get_db()
    try:
        # Prevent demoting last admin
        if new_role != "administrator":
            admin_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM users WHERE role='administrator' AND disabled=0"
            ).fetchone()["cnt"]
            target_role = conn.execute(
                "SELECT role FROM users WHERE id=?", (user_id,)
            ).fetchone()
            if target_role and target_role["role"] == "administrator" and admin_count <= 1:
                raise HTTPException(status_code=400, detail="Cannot demote the last administrator")

        conn.execute("UPDATE users SET role=? WHERE id=?", (new_role, user_id))
        conn.commit()
        log.info("Admin '%s' changed role of user %d to '%s'", admin.get("sub"), user_id, new_role)
        return {"message": f"User {user_id} role updated to '{new_role}'"}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.patch("/v1/identity/users/{user_id}/status")
async def patch_user_status(
    user_id: int,
    request: Request,
    admin: dict = Depends(require_admin),
):
    """Enable or disable a user (admin only). Cannot disable the last administrator."""
    body = await request.json()
    disabled = body.get("disabled", False)

    conn = get_db()
    try:
        # Prevent disabling last admin
        if disabled:
            admin_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM users WHERE role='administrator' AND disabled=0"
            ).fetchone()["cnt"]
            target = conn.execute(
                "SELECT role FROM users WHERE id=?", (user_id,)
            ).fetchone()
            if target and target["role"] == "administrator" and admin_count <= 1:
                raise HTTPException(status_code=400, detail="Cannot disable the last administrator")

        conn.execute("UPDATE users SET disabled=? WHERE id=?", (1 if disabled else 0, user_id))
        # When disabling user, revoke all active sessions
        if disabled:
            revoked_count = conn.execute(
                "UPDATE sessions SET revoked=1 WHERE user_id=? AND revoked=0",
                (user_id,),
            ).rowcount
            log.info("Admin '%s' disabled user %d — revoked %d sessions",
                     admin.get("sub"), user_id, revoked_count)
        conn.commit()
        log.info("Admin '%s' %s user %d", admin.get("sub"),
                 "disabled" if disabled else "enabled", user_id)
        return {"message": f"User {user_id} {'disabled' if disabled else 'enabled'}"}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.patch("/v1/identity/orgs/{org_id}/tier")
async def patch_org_tier(
    org_id: int,
    request: Request,
    admin: dict = Depends(require_admin),
):
    """Update organisation tier (admin only)."""
    body = await request.json()
    tier = body.get("tier", "").strip()
    valid_tiers = ["free", "starter", "pro", "enterprise"]
    if tier not in valid_tiers:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Valid: {', '.join(valid_tiers)}")

    conn = get_db()
    try:
        org = conn.execute("SELECT id, name FROM organisations WHERE id=?", (org_id,)).fetchone()
        if not org:
            raise HTTPException(status_code=404, detail=f"Organisation {org_id} not found")
        conn.execute("UPDATE organisations SET tier=? WHERE id=?", (tier, org_id))
        conn.commit()
        log.info("Admin '%s' changed org %d ('%s') tier → '%s'",
                 admin.get("sub"), org_id, org["name"], tier)
        return {"message": f"Organisation {org_id} tier updated to '{tier}'", "tier": tier, "org_name": org["name"]}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# ── Routes: Status ─────────────────────────────────────────────

@app.get("/v1/identity/status")
async def service_status():
    """Overall service health including user count."""
    try:
        conn = get_db()
        user_count = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"]
        admin_count = conn.execute("SELECT COUNT(*) as cnt FROM users WHERE role='administrator'").fetchone()["cnt"]
        oauth_count = conn.execute("SELECT COUNT(DISTINCT provider) as cnt FROM oauth_accounts").fetchone()["cnt"]
        conn.close()
        return StatusResponse(
            service="aither-identity",
            version="1.0.0",
            status=f"operational — {user_count} users ({admin_count} admins, {oauth_count} OAuth providers linked)",
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
