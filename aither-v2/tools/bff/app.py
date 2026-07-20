"""
Aither BFF v0.4.0 — Auth / API Token / Agent Access

Central auth layer for MVP:
- Admin login via Kubernetes Secret credentials
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

# ---------------------------------------------------------------------------
# Model IDs
# ---------------------------------------------------------------------------
MODEL_14B = "qwen-14b"
MODEL_32B = "qwen-32b-base"

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
    # Strip "athr_" prefix before hashing — hash is of the full raw token
    # We hash the full token for consistency
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
                if sess.get("username") == ADMIN_USERNAME:
                    return True, "admin"
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

    # 3. Handle admin login via basic auth for POST /api/v1/auth/login
    # (Login endpoint bypasses this check)
    path = req.url.path
    if path in ("/api/v1/auth/login", "/api/v1/auth/me", "/api/v1/auth/logout"):
        # These are handled by their own endpoints
        pass

    return False, "Authentication required"

# ---------------------------------------------------------------------------
# Upstream credential helpers
# ---------------------------------------------------------------------------
async def _upstream_headers() -> dict:
    """Headers for upstream calls — use internal credentials, NOT user token."""
    h = {"Content-Type": "application/json"}
    # 14B and 32B gateway both need auth
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
    """Convert chat messages to a completion prompt for base model.
    Simple but functional for MVP.
    """
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

    # Check auth config
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

app = FastAPI(title="Aither BFF", version="0.4.0", lifespan=lifespan)

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

# ---------------------------------------------------------------------------
# Middleware: auth guard
# ---------------------------------------------------------------------------
AUTH_EXEMPT_PATHS = {"/health", "/api/v1/auth/login"}

@app.middleware("http")
async def auth_middleware(req: Request, call_next):
    path = req.url.path
    method = req.method

    # Health is always public
    if path == "/health":
        return await call_next(req)

    # Auth login/logout/me are handled by their own endpoints
    if path.startswith("/api/v1/auth/"):
        return await call_next(req)

    # Check if endpoint requires auth
    if path in AUTH_REQUIRED_ENDPOINTS and method in AUTH_REQUIRED_ENDPOINTS[path]:
        auth_ok, scope = await _authenticate_request(req)
        if not auth_ok:
            return JSONResponse(
                status_code=401,
                content={"error": scope},
            )
        # Store auth info in request state for downstream use
        req.state.auth_ok = auth_ok
        req.state.auth_scope = scope

    return await call_next(req)

# ---------------------------------------------------------------------------
# Health (no auth)
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    rl_status = "enabled" if RATE_LIMIT_ENABLED else "disabled"
    redis_s = "connected" if redis_available else "unavailable"
    auth_cfg = "configured" if not _validate_auth_config() else "partial"
    return {
        "status": "ok",
        "version": "0.4.0",
        "rate_limit": rl_status,
        "redis": redis_s,
        "auth": auth_cfg,
    }

# ---------------------------------------------------------------------------
# Admin auth endpoints
# ---------------------------------------------------------------------------
@app.post("/api/v1/auth/login")
async def login(req: Request):
    body = await req.json()
    if not body or not body.get("username") or not body.get("password"):
        raise HTTPException(status_code=400, detail="Username and password required")

    username = body["username"]
    password = body["password"]

    # Constant-time comparison
    if not hmac.compare_digest(username, ADMIN_USERNAME):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    if not hmac.compare_digest(pw_hash, ADMIN_PASSWORD_HASH):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not redis_available:
        raise HTTPException(status_code=503, detail="Auth backend unavailable (Redis)")

    # Create session
    session_id = _make_session_id()
    session_data = json.dumps({
        "username": body.username,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "ip": req.client.host if req.client else "unknown",
    })
    session_key = _session_key(session_id)
    await redis_client.setex(session_key, 86400, session_data)  # 24h TTL

    # Set cookie
    response = JSONResponse(content={"status": "ok", "session_id": session_id})
    response.set_cookie(
        key="session_id",
        value=session_id,
        max_age=86400,
        httponly=True,
        samesite="strict",
        secure=False,  # Set True in production with HTTPS
    )
    logger.info("Admin login success: session=%s ip=%s", session_id[:12], req.client.host if req.client else "?")
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
    session_key = _session_key(session_id)
    data = await redis_client.get(session_key)
    if not data:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    try:
        sess = json.loads(data)
        return {"username": sess.get("username"), "created_at": sess.get("created_at")}
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=500, detail="Invalid session data")

# ---------------------------------------------------------------------------
# API Token management
# ---------------------------------------------------------------------------
@app.post("/api/v1/tokens")
async def create_token(req: Request):
    """Create a new API token. Returns raw token ONCE."""
    body_data = await req.json()
    body = CreateTokenRequest(**body_data)

    # Check auth
    auth_ok, scope = await _authenticate_request(req)
    if not auth_ok:
        raise HTTPException(status_code=401, detail=scope)
    if isinstance(scope, list) and "tokens:create" not in scope and "admin" not in (scope if not isinstance(scope, str) else scope if scope == "admin" else ""):
        raise HTTPException(status_code=403, detail="Insufficient scope: tokens:create required")

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
    # Also add to the hash set for listing
    await redis_client.sadd(_token_hash_set_key(), token_hash)

    logger.info("Token created: id=%s name=%s scopes=%s", meta["token_id"], meta["name"], meta["scopes"])

    # Return raw token ONCE
    return {
        "token_id": meta["token_id"],
        "token": raw_token,  # Only shown once!
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
    if isinstance(scope, list) and "tokens:read" not in scope and "admin" not in (scope if isinstance(scope, str) and scope == "admin" else ""):
        raise HTTPException(status_code=403, detail="Insufficient scope: tokens:read required")

    if not redis_available:
        raise HTTPException(status_code=503, detail="Token backend unavailable (Redis)")

    token_hashes = await redis_client.smembers(_token_hash_set_key())
    tokens = []
    for th in token_hashes:
        data = await redis_client.get(_token_meta_key(th))
        if data:
            try:
                meta = json.loads(data)
                # Strip hash — never expose raw hash either
                display = {
                    "token_id": meta.get("token_id"),
                    "name": meta.get("name"),
                    "scopes": meta.get("scopes"),
                    "created_at": meta.get("created_at"),
                    "last_used_at": meta.get("last_used_at"),
                    "revoked": meta.get("revoked", False),
                    "revoked_at": meta.get("revoked_at", ""),
                }
                tokens.append(display)
            except (json.JSONDecodeError, TypeError):
                pass

    return {"tokens": tokens}

@app.delete("/api/v1/tokens/{token_id}")
async def revoke_token(token_id: str, req: Request):
    """Revoke an API token by token_id."""
    auth_ok, scope = await _authenticate_request(req)
    if not auth_ok:
        raise HTTPException(status_code=401, detail=scope)
    if isinstance(scope, list) and "tokens:revoke" not in scope and "admin" not in (scope if isinstance(scope, str) and scope == "admin" else ""):
        raise HTTPException(status_code=403, detail="Insufficient scope: tokens:revoke required")

    if not redis_available:
        raise HTTPException(status_code=503, detail="Token backend unavailable (Redis)")

    # Find token by token_id
    token_hashes = await redis_client.smembers(_token_hash_set_key())
    found = False
    for th in token_hashes:
        data = await redis_client.get(_token_meta_key(th))
        if data:
            try:
                meta = json.loads(data)
                if meta.get("token_id") == token_id:
                    meta["revoked"] = True
                    meta["revoked_at"] = datetime.now(timezone.utc).isoformat()
                    await redis_client.set(_token_meta_key(th), json.dumps(meta))
                    found = True
                    logger.info("Token revoked: id=%s name=%s", token_id, meta.get("name", "?"))
                    break
            except (json.JSONDecodeError, TypeError):
                pass

    if not found:
        raise HTTPException(status_code=404, detail=f"Token not found: {token_id}")

    return {"status": "revoked", "token_id": token_id}

# ---------------------------------------------------------------------------
# Model endpoints (auth-protected by middleware + rate limited)
# ---------------------------------------------------------------------------
@app.get("/api/v1/models")
async def list_models(req: Request):
    # Rate limit check
    allowed = await _check_rate_limit(req)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")

    return {
        "models": [
            {"id": "14b", "name": MODEL_14B, "type": "chat"},
            {"id": "32b", "name": MODEL_32B, "type": "completion"},
        ]
    }

@app.post("/api/v1/chat")
async def chat(req: Request):
    body = await req.json()
    model = body.get("model", "")

    # Rate limit check
    allowed = await _check_rate_limit(req)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")

    if model == "32b" or model == MODEL_32B:
        # 32B chat adapter over completion
        messages = body.get("messages", [])
        prompt = _chat_to_completion_prompt(messages)
        completion_body = {
            "model": MODEL_32B,
            "prompt": prompt,
            "max_tokens": body.get("max_tokens", 64),
            "temperature": body.get("temperature", 0.0),
        }
        upstream_token = _get_upstream_auth(MODEL_32B)
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {upstream_token}"}
        url = f"{GATEWAY_32B_URL}/v1/completions"
        async with client.stream("POST", url, json=completion_body, headers=headers) as resp:
            content = await resp.aread()
            return Response(
                content=content,
                status_code=resp.status_code,
                media_type=resp.headers.get("content-type", "application/json"),
            )

    if model == "14b" or model == MODEL_14B:
        body["model"] = MODEL_14B
        upstream_token = _get_upstream_auth(MODEL_14B)
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {upstream_token}"}
        url = f"{CHAT_14B_URL}/v1/chat/completions"
        async with client.stream("POST", url, json=body, headers=headers) as resp:
            content = await resp.aread()
            return Response(
                content=content,
                status_code=resp.status_code,
                media_type=resp.headers.get("content-type", "application/json"),
            )

    raise HTTPException(status_code=400, detail=f"Unknown model: {model}")

@app.post("/api/v1/completions")
async def completions(req: Request):
    body = await req.json()
    model = body.get("model", "")

    # Rate limit check
    allowed = await _check_rate_limit(req)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")

    if model == "32b" or model == MODEL_32B:
        body["model"] = MODEL_32B
        upstream_token = _get_upstream_auth(MODEL_32B)
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {upstream_token}"}
        url = f"{GATEWAY_32B_URL}/v1/completions"
    elif model == "14b" or model == MODEL_14B:
        body["model"] = MODEL_14B
        upstream_token = _get_upstream_auth(MODEL_14B)
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {upstream_token}"}
        url = f"{CHAT_14B_URL}/v1/completions"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model}")

    async with client.stream("POST", url, json=body, headers=headers) as resp:
        content = await resp.aread()
        return Response(
            content=content,
            status_code=resp.status_code,
            media_type=resp.headers.get("content-type", "application/json"),
        )

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000)
