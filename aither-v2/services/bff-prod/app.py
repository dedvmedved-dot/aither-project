# Aither Portal Backend (BFF)
#
# Environment variables:
#   PORTAL_IDENTITY_URL    — Identity service URL (default: http://aither-identity:8000)
#   PORTAL_LOG_LEVEL       — logging level (default: INFO)
#   PORTAL_CORS_ORIGIN     — Allowed CORS origin (default: *)
#   PORTAL_BFF_TOKEN       — Token for BFF→Identity internal communication (optional)

import os
import json
import logging
import time
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import prometheus_client
from prometheus_client import Counter, Histogram, Gauge

# ── Configuration ──────────────────────────────────────────────

IDENTITY_URL = os.environ.get("PORTAL_IDENTITY_URL", "http://aither-identity:8000")
AI_PLATFORM_URL = os.environ.get("PORTAL_AI_PLATFORM_URL", "http://aither-ai-platform:8000")
LOG_LEVEL = os.environ.get("PORTAL_LOG_LEVEL", "INFO").upper()
CORS_ORIGIN = os.environ.get("PORTAL_CORS_ORIGIN", "http://localhost:3000")
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
    import logging; logging.warning(f"AUTH HEADER RECEIVED: [{auth[:50] if auth else 'EMPTY'}]")
    try:
        c = await get_client()
        r = await c.post("/v1/identity/logout", headers={"Authorization": auth})
        if r.status_code == 200:
            return r.json()
        raise HTTPException(status_code=r.status_code, detail=r.json().get("detail", "Logout failed"))
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Identity service unavailable: {e}")

@app.get("/api/v1/auth/me")
async def me(request: Request):
    """Get current user info."""
    auth = request.headers.get("Authorization", "")
    import logging; logging.warning(f"AUTH HEADER RECEIVED: [{auth[:50] if auth else 'EMPTY'}]")
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
    import logging; logging.warning(f"AUTH HEADER RECEIVED: [{auth[:50] if auth else 'EMPTY'}]")
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
    import logging; logging.warning(f"AUTH HEADER RECEIVED: [{auth[:50] if auth else 'EMPTY'}]")
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
    import logging; logging.warning(f"AUTH HEADER RECEIVED: [{auth[:50] if auth else 'EMPTY'}]")
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
    import logging; logging.warning(f"AUTH HEADER RECEIVED: [{auth[:50] if auth else 'EMPTY'}]")
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
    import logging; logging.warning(f"AUTH HEADER RECEIVED: [{auth[:50] if auth else 'EMPTY'}]")
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
    import logging; logging.warning(f"AUTH HEADER RECEIVED: [{auth[:50] if auth else 'EMPTY'}]")
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
    import logging; logging.warning(f"AUTH HEADER RECEIVED: [{auth[:50] if auth else 'EMPTY'}]")
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
    import logging; logging.warning(f"AUTH HEADER RECEIVED: [{auth[:50] if auth else 'EMPTY'}]")
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
    import logging; logging.warning(f"AUTH HEADER RECEIVED: [{auth[:50] if auth else 'EMPTY'}]")
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
    import logging; logging.warning(f"AUTH HEADER RECEIVED: [{auth[:50] if auth else 'EMPTY'}]")
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
    import logging; logging.warning(f"AUTH HEADER RECEIVED: [{auth[:50] if auth else 'EMPTY'}]")
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
    import logging; logging.warning(f"AUTH HEADER RECEIVED: [{auth[:50] if auth else 'EMPTY'}]")
    try:
        async with httpx.AsyncClient(base_url=AI_PLATFORM_URL, timeout=10.0) as ac:
            r = await ac.delete(f"/api/v1/conversations/{conv_id}", headers={"Authorization": auth})
            return Response(content=r.content, status_code=r.status_code, media_type="application/json")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"AI Platform unreachable: {e}")

# ── Shutdown ───────────────────────────────────────────────────

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

