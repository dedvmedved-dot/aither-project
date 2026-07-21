# Aither Portal Backend (BFF)
#
# Environment variables:
#   PORTAL_IDENTITY_URL    — Identity service URL (default: http://aither-identity:8000)
#   PORTAL_LOG_LEVEL       — logging level (default: INFO)
#   PORTAL_CORS_ORIGIN     — Allowed CORS origin (default: *)
#   PORTAL_BFF_TOKEN       — Token for BFF→Identity internal communication (optional)

import os
import logging

import httpx
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Configuration ──────────────────────────────────────────────

IDENTITY_URL = os.environ.get("PORTAL_IDENTITY_URL", "http://aither-identity:8000")
LOG_LEVEL = os.environ.get("PORTAL_LOG_LEVEL", "INFO").upper()
CORS_ORIGIN = os.environ.get("PORTAL_CORS_ORIGIN", "*")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("aither-portal-bff")

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
    version="1.0.0",
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

# ── Routes ─────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "portal-backend"}

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
    return {"service": "aither-portal-backend", "version": "1.0.0", "build": "stage15"}

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
    return {"status": "operational" if all(v == "healthy" or isinstance(v, dict) for v in results.values()) else "degraded", "services": results}

# ── Shutdown ───────────────────────────────────────────────────

@app.on_event("shutdown")
async def shutdown():
    global client
    if client:
        await client.aclose()
        client = None
