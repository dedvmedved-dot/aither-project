# Aither Portal Backend (BFF)
#
# Environment variables:
#   PORTAL_IDENTITY_URL      — Identity service URL (default: http://aither-identity:8000)
#   PORTAL_AI_PLATFORM_URL   — AI Platform URL (default: http://aither-ai-platform:8000)
#   PORTAL_LOG_LEVEL         — logging level (default: INFO)
#   PORTAL_CORS_ORIGIN       — Allowed CORS origin (default: *)
#   PORTAL_GATEWAY_URL       — Gateway URL (default: http://aither-gateway:8000)
#   PORTAL_GATEWAY_ADMIN_KEY — Gateway X-Admin-Key for admin operations
#   PORTAL_JWT_PRIVATE_KEY   — RS256 private key PEM for delegation JWT
#   PORTAL_JWT_PRIVATE_KEY_FILE — alternative: path to private key file

import os
import json
import logging
import time
import uuid
import random
import smtplib
import threading
from email.mime.text import MIMEText
from datetime import datetime, timezone

import httpx
import jwt as pyjwt
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import prometheus_client
from prometheus_client import Counter, Histogram, Gauge

# ── Configuration ──────────────────────────────────────────────

IDENTITY_URL = os.environ.get("PORTAL_IDENTITY_URL", "http://aither-identity:8000")
AI_PLATFORM_URL = os.environ.get("PORTAL_AI_PLATFORM_URL", "http://aither-ai-platform:8000")
GATEWAY_URL = os.environ.get("PORTAL_GATEWAY_URL", "http://aither-gateway.aither-inference.svc:8000")
GATEWAY_ADMIN_KEY = os.environ.get("PORTAL_GATEWAY_ADMIN_KEY", "")
LOG_LEVEL = os.environ.get("PORTAL_LOG_LEVEL", "INFO").upper()
CORS_ORIGIN = os.environ.get("PORTAL_CORS_ORIGIN", "http://localhost:3000")

# Delegation JWT private key
_JWT_PRIVATE_KEY = os.environ.get("PORTAL_JWT_PRIVATE_KEY", "")
if not _JWT_PRIVATE_KEY:
    _key_file = os.environ.get("PORTAL_JWT_PRIVATE_KEY_FILE", "/app/delegation/private.pem")
    try:
        with open(_key_file) as f:
            _JWT_PRIVATE_KEY = f.read()
    except FileNotFoundError:
        log = logging.getLogger("aither-portal-bff")
        log.warning("JWT private key not found at %s — delegation JWTs will fail", _key_file)

DELEGATION_JWT_TTL = 60  # seconds

# ── SMTP / Email config ────────────────────────────────────────
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT") or "465")
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM") or SMTP_USER or "aither@fb1.spb.ru"
REGISTRATION_CODE_TTL = 90  # seconds

# In-memory pending registrations: {reg_token: {username, password, email, code, created_at}}
_pending_registrations: dict = {}
_pending_lock = threading.Lock()

# Upstream model credentials (server-side, from K8s Secrets — never returned to browser)
UPSTREAM_14B_URL = os.environ.get("UPSTREAM_14B_URL", "http://vllm-14b-instruct.aither-inference.svc:8000")
UPSTREAM_14B_TOKEN = os.environ.get("UPSTREAM_14B_TOKEN", "")
UPSTREAM_32B_URL = os.environ.get("UPSTREAM_32B_URL", "http://nginx-gateway-32b.aither-inference.svc:8000")
UPSTREAM_32B_TOKEN = os.environ.get("UPSTREAM_32B_TOKEN", "")
# In production, set PORTAL_CORS_ORIGIN to the Portal Frontend URL.
# Example: PORTAL_CORS_ORIGIN=https://portal.aither.example.com
# Multiple origins are not supported by this middleware — use a reverse proxy for complex rules.

class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter."""
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "aither-portal-bff",
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
log = logging.getLogger("aither-portal-bff")
log.propagate = False
_handler = logging.StreamHandler()
_handler.setFormatter(JSONFormatter())
log.addHandler(_handler)

# ── HTTP client ────────────────────────────────────────────────

client: httpx.AsyncClient | None = None

async def get_client() -> httpx.AsyncClient:
    global client
    if client is None:
        client = httpx.AsyncClient(base_url=IDENTITY_URL, timeout=10.0)
    return client

# In-memory cache of full API keys per user — REMOVED (R7-R5-EMG-FE-02 S4)
# Chat now uses delegation JWT (Variant A), not raw API keys.
# No automatic key creation on cache miss. No process-memory credential storage.
# _user_api_keys: dict[str, str] = {}

# ── Auth helpers ────────────────────────────────────────────────

async def _get_user_from_token(request: Request) -> dict:
    """Validate Bearer token against Identity, return user dict with org_id, scopes, tier, org_status, disabled."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        async with httpx.AsyncClient(base_url=IDENTITY_URL, timeout=10.0) as ic:
            r = await ic.get("/v1/identity/me", headers={"Authorization": auth})
            if r.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid token")
            user_data = r.json()
            if user_data.get("disabled"):
                raise HTTPException(status_code=403, detail="Account disabled")
            return user_data
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Identity service unreachable")

def _check_chat_entitlement(user: dict, model: str) -> None:
    """Verify user has entitlement to use the specified model.

    Strict model allowlist: only qwen-14b and qwen-32b-base permitted.
    Unknown models → 400 BEFORE any upstream call.
    """
    # Strict model allowlist
    ALLOWED_MODELS = {"qwen-14b", "qwen-32b-base"}
    model_lower = model.lower().strip()
    if model_lower not in ALLOWED_MODELS:
        raise HTTPException(status_code=400, detail=f"unknown_model: '{model}' not in allowlist. Available: qwen-14b, qwen-32b-base")

    # Organisation must be assigned and active
    org_id = user.get("org_id")
    if not org_id:
        raise HTTPException(status_code=403, detail="entitlement_missing: no organisation assigned")
    if user.get("org_status") != "active":
        raise HTTPException(status_code=403, detail="entitlement_missing: organisation is not active")
    # Tier must be present
    if not user.get("tier"):
        raise HTTPException(status_code=403, detail="entitlement_missing: no tier assigned")
    # Model-specific scope enforcement
    scopes_str = (user.get("scopes") or "").strip()
    scopes = [s.strip() for s in scopes_str.split(",") if s.strip()]
    if model_lower == "qwen-32b-base":
        if "model:32b:chat-adapter" not in scopes:
            raise HTTPException(status_code=403, detail="entitlement_missing: scope 'model:32b:chat-adapter' required for qwen-32b-base")
    else:  # qwen-14b
        if "model:14b:chat" not in scopes:
            raise HTTPException(status_code=403, detail="entitlement_missing: scope 'model:14b:chat' required for qwen-14b")

def _require_admin(user: dict) -> None:
    """Raise 403 if user is not admin."""
    if user.get("role") not in ("admin", "administrator"):
        raise HTTPException(status_code=403, detail="Admin role required")

def _require_monitoring_role(user: dict) -> None:
    """Raise 403 if user is not admin or operator.
    Monitoring: administrator=full, operator=monitoring only, user=none.
    """
    role = user.get("role", "")
    if role not in ("admin", "administrator", "operator"):
        raise HTTPException(status_code=403, detail="Admin or operator role required")

def _mint_delegation_jwt(user: dict) -> str:
    """Create a short-lived RS256 delegation JWT for Gateway.

    Claims: iss=aither-bff, aud=aither-gateway, org_id from identity,
    tier from billing, actual scopes from identity. TTL ≤ 60s.
    NO FALLBACKS — empty org/scopes/tier → 403.
    """
    if not _JWT_PRIVATE_KEY:
        raise HTTPException(status_code=500, detail="Delegation JWT signing key not configured")
    now = int(time.time())
    org_id = user.get("org_id")
    if not org_id:
        raise HTTPException(status_code=403, detail="entitlement_missing: org_id not assigned")
    org_id = str(org_id)
    scopes_str = (user.get("scopes") or "").strip()
    if not scopes_str:
        raise HTTPException(status_code=403, detail="entitlement_missing: no scopes assigned")
    scopes = [s.strip() for s in scopes_str.split(",") if s.strip()]
    if not scopes:
        raise HTTPException(status_code=403, detail="entitlement_missing: empty scopes")
    tier = user.get("tier")
    if not tier:
        raise HTTPException(status_code=403, detail="entitlement_missing: tier not assigned")
    payload = {
        "iss": "aither-bff",
        "aud": "aither-gateway",
        "sub": user.get("username", ""),
        "user_id": str(user.get("id", "")),
        "org_id": org_id,
        "role": user.get("role", "user"),
        "tier": user.get("tier", "free"),  # from billing config
        "scopes": scopes,
        "jti": uuid.uuid4().hex[:16],
        "iat": now,
        "nbf": now,
        "exp": now + DELEGATION_JWT_TTL,
    }
    return pyjwt.encode(payload, _JWT_PRIVATE_KEY, algorithm="RS256")

# ── Models ─────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    user: dict

class UserInfo(BaseModel):
    id: int
    username: str
    role: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str

class VerifyRegistrationRequest(BaseModel):
    registration_token: str
    code: str

# ── Application ────────────────────────────────────────────────

app = FastAPI(
    title="Aither Portal Backend (BFF)",
    version="0.6.0-r7r7-c2-d18",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN] if CORS_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Prometheus Metrics ──────────────────────────────────────────

metrics_uptime = Gauge("portal_backend_uptime_seconds", "Service uptime in seconds")
metrics_http_requests_total = Counter(
    "portal_backend_http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "endpoint", "status_code"],
)
metrics_http_request_duration_seconds = Histogram(
    "portal_backend_http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
metrics_active_requests = Gauge(
    "portal_backend_active_requests", "Currently active requests"
)
metrics_memory_usage_bytes = Gauge(
    "portal_backend_memory_usage_bytes",
    "Current process memory usage in bytes",
)
metrics_errors_total = Counter(
    "portal_backend_errors_total",
    "Total errors by type",
    labelnames=["type"],
)

APP_START_TIME = time.time()


# ── Metrics ASGI Middleware ─────────────────────────────────────

async def metrics_middleware(request: Request, call_next):
    """Instrument HTTP requests with Prometheus metrics."""
    # Update global gauges opportunistically on each request
    metrics_uptime.set(time.time() - APP_START_TIME)
    try:
        # Read RSS memory from /proc/self/status (Linux)
        with open("/proc/self/status") as _f:
            for _line in _f:
                if _line.startswith("VmRSS:"):
                    metrics_memory_usage_bytes.set(
                        int(_line.split()[1]) * 1024
                    )
                    break
    except Exception:
        pass

    # Track active requests
    metrics_active_requests.inc()
    start_time = time.time()

    try:
        response = await call_next(request)

        # Record request duration
        duration = time.time() - start_time

        # Normalize endpoint path to avoid unbounded label cardinality
        endpoint = request.url.path

        metrics_http_request_duration_seconds.labels(
            method=request.method, endpoint=endpoint
        ).observe(duration)

        metrics_http_requests_total.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=response.status_code,
        ).inc()

        return response
    except Exception as exc:
        duration = time.time() - start_time
        endpoint = request.url.path

        metrics_http_request_duration_seconds.labels(
            method=request.method, endpoint=endpoint
        ).observe(duration)

        metrics_http_requests_total.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=500,
        ).inc()

        metrics_errors_total.labels(type="internal").inc()
        raise
    finally:
        metrics_active_requests.dec()


app.middleware("http")(metrics_middleware)


# ── Routes ─────────────────────────────────────────────────────

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint for scraping."""
    return prometheus_client.generate_latest()


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.6.0-r7r7-c2-d18"}

@app.get("/ready")
async def ready():
    try:
        c = await get_client()
        r = await c.get("/ready")
        if r.status_code == 200:
            return {"status": "ok", "identity": "connected"}
        return {"status": "degraded", "identity": r.json()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Identity service unreachable: {e}")

@app.get("/version")
async def version():
    return {"service": "aither-portal-backend", "version": "0.6.0-r7r7-c2-d18", "build": "stage15"}

@app.post("/api/v1/auth/login")
async def login(req: LoginRequest):
    """Proxy login to Identity service."""
    try:
        c = await get_client()
        r = await c.post("/v1/identity/auth", json=req.model_dump())
        if r.status_code == 200:
            data = r.json()
            log.info("Login: user='%s'", req.username)
            return data
        elif r.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        else:
            log.warning("Login failed (status %d): user='%s'", r.status_code, req.username)
            raise HTTPException(status_code=r.status_code, detail=r.json().get("detail", "Login failed"))
    except httpx.RequestError as e:
        log.error("Identity unreachable during login: %s", e)
        raise HTTPException(status_code=503, detail="Identity service unavailable")

@app.post("/api/v1/auth/logout")
async def logout(request: Request):
    """Proxy logout to Identity service."""
    auth = request.headers.get("Authorization", "")
    try:
        c = await get_client()
        r = await c.post("/v1/identity/logout", headers={"Authorization": auth})
        if r.status_code == 200:
            return r.json()
        raise HTTPException(status_code=r.status_code, detail=r.json().get("detail", "Logout failed"))
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Identity service unavailable: {e}")

# ── Email sending ────────────────────────────────────────────────

def _send_verification_email(to_email: str, code: str) -> bool:
    """Send a 6-digit verification code via SMTP. Returns True on success."""
    if not SMTP_HOST:
        log.warning("SMTP_HOST not configured — cannot send email to %s (code: %s)", to_email, code)
        return False
    try:
        subject = "Aither — Код подтверждения регистрации"
        body = (
            f"Здравствуйте!\n\n"
            f"Ваш код подтверждения для регистрации в Aither: {code}\n\n"
            f"Код действителен в течение {REGISTRATION_CODE_TTL} секунд.\n"
            f"Если вы не запрашивали регистрацию, проигнорируйте это письмо.\n\n"
            f"— Команда Aither"
        )
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = to_email

        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
                if SMTP_USER and SMTP_PASS:
                    smtp.login(SMTP_USER, SMTP_PASS)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
                smtp.starttls()
                if SMTP_USER and SMTP_PASS:
                    smtp.login(SMTP_USER, SMTP_PASS)
                smtp.send_message(msg)
        log.info("Verification code sent to %s", to_email)
        return True
    except Exception as e:
        log.error("Failed to send verification email to %s: %s", to_email, e)
        return False

# ── Registration with email verification ─────────────────────────

def _cleanup_expired_registrations():
    """Remove expired pending registrations."""
    now = time.time()
    with _pending_lock:
        expired = [k for k, v in _pending_registrations.items()
                   if now - v["created_at"] > REGISTRATION_CODE_TTL + 30]
        for k in expired:
            del _pending_registrations[k]

@app.post("/api/v1/auth/register")
async def register(req: RegisterRequest):
    """Step 1: Start registration — send verification code to email."""
    # Cleanup expired first
    _cleanup_expired_registrations()

    # Validate inputs
    if not req.username or len(req.username.strip()) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if not req.password or len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if not req.email or "@" not in req.email:
        raise HTTPException(status_code=400, detail="Invalid email address")

    # Check username uniqueness via Identity
    try:
        c = await get_client()
        # Try a quick check — if user exists, identity returns their info
        r = await c.get(f"/v1/identity/users/check?username={req.username.strip()}")
        if r.status_code == 200:
            raise HTTPException(status_code=409, detail="Username already taken")
    except HTTPException:
        raise
    except Exception:
        pass  # If check endpoint doesn't exist, proceed

    # Generate 6-digit code
    code = str(random.randint(100000, 999999))
    reg_token = uuid.uuid4().hex

    # Store pending registration
    with _pending_lock:
        _pending_registrations[reg_token] = {
            "username": req.username.strip(),
            "password": req.password,
            "email": req.email.strip(),
            "code": code,
            "created_at": time.time(),
        }

    # Send email
    email_sent = _send_verification_email(req.email.strip(), code)
    if not email_sent:
        # If email not sent, still allow for testing (code returned in dev mode)
        log.warning("Email not sent for %s — registration pending with code in logs only", req.email)

    log.info("Registration started: user='%s' email='%s'", req.username, req.email)
    return {
        "status": "ok" if email_sent else "email_failed",
        "registration_token": reg_token,
        "message": "Код подтверждения отправлен на email" if email_sent
                   else "Не удалось отправить email. Код доступен в логах.",
        "expires_in": REGISTRATION_CODE_TTL,
    }

@app.post("/api/v1/auth/verify-registration")
async def verify_registration(req: VerifyRegistrationRequest):
    """Step 2: Verify code and create user in Identity."""
    _cleanup_expired_registrations()

    with _pending_lock:
        pending = _pending_registrations.pop(req.registration_token, None)

    if not pending:
        raise HTTPException(status_code=404, detail="Registration session not found or expired")

    # Check expiry
    if time.time() - pending["created_at"] > REGISTRATION_CODE_TTL:
        raise HTTPException(status_code=410, detail="Verification code expired — please register again")

    # Check code
    if pending["code"] != req.code.strip():
        raise HTTPException(status_code=400, detail="Неверный код подтверждения")

    # Create user via Identity
    try:
        c = await get_client()
        r = await c.post("/v1/identity/register", json={
            "username": pending["username"],
            "password": pending["password"],
        })
        if r.status_code == 201 or r.status_code == 200:
            user_data = r.json()
            log.info("Registration complete: user='%s' email='%s'",
                     pending["username"], pending["email"])
            return {
                "status": "ok",
                "message": "Регистрация успешно завершена! Теперь вы можете войти.",
                "user": user_data,
            }
        elif r.status_code == 409:
            raise HTTPException(status_code=409, detail="Username already taken")
        else:
            raise HTTPException(status_code=r.status_code,
                                detail=r.json().get("detail", "User creation failed"))
    except HTTPException:
        raise
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Identity service unavailable: {e}")

@app.get("/api/v1/auth/me")
async def me(request: Request):
    """Get current user info."""
    auth = request.headers.get("Authorization", "")
    try:
        c = await get_client()
        r = await c.get("/v1/identity/me", headers={"Authorization": auth})
        if r.status_code == 200:
            return r.json()
        raise HTTPException(status_code=r.status_code, detail=r.json().get("detail", "Not authenticated"))
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Identity service unavailable: {e}")

@app.get("/api/v1/status")
async def portal_status():
    """Aggregated system status."""
    results = {"portal-backend": "healthy"}
    try:
        c = await get_client()
        r = await c.get("/v1/identity/status")
        results["identity"] = r.json() if r.status_code == 200 else "unreachable"
    except Exception:
        results["identity"] = "unreachable"
    try:
        ac = httpx.AsyncClient(base_url=AI_PLATFORM_URL, timeout=5.0)
        r = await ac.get("/health")
        results["ai-platform"] = "healthy" if r.status_code == 200 else "unreachable"
        await ac.aclose()
    except Exception:
        results["ai-platform"] = "unreachable"
    return {"status": "operational" if all(v == "healthy" or isinstance(v, dict) for v in results.values()) else "degraded", "services": results}

# ── AI Platform API Proxy ──────────────────────────────────────

@app.get("/api/v1/models")
async def proxy_models(request: Request):
    """Proxy to AI Platform: GET /api/v1/models."""
    auth = request.headers.get("Authorization", "")
    try:
        async with httpx.AsyncClient(base_url=AI_PLATFORM_URL, timeout=10.0) as ac:
            r = await ac.get("/api/v1/models", headers={"Authorization": auth})
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"AI Platform unreachable: {e}")

@app.post("/api/v1/models")
async def proxy_create_model(request: Request):
    """Proxy to AI Platform: POST /api/v1/models."""
    auth = request.headers.get("Authorization", "")
    body = await request.body()
    try:
        async with httpx.AsyncClient(base_url=AI_PLATFORM_URL, timeout=10.0) as ac:
            r = await ac.post("/api/v1/models", content=body, headers={"Authorization": auth, "Content-Type": "application/json"})
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"AI Platform unreachable: {e}")

@app.get("/api/v1/api-keys")
async def proxy_api_keys(request: Request):
    """Proxy to AI Platform: GET /api/v1/api-keys."""
    auth = request.headers.get("Authorization", "")
    try:
        async with httpx.AsyncClient(base_url=AI_PLATFORM_URL, timeout=10.0) as ac:
            r = await ac.get("/api/v1/api-keys", headers={"Authorization": auth})
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"AI Platform unreachable: {e}")

@app.post("/api/v1/api-keys")
async def proxy_create_api_key(request: Request):
    """Proxy to AI Platform: POST /api/v1/api-keys."""
    auth = request.headers.get("Authorization", "")
    body = await request.body()
    try:
        async with httpx.AsyncClient(base_url=AI_PLATFORM_URL, timeout=10.0) as ac:
            r = await ac.post("/api/v1/api-keys", content=body, headers={"Authorization": auth, "Content-Type": "application/json"})
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"AI Platform unreachable: {e}")

@app.delete("/api/v1/api-keys/{key_id}")
async def proxy_revoke_api_key(key_id: int, request: Request):
    """Proxy to AI Platform: DELETE /api/v1/api-keys/{id}."""
    auth = request.headers.get("Authorization", "")
    try:
        async with httpx.AsyncClient(base_url=AI_PLATFORM_URL, timeout=10.0) as ac:
            r = await ac.delete(f"/api/v1/api-keys/{key_id}", headers={"Authorization": auth})
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"AI Platform unreachable: {e}")

@app.get("/api/v1/assistants")
async def proxy_assistants(request: Request):
    """Proxy to AI Platform: GET /api/v1/assistants."""
    auth = request.headers.get("Authorization", "")
    try:
        async with httpx.AsyncClient(base_url=AI_PLATFORM_URL, timeout=10.0) as ac:
            r = await ac.get("/api/v1/assistants", headers={"Authorization": auth})
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"AI Platform unreachable: {e}")

@app.post("/api/v1/assistants")
async def proxy_create_assistant(request: Request):
    """Proxy to AI Platform: POST /api/v1/assistants."""
    auth = request.headers.get("Authorization", "")
    body = await request.body()
    try:
        async with httpx.AsyncClient(base_url=AI_PLATFORM_URL, timeout=10.0) as ac:
            r = await ac.post("/api/v1/assistants", content=body, headers={"Authorization": auth, "Content-Type": "application/json"})
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"AI Platform unreachable: {e}")

@app.get("/api/v1/conversations")
async def proxy_conversations(request: Request):
    """Proxy to AI Platform: GET /api/v1/conversations."""
    auth = request.headers.get("Authorization", "")
    try:
        async with httpx.AsyncClient(base_url=AI_PLATFORM_URL, timeout=10.0) as ac:
            r = await ac.get("/api/v1/conversations", headers={"Authorization": auth})
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"AI Platform unreachable: {e}")

@app.post("/api/v1/conversations")
async def proxy_create_conversation(request: Request):
    """Proxy to AI Platform: POST /api/v1/conversations."""
    auth = request.headers.get("Authorization", "")
    body = await request.body()
    try:
        async with httpx.AsyncClient(base_url=AI_PLATFORM_URL, timeout=10.0) as ac:
            r = await ac.post("/api/v1/conversations", content=body, headers={"Authorization": auth, "Content-Type": "application/json"})
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"AI Platform unreachable: {e}")

@app.get("/api/v1/conversations/{conv_id}")
async def proxy_get_conversation(conv_id: int, request: Request):
    """Proxy to AI Platform: GET /api/v1/conversations/{id}."""
    auth = request.headers.get("Authorization", "")
    try:
        async with httpx.AsyncClient(base_url=AI_PLATFORM_URL, timeout=10.0) as ac:
            r = await ac.get(f"/api/v1/conversations/{conv_id}", headers={"Authorization": auth})
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"AI Platform unreachable: {e}")

@app.post("/api/v1/conversations/{conv_id}/messages")
async def proxy_send_message(conv_id: int, request: Request):
    """Proxy to AI Platform: POST /api/v1/conversations/{id}/messages."""
    auth = request.headers.get("Authorization", "")
    body = await request.body()
    try:
        async with httpx.AsyncClient(base_url=AI_PLATFORM_URL, timeout=60.0) as ac:
            r = await ac.post(f"/api/v1/conversations/{conv_id}/messages", content=body, headers={"Authorization": auth, "Content-Type": "application/json"})
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"AI Platform unreachable: {e}")

@app.delete("/api/v1/conversations/{conv_id}")
async def proxy_delete_conversation(conv_id: int, request: Request):
    """Proxy to AI Platform: DELETE /api/v1/conversations/{id}."""
    auth = request.headers.get("Authorization", "")
    try:
        async with httpx.AsyncClient(base_url=AI_PLATFORM_URL, timeout=10.0) as ac:
            r = await ac.delete(f"/api/v1/conversations/{conv_id}", headers={"Authorization": auth})
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"AI Platform unreachable: {e}")

# ── Token (API Key) endpoints — frontend uses /tokens ───────────

@app.get("/api/v1/tokens")
async def list_tokens(request: Request):
    """Proxy to AI Platform /api/v1/api-keys, transform to {tokens: [...]}."""
    auth = request.headers.get("Authorization", "")
    try:
        async with httpx.AsyncClient(base_url=AI_PLATFORM_URL, timeout=10.0) as ac:
            r = await ac.get("/api/v1/api-keys", headers={"Authorization": auth})
            if r.status_code != 200:
                return Response(content=r.content, status_code=r.status_code, media_type="application/json")
            keys = r.json()
            tokens = []
            for k in keys:
                tokens.append({
                    "token_id": k.get("id"),
                    "name": k.get("name", ""),
                    "scopes": [],  # AI Platform doesn't return scopes in list
                    "created_at": k.get("created_at", ""),
                    "revoked": bool(k.get("revoked_at")),
                    "prefix": k.get("key_prefix", ""),
                })
            return JSONResponse({"tokens": tokens})
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"AI Platform unreachable: {e}")

@app.post("/api/v1/tokens")
async def create_token(request: Request):
    """Proxy to AI Platform /api/v1/api-keys, transform response."""
    auth = request.headers.get("Authorization", "")
    body = await request.body()
    try:
        async with httpx.AsyncClient(base_url=AI_PLATFORM_URL, timeout=10.0) as ac:
            r = await ac.post("/api/v1/api-keys", content=body,
                            headers={"Authorization": auth, "Content-Type": "application/json"})
            if r.status_code != 201:
                return Response(content=r.content, status_code=r.status_code, media_type="application/json")
            created = r.json()
            return JSONResponse({
                "token_id": created.get("id"),
                "token": created.get("full_key", ""),
                "name": created.get("name", ""),
                "key_prefix": created.get("key_prefix", ""),
                "created_at": created.get("created_at", ""),
            })
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"AI Platform unreachable: {e}")

@app.delete("/api/v1/tokens/{token_id}")
async def revoke_token(token_id: str, request: Request):
    """Proxy to AI Platform /api/v1/api-keys/{id}."""
    auth = request.headers.get("Authorization", "")
    try:
        async with httpx.AsyncClient(base_url=AI_PLATFORM_URL, timeout=10.0) as ac:
            r = await ac.delete(f"/api/v1/api-keys/{token_id}", headers={"Authorization": auth})
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"AI Platform unreachable: {e}")


# ── Admin Gateway Facade ────────────────────────────────────────

@app.get("/api/v1/admin/gateway/queues")
async def admin_gateway_queues(request: Request):
    user = await _get_user_from_token(request)
    _require_admin(user)
    jwt_token = _mint_delegation_jwt(user)
    try:
        async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=10.0) as gc:
            r = await gc.get("/admin/queues", headers={
                "Authorization": f"Bearer {jwt_token}",
                "X-Admin-Key": GATEWAY_ADMIN_KEY,
            })
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Gateway unreachable: {e}")

@app.get("/api/v1/admin/gateway/models")
async def admin_gateway_models(request: Request):
    user = await _get_user_from_token(request)
    _require_admin(user)
    jwt_token = _mint_delegation_jwt(user)
    try:
        async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=10.0) as gc:
            r = await gc.get("/admin/models", headers={
                "Authorization": f"Bearer {jwt_token}",
                "X-Admin-Key": GATEWAY_ADMIN_KEY,
            })
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Gateway unreachable: {e}")

@app.post("/api/v1/admin/gateway/models/{model}/drain")
async def admin_gateway_drain(model: str, request: Request):
    user = await _get_user_from_token(request)
    _require_admin(user)
    jwt_token = _mint_delegation_jwt(user)
    try:
        async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=10.0) as gc:
            r = await gc.post(f"/admin/models/{model}/drain", headers={
                "Authorization": f"Bearer {jwt_token}",
                "X-Admin-Key": GATEWAY_ADMIN_KEY,
            })
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Gateway unreachable: {e}")

@app.post("/api/v1/admin/gateway/models/{model}/undrain")
async def admin_gateway_undrain(model: str, request: Request):
    user = await _get_user_from_token(request)
    _require_admin(user)
    jwt_token = _mint_delegation_jwt(user)
    try:
        async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=10.0) as gc:
            r = await gc.post(f"/admin/models/{model}/undrain", headers={
                "Authorization": f"Bearer {jwt_token}",
                "X-Admin-Key": GATEWAY_ADMIN_KEY,
            })
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Gateway unreachable: {e}")

@app.get("/api/v1/admin/gateway/health")
async def admin_gateway_health(request: Request):
    user = await _get_user_from_token(request)
    _require_admin(user)
    jwt_token = _mint_delegation_jwt(user)
    try:
        async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=10.0) as gc:
            r = await gc.get("/admin/health", headers={
                "Authorization": f"Bearer {jwt_token}",
                "X-Admin-Key": GATEWAY_ADMIN_KEY,
            })
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Gateway unreachable: {e}")

@app.get("/api/v1/admin/gateway/reaper")
async def admin_gateway_reaper(request: Request):
    user = await _get_user_from_token(request)
    _require_admin(user)
    jwt_token = _mint_delegation_jwt(user)
    try:
        async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=10.0) as gc:
            r = await gc.get("/admin/reaper", headers={
                "Authorization": f"Bearer {jwt_token}",
                "X-Admin-Key": GATEWAY_ADMIN_KEY,
            })
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Gateway unreachable: {e}")

# ── Admin User Management ───────────────────────────────────────

@app.get("/api/v1/admin/users")
async def admin_list_users(request: Request):
    user = await _get_user_from_token(request)
    _require_admin(user)
    try:
        async with httpx.AsyncClient(base_url=IDENTITY_URL, timeout=10.0) as ic:
            r = await ic.get("/v1/identity/users", headers={"Authorization": request.headers.get("Authorization", "")})
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Identity unreachable: {e}")

@app.post("/api/v1/admin/users", status_code=201)
async def admin_create_user(request: Request):
    """Create a new user (admin only)."""
    user = await _get_user_from_token(request)
    _require_admin(user)
    body = await request.body()
    try:
        async with httpx.AsyncClient(base_url=IDENTITY_URL, timeout=10.0) as ic:
            r = await ic.post("/v1/identity/users", content=body,
                            headers={"Authorization": request.headers.get("Authorization", ""),
                                     "Content-Type": "application/json"})
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Identity unreachable: {e}")

@app.patch("/api/v1/admin/users/{user_id}/role")
async def admin_patch_user_role(user_id: int, request: Request):
    """Change user role (admin only). Cannot demote last admin."""
    user = await _get_user_from_token(request)
    _require_admin(user)
    body = await request.body()
    try:
        async with httpx.AsyncClient(base_url=IDENTITY_URL, timeout=10.0) as ic:
            r = await ic.patch(f"/v1/identity/users/{user_id}/role", content=body,
                             headers={"Authorization": request.headers.get("Authorization", ""),
                                      "Content-Type": "application/json"})
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Identity unreachable: {e}")

@app.patch("/api/v1/admin/users/{user_id}/status")
async def admin_patch_user_status(user_id: int, request: Request):
    """Enable/disable user (admin only). Cannot disable last admin."""
    user = await _get_user_from_token(request)
    _require_admin(user)
    body = await request.body()
    try:
        async with httpx.AsyncClient(base_url=IDENTITY_URL, timeout=10.0) as ic:
            r = await ic.patch(f"/v1/identity/users/{user_id}/status", content=body,
                             headers={"Authorization": request.headers.get("Authorization", ""),
                                      "Content-Type": "application/json"})
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Identity unreachable: {e}")

# ── Admin Organisation Management ──────────────────────────────
# REMOVED (FE-04): Gateway /admin/organisations not implemented.
# All /api/v1/admin/orgs/* routes return 501 until Gateway backend exists.
#
# ═══ REMOVED ROUTES ═══
# GET    /api/v1/admin/orgs              → 501
# GET    /api/v1/admin/orgs/{org_id}     → 501
# PATCH  /api/v1/admin/orgs/{org_id}/tier → 501
# POST   /api/v1/admin/orgs/{org_id}/credit → 501
# POST   /api/v1/admin/orgs/{org_id}/debit  → 501
#
# These are NOT exposed to frontend until Gateway backend is available.

# ── Billing & Usage Facade (Portal Backend → Gateway) ──────────

async def _proxy_to_gateway_user(request: Request, gw_path: str) -> Response:
    """Proxy request to Gateway with delegation JWT for the authenticated user."""
    user = await _get_user_from_token(request)
    jwt_token = _mint_delegation_jwt(user)
    try:
        async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=10.0) as gc:
            r = await gc.get(gw_path, headers={"Authorization": f"Bearer {jwt_token}"})
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Gateway unreachable: {e}")

@app.get("/api/v1/billing/me")
async def billing_me(request: Request):
    """Return billing info — tier from Identity, session counters as fallback."""
    user = await _get_user_from_token(request)
    return {
        "org_id": str(user.get("org_id", "")),
        "balance": 0,
        "reserved": 0,
        "available": 0,
        "tier": user.get("tier", "free"),
        "quota_daily": 1000 if user.get("tier") == "free" else 5000,
    }

@app.get("/api/v1/billing/me/ledger")
async def billing_ledger(request: Request):
    return await _proxy_to_gateway_user(request, "/v1/billing/me/ledger")

@app.get("/api/v1/usage/me")
async def usage_me(request: Request):
    return await _proxy_to_gateway_user(request, "/v1/usage/me")

@app.post("/api/v1/billing/tier")
async def update_tier(request: Request):
    """Update current user's organisation tier.
    Calls Identity PATCH /v1/identity/orgs/{org_id}/tier — admin required."""
    body = await request.json()
    tier = body.get("tier", "").strip()
    if not tier:
        raise HTTPException(status_code=400, detail="tier is required")

    user = await _get_user_from_token(request)
    org_id = user.get("org_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="No organisation assigned")

    try:
        c = await get_client()
        r = await c.patch(
            f"/v1/identity/orgs/{org_id}/tier",
            json={"tier": tier},
            headers={"Authorization": request.headers.get("Authorization", "")},
        )
        if r.status_code == 200:
            return r.json()
        raise HTTPException(status_code=r.status_code, detail=r.json().get("detail", "Identity error"))
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Identity service unavailable: {e}")

# NOTE: /api/v1/usage/me/daily and /api/v1/usage/me/models removed (FE-04):
# Gateway does not implement these endpoints. Re-add when Gateway backend supports them.

# ── RAG Facade (local document store, no Gateway dependency) ─────
import re as _re
from pathlib import Path as _Path

class SimpleRAG:
    """Lightweight in-memory document store with token-overlap search."""

    def __init__(self, docs_dir: str = "/data/rag-docs"):
        self.documents: list[dict] = []
        self._loaded = False
        self._load(docs_dir)
        self._loaded = True
        log.info(f"SimpleRAG loaded {len(self.documents)} chunks from {docs_dir}")

    def _load(self, docs_dir: str) -> None:
        root = _Path(docs_dir)
        if not root.is_dir():
            log.warning(f"SimpleRAG: doc dir not found: {docs_dir}")
            return
        for md_file in sorted(root.rglob("*.md")):
            try:
                text = md_file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            # Split into sections by headings
            sections = _re.split(r'\n(?=#{1,4}\s)', text)
            for sec in sections:
                sec = sec.strip()
                if not sec or len(sec) < 20:
                    continue
                # Extract title from first heading
                title_match = _re.match(r'^#{1,4}\s+(.+)$', sec, _re.MULTILINE)
                title = title_match.group(1).strip() if title_match else md_file.stem
                tokens = set(_re.findall(r'[а-яёa-z0-9]{3,}', sec.lower()))
                self.documents.append({
                    "source": str(md_file.relative_to(root)),
                    "title": title,
                    "text": sec[:2000],  # cap chunk size
                    "tokens": tokens,
                })

    def query(self, query_text: str, top_k: int = 5) -> list[dict]:
        if not self.documents:
            return []
        query_tokens = set(_re.findall(r'[а-яёa-z0-9]{3,}', query_text.lower()))
        if not query_tokens:
            return []
        scored = []
        for doc in self.documents:
            overlap = len(query_tokens & doc["tokens"])
            if overlap == 0:
                continue
            union = len(query_tokens | doc["tokens"])
            score = overlap / union if union > 0 else 0
            # Boost for substring match in title
            if any(qt in doc["title"].lower() for qt in query_tokens if len(qt) >= 4):
                score += 0.2
            # Boost for substring match in text
            ql = query_text.lower()
            if ql in doc["text"].lower():
                score += 0.3
            scored.append({**doc, "score": round(min(score, 1.0), 4)})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    @property
    def doc_count(self) -> int:
        return len(self.documents)

    @property
    def is_ready(self) -> bool:
        return self._loaded and len(self.documents) > 0


# Global RAG instance — initialised at startup
_rag = SimpleRAG(docs_dir=os.environ.get("RAG_DOCS_DIR", "/data/rag-docs"))


def _require_rag_scope(user: dict, scope: str) -> None:
    """Enforce exact RAG scope. Fails with 403 if scope not in user scopes."""
    scopes_str = (user.get("scopes") or "").strip()
    scopes = [s.strip() for s in scopes_str.split(",") if s.strip()]
    if scope not in scopes:
        raise HTTPException(status_code=403, detail=f"entitlement_missing: scope '{scope}' required")


@app.get("/api/v1/rag/status")
async def rag_status(request: Request):
    """RAG status — available to all authenticated users."""
    _ = await _get_user_from_token(request)  # require auth, but any user can check
    return {
        "status": "available" if _rag.is_ready else "empty",
        "documents": _rag.doc_count,
        "engine": "SimpleRAG (local)",
    }


@app.post("/api/v1/rag/query")
async def rag_query(request: Request):
    """True RAG: retrieve documents + generate answer with LLM context.

    1. Search SimpleRAG for relevant documents
    2. Build augmented prompt with retrieved context
    3. Call LLM (qwen-14b) to generate answer from context
    4. Return answer + sources
    """
    user = await _get_user_from_token(request)
    _require_rag_scope(user, "rag:query")
    body = await request.json()
    query = (body.get("query") or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    # 1. Retrieve relevant documents
    top_k = int(body.get("top_k", 7))
    results = _rag.query(query, top_k=top_k)

    if not results:
        return {
            "query": query,
            "answer": "В базе знаний не найдено релевантных документов по вашему запросу.",
            "sources": [],
            "model": "rag-local",
        }

    # 2. Build context from retrieved documents
    context_parts = []
    for i, r in enumerate(results):
        context_parts.append(f"[Документ {i+1}: {r['title']} (источник: {r['source']})]\n{r['text']}")
    context = "\n\n---\n\n".join(context_parts)

    # 3. Build augmented prompt — detailed, structured answer
    system_msg = (
        "Ты — AI-ассистент платформы Aither, эксперт по инфраструктуре AI-платформ. "
        "Отвечай на русском языке. Твоя задача — дать ПОДРОБНЫЙ, СТРУКТУРИРОВАННЫЙ ответ, "
        "используя информацию из предоставленного контекста.\n\n"
        "ПРАВИЛА:\n"
        "1. Отвечай развёрнуто: 2-5 абзацев, с примерами и пояснениями.\n"
        "2. Используй ТОЛЬКО информацию из контекста — не придумывай факты.\n"
        "3. Если в контексте нет полного ответа, опиши что известно и что отсутствует.\n"
        "4. Структурируй ответ: начни с краткого вывода, затем детали, затем ограничения.\n"
        "5. Указывай номера документов-источников в квадратных скобках: [1], [2].\n"
        "6. Если уместно, используй маркированные списки для перечисления."
    )
    user_msg = (
        f"КОНТЕКСТ ИЗ БАЗЫ ЗНАНИЙ AITHER:\n\n{context}\n\n"
        f"==========\n\n"
        f"ВОПРОС ПОЛЬЗОВАТЕЛЯ: {query}\n\n"
        f"Дай подробный, структурированный ответ на вопрос, "
        f"используя только информацию из контекста выше. "
        f"Указывай источники в квадратных скобках, например [1]."
    )

    # 4. Call LLM
    try:
        async with httpx.AsyncClient(base_url=UPSTREAM_14B_URL, timeout=120.0) as ac:
            chat_resp = await ac.post(
                "/v1/chat/completions",
                json={
                    "model": "qwen-14b",
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_msg},
                    ],
                    "max_tokens": 1500,
                    "temperature": 0.4,
                    "stream": False,
                },
                headers={"Authorization": f"Bearer {UPSTREAM_14B_TOKEN}"},
            )
            if chat_resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"LLM error: {chat_resp.status_code}")

            llm_data = chat_resp.json()
            answer = llm_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not answer:
                answer = "Модель не смогла сгенерировать ответ."

    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"LLM unreachable: {e}")

    return {
        "query": query,
        "answer": answer,
        "sources": [
            {"source": r["source"], "title": r["title"], "score": r["score"]}
            for r in results
        ],
        "model": "qwen-14b (RAG)",
    }


@app.post("/api/v1/rag/hybrid-query")
async def rag_hybrid(request: Request):
    """Hybrid search (token-overlap + substring boost)."""
    user = await _get_user_from_token(request)
    _require_rag_scope(user, "rag:query")
    body = await request.json()
    query = (body.get("query") or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    results = _rag.query(query, top_k=int(body.get("top_k", 8)))
    return {
        "query": query,
        "results": [
            {
                "source": r["source"],
                "title": r["title"],
                "score": r["score"],
                "text": r["text"][:500],
            }
            for r in results
        ],
        "total": len(results),
        "engine": "token-overlap + substring boost",
    }


@app.get("/api/v1/rag/doc")
async def rag_get_doc(request: Request, source: str = ""):
    """Return full content of a RAG document by source filename."""
    _ = await _get_user_from_token(request)
    if not source:
        raise HTTPException(status_code=400, detail="source parameter is required")
    docs_dir = os.environ.get("RAG_DOCS_DIR", "/data/rag-docs")
    # Security: prevent path traversal
    safe_source = _Path(source).name
    file_path = _Path(docs_dir) / safe_source
    if not file_path.is_file():
        # Try recursive search
        for f in _Path(docs_dir).rglob(safe_source):
            file_path = f
            break
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"Document not found: {source}")
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to read document")
    return {
        "source": str(file_path.relative_to(docs_dir)),
        "title": file_path.stem,
        "content": content,
        "size": len(content),
    }


@app.post("/api/v1/rag/ingest")
async def rag_ingest(request: Request):
    """Re-scan docs directory (requires rag:ingest scope)."""
    user = await _get_user_from_token(request)
    _require_rag_scope(user, "rag:ingest")
    global _rag
    docs_dir = os.environ.get("RAG_DOCS_DIR", "/data/rag-docs")
    _rag = SimpleRAG(docs_dir=docs_dir)
    return {"status": "reindexed", "documents": _rag.doc_count}


@app.post("/api/v1/rag/wiki-ingest")
async def rag_wiki_ingest(request: Request):
    """Re-scan wiki docs directory (admin only, requires rag:wiki-admin)."""
    user = await _get_user_from_token(request)
    _require_rag_scope(user, "rag:wiki-admin")
    _require_admin(user)
    body = await request.json()
    docs_dir = body.get("docs_dir", os.environ.get("RAG_DOCS_DIR", "/data/rag-docs"))
    global _rag
    _rag = SimpleRAG(docs_dir=docs_dir)
    return {"status": "reindexed", "documents": _rag.doc_count, "source": docs_dir}


# ── Monitoring Facade ────────────────────────────────────────────

@app.get("/api/v1/monitoring/summary")
async def monitoring_summary(request: Request):
    """Get monitoring summary (admin/operator)."""
    user = await _get_user_from_token(request)
    _require_monitoring_role(user)
    jwt_token = _mint_delegation_jwt(user)
    try:
        async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=10.0) as gc:
            r = await gc.get("/admin/health", headers={
                "Authorization": f"Bearer {jwt_token}",
                "X-Admin-Key": GATEWAY_ADMIN_KEY,
            })
            health_data = r.json() if r.status_code == 200 else {}
            return {
                "gateway": "ok" if r.status_code == 200 else "error",
                "dependencies": health_data.get("dependencies", {}),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Gateway unreachable: {e}")

@app.get("/api/v1/monitoring/models")
async def monitoring_models(request: Request):
    """Model metrics (admin/operator) — passes X-Admin-Key."""
    user = await _get_user_from_token(request)
    _require_monitoring_role(user)
    jwt_token = _mint_delegation_jwt(user)
    try:
        async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=10.0) as gc:
            r = await gc.get("/admin/models", headers={
                "Authorization": f"Bearer {jwt_token}",
                "X-Admin-Key": GATEWAY_ADMIN_KEY,
            })
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Gateway unreachable: {e}")

# NOTE (FE-05): /api/v1/monitoring/security and /api/v1/monitoring/billing REMOVED.
# Gateway /admin/security/events and /admin/billing/stats are not implemented.
# Re-add when Gateway backend supports these endpoints.

@app.get("/api/v1/monitoring/dependencies")
async def monitoring_dependencies(request: Request):
    """Service dependency status (admin/operator)."""
    user = await _get_user_from_token(request)
    _require_monitoring_role(user)
    jwt_token = _mint_delegation_jwt(user)
    try:
        async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=10.0) as gc:
            r = await gc.get("/admin/health", headers={
                "Authorization": f"Bearer {jwt_token}",
                "X-Admin-Key": GATEWAY_ADMIN_KEY,
            })
            health_data = r.json() if r.status_code == 200 else {}
            return {"dependencies": health_data.get("dependencies", {})}
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Gateway unreachable: {e}")


# ── Chat (Delegation JWT — Variant A) ────────────────────────────

@app.post("/api/v1/chat")
async def chat_completions(request: Request):
    """Chat completions — direct upstream with server-side credentials.

    Flow: Browser → Portal Backend → direct upstream (14B) or nginx proxy (32B).
    NOT routed through Gateway. Server-side credentials from K8s Secrets.
    No raw API keys stored in process memory. No delegation JWT for chat.
    """
    body = await request.body()
    try:
        body_json = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    model = body_json.get("model", "qwen-14b")
    messages = body_json.get("messages", [])
    max_tokens = body_json.get("max_tokens", 512)
    temperature = body_json.get("temperature", 0.7)

    # 1. Verify user identity (session + disabled check)
    user = await _get_user_from_token(request)

    # 2. Verify entitlement: org active, tier present, model scope
    _check_chat_entitlement(user, model)

    # 3. Determine upstream based on model
    if "32b" in model.lower():
        upstream_url = UPSTREAM_32B_URL
        upstream_token = UPSTREAM_32B_TOKEN
    else:
        upstream_url = UPSTREAM_14B_URL
        upstream_token = UPSTREAM_14B_TOKEN

    if not upstream_token:
        raise HTTPException(status_code=503, detail="Upstream credentials not configured")

    # 3. Forward directly to upstream with server-side credential
    try:
        async with httpx.AsyncClient(base_url=upstream_url, timeout=120.0) as ac:
            chat_resp = await ac.post(
                "/v1/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": False,
                },
                headers={
                    "Authorization": f"Bearer {upstream_token}",
                    "Content-Type": "application/json",
                },
            )
            return Response(
                content=chat_resp.content,
                status_code=chat_resp.status_code,
                media_type="application/json",
            )
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Upstream model unreachable: {e}")


@app.on_event("startup")
async def startup():
    """Initialize Prometheus metrics on service start."""
    log.info("Starting metrics instrumentation")
    metrics_uptime.set(0)
    metrics_memory_usage_bytes.set(0)


@app.on_event("shutdown")
async def shutdown():
    global client
    if client:
        await client.aclose()
        client = None
