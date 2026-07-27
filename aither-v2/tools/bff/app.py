"""
Aither BFF v0.5.0 — Auth / API Token / Agent Access / User Registration

Central auth layer for MVP:
- Admin login via Kubernetes Secret credentials
- Registered user login via Argon2id
- Self-registration (invite-based)
- API token management (create, list, revoke)
- Agent access with API tokens
- User token NOT forwarded to upstream vLLM/gateway
- 32B chat adapter over completion endpoint
- Redis-backed rate limiting (inherited from Stage 06)
"""
import os
import re
import json
import time
import uuid
import secrets
import hashlib
import logging
import hmac
from datetime import datetime, timezone
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response, Cookie
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import httpx
import redis.asyncio as redis_asyncio

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError
    _argon2 = PasswordHasher()
    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False
    _argon2 = None

try:
    import jwt as pyjwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    pyjwt = None

# ---------------------------------------------------------------------------
# ── Model IDs
# ───────────────────────────────────────────────────────────────────────
MODEL_14B = "qwen-14b"
MODEL_32B = "qwen-32b-base"
# Aliases users may send
_MODEL_ALIASES = {"14b": MODEL_14B, "32b": MODEL_32B, "qwen-14b": MODEL_14B, "qwen-32b-base": MODEL_32B}

# ---------------------------------------------------------------------------
# Upstream URLs
# ---------------------------------------------------------------------------
CHAT_14B_URL = os.environ.get("BFF_14B_BASE_URL", "http://vllm-14b-instruct.aither-inference.svc:8000")
GATEWAY_32B_URL = os.environ.get("BFF_32B_GATEWAY_URL", "http://nginx-gateway-32b.aither-inference.svc:8000")
TIMEOUT = int(os.environ.get("BFF_REQUEST_TIMEOUT_SECONDS", "300"))

# ---------------------------------------------------------------------------
# Rate limiting (Stage 06)
# ---------------------------------------------------------------------------
RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"
REDIS_URL = os.environ.get("REDIS_URL", "redis://aither-redis-rate-limit.aither-inference.svc:6379/0")
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60"))
RATE_LIMIT_MAX_REQUESTS = int(os.environ.get("RATE_LIMIT_MAX_REQUESTS", "10"))

# ---------------------------------------------------------------------------
# Auth / Token settings (Stage 07.1)
# ---------------------------------------------------------------------------
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "")
AUTH_TOKEN_HASH_SECRET = os.environ.get("AUTH_TOKEN_HASH_SECRET", "")
# Upstream internal credentials — NEVER use user token here
BFF_14B_UPSTREAM_AUTH_TOKEN = os.environ.get("BFF_14B_UPSTREAM_AUTH_TOKEN", "")
BFF_32B_GATEWAY_AUTH_TOKEN = os.environ.get("BFF_32B_GATEWAY_AUTH_TOKEN", "")
TOKEN_PREFIX = "athr_"
REDIS_AUTH_NS = "aither-auth"
REDIS_TOKEN_NS = f"{REDIS_AUTH_NS}:token"
REDIS_SESSION_NS = f"{REDIS_AUTH_NS}:session"
REDIS_USER_NS = f"{REDIS_AUTH_NS}:user"
REDIS_INVITE_NS = f"{REDIS_AUTH_NS}:invite"
REDIS_USER_SESSION_NS = f"{REDIS_AUTH_NS}:user-session"

# Reserved usernames (R7-R4)
RESERVED_USERNAMES = {
    "admin", "administrator", "root", "system", "support",
    "operator", "owner", "api", "null", "undefined"
}

# Authorization policy (R7-R4)
_USER_SESSION_SCOPES = {
    "admin": ["admin"],
    "registered_user": ["model:14b:chat", "model:32b:chat-adapter"],
    "legacy_beta_user": ["model:14b:chat", "model:32b:chat-adapter"],
}

def _normalize_username(username: str) -> str:
    return username.strip().lower()

def _user_key(username_normalized: str) -> str:
    return f"{REDIS_USER_NS}:{username_normalized}"

def _user_session_key(session_id: str) -> str:
    return f"{REDIS_USER_SESSION_NS}:{session_id}"

def _invite_key(invite_hash: str) -> str:
    return f"{REDIS_INVITE_NS}:{invite_hash}"

def _hash_password_argon2(password: str) -> str:
    if not ARGON2_AVAILABLE:
        raise RuntimeError("argon2-cffi not installed")
    return _argon2.hash(password)

def _verify_password_argon2(password: str, password_hash: str) -> bool:
    if not ARGON2_AVAILABLE:
        raise RuntimeError("argon2-cffi not installed")
    try:
        return _argon2.verify(password_hash, password)
    except VerifyMismatchError:
        return False

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
logger = logging.getLogger("aither-bff")
client: httpx.AsyncClient = None
redis_client: redis_asyncio.Redis = None
redis_available = False

# ---------------------------------------------------------------------------
# Rate limiting helpers (Stage 06 — unchanged)
# ---------------------------------------------------------------------------
async def _rate_limit_key(req: Request) -> str:
    auth = req.headers.get("authorization") or req.headers.get("Authorization") or ""
    if auth:
        h = hashlib.sha256(auth.encode()).hexdigest()
        return f"rl:{h}"
    forwarded = req.headers.get("x-forwarded-for", "")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (req.client.host if req.client else "unknown")
    return f"rl:ip:{client_ip}"

async def _check_rate_limit(req: Request) -> bool:
    global redis_available
    if not RATE_LIMIT_ENABLED:
        return True
    if not redis_available:
        logger.warning("Redis unavailable — fail-open, allowing request")
        return True
    try:
        key = await _rate_limit_key(req)
        window = int(time.time()) // RATE_LIMIT_WINDOW_SECONDS
        rl_key = f"{key}:{window}"
        count = await redis_client.incr(rl_key)
        if count == 1:
            await redis_client.expire(rl_key, RATE_LIMIT_WINDOW_SECONDS + 5)
        if count > RATE_LIMIT_MAX_REQUESTS:
            logger.warning("Rate limit exceeded for key=%s count=%d", key[:20], count)
            return False
        return True
    except Exception as e:
        logger.error("Redis rate check error: %s — fail-open", str(e))
        redis_available = False
        return True

# ---------------------------------------------------------------------------
# Auth helpers (Stage 07.1)
# ---------------------------------------------------------------------------
AUTH_REQUIRED_ENDPOINTS = {
    "/api/v1/models": {"GET"},
    "/api/v1/chat": {"POST"},
    "/api/v1/completions": {"POST"},
    "/api/v1/tokens": {"GET", "POST"},
}

def _validate_auth_config() -> str:
    """Check that required auth env vars are set. Return error message or ''."""
    missing = []
    if not ADMIN_USERNAME:
        missing.append("ADMIN_USERNAME")
    if not ADMIN_PASSWORD_HASH:
        missing.append("ADMIN_PASSWORD_HASH")
    if not SESSION_SECRET:
        missing.append("SESSION_SECRET")
    if not AUTH_TOKEN_HASH_SECRET:
        missing.append("AUTH_TOKEN_HASH_SECRET")
    if not BFF_14B_UPSTREAM_AUTH_TOKEN:
        missing.append("BFF_14B_UPSTREAM_AUTH_TOKEN")
    if not BFF_32B_GATEWAY_AUTH_TOKEN:
        missing.append("BFF_32B_GATEWAY_AUTH_TOKEN")
    if missing:
        return f"Missing auth env vars: {', '.join(missing)}"
    return ""

def _hash_api_token(raw_token: str) -> str:
    """Hash an API token using HMAC-SHA256."""
    return hmac.new(
        AUTH_TOKEN_HASH_SECRET.encode(),
        raw_token.encode(),
        hashlib.sha256,
    ).hexdigest()

def _generate_api_token() -> tuple[str, str]:
    """Generate (raw_token, token_hash)."""
    raw = TOKEN_PREFIX + secrets.token_urlsafe(32)
    return raw, _hash_api_token(raw)

def _make_session_id() -> str:
    return uuid.uuid4().hex

def _session_key(session_id: str) -> str:
    return f"{REDIS_SESSION_NS}:{session_id}"

def _token_meta_key(token_hash: str) -> str:
    return f"{REDIS_TOKEN_NS}:{token_hash}"

def _token_hash_set_key() -> str:
    return f"{REDIS_TOKEN_NS}:all"

def _verify_token(raw_token: str) -> str | None:
    """Verify a bearer token. Returns token_hash or None."""
    if not raw_token.startswith(TOKEN_PREFIX):
        return None
    token_hash = _hash_api_token(raw_token)
    return token_hash

async def _load_token_meta(token_hash: str) -> dict | None:
    """Load token metadata from Redis."""
    if not redis_available:
        return None
    key = _token_meta_key(token_hash)
    data = await redis_client.get(key)
    if data is None:
        return None
    try:
        meta = json.loads(data)
        if meta.get("revoked", False):
            return None
        # Update last_used_at
        meta["last_used_at"] = datetime.now(timezone.utc).isoformat()
        await redis_client.set(key, json.dumps(meta))
        return meta
    except (json.JSONDecodeError, TypeError):
        return None

async def _authenticate_request(req: Request) -> tuple[bool, str]:
    """Authenticate incoming request.
    Returns (is_authenticated, scope_or_error).
    """
    # 1. Check session cookie for admin
    session_id = req.cookies.get("session_id", "")
    auth_header = req.headers.get("authorization") or req.headers.get("Authorization") or ""

    # Try admin session first
    if session_id and redis_available:
        session_key = _session_key(session_id)
        session_data = await redis_client.get(session_key)
        if session_data:
            try:
                sess = json.loads(session_data)
                if sess.get("role") == "admin" or sess.get("username") == ADMIN_USERNAME:
                    return True, "admin"
            except (json.JSONDecodeError, TypeError):
                pass
        # Try user session
        user_session_key = _user_session_key(session_id)
        user_session_data = await redis_client.get(user_session_key)
        if user_session_data:
            try:
                sess = json.loads(user_session_data)
                role = sess.get("role", "registered_user")
                scopes = _USER_SESSION_SCOPES.get(role, ["model:14b:chat", "model:32b:chat-adapter"])
                return True, scopes
            except (json.JSONDecodeError, TypeError):
                pass

    # Try API token (Bearer auth)
    if auth_header.startswith("Bearer "):
        raw_token = auth_header[len("Bearer "):].strip()
        token_hash = _verify_token(raw_token)
        if token_hash is None:
            return False, "Invalid token format"
        meta = await _load_token_meta(token_hash)
        if meta is None:
            return False, "Token not found or revoked"
        scopes = meta.get("scopes", [])
        return True, scopes

    # 3. Handle auth endpoints
    path = req.url.path
    if path in ("/api/v1/auth/login", "/api/v1/auth/me", "/api/v1/auth/logout", "/api/v1/auth/register"):
        pass

    return False, "Authentication required"

def _check_scope(req: Request, required_scope: str) -> bool:
    """Check if request has the required scope. Admin bypasses all scope checks."""
    scope = getattr(req.state, "auth_scope", None)
    if scope is None:
        return False
    if isinstance(scope, str) and scope == "admin":
        return True
    if isinstance(scope, list):
        return required_scope in scope
    return False

# ---------------------------------------------------------------------------
# Gateway routing (CHANGE-0022-C5)
# ---------------------------------------------------------------------------
BFF_GATEWAY_URL = os.environ.get("BFF_GATEWAY_URL", "")
BFF_GATEWAY_MODE = os.environ.get("BFF_GATEWAY_MODE", "").lower() == "true" or bool(BFF_GATEWAY_URL)
DELEGATION_PRIVATE_KEY_PATH = os.environ.get("DELEGATION_PRIVATE_KEY_PATH", "/app/delegation/private.pem")

_del_key = None  # cached RS256 private key

def _load_del_key() -> str:
    """Load delegation RS256 private key (fail-closed)."""
    global _del_key
    if _del_key is not None:
        return _del_key if _del_key is not False else ""
    try:
        with open(DELEGATION_PRIVATE_KEY_PATH) as f:
            _del_key = f.read()
        logger.info("Delegation RS256 key loaded from %s", DELEGATION_PRIVATE_KEY_PATH)
        return _del_key
    except Exception as e:
        logger.error("Delegation key missing: %s", e)
        _del_key = False
        return ""

def sign_delegation_jwt(org_id: str, user_id: str, tier: str, scopes: list, role: str = "") -> str:
    """Sign RS256 JWT for Gateway delegation. One per request. TTL ≤ 60s."""
    key = _load_del_key()
    if not key:
        raise RuntimeError("delegation_key_unavailable")
    if not JWT_AVAILABLE:
        raise RuntimeError("pyjwt not available")
    now = int(time.time())
    payload = {
        "iss": "aither-bff", "aud": "aither-gateway", "sub": user_id,
        "org_id": org_id, "user_id": user_id, "tier": tier,
        "scopes": scopes if isinstance(scopes, list) else [scopes],
        "role": role, "jti": uuid.uuid4().hex[:16],
        "iat": now, "nbf": now, "exp": now + 60,
    }
    return pyjwt.encode(payload, key, algorithm="RS256")

def _gateway_headers(req: Request) -> dict:
    """Build headers for Gateway call with delegation JWT from session identity."""
    user = getattr(req.state, "auth_user", "")
    user_id = str(getattr(req.state, "auth_user_id", user or "bff"))
    scope = getattr(req.state, "auth_scope", [])
    # Admin scope sets admin role with all model scopes
    if isinstance(scope, str) and scope == "admin":
        role = "admin"
        scopes = ["model:14b:chat", "model:32b:chat-adapter", "model:32b:completion"]
        # Admin uses known admin org with standard tier
        org_id = "admin"
        tier = "standard"
        if not user:
            user_id = "admin"
    elif isinstance(scope, str):
        role = "user"
        scopes = [scope]
        org_id = getattr(req.state, "auth_org_id", None)
        tier = getattr(req.state, "auth_tier", "free")
    elif isinstance(scope, list):
        role = getattr(req.state, "auth_role", "user")
        scopes = scope
        org_id = getattr(req.state, "auth_org_id", None)
        tier = getattr(req.state, "auth_tier", "free")
    else:
        role = "user"
        scopes = ["model:14b:chat"]
        org_id = None
        tier = "free"
    if org_id is None:
        org_id = user_id
    jwt_token = sign_delegation_jwt(org_id=org_id, user_id=user_id, tier=tier, scopes=scopes, role=role)
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {jwt_token}",
    }

# Upstream credential helpers
async def _upstream_headers() -> dict:
    """Headers for upstream calls — use internal credentials, NOT user token."""
    h = {"Content-Type": "application/json"}
    h["Authorization"] = f"Bearer {BFF_14B_UPSTREAM_AUTH_TOKEN}"
    return h

def _get_upstream_auth(model: str) -> str:
    """Return the correct upstream auth token for a given model."""
    if model == MODEL_32B:
        return BFF_32B_GATEWAY_AUTH_TOKEN
    return BFF_14B_UPSTREAM_AUTH_TOKEN

# ---------------------------------------------------------------------------
# 32B Chat adapter
# ---------------------------------------------------------------------------
def _chat_to_completion_prompt(messages: list) -> str:
    """Convert chat messages to a completion prompt for base model."""
    lines = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        lines.append(f"<|{role}|>\n{content}")
    lines.append("<|assistant|>\n")
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# Startup / Shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global client, redis_client, redis_available
    client = httpx.AsyncClient(timeout=TIMEOUT)

    auth_issue = _validate_auth_config()
    if auth_issue:
        logger.warning("Auth config issue: %s — auth endpoints may fail", auth_issue)
    else:
        logger.info("Auth config OK (secrets loaded from env)")

    try:
        redis_client = redis_asyncio.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        redis_available = True
        logger.info("Redis connected at %s", REDIS_URL)
    except Exception as e:
        redis_client = None
        redis_available = False
        logger.warning("Redis unavailable at %s: %s — fail-open for RL, auth will be PARTIAL", REDIS_URL, str(e))

    yield
    if redis_client:
        await redis_client.aclose()
    await client.aclose()

app = FastAPI(title="Aither BFF", version="0.5.0-r7r4", lifespan=lifespan)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    model: str
    messages: list
    max_tokens: int = 64
    temperature: float = 0.0

class CompletionRequest(BaseModel):
    model: str
    prompt: str
    max_tokens: int = 64
    temperature: float = 0.0

class LoginRequest(BaseModel):
    username: str
    password: str

class CreateTokenRequest(BaseModel):
    name: str = ""
    scopes: list = ["model:14b:chat", "model:32b:completion"]
    expires_at: str = ""

class RegisterRequest(BaseModel):
    username: str
    password: str
    password_confirmation: str
    invite_code: str

# ---------------------------------------------------------------------------
# Middleware: auth guard
# ---------------------------------------------------------------------------
AUTH_EXEMPT_PATHS = {"/health", "/api/v1/auth/login", "/api/v1/auth/register"}

@app.middleware("http")
async def auth_middleware(req: Request, call_next):
    path = req.url.path
    method = req.method

    if path == "/health":
        return await call_next(req)

    if path.startswith("/api/v1/auth/"):
        return await call_next(req)

    if path in AUTH_REQUIRED_ENDPOINTS and method in AUTH_REQUIRED_ENDPOINTS[path]:
        auth_ok, scope = await _authenticate_request(req)
        if not auth_ok:
            return JSONResponse(
                status_code=401,
                content={"error": scope},
            )
        req.state.auth_ok = auth_ok
        req.state.auth_scope = scope

    return await call_next(req)

# ---------------------------------------------------------------------------
# Health (no auth)
# ---------------------------------------------------------------------------
@app.get("/ready")
async def ready():
    """Readiness: checks Redis, Gateway health (if in Gateway mode), delegation key."""
    deps = {}
    critical = False
    # Redis
    try:
        if redis_client:
            await redis_client.ping()
            deps["redis"] = "ok"
        else:
            deps["redis"] = "not_connected"
            critical = True
    except Exception:
        deps["redis"] = "unavailable"
        critical = True
    # Gateway health (only in Gateway mode)
    if BFF_GATEWAY_MODE:
        try:
            hr = await client.get(f"{BFF_GATEWAY_URL}/health", timeout=5)
            hr.raise_for_status()
            deps["gateway_health"] = "ok"
        except Exception as e:
            deps["gateway_health"] = f"error: {e}"
            critical = True
        # Delegation key
        key = _load_del_key()
        if key:
            deps["delegation_key"] = "loaded"
        else:
            deps["delegation_key"] = "missing"
            critical = True
        # Gateway model catalog
        try:
            mr = await client.get(f"{BFF_GATEWAY_URL}/v1/models", timeout=5)
            mr.raise_for_status()
            models = mr.json().get("data", [])
            deps["gateway_models"] = f"{len(models)} models"
        except Exception as e:
            deps["gateway_models"] = f"error: {e}"
            critical = True
    status_str = "degraded" if critical else "ok"
    return JSONResponse({"status": status_str, "dependencies": deps}, status_code=503 if critical else 200)


@app.get("/health")
async def health():
    rl_status = "enabled" if RATE_LIMIT_ENABLED else "disabled"
    redis_s = "connected" if redis_available else "unavailable"
    auth_cfg = "configured" if not _validate_auth_config() else "partial"
    return {
        "status": "ok",
        "version": "0.5.0-r7r4",
        "rate_limit": rl_status,
        "redis": redis_s,
        "auth": auth_cfg,
    }

# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------
@app.post("/api/v1/auth/login")
async def login(req: Request):
    body = await req.json()
    if not body or not body.get("username") or not body.get("password"):
        raise HTTPException(status_code=400, detail="Username and password required")

    username = body["username"]
    password = body["password"]

    # Try admin login
    if hmac.compare_digest(username, ADMIN_USERNAME):
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        if not hmac.compare_digest(pw_hash, ADMIN_PASSWORD_HASH):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not redis_available:
            raise HTTPException(status_code=503, detail="Auth backend unavailable (Redis)")
        session_id = _make_session_id()
        session_data = json.dumps({
            "username": username, "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ip": req.client.host if req.client else "unknown",
        })
        await redis_client.setex(_session_key(session_id), 86400, session_data)
        response = JSONResponse(content={"status": "ok", "session_id": session_id, "user": {"username": username, "role": "admin"}})
        response.set_cookie(key="session_id", value=session_id, max_age=86400, httponly=True, samesite="strict", secure=False)
        logger.info("Admin login success: session=%s", session_id[:12])
        return response

    # Try registered user login
    username_normalized = _normalize_username(username)
    user_key = _user_key(username_normalized)
    user_data_raw = await redis_client.get(user_key)
    if not user_data_raw:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    try:
        user_data = json.loads(user_data_raw)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user_data.get("status") != "active":
        raise HTTPException(status_code=401, detail="Account is not active")
    if not ARGON2_AVAILABLE:
        raise HTTPException(status_code=503, detail="Auth backend unavailable")
    if not _verify_password_argon2(password, user_data.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user_data["last_login_at"] = datetime.now(timezone.utc).isoformat()
    await redis_client.set(user_key, json.dumps(user_data))
    session_id = _make_session_id()
    session_data = json.dumps({
        "user_id": user_data["user_id"], "username": username,
        "role": user_data.get("role", "registered_user"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await redis_client.setex(_user_session_key(session_id), 86400, session_data)
    response = JSONResponse(content={"status": "ok", "session_id": session_id, "user": {"username": username, "user_id": user_data["user_id"], "role": user_data.get("role", "registered_user")}})
    response.set_cookie(key="session_id", value=session_id, max_age=86400, httponly=True, samesite="strict", secure=False)
    logger.info("User login success: user=%s", username)
    return response

@app.post("/api/v1/auth/logout")
async def logout():
    response = JSONResponse(content={"status": "logged_out"})
    response.delete_cookie("session_id")
    return response

@app.get("/api/v1/auth/me")
async def auth_me(req: Request):
    session_id = req.cookies.get("session_id", "")
    if not session_id or not redis_available:
        raise HTTPException(status_code=401, detail="Not authenticated")
    # Try admin session
    session_key = _session_key(session_id)
    data = await redis_client.get(session_key)
    if data:
        try:
            sess = json.loads(data)
            return {"username": sess.get("username"), "role": "admin", "created_at": sess.get("created_at")}
        except (json.JSONDecodeError, TypeError):
            pass
    # Try user session
    user_session_key = _user_session_key(session_id)
    data = await redis_client.get(user_session_key)
    if data:
        try:
            sess = json.loads(data)
            return {"username": sess.get("username"), "role": sess.get("role", "registered_user"), "user_id": sess.get("user_id"), "created_at": sess.get("created_at")}
        except (json.JSONDecodeError, TypeError):
            pass
    raise HTTPException(status_code=401, detail="Session expired or invalid")

# ---------------------------------------------------------------------------
# User Registration (R7-R4)
# ---------------------------------------------------------------------------
@app.post("/api/v1/auth/register")
async def register(req: Request):
    if not redis_available:
        raise HTTPException(status_code=503, detail="Registration backend unavailable")
    body = await req.json()
    reg = RegisterRequest(**body)
    username_raw = reg.username.strip()
    if not username_raw or len(username_raw) < 3 or len(username_raw) > 64:
        raise HTTPException(status_code=400, detail="Username must be 3-64 characters")
    if not re.match(r'^[a-zA-Z0-9_.@-]+$', username_raw):
        raise HTTPException(status_code=400, detail="Username contains invalid characters")
    username_normalized = _normalize_username(username_raw)
    if username_normalized in RESERVED_USERNAMES:
        raise HTTPException(status_code=400, detail="This username is reserved")
    if not reg.password or len(reg.password) < 12:
        raise HTTPException(status_code=400, detail="Password must be at least 12 characters")
    if reg.password != reg.password_confirmation:
        raise HTTPException(status_code=400, detail="Password confirmation does not match")
    if reg.password.lower() == username_normalized:
        raise HTTPException(status_code=400, detail="Password must not match username")
    invite_hash = hashlib.sha256(reg.invite_code.encode()).hexdigest()
    invite_key = _invite_key(invite_hash)
    invite_data_raw = await redis_client.get(invite_key)
    if not invite_data_raw:
        raise HTTPException(status_code=403, detail="Invalid or expired invite code")
    try:
        invite_data = json.loads(invite_data_raw)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=403, detail="Invalid invite data")
    if invite_data.get("status") != "active":
        raise HTTPException(status_code=403, detail="Invite code is not active")
    expires_at = invite_data.get("expires_at", "")
    if expires_at:
        try:
            exp = datetime.fromisoformat(expires_at)
            if datetime.now(timezone.utc) > exp:
                raise HTTPException(status_code=403, detail="Invite code has expired")
        except (ValueError, TypeError):
            pass
    use_count = invite_data.get("use_count", 0)
    use_limit = invite_data.get("use_limit", 1)
    if use_count >= use_limit:
        raise HTTPException(status_code=403, detail="Invite code already used")
    if not ARGON2_AVAILABLE:
        raise HTTPException(status_code=503, detail="Password hashing unavailable")
    try:
        password_hash = _hash_password_argon2(reg.password)
    except Exception as e:
        logger.error("Argon2id hash failed: %s", str(e))
        raise HTTPException(status_code=503, detail="Password hashing failed")
    # Atomic: check username uniqueness + consume invite via Lua
    lua = """
    local user_key = KEYS[1]
    local invite_key = KEYS[2]
    if redis.call('EXISTS', user_key) == 1 then return {0, 'username_exists'} end
    local inv = redis.call('GET', invite_key)
    if not inv then return {0, 'invite_gone'} end
    local d = cjson.decode(inv)
    if d.status ~= 'active' then return {0, 'invite_not_active'} end
    if d.use_count >= d.use_limit then return {0, 'invite_used'} end
    redis.call('SET', user_key, ARGV[1])
    d.status = 'used'
    d.use_count = d.use_count + 1
    d.used_at = ARGV[2]
    d.registered_user_id = ARGV[3]
    redis.call('SET', invite_key, cjson.encode(d))
    return {1, 'ok'}
    """
    user_id = uuid.uuid4().hex
    model_scopes = invite_data.get("model_scopes", ["model:14b:chat", "model:32b:chat-adapter"])
    user_data = json.dumps({
        "user_id": user_id, "username": username_raw, "username_normalized": username_normalized,
        "password_hash": password_hash, "role": "registered_user", "status": "active",
        "model_scopes": model_scopes, "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(), "last_login_at": "",
        "failed_login_count": 0, "locked_until": "", "invite_id": invite_data.get("invite_id", ""),
    })
    invite_data["status"] = "used"
    invite_data["use_count"] = use_count + 1
    invite_data["used_at"] = datetime.now(timezone.utc).isoformat()
    invite_data["registered_user_id"] = user_id
    try:
        result = await redis_client.eval(lua, 2, _user_key(username_normalized), invite_key, user_data, json.dumps(invite_data))
    except Exception as e:
        logger.error("Registration Lua failed: %s", str(e))
        raise HTTPException(status_code=503, detail="Registration failed — backend error")
    if result[0] == 0:
        if result[1] == 'username_exists':
            raise HTTPException(status_code=409, detail="Username already taken")
        raise HTTPException(status_code=403, detail="Registration failed")
    logger.info("User registered: %s (id=%s)", username_raw, user_id)
    session_id = _make_session_id()
    await redis_client.setex(_user_session_key(session_id), 86400, json.dumps({"user_id": user_id, "username": username_raw, "role": "registered_user", "created_at": datetime.now(timezone.utc).isoformat()}))
    response = JSONResponse(content={"status": "ok", "session_id": session_id, "user": {"user_id": user_id, "username": username_raw, "role": "registered_user", "model_scopes": model_scopes}})
    response.set_cookie(key="session_id", value=session_id, max_age=86400, httponly=True, samesite="strict", secure=False)
    return response

# ---------------------------------------------------------------------------
# API Token management
# ---------------------------------------------------------------------------
@app.post("/api/v1/tokens")
async def create_token(req: Request):
    """Create a new API token. Returns raw token ONCE."""
    body_data = await req.json()
    body = CreateTokenRequest(**body_data)

    auth_ok, scope = await _authenticate_request(req)
    if not auth_ok:
        raise HTTPException(status_code=401, detail=scope)

    if not redis_available:
        raise HTTPException(status_code=503, detail="Token backend unavailable (Redis)")

    raw_token, token_hash = _generate_api_token()

    meta = {
        "token_id": uuid.uuid4().hex[:12],
        "token_hash": token_hash,
        "name": body.name or "unnamed",
        "scopes": body.scopes or ["model:14b:chat"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_used_at": "",
        "revoked": False,
        "revoked_at": "",
    }

    key = _token_meta_key(token_hash)
    await redis_client.set(key, json.dumps(meta))
    await redis_client.sadd(_token_hash_set_key(), token_hash)

    logger.info("Token created: id=%s name=%s scopes=%s", meta["token_id"], meta["name"], meta["scopes"])

    return {
        "token_id": meta["token_id"],
        "token": raw_token,
        "name": meta["name"],
        "scopes": meta["scopes"],
        "created_at": meta["created_at"],
    }

@app.get("/api/v1/tokens")
async def list_tokens(req: Request):
    """List token metadata — NO raw tokens."""
    auth_ok, scope = await _authenticate_request(req)
    if not auth_ok:
        raise HTTPException(status_code=401, detail=scope)

    if not redis_available:
        raise HTTPException(status_code=503, detail="Token backend unavailable (Redis)")

    token_hashes = await redis_client.smembers(_token_hash_set_key())
    tokens = []
    for th in token_hashes:
        key = _token_meta_key(th)
        data = await redis_client.get(key)
        if data:
            try:
                meta = json.loads(data)
                tokens.append({
                    "token_id": meta.get("token_id", ""),
                    "name": meta.get("name", "unnamed"),
                    "scopes": meta.get("scopes", []),
                    "created_at": meta.get("created_at", ""),
                    "last_used_at": meta.get("last_used_at", ""),
                    "revoked": meta.get("revoked", False),
                    "revoked_at": meta.get("revoked_at", ""),
                })
            except (json.JSONDecodeError, TypeError):
                pass

    tokens.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return {"tokens": tokens}

@app.delete("/api/v1/tokens/{token_id}")
async def revoke_token(req: Request, token_id: str):
    """Revoke a token by its token_id."""
    auth_ok, scope = await _authenticate_request(req)
    if not auth_ok:
        raise HTTPException(status_code=401, detail=scope)

    if not redis_available:
        raise HTTPException(status_code=503, detail="Token backend unavailable (Redis)")

    # Find the token by iterating token_hashes
    token_hashes = await redis_client.smembers(_token_hash_set_key())
    for th in token_hashes:
        key = _token_meta_key(th)
        data = await redis_client.get(key)
        if data:
            try:
                meta = json.loads(data)
                if meta.get("token_id") == token_id and not meta.get("revoked", False):
                    meta["revoked"] = True
                    meta["revoked_at"] = datetime.now(timezone.utc).isoformat()
                    await redis_client.set(key, json.dumps(meta))
                    logger.info("Token revoked: id=%s", token_id)
                    return {"status": "revoked", "token_id": token_id, "revoked_at": meta["revoked_at"]}
            except (json.JSONDecodeError, TypeError):
                pass

    raise HTTPException(status_code=404, detail="Token not found or already revoked")

# ---------------------------------------------------------------------------
# Chat endpoints
# ---------------------------------------------------------------------------
@app.post("/api/v1/chat")
async def chat(req: Request):
    auth_ok, scope = await _authenticate_request(req)
    if not auth_ok:
        raise HTTPException(status_code=401, detail=scope)

    if not await _check_rate_limit(req):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    body_data = await req.json()
    body = ChatRequest(**body_data)

    # ── Gateway mode (CHANGE-0022-C5): route through Aither Gateway ──
    if BFF_GATEWAY_MODE and BFF_GATEWAY_URL:
        # Resolve model alias to canonical name
        gw_model = _MODEL_ALIASES.get(body.model, body.model)
        is_32b = (body.model == MODEL_32B or body.model in ("32b",))
        if is_32b:
            payload = {
                "model": gw_model,
                "prompt": _chat_to_completion_prompt(body.messages),
                "max_tokens": body.max_tokens,
                "temperature": body.temperature,
                "stream": False,
            }
            upstream_url = f"{BFF_GATEWAY_URL}/v1/completions"
        else:
            payload = {
                "model": gw_model,
                "messages": body.messages,
                "max_tokens": body.max_tokens,
                "temperature": body.temperature,
                "stream": False,
            }
            upstream_url = f"{BFF_GATEWAY_URL}/v1/chat/completions"
        headers = _gateway_headers(req)
        try:
            resp = await client.post(upstream_url, json=payload, headers=headers, timeout=TIMEOUT)
            if resp.status_code != 200:
                error_body = (await resp.aread()).decode()
                logger.error("Gateway returned %d: %s", resp.status_code, error_body[:200])
                raise HTTPException(status_code=resp.status_code, detail=f"Gateway: {error_body[:300]}")
            return JSONResponse(content=resp.json())
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Gateway timeout")
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Gateway error: {str(e)}")

    # ── Direct mode (original production path) ──
    if body.model == MODEL_14B:
        upstream_url = f"{CHAT_14B_URL}/v1/chat/completions"
        upstream_model = "/models/Qwen2.5-14B-Instruct"
        headers = await _upstream_headers()
        payload = {
            "model": upstream_model,
            "messages": body.messages,
            "max_tokens": body.max_tokens,
            "temperature": body.temperature,
            "stream": False,
        }
    elif body.model == MODEL_32B:
        upstream_url = f"{GATEWAY_32B_URL}/v1/completions"
        upstream_model = "/models/Qwen2.5-32B-Instruct-GPTQ"
        prompt = _chat_to_completion_prompt(body.messages)
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {BFF_32B_GATEWAY_AUTH_TOKEN}"}
        payload = {
            "model": upstream_model,
            "prompt": prompt,
            "max_tokens": body.max_tokens,
            "temperature": body.temperature,
            "stream": False,
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unknown model: {body.model}")

    try:
        resp = await client.post(upstream_url, json=payload, headers=headers, timeout=TIMEOUT)
        if resp.status_code != 200:
            logger.error("Upstream %s returned %d: %s", body.model, resp.status_code, (await resp.aread()).decode()[:200])
            raise HTTPException(status_code=502, detail=f"Upstream model error: HTTP {resp.status_code}")
        return JSONResponse(content=resp.json())
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Upstream timeout")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {str(e)}")

@app.post("/api/v1/completions")
async def completions(req: Request):
    auth_ok, scope = await _authenticate_request(req)
    if not auth_ok:
        raise HTTPException(status_code=401, detail=scope)

    if not await _check_rate_limit(req):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    body_data = await req.json()
    body = CompletionRequest(**body_data)

    if body.model == MODEL_32B:
        upstream_url = f"{GATEWAY_32B_URL}/v1/completions"
        upstream_model = "/models/Qwen2.5-32B-Instruct-GPTQ"
    else:
        raise HTTPException(status_code=400, detail=f"Model {body.model} does not support completions")

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {BFF_32B_GATEWAY_AUTH_TOKEN}"}
    payload = {
        "model": upstream_model,
        "prompt": body.prompt,
        "max_tokens": body.max_tokens,
        "temperature": body.temperature,
        "stream": False,
    }

    try:
        resp = await client.post(upstream_url, json=payload, headers=headers, timeout=TIMEOUT)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Upstream error: HTTP {resp.status_code}")
        return JSONResponse(content=resp.json())
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Upstream timeout")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {str(e)}")

@app.get("/api/v1/models")
async def list_models(req: Request):
    auth_ok, scope = await _authenticate_request(req)
    if not auth_ok:
        raise HTTPException(status_code=401, detail=scope)
    return {
        "data": [
            {"id": "qwen-14b", "object": "model", "owned_by": "aither"},
            {"id": "qwen-32b-base", "object": "model", "owned_by": "aither"},
        ]
    }

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
