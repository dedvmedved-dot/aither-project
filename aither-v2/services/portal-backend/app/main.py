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
import re
import time
import uuid
import random
import smtplib
import threading
from email.mime.text import MIMEText
from datetime import datetime, timezone

import httpx
import jwt as pyjwt
from fastapi import FastAPI, HTTPException, Depends, Request, Response, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse
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

# ── In-memory per-user usage tracker ───────────────────────────
# Lightweight counters — survive pod restart (reset to zero, which is fine for billing).
# Keyed by user_id (int). Stores: total_requests, total_tokens, today date + counters.
_usage_lock = threading.Lock()
_usage_data: dict[int, dict] = {}


def _track_usage(user_id: int, prompt_tokens: int, completion_tokens: int) -> None:
    """Record one request + token counts for a user."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with _usage_lock:
        entry = _usage_data.get(user_id)
        if entry is None or entry.get("_date") != today:
            entry = {
                "_date": today,
                "requests_today": 0,
                "tokens_today": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_requests": 0,
                "total_tokens": 0,
            }
            _usage_data[user_id] = entry
        entry["requests_today"] += 1
        entry["total_requests"] += 1
        entry["tokens_today"] += prompt_tokens + completion_tokens
        entry["total_tokens"] += prompt_tokens + completion_tokens
        entry["input_tokens"] += prompt_tokens
        entry["output_tokens"] += completion_tokens


def _get_usage(user_id: int) -> dict:
    """Return usage stats for a user, zero-filled if no data."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with _usage_lock:
        entry = _usage_data.get(user_id)
        if entry is None or entry.get("_date") != today:
            return {
                "requests_today": 0,
                "total_requests": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "tokens_today": 0,
                "total_tokens": 0,
            }
        return {
            "requests_today": entry.get("requests_today", 0),
            "total_requests": entry.get("total_requests", 0),
            "input_tokens": entry.get("input_tokens", 0),
            "output_tokens": entry.get("output_tokens", 0),
            "tokens_today": entry.get("tokens_today", 0),
            "total_tokens": entry.get("total_tokens", 0),
        }
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
# UPSTREAM_14B_* is a stale variable name retained only for the RAG feature (out of cutover scope).
UPSTREAM_14B_URL = os.environ.get("UPSTREAM_14B_URL", "http://vllm-14b-instruct.aither-inference.svc:8000")
UPSTREAM_14B_TOKEN = os.environ.get("UPSTREAM_14B_TOKEN", "")

# Exact model -> upstream routing map (no substring matching, no fallback).
# Both active Qwen3-family models share the existing model:qwen3:chat scope.
MODEL_UPSTREAM_URLS = {
    "qwen3-32b": os.environ.get("UPSTREAM_QWEN3_32B_URL", "http://vllm-qwen3-32b-awq.aither-inference.svc:8000"),
    "qwen3.8-27b": os.environ.get("UPSTREAM_QWEN38_27B_URL", "http://vllm-qwen38-27b-fp8.aither-inference.svc:8000"),
}
MODEL_UPSTREAM_TOKENS = {
    "qwen3-32b": os.environ.get("UPSTREAM_QWEN3_32B_TOKEN", ""),
    "qwen3.8-27b": os.environ.get("UPSTREAM_QWEN38_27B_TOKEN", ""),
}


def _resolve_upstream(model: str) -> tuple[str, str]:
    """Exact-key upstream resolution. Unknown model -> controlled 404, never routed."""
    model_lower = model.lower().strip()
    if model_lower not in MODEL_UPSTREAM_URLS:
        raise HTTPException(status_code=404, detail=f"model_not_found: '{model}'")
    return MODEL_UPSTREAM_URLS[model_lower], MODEL_UPSTREAM_TOKENS[model_lower]
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

    Strict model allowlist: exactly the two active Qwen3-family models.
    Unknown models → 400 BEFORE any upstream call.
    """
    # Strict model allowlist (exact keys, no substring matching)
    ALLOWED_MODELS = {"qwen3-32b", "qwen3.8-27b"}
    model_lower = model.lower().strip()
    if model_lower not in ALLOWED_MODELS:
        raise HTTPException(status_code=400, detail=f"model_not_found: '{model}' not in allowlist. Available: qwen3-32b, qwen3.8-27b")

    # Organisation must be assigned and active
    org_id = user.get("org_id")
    if not org_id:
        raise HTTPException(status_code=403, detail="entitlement_missing: no organisation assigned")
    if user.get("org_status") != "active":
        raise HTTPException(status_code=403, detail="entitlement_missing: organisation is not active")
    # Tier must be present
    if not user.get("tier"):
        raise HTTPException(status_code=403, detail="entitlement_missing: no tier assigned")
    # Model-specific scope enforcement — both active models require model:qwen3:chat
    scopes_str = (user.get("scopes") or "").strip()
    scopes = [s.strip() for s in scopes_str.split(",") if s.strip()]
    if "model:qwen3:chat" not in scopes:
        raise HTTPException(status_code=403, detail="entitlement_missing: scope 'model:qwen3:chat' required")

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

# ── Password Policy ────────────────────────────────────────────
# Minimum 16 characters.
# Must contain: uppercase (A-Z), lowercase (a-z), digit (0-9), special char.

def _validate_password(password: str) -> str | None:
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

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    registration_token: str
    code: str
    new_password: str

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
    if not _chat_db_ready:
        raise HTTPException(status_code=503, detail="Chat DB unavailable")
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
    pw_err = _validate_password(req.password)
    if pw_err:
        raise HTTPException(status_code=400, detail=pw_err)
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
            "email": pending.get("email", ""),
        }, headers={"X-Internal-Secret": IDENTITY_INTERNAL_SECRET})
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

# ── Forgot / Reset password ───────────────────────────────────────

@app.post("/api/v1/auth/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    """Step 1: Send verification code to registered email (if user exists)."""
    _cleanup_expired_registrations()

    if not req.email or "@" not in req.email:
        raise HTTPException(status_code=400, detail="Invalid email address")

    # Look up user by email in identity — we need to find the username
    try:
        c = await get_client()
        # Identity: find user by email (we need to add this or use users list)
        r = await c.get(f"/v1/identity/users/lookup?email={req.email.strip()}", headers={"X-Internal-Secret": IDENTITY_INTERNAL_SECRET})
        if r.status_code != 200:
            # Don't reveal whether email exists — always return same message
            log.info("Forgot password: email not found '%s'", req.email)
            return {"status": "ok", "message": "Если email зарегистрирован, код отправлен на него.", "expires_in": REGISTRATION_CODE_TTL}
        user_data = r.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Identity service unavailable: {e}")

    username = user_data.get("username", "")
    if not username:
        return {"status": "ok", "message": "Если email зарегистрирован, код отправлен на него.", "expires_in": REGISTRATION_CODE_TTL}

    # Generate code and store pending reset
    code = str(random.randint(100000, 999999))
    reg_token = uuid.uuid4().hex

    with _pending_lock:
        _pending_registrations[reg_token] = {
            "username": username,
            "password": "",  # not used for reset
            "email": req.email.strip(),
            "code": code,
            "created_at": time.time(),
            "is_reset": True,  # flag for reset-password endpoint
        }

    email_sent = _send_verification_email(req.email.strip(), code)
    log.info("Forgot password: user='%s' email='%s' sent=%s", username, req.email, email_sent)
    return {
        "status": "ok" if email_sent else "email_failed",
        "registration_token": reg_token,
        "message": "Код подтверждения отправлен на email" if email_sent
                   else "Не удалось отправить email.",
        "expires_in": REGISTRATION_CODE_TTL,
    }


@app.post("/api/v1/auth/reset-password")
async def reset_password(req: ResetPasswordRequest):
    """Step 2: Verify code and set new password."""
    _cleanup_expired_registrations()

    with _pending_lock:
        pending = _pending_registrations.pop(req.registration_token, None)

    if not pending or not pending.get("is_reset"):
        raise HTTPException(status_code=404, detail="Reset session not found or expired")

    if time.time() - pending["created_at"] > REGISTRATION_CODE_TTL:
        raise HTTPException(status_code=410, detail="Verification code expired")

    if pending["code"] != req.code.strip():
        raise HTTPException(status_code=400, detail="Неверный код подтверждения")

    pw_err = _validate_password(req.new_password)
    if pw_err:
        raise HTTPException(status_code=400, detail=pw_err)

    # Call identity to reset password
    try:
        c = await get_client()
        r = await c.post("/v1/identity/reset-password", json={
            "username": pending["username"],
            "new_password": req.new_password,
        }, headers={"X-Internal-Secret": IDENTITY_INTERNAL_SECRET})
        if r.status_code == 200:
            log.info("Password reset complete: user='%s'", pending["username"])
            return {"status": "ok", "message": "Пароль успешно изменён. Теперь вы можете войти."}
        else:
            raise HTTPException(status_code=r.status_code,
                                detail=r.json().get("detail", "Password reset failed"))
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
    """Return the active model catalog.

    - External OpenAI-compatible API keys (`Bearer aither_...`) receive the
      scope-filtered list (behavior unchanged).
    - A normal authenticated Portal web session is validated against Identity
      using the same accepted contract as `/api/v1/auth/me` and `/api/v1/chat`,
      then receives the exact active catalog (`qwen3-32b`, `qwen3.8-27b`)
      filtered by the `model:qwen3:chat` entitlement.
    - A Portal session is never proxied to AI Platform as if it were a JWT.
    """
    auth = request.headers.get("Authorization", "")
    # API key auth: return filtered model list (external OpenAI-compatible path unchanged)
    if auth.startswith("Bearer aither_"):
        ctx = await _introspect_api_key(auth[7:].strip())
        effective = set(ctx.get("effective_scopes", []))
        models = _model_catalog(effective)
        if not models:
            raise HTTPException(status_code=403, detail="No models available for this key")
        return {"object": "list", "data": models}

    # Portal web session: validate through Identity (fail closed).
    # Missing/invalid session -> 401; disabled account -> 403; Identity down -> 503.
    user = await _get_user_from_token(request)

    # Entitlement gate: both active models require the single model:qwen3:chat scope.
    scopes_str = (user.get("scopes") or "").strip()
    scopes = [s.strip() for s in scopes_str.split(",") if s.strip()]
    if "model:qwen3:chat" not in scopes:
        raise HTTPException(status_code=403, detail="entitlement_missing: scope 'model:qwen3:chat' required")

    models = _model_catalog()
    return {"object": "list", "data": models}

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

# ── API Keys (proxied to Identity) ────────────────────────────

IDENTITY_INTERNAL_SECRET = os.environ.get("IDENTITY_INTERNAL_API_SECRET", "")
if not IDENTITY_INTERNAL_SECRET:
    import sys
    print("FATAL: IDENTITY_INTERNAL_API_SECRET is required", file=sys.stderr)
    sys.exit(1)


async def _introspect_api_key(api_key: str) -> dict:
    """Validate API key via Identity introspection. Returns context or raises 401."""
    try:
        async with httpx.AsyncClient(base_url=IDENTITY_URL, timeout=10.0) as ic:
            r = await ic.post("/v1/identity/internal/api-keys/introspect",
                json={"api_key": api_key},
                headers={"X-Internal-Secret": IDENTITY_INTERNAL_SECRET})
            if r.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid API key")
            ctx = r.json()
            if not ctx.get("active"):
                reason = ctx.get("reason", "unknown")
                if reason == "revoked":
                    raise HTTPException(status_code=401, detail="API key revoked")
                elif reason == "expired":
                    raise HTTPException(status_code=401, detail="API key expired")
                elif reason == "user_disabled":
                    raise HTTPException(status_code=403, detail="Account disabled")
                elif reason == "organisation_inactive":
                    raise HTTPException(status_code=403, detail="Organisation inactive")
                else:
                    raise HTTPException(status_code=401, detail="Invalid API key")
            return ctx
    except HTTPException:
        raise
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Identity service unreachable")


@app.get("/api/v1/api-keys")
async def proxy_api_keys(request: Request):
    """Proxy to Identity: GET /v1/identity/api-keys."""
    auth = request.headers.get("Authorization", "")
    try:
        async with httpx.AsyncClient(base_url=IDENTITY_URL, timeout=10.0) as ic:
            r = await ic.get("/v1/identity/api-keys", headers={"Authorization": auth})
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Identity service unreachable")


@app.post("/api/v1/api-keys")
async def proxy_create_api_key(request: Request):
    """Proxy to Identity: POST /v1/identity/api-keys."""
    auth = request.headers.get("Authorization", "")
    body = await request.body()
    try:
        async with httpx.AsyncClient(base_url=IDENTITY_URL, timeout=10.0) as ic:
            r = await ic.post("/v1/identity/api-keys", content=body,
                headers={"Authorization": auth, "Content-Type": "application/json"})
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Identity service unreachable")


@app.delete("/api/v1/api-keys/{key_id}")
async def proxy_revoke_api_key(key_id: int, request: Request):
    """Proxy to Identity: DELETE /v1/identity/api-keys/{id}."""
    auth = request.headers.get("Authorization", "")
    try:
        async with httpx.AsyncClient(base_url=IDENTITY_URL, timeout=10.0) as ic:
            r = await ic.delete(f"/v1/identity/api-keys/{key_id}", headers={"Authorization": auth})
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Identity service unreachable")


# ── External /v1/* API (OpenAI-compatible, API key auth) ─────

CURRENT_MODELS = {
    "qwen3-32b": {"scope": "model:qwen3:chat", "display": "Qwen3-32B-AWQ"},
    "qwen3.8-27b": {"scope": "model:qwen3:chat", "display": "Qwen3.8-27B-FP8"},
}

# ── Deterministic agent role routing (no LLM router, no fallback) ──
# Logical agent roles map 1:1 to physical models. Direct physical model IDs
# remain fully supported. Aliases are resolved BEFORE entitlement/upstream so
# the effective physical model governs scope checks and upstream routing.
AGENT_MODEL_ALIASES = {
    "agent-fast": "qwen3-32b",
    "agent-deep": "qwen3.8-27b",
}


def _resolve_requested_model(requested_model: str) -> tuple[str, str, str | None]:
    """Resolve a logical agent role to its physical model.

    Returns (requested, effective_model, logical_role_or_none).
    Physical model IDs pass through unchanged (role=None). Unknown strings pass
    through unchanged so the downstream entitlement/upstream lookup fails closed
    (404 model_not_found). No fuzzy matching, no substring matching, no fallback.
    """
    m = (requested_model or "").strip()
    if m in AGENT_MODEL_ALIASES:
        return m, AGENT_MODEL_ALIASES[m], m
    return m, m, None


def _model_catalog(scopes: set[str] | None = None) -> list[dict]:
    """Build the OpenAI-compatible model list: physical models + agent role aliases.

    When `scopes` is provided, only models whose scope is in `scopes` are listed
    (aliases inherit the scope of their physical model). When None, all models.
    """
    entries = []
    for model_id, info in CURRENT_MODELS.items():
        if scopes is None or info["scope"] in scopes:
            entries.append({"id": model_id, "object": "model", "created": 1722900000, "owned_by": "aither"})
    for alias, physical in AGENT_MODEL_ALIASES.items():
        info = CURRENT_MODELS[physical]
        if scopes is None or info["scope"] in scopes:
            entries.append({"id": alias, "object": "model", "created": 1722900000, "owned_by": "aither"})
    return entries

# Architect output-budget policy (P0-R1): default 2048, hard max 4096 (clamp).
DEFAULT_MAX_TOKENS = 2048
HARD_MAX_TOKENS = 4096


def _resolve_max_tokens(value):
    """Resolve max_tokens under the output-budget policy.

    default=2048; >4096 clamps to 4096; bool/non-integer/<=0 -> controlled 400.
    """
    if value is None:
        return DEFAULT_MAX_TOKENS
    if isinstance(value, bool) or not isinstance(value, int):
        raise HTTPException(status_code=400, detail="max_tokens must be an integer")
    if value <= 0:
        raise HTTPException(status_code=400, detail="max_tokens must be a positive integer")
    if value > HARD_MAX_TOKENS:
        return HARD_MAX_TOKENS
    return value


async def _chat_via_api_key(auth_header: str, body_json: dict):
    """Handle chat request authenticated via API key."""
    api_key = auth_header[7:].strip()  # Remove "Bearer "
    ctx = await _introspect_api_key(api_key)
    
    model = body_json.get("model", "")
    model = _resolve_requested_model(model)[1]  # logical role -> physical model
    _check_api_key_entitlement(ctx, model)
    
    messages = body_json.get("messages", [])
    max_tokens = _resolve_max_tokens(body_json.get("max_tokens"))
    temperature = body_json.get("temperature", 0.7)
    stream = body_json.get("stream", False)
    tools = body_json.get("tools")
    tool_choice = body_json.get("tool_choice")
    parallel_tool_calls = body_json.get("parallel_tool_calls")

    upstream_url, upstream_token = _resolve_upstream(model)

    if not upstream_token:
        raise HTTPException(status_code=503, detail="Upstream not configured")

    req_body = {
        "model": model, "messages": messages,
        "max_tokens": max_tokens, "temperature": temperature, "stream": stream,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    if tools is not None:
        req_body["tools"] = tools
    if tool_choice is not None:
        req_body["tool_choice"] = tool_choice
    if parallel_tool_calls is not None:
        req_body["parallel_tool_calls"] = parallel_tool_calls
    
    try:
        async with httpx.AsyncClient(base_url=upstream_url, timeout=600.0) as ac:
            r = await ac.post("/v1/chat/completions", json=req_body,
                headers={"Authorization": f"Bearer {upstream_token}", "Content-Type": "application/json"})
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Upstream model unreachable")


def _check_api_key_entitlement(ctx: dict, model: str):
    """Verify API key has entitlement to use the model."""
    model_lower = model.lower().strip()
    if model_lower not in CURRENT_MODELS:
        raise HTTPException(status_code=404, detail=f"model_not_found: '{model}'")

    required_scope = CURRENT_MODELS[model_lower]["scope"]
    effective = ctx.get("effective_scopes", [])
    if required_scope not in effective:
        raise HTTPException(status_code=403, detail=f"insufficient_scope: '{required_scope}' required")


async def _get_ctx_from_api_key(request: Request) -> dict:
    """Extract and validate API key from Authorization header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="invalid_api_key: Bearer token required")
    api_key = auth[7:].strip()
    if not api_key.startswith("aither_"):
        raise HTTPException(status_code=401, detail="invalid_api_key: not an API key")
    return await _introspect_api_key(api_key)


@app.get("/v1/models")
async def external_list_models(request: Request):
    """OpenAI-compatible model list — filtered by API key scopes."""
    ctx = await _get_ctx_from_api_key(request)
    effective = set(ctx.get("effective_scopes", []))
    
    models = _model_catalog(effective)
    
    if not models:
        raise HTTPException(status_code=403, detail="No models available for this key")
    
    return {"object": "list", "data": models}


@app.post("/v1/chat/completions")
async def external_chat(request: Request):
    """OpenAI-compatible chat completions with API key auth."""
    ctx = await _get_ctx_from_api_key(request)
    
    body = await request.json()
    model = body.get("model", "")
    model = _resolve_requested_model(model)[1]  # logical role -> physical model
    _check_api_key_entitlement(ctx, model)
    
    messages = body.get("messages", [])
    max_tokens = _resolve_max_tokens(body.get("max_tokens"))
    temperature = body.get("temperature", 0.7)
    stream = body.get("stream", False)
    tools = body.get("tools")
    tool_choice = body.get("tool_choice")
    parallel_tool_calls = body.get("parallel_tool_calls")

    # Determine upstream (exact-key, no substring matching)
    upstream_url, upstream_token = _resolve_upstream(model)

    if not upstream_token:
        raise HTTPException(status_code=503, detail="Upstream not configured")

    req_body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    if tools is not None:
        req_body["tools"] = tools
    if tool_choice is not None:
        req_body["tool_choice"] = tool_choice
    if parallel_tool_calls is not None:
        req_body["parallel_tool_calls"] = parallel_tool_calls
    
    try:
        if stream:
            async with httpx.AsyncClient(base_url=upstream_url, timeout=600.0) as ac:
                r = await ac.post("/v1/chat/completions", json=req_body,
                    headers={"Authorization": f"Bearer {upstream_token}", "Content-Type": "application/json"})
                return StreamingResponse(
                    r.aiter_bytes(),
                    media_type="text/event-stream",
                    headers={"X-Request-ID": str(uuid.uuid4())}
                )
        else:
            async with httpx.AsyncClient(base_url=upstream_url, timeout=600.0) as ac:
                r = await ac.post("/v1/chat/completions", json=req_body,
                    headers={"Authorization": f"Bearer {upstream_token}", "Content-Type": "application/json"})
                return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Upstream model unreachable")


# ── API Key aliases (frontend uses /api/v1/tokens) ──────────────

@app.get("/api/v1/tokens")
async def proxy_tokens(request: Request):
    """Alias: GET /api/v1/tokens → /api/v1/api-keys."""
    return await proxy_api_keys(request)

@app.post("/api/v1/tokens")
async def proxy_create_token(request: Request):
    """Alias: POST /api/v1/tokens → /api/v1/api-keys."""
    return await proxy_create_api_key(request)

@app.delete("/api/v1/tokens/{key_id}")
async def proxy_revoke_token(key_id: int, request: Request):
    """Alias: DELETE /api/v1/tokens/{id} → /api/v1/api-keys/{id}."""
    return await proxy_revoke_api_key(key_id, request)

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
    """Return billing info — tier from Identity, usage from tracker."""
    user = await _get_user_from_token(request)
    uid = user.get("id") or user.get("uid") or 0
    usage = _get_usage(int(uid)) if uid else {}
    return {
        "org_id": str(user.get("org_id", "")),
        "balance": 0,
        "reserved": 0,
        "available": 0,
        "tier": user.get("tier", "free"),
        "quota_daily": 1000 if user.get("tier") == "free" else 5000,
        "requests_today": usage.get("requests_today", 0),
        "tokens_today": usage.get("tokens_today", 0),
    }

@app.get("/api/v1/billing/me/ledger")
async def billing_ledger(request: Request):
    return await _proxy_to_gateway_user(request, "/v1/billing/me/ledger")

@app.get("/api/v1/usage/me")
async def usage_me(request: Request):
    """Return usage stats — from in-memory tracker."""
    user = await _get_user_from_token(request)
    uid = user.get("id") or user.get("uid") or 0
    usage = _get_usage(int(uid)) if uid else {}
    return {
        **usage,
        "tier": user.get("tier", "free"),
    }

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
    """Chat completions — JWT auth (browser) or API key auth (agents)."""
    body = await request.body()
    try:
        body_json = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Check if API key auth (aither_...)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer aither_"):
        return await _chat_via_api_key(auth_header, body_json)

    model = body_json.get("model", "qwen3-32b")
    model = _resolve_requested_model(model)[1]  # logical role -> physical model
    messages = body_json.get("messages", [])
    max_tokens = _resolve_max_tokens(body_json.get("max_tokens"))
    temperature = body_json.get("temperature", 0.7)

    # 1. Verify user identity (session + disabled check)
    user = await _get_user_from_token(request)

    # 2. Verify entitlement: org active, tier present, model scope
    _check_chat_entitlement(user, model)

    # 3. Determine upstream based on model (exact-key, no substring matching)
    upstream_url, upstream_token = _resolve_upstream(model)

    if not upstream_token:
        raise HTTPException(status_code=503, detail="Upstream credentials not configured")

    # 3. Forward directly to upstream with server-side credential
    try:
        async with httpx.AsyncClient(base_url=upstream_url, timeout=600.0) as ac:
            req_body = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False,
                "chat_template_kwargs": {"enable_thinking": False},
            }
            chat_resp = await ac.post(
                "/v1/chat/completions",
                json=req_body,
                headers={
                    "Authorization": f"Bearer {upstream_token}",
                    "Content-Type": "application/json",
                },
            )
            # 4. Track usage from upstream response
            try:
                resp_json = chat_resp.json()
                usage_info = resp_json.get("usage", {})
                prompt_tokens = usage_info.get("prompt_tokens", 0)
                completion_tokens = usage_info.get("completion_tokens", 0)
                uid = user.get("id") or user.get("uid") or 0
                if uid and (prompt_tokens or completion_tokens):
                    _track_usage(int(uid), prompt_tokens, completion_tokens)
            except Exception:
                pass  # best-effort tracking
            return Response(
                content=chat_resp.content,
                status_code=chat_resp.status_code,
                media_type="application/json",
            )
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Upstream model unreachable: {e}")


# ── Chat History Persistence (server-side, per-user) ──────────

import sqlite3
import zipfile
import io
import hashlib

CHAT_DB_PATH = os.environ.get("CHAT_DB_PATH", "/data/chat/chat_history.db")
_chat_db_ready = False

# Schema version tracked via PRAGMA user_version (DB-level, not the per-row column).
CHAT_SCHEMA_VERSION = 2

# Canonical v2 schema — foreign keys use ON DELETE CASCADE, legacy id is enforced
# by a partial UNIQUE index (idempotency), message order by a UNIQUE (conversation, seq).
_SCHEMA_V2_TABLES = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    model TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    legacy_client_id TEXT NULL,
    tokens INTEGER NOT NULL DEFAULT 0,
    requests INTEGER NOT NULL DEFAULT 0,
    schema_version INTEGER NOT NULL DEFAULT 2
);
CREATE TABLE IF NOT EXISTS message_nodes (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    parent_id TEXT NULL,
    sequence_no INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    model TEXT NULL,
    answer_id TEXT NULL,
    created_at TEXT NOT NULL,
    metadata_json TEXT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES message_nodes(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_conv_user_updated ON conversations(user_id, updated_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_conv_legacy_unique ON conversations(user_id, legacy_client_id) WHERE legacy_client_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_msg_conv_seq ON message_nodes(conversation_id, sequence_no);
"""

# v1 -> v2 migration. SQLite cannot ALTER a foreign key in place, so we rebuild both
# tables, copy the data, drop the old ones and rename. Orphaned message_nodes (whose
# parent conversation no longer exists) are intentionally dropped so foreign_key_check
# ends clean. The whole migration runs inside one transaction (atomic).
_SCHEMA_V2_MIGRATE = """
PRAGMA foreign_keys=OFF;
BEGIN;
CREATE TABLE conversations_new (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    model TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    legacy_client_id TEXT NULL,
    tokens INTEGER NOT NULL DEFAULT 0,
    requests INTEGER NOT NULL DEFAULT 0,
    schema_version INTEGER NOT NULL DEFAULT 2
);
CREATE TABLE message_nodes_new (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    parent_id TEXT NULL,
    sequence_no INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    model TEXT NULL,
    answer_id TEXT NULL,
    created_at TEXT NOT NULL,
    metadata_json TEXT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES message_nodes(id) ON DELETE CASCADE
);
INSERT INTO conversations_new (id, user_id, title, model, created_at, updated_at, legacy_client_id, tokens, requests, schema_version)
    SELECT id, user_id, title, model, created_at, updated_at, legacy_client_id, tokens, requests, 2 FROM conversations;
INSERT INTO message_nodes_new (id, conversation_id, parent_id, sequence_no, role, content, model, answer_id, created_at, metadata_json)
    SELECT mn.id, mn.conversation_id, mn.parent_id, mn.sequence_no, mn.role, mn.content, mn.model, mn.answer_id, mn.created_at, mn.metadata_json
    FROM message_nodes mn
    WHERE EXISTS (SELECT 1 FROM conversations c WHERE c.id = mn.conversation_id);
DROP TABLE message_nodes;
DROP TABLE conversations;
ALTER TABLE conversations_new RENAME TO conversations;
ALTER TABLE message_nodes_new RENAME TO message_nodes;
CREATE INDEX idx_conv_user_updated ON conversations(user_id, updated_at);
CREATE UNIQUE INDEX idx_conv_legacy_unique ON conversations(user_id, legacy_client_id) WHERE legacy_client_id IS NOT NULL;
CREATE UNIQUE INDEX idx_msg_conv_seq ON message_nodes(conversation_id, sequence_no);
-- Rebuild the linear parent chain for any pre-existing R1 conversations:
-- first node NULL, each subsequent node -> previous node (by sequence_no).
UPDATE message_nodes
SET parent_id = (
    SELECT prev_id FROM (
        SELECT id, LAG(id) OVER (PARTITION BY conversation_id ORDER BY sequence_no) AS prev_id
        FROM message_nodes
    ) t WHERE t.id = message_nodes.id
);
PRAGMA user_version=2;
COMMIT;
"""


def _chat_conn():
    conn = sqlite3.connect(CHAT_DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def _chat_migrate():
    """Idempotent schema migration to CHAT_SCHEMA_VERSION.

    Uses a dedicated connection because rebuilding foreign-key tables requires
    PRAGMA foreign_keys=OFF, while the normal request connection turns it ON.
    """
    conn = sqlite3.connect(CHAT_DB_PATH, timeout=10)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        ver = conn.execute("PRAGMA user_version").fetchone()[0]
        has_conv = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='conversations'"
        ).fetchone()
        has_msg = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='message_nodes'"
        ).fetchone()

        if not has_conv and not has_msg:
            # Fresh database — create v2 schema directly.
            conn.executescript(_SCHEMA_V2_TABLES)
            conn.execute("PRAGMA user_version=%d" % CHAT_SCHEMA_VERSION)
            conn.commit()
            return

        if ver >= CHAT_SCHEMA_VERSION:
            return

        # Duplicate pre-check (BLOCKER 6): refuse to migrate if non-NULL
        # (user_id, legacy_client_id) already has duplicates — building the
        # UNIQUE index would be unsafe and must not silently pick/merge rows.
        dups = conn.execute(
            "SELECT COUNT(*) FROM ("
            "  SELECT user_id, legacy_client_id FROM conversations "
            "  WHERE legacy_client_id IS NOT NULL "
            "  GROUP BY user_id, legacy_client_id HAVING COUNT(*) > 1"
            ")"
        ).fetchone()[0]
        if dups:
            raise RuntimeError("BLOCKED_LEGACY_DUPLICATES: %d duplicate (user_id, legacy_client_id) group(s)" % dups)

        # Existing (R1) schema — rebuild into v2 in one atomic transaction.
        conn.executescript(_SCHEMA_V2_MIGRATE)
        conn.commit()

        # Post-migration validation.
        fk_issues = conn.execute("PRAGMA foreign_key_check").fetchall()
        if fk_issues:
            raise RuntimeError("foreign_key_check failed after migration: %r" % (fk_issues,))
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError("integrity_check failed after migration: %r" % (integrity,))
    finally:
        conn.close()


def _chat_init():
    global _chat_db_ready
    try:
        _chat_migrate()
        _chat_db_ready = True
    except Exception as e:
        log.error("chat db init/migrate failed: %s", e)
        _chat_db_ready = False


async def _chat_owner(request: Request) -> int:
    user = await _get_user_from_token(request)
    return int(user.get("id") or user.get("uid") or 0)


def _chat_safe_filename(title, chat_id):
    s = re.sub(r'[/\\\x00-\x1f]', '', title or '')
    s = re.sub(r'\.\.+', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = (s or 'chat')[:60]
    return s + '_' + str(chat_id)[:8]


def _chat_to_md(conv, messages):
    lines = [
        '# ' + (conv['title'] or 'Без названия'), '',
        '**Chat ID:** ' + str(conv['id']), '',
        '**Создан:** ' + str(conv['created_at']), '',
        '**Обновлён:** ' + str(conv['updated_at']), '',
        '**Модель:** ' + (conv['model'] or ''), '',
        '---', '',
    ]
    for m in messages:
        if m['role'] == 'user':
            lines.append('## Пользователь')
        else:
            lines.append('## ' + (m['model'] or 'Ассистент'))
        lines.append('')
        lines.append(m['content'] or '')
        lines.append('')
        lines.append('---')
        lines.append('')
    return '\n'.join(lines)


_chat_init()


@app.get("/api/v1/chats")
async def chat_list(request: Request):
    user_id = await _chat_owner(request)
    conn = _chat_conn()
    try:
        rows = conn.execute(
            "SELECT id, title, model, created_at, updated_at, legacy_client_id, tokens, requests FROM conversations WHERE user_id=? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
        return {"chats": [dict(r) for r in rows]}
    finally:
        conn.close()


@app.post("/api/v1/chats")
async def chat_create(request: Request):
    user_id = await _chat_owner(request)
    body = await request.json()
    # Canonical conversation id is ALWAYS server-generated (BLOCKER 4).
    # A client-supplied canonical id is rejected outright.
    if body.get("id") is not None:
        raise HTTPException(status_code=400, detail="chat id is server-generated")
    legacy_client_id = body.get("legacy_client_id") or None
    now = datetime.now(timezone.utc).isoformat()
    conn = _chat_conn()
    try:
        # Idempotent for the same (user_id, legacy_client_id): return the existing chat.
        if legacy_client_id:
            existing = conn.execute(
                "SELECT id FROM conversations WHERE user_id=? AND legacy_client_id=?",
                (user_id, legacy_client_id),
            ).fetchone()
            if existing:
                return {"id": existing["id"], "status": "created"}
        conv_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO conversations (id, user_id, title, model, created_at, updated_at, legacy_client_id, tokens, requests) VALUES (?,?,?,?,?,?,?,?,?)",
            (conv_id, user_id, body.get("title") or "Новый чат", body.get("model"), now, now, legacy_client_id, body.get("tokens") or 0, body.get("requests") or 0),
        )
        conn.commit()
        return {"id": conv_id, "status": "created"}
    except sqlite3.IntegrityError:
        conn.rollback()
        if legacy_client_id:
            existing = conn.execute(
                "SELECT id FROM conversations WHERE user_id=? AND legacy_client_id=?",
                (user_id, legacy_client_id),
            ).fetchone()
            if existing:
                return {"id": existing["id"], "status": "created"}
        raise HTTPException(status_code=409, detail="Chat creation conflict")
    finally:
        conn.close()


@app.get("/api/v1/chats/export")
async def chat_export(request: Request):
    user_id = await _chat_owner(request)
    conn = _chat_conn()
    try:
        convs = conn.execute("SELECT * FROM conversations WHERE user_id=? ORDER BY updated_at DESC", (user_id,)).fetchall()
        rows = []
        for c in convs:
            msgs = conn.execute("SELECT * FROM message_nodes WHERE conversation_id=? ORDER BY sequence_no", (c["id"],)).fetchall()
            rows.append((c, msgs))
    finally:
        conn.close()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%SZ")
    buf = io.BytesIO()
    index_lines = [
        "# Aither — экспорт истории чатов", '',
        'Экспортировано: ' + datetime.now(timezone.utc).isoformat(), '',
        'Количество чатов: ' + str(len(convs)), '',
        '| № | Чат | Создан | Обновлён | Модель | Сообщений | Файл |', '|---:|---|---|---|---|---:|---|',
    ]
    filenames = {}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, (c, msgs) in enumerate(rows, 1):
            safe = _chat_safe_filename(c["title"], c["id"])
            n = 1
            base = safe
            while safe in filenames:
                safe = base + '_' + str(n)
                n += 1
            filenames[safe] = True
            fname = safe + '.md'
            zf.writestr(fname, _chat_to_md(c, msgs))
            index_lines.append('| %d | %s | %s | %s | %s | %d | [%s](%s) |' % (i, c['title'], c['created_at'][:10], c['updated_at'][:10], c['model'] or '', len(msgs), fname, fname))
        zf.writestr('00_INDEX.md', '\n'.join(index_lines))
    buf.seek(0)
    data = buf.read()
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="Aither_chat_history_%s.zip"' % ts},
    )


@app.get("/api/v1/chats/{chat_id}")
async def chat_get(chat_id: str, request: Request):
    user_id = await _chat_owner(request)
    conn = _chat_conn()
    try:
        conv = conn.execute("SELECT * FROM conversations WHERE id=? AND user_id=?", (chat_id, user_id)).fetchone()
        if not conv:
            raise HTTPException(status_code=404, detail="Chat not found")
        msgs = conn.execute("SELECT * FROM message_nodes WHERE conversation_id=? ORDER BY sequence_no", (chat_id,)).fetchall()
        return {"chat": dict(conv), "messages": [dict(m) for m in msgs]}
    finally:
        conn.close()


@app.put("/api/v1/chats/{chat_id}")
async def chat_update(chat_id: str, request: Request):
    user_id = await _chat_owner(request)
    body = await request.json()
    now = datetime.now(timezone.utc).isoformat()
    conn = _chat_conn()
    try:
        exists = conn.execute("SELECT id FROM conversations WHERE id=? AND user_id=?", (chat_id, user_id)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Chat not found")
        # Update conversation metadata + messages (replace-all, linear mode)
        conn.execute("UPDATE conversations SET title=?, model=?, updated_at=?, tokens=?, requests=? WHERE id=? AND user_id=?",
                     (body.get("title") or "Новый чат", body.get("model"), now, body.get("tokens") or 0, body.get("requests") or 0, chat_id, user_id))
        conn.execute("DELETE FROM message_nodes WHERE conversation_id=?", (chat_id,))
        seq = 0
        prev_id = None
        for m in (body.get("messages") or []):
            seq += 1
            node_id = str(uuid.uuid4())
            # Deterministic linear parent chain: first node NULL, each next -> previous node.
            conn.execute(
                "INSERT INTO message_nodes (id, conversation_id, parent_id, sequence_no, role, content, model, answer_id, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (node_id, chat_id, prev_id, seq, m.get("role") or "user", m.get("content") or "", m.get("model"), m.get("answer_id"), now),
            )
            prev_id = node_id
        conn.commit()
        return {"id": chat_id, "status": "updated"}
    finally:
        conn.close()


@app.delete("/api/v1/chats/{chat_id}")
async def chat_delete(chat_id: str, request: Request):
    user_id = await _chat_owner(request)
    conn = _chat_conn()
    try:
        cur = conn.execute("DELETE FROM conversations WHERE id=? AND user_id=?", (chat_id, user_id))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Chat not found")
        return {"id": chat_id, "status": "deleted"}
    finally:
        conn.close()


@app.post("/api/v1/chats/import-legacy")
async def chat_import_legacy(request: Request):
    user_id = await _chat_owner(request)
    body = await request.json()
    sessions = body.get("sessions") or []
    now = datetime.now(timezone.utc).isoformat()
    imported = 0
    skipped = 0
    conn = _chat_conn()
    try:
        for s in sessions:
            legacy_id = s.get("id") or s.get("legacy_client_id")
            if legacy_id:
                existing = conn.execute("SELECT id FROM conversations WHERE user_id=? AND legacy_client_id=?", (user_id, legacy_id)).fetchone()
                if existing:
                    skipped += 1
                    continue
            conv_id = str(uuid.uuid4())
            conn.execute("SAVEPOINT import_session")
            try:
                conn.execute(
                    "INSERT INTO conversations (id, user_id, title, model, created_at, updated_at, legacy_client_id, tokens, requests) VALUES (?,?,?,?,?,?,?,?,?)",
                    (conv_id, user_id, s.get("title") or "Новый чат", s.get("model"), now, now, legacy_id, s.get("tokens") or 0, s.get("requests") or 0),
                )
            except sqlite3.IntegrityError:
                conn.execute("ROLLBACK TO import_session")
                conn.execute("RELEASE import_session")
                skipped += 1
                continue
            seq = 0
            prev_id = None
            for m in (s.get("history") or []):
                seq += 1
                node_id = str(uuid.uuid4())
                # Deterministic linear parent chain: first node NULL, each next -> previous node.
                conn.execute(
                    "INSERT INTO message_nodes (id, conversation_id, parent_id, sequence_no, role, content, model, answer_id, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (node_id, conv_id, prev_id, seq, m.get("role") or "user", m.get("content") or "", m.get("model"), m.get("answer_id"), now),
                )
                prev_id = node_id
            conn.execute("RELEASE import_session")
            imported += 1
        conn.commit()
        return {"imported": imported, "skipped": skipped}
    finally:
        conn.close()


# ── Feedback ────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    topic: str
    message: str
    file_name: str | None = None
    file_content: str | None = None  # base64-encoded


@app.post("/api/v1/feedback", status_code=201)
async def submit_feedback(
    request: Request,
    topic: str = Form(...),
    message: str = Form(...),
    file: UploadFile | None = File(None),
):
    """Submit feedback with optional file attachment — proxy to identity service."""
    try:
        headers = {}
        auth = request.headers.get("Authorization", "")
        if auth:
            headers["Authorization"] = auth
        
        body: dict = {"topic": topic.strip(), "message": message.strip()}
        
        # Read and base64-encode attached file
        if file and file.filename:
            import base64
            content = await file.read()
            if len(content) > 5 * 1024 * 1024:  # 5MB limit
                raise HTTPException(status_code=413, detail="File too large (max 5MB)")
            body["file_name"] = file.filename
            body["file_content"] = base64.b64encode(content).decode()
        
        async with httpx.AsyncClient(base_url=IDENTITY_URL, timeout=30.0) as ic:
            r = await ic.post("/v1/identity/feedback", json=body, headers=headers)
            return r.json()
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Feedback service unavailable")


@app.get("/api/v1/feedback")
async def list_feedback(request: Request):
    """List feedback (admin only)."""
    user = await _get_user_from_token(request)
    _require_admin(user)
    try:
        async with httpx.AsyncClient(base_url=IDENTITY_URL, timeout=10.0) as ic:
            r = await ic.get("/v1/identity/feedback", headers={"Authorization": request.headers.get("Authorization", "")})
            return r.json()
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Feedback service unavailable")


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
