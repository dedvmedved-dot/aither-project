"""Aither Gateway — FastAPI/ASGI. CHANGE-0022."""
import os, time, uuid, logging, hashlib, threading, json
from contextlib import asynccontextmanager
from typing import Optional

import yaml
import httpx
import redis.asyncio as aioredis
import psycopg2
import psycopg2.pool
import jwt as pyjwt
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from config import settings
from auth import check_auth, check_admin
from routing import route_model
from rate_limit import check_rate_limit
from billing import reserve, settle, refund
from usage import record_usage
from security import check_security
from security_egress import check_egress
from catalog import ModelEntry, load_catalog, resolve
from reaper import start_reaper

logger = logging.getLogger("aither.gateway")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

class ChatMsg(BaseModel):
    role: str; content: str

class ChatReq(BaseModel):
    model: str = "qwen-14b"
    messages: list[ChatMsg] = []
    max_tokens: int = 256
    temperature: float = 0.7
    stream: bool = False

class CompReq(BaseModel):
    model: str = "qwen-32b-base"
    prompt: str = ""
    max_tokens: int = 256
    temperature: float = 0.7
    stream: bool = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Gateway CHANGE-0022 starting")
    app.state.redis = aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True, socket_connect_timeout=2)
    app.state.db = psycopg2.pool.SimpleConnectionPool(1, 10, settings.PG_URL)
    app.state.http = httpx.AsyncClient(timeout=httpx.Timeout(settings.UPSTREAM_TIMEOUT))
    app.state.catalog = load_catalog(settings.CATALOG_PATH)
    logger.info("Catalog: %d models", len(app.state.catalog))
    if settings.BILLING_ENABLED:
        threading.Thread(target=start_reaper, args=(app.state.db, app.state.redis), daemon=True).start()
    yield
    await app.state.http.aclose()
    await app.state.redis.aclose()
    app.state.db.closeall()

app = FastAPI(title="Aither Gateway", version="2.0.0", lifespan=lifespan)

@app.middleware("http")
async def req_id_mw(request: Request, call_next):
    request.state.rid = request.headers.get("X-Request-ID", uuid.uuid4().hex[:8])
    resp = await call_next(request)
    resp.headers["X-Request-ID"] = request.state.rid
    return resp

def _err(c: int, m: str, **kw): return JSONResponse({"error": m, **kw}, status_code=c)

@app.get("/health")
async def health(): return {"status":"ok","service":"aither-gateway","change":"CHANGE-0022"}

@app.get("/ready")
async def ready(request: Request):
    deps = {}
    try:
        await request.app.state.redis.ping(); deps["redis"] = "ok"
    except Exception as e: deps["redis"] = str(e)
    try:
        c = request.app.state.db.getconn(); request.app.state.db.putconn(c); deps["postgres"] = "ok"
    except Exception as e: deps["postgres"] = str(e)
    return {"status":"ok" if all(v=="ok" for v in deps.values()) else "degraded","dependencies":deps}

@app.get("/v1/models")
async def list_models(request: Request):
    return {"object":"list","data":[m.to_dict() for m in request.app.state.catalog]}

@app.post("/v1/chat/completions")
async def chat(req: ChatReq, request: Request):
    return await _pipeline(req.model, [{"role":m.role,"content":m.content} for m in req.messages], req.max_tokens, req.temperature, req.stream, "chat", request)

@app.post("/v1/completions")
async def comp(req: CompReq, request: Request):
    return await _pipeline(req.model, req.prompt, req.max_tokens, req.temperature, req.stream, "completion", request)

async def _pipeline(model_id: str, content, max_tokens: int, temperature: float, stream: bool, mode: str, request: Request):
    rid = request.state.rid
    token = request.headers.get("Authorization","").removeprefix("Bearer ").strip()

    # Auth
    ar = await check_auth(token, request.app)
    if ar.status != "ok": return _err(401, ar.reason)
    org_id, tier = ar.org_id, ar.tier

    # Model routing
    model = route_model(model_id, request.app.state.catalog, tier)
    if not model: return _err(403, f"model_not_available", tier=tier, model=model_id)

    # Rate limit
    if settings.RL_ENABLED:
        ok, reason = await check_rate_limit(org_id, tier, request.app.state.redis)
        if not ok: return _err(429, reason)

    # Security ingress
    if settings.SECURITY_ENABLED:
        body = await request.body()
        sec_ok, sec_reason = check_security(body.decode(errors="replace"))
        if not sec_ok: return _err(403, sec_reason)

    # Billing reserve
    ref = None
    if settings.BILLING_ENABLED:
        ref = reserve(org_id, 100, request.app.state.db)
        if ref is None: return _err(402, "insufficient_balance")

    # Upstream call
    payload = {"model": model.served_model_name, "max_tokens": max_tokens, "temperature": temperature, "stream": False}
    if mode == "chat": payload["messages"] = content if isinstance(content, list) else [{"role":"user","content":content}]
    else: payload["prompt"] = content if isinstance(content, str) else str(content)

    headers = {"Content-Type":"application/json"}
    if settings.VLLM_API_KEY: headers["Authorization"] = f"Bearer {settings.VLLM_API_KEY}"

    try:
        upstream_url = f"{model.upstream_url}/v1/chat/completions" if mode=="chat" else f"{model.upstream_url}/v1/completions"
        resp = await request.app.state.http.post(upstream_url, json=payload, headers=headers)
    except httpx.TimeoutException:
        if ref: refund(org_id, ref, request.app.state.db)
        return _err(504, "upstream_timeout")
    except httpx.ConnectError:
        if ref: refund(org_id, ref, request.app.state.db)
        return _err(502, "upstream_unavailable")

    if resp.status_code != 200:
        if ref: refund(org_id, ref, request.app.state.db)
        return _err(502, f"upstream_error_{resp.status_code}")

    data = resp.json()
    usage = data.get("usage", {})
    total = usage.get("total_tokens", 0)

    # Security egress
    if settings.SECURITY_ENABLED:
        egr_ok, egr_reason = check_egress(json.dumps(data))
        if not egr_ok:
            if ref: refund(org_id, ref, request.app.state.db)
            return _err(403, egr_reason)

    if ref: settle(org_id, ref, total, request.app.state.db)
    record_usage(org_id, rid, model_id, usage.get("prompt_tokens",0), usage.get("completion_tokens",0), 200, "settle", request.app.state.db)
    return data

# Admin
def _admin(request: Request):
    if not check_admin(request): raise HTTPException(403, "admin_required")

@app.get("/admin/queues")
async def a_queues(request: Request): _admin(request); return {"queues":[]}
@app.get("/admin/models")
async def a_models(request: Request): _admin(request); return {"models": [m.to_dict() for m in request.app.state.catalog]}
@app.post("/admin/models/{mid}/drain")
async def a_drain(mid: str, request: Request): _admin(request); return {"drained": mid}
@app.get("/admin/health")
async def a_health(request: Request): _admin(request); return {"status":"ok"}
@app.get("/v1/rag/status")
async def rag_status(request: Request): return {"ready": False}
