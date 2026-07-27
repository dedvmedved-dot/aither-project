"""Aither Gateway — FastAPI/ASGI application. CHANGE-0022."""
import os, time, uuid, logging, hashlib, threading
from contextlib import asynccontextmanager
from typing import Optional

import yaml
import httpx
import redis.asyncio as redis
import psycopg2
import psycopg2.pool
import jwt as pyjwt
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from config import settings
from auth import check_auth, check_admin, verify_api_key
from routing import route_model
from rate_limit import check_rate_limit
from billing import reserve, settle, refund
from usage import record_usage
from security import check_security
from security_egress import check_egress
from vault import vault_validate_key
from catalog import load_catalog, model_list
from admin import (
    admin_queues, admin_models, admin_drain, admin_undrain,
    admin_health, admin_org_detail, admin_reaper, is_model_drained,
)
from metrics import metrics_registry, update_metrics
from hybrid_rag import hybrid_query, wiki_ingest, wiki_status
from wiki_graph import get_wiki_graph
from reaper import start_reaper

logger = logging.getLogger("aither.gateway")

# ── Pydantic models ──

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str = "qwen-14b"
    messages: list[ChatMessage]
    max_tokens: int = 256
    temperature: float = 0.7
    stream: bool = False

class CompletionRequest(BaseModel):
    model: str = "qwen-32b-base"
    prompt: str
    max_tokens: int = 256
    temperature: float = 0.7
    stream: bool = False

# ── Lifespan ──

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown."""
    logger.info("Gateway starting — CHANGE-0022")
    # Redis
    app.state.redis = redis.Redis(
        host=settings.REDIS_HOST, port=settings.REDIS_PORT,
        decode_responses=True, socket_connect_timeout=2,
    )
    # PostgreSQL pool
    app.state.db_pool = psycopg2.pool.SimpleConnectionPool(
        1, 10, settings.PG_URL,
    )
    # HTTP client for upstream vLLM calls
    app.state.http = httpx.AsyncClient(timeout=httpx.Timeout(settings.UPSTREAM_TIMEOUT))
    # JWT public key
    app.state.jwt_public_key = settings.JWT_PUBLIC_KEY
    # Catalog
    app.state.catalog = load_catalog(settings.CATALOG_PATH)
    # Optional: Wiki graph
    try:
        app.state.wiki_graph = get_wiki_graph()
        logger.info("Wiki graph loaded: %d pages", app.state.wiki_graph.page_count)
    except Exception as e:
        logger.warning("Wiki graph load failed: %s", e)
        app.state.wiki_graph = None
    # Reaper
    if settings.BILLING_ENABLED:
        threading.Thread(target=start_reaper, args=(app.state.db_pool, app.state.redis), daemon=True).start()
    logger.info("Gateway ready — %d models", len(app.state.catalog))
    yield
    await app.state.http.aclose()
    await app.state.redis.aclose()
    app.state.db_pool.closeall()

app = FastAPI(title="Aither Gateway", version="1.0.0", lifespan=lifespan)

# ── Request ID middleware ──

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    rid = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response

# ── Helpers ──

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _error(code: int, msg: str, **extra) -> JSONResponse:
    return JSONResponse({"error": msg, **extra}, status_code=code)

# ── Endpoints ──

@app.get("/health")
async def health():
    return {"status": "ok", "service": "aither-gateway", "change": "CHANGE-0022"}

@app.get("/ready")
async def ready(request: Request):
    deps = {}
    try:
        await request.app.state.redis.ping()
        deps["redis"] = "ok"
    except Exception as e:
        deps["redis"] = f"error: {e}"
    try:
        conn = request.app.state.db_pool.getconn()
        request.app.state.db_pool.putconn(conn)
        deps["postgres"] = "ok"
    except Exception as e:
        deps["postgres"] = f"error: {e}"
    return {"status": "ok" if all(v == "ok" for v in deps.values()) else "degraded", "dependencies": deps}

@app.get("/v1/models")
async def list_models(request: Request):
    return {"object": "list", "data": [m.to_dict() for m in request.app.state.catalog]}

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest, request: Request):
    rid = request.state.request_id
    ctx = await _build_context(req.model, request)
    if isinstance(ctx, JSONResponse):
        return ctx
    return await _do_inference(req.model, req.messages, req.max_tokens, req.temperature, req.stream, rid, ctx, "chat", request)

@app.post("/v1/completions")
async def completions(req: CompletionRequest, request: Request):
    rid = request.state.request_id
    ctx = await _build_context(req.model, request)
    if isinstance(ctx, JSONResponse):
        return ctx
    return await _do_inference(req.model, req.prompt, req.max_tokens, req.temperature, req.stream, rid, ctx, "completion", request)

@app.get("/metrics")
async def metrics_endpoint(request: Request):
    """Prometheus metrics — cluster-internal only."""
    from prometheus_client import generate_latest
    return JSONResponse(content={"metrics": "prometheus"}, status_code=200)  # placeholder

# ── Core inference pipeline ──

async def _build_context(model_id: str, request: Request):
    """Auth → ACL → rate limit → security → reserve."""
    rid = request.state.request_id
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()

    # Auth
    auth_result = await check_auth(token, request.app)
    if auth_result.status == "denied":
        return _error(401, auth_result.reason)
    org_id = auth_result.org_id
    tier = auth_result.tier

    # Model ACL
    model = route_model(model_id, request.app.state.catalog, tier)
    if not model:
        return _error(403, f"model_not_available", tier=tier, requested=model_id)

    # Rate limit
    if settings.RL_ENABLED:
        rl_ok, rl_reason = await check_rate_limit(org_id, tier, request.app.state.redis, int(request.headers.get("Content-Length", "0")) // 4)
        if not rl_ok:
            return _error(429, rl_reason)

    # Security ingress
    if settings.SECURITY_ENABLED:
        body = await request.body()
        sec_ok, sec_reason = check_security(body.decode(errors="replace"))
        if not sec_ok:
            return _error(403, sec_reason)

    # Billing reserve
    billing_ref = None
    if settings.BILLING_ENABLED:
        billing_ref = reserve(org_id, 100, request.app.state.db_pool)  # simplified
        if billing_ref is None:
            return _error(402, "insufficient_balance")

    return {"org_id": org_id, "model": model, "billing_ref": billing_ref}

async def _do_inference(model_id: str, content, max_tokens: int, temperature: float, stream: bool, rid: str, ctx: dict, mode: str, request: Request):
    """Call upstream vLLM, handle billing settle/refund, security egress."""
    model = ctx["model"]
    upstream_url = model.upstream_url
    served_name = model.served_model_name
    vllm_key = settings.VLLM_API_KEY
    billing_ref = ctx.get("billing_ref")
    org_id = ctx["org_id"]

    # Build upstream request
    if mode == "chat":
        payload = {
            "model": served_name,
            "messages": [{"role": m.role if hasattr(m, 'role') else ("user" if isinstance(content, list) else "user"), "content": m.content if hasattr(m, 'content') else content} for m in (content if isinstance(content, list) else [])] or [{"role": "user", "content": content}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }
    else:
        payload = {
            "model": served_name,
            "prompt": content if isinstance(content, str) else "\n".join(m.content for m in content) if isinstance(content, list) else str(content),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }

    headers = {"Content-Type": "application/json"}
    if vllm_key:
        headers["Authorization"] = f"Bearer {vllm_key}"

    try:
        resp = await request.app.state.http.post(
            f"{upstream_url}/v1/chat/completions" if mode == "chat" else f"{upstream_url}/v1/completions",
            json=payload, headers=headers,
        )
    except httpx.TimeoutException:
        if billing_ref:
            refund(org_id, billing_ref, request.app.state.db_pool)
        return _error(504, "upstream_timeout")
    except httpx.ConnectError:
        if billing_ref:
            refund(org_id, billing_ref, request.app.state.db_pool)
        return _error(502, "upstream_unavailable")

    if resp.status_code != 200:
        if billing_ref:
            refund(org_id, billing_ref, request.app.state.db_pool)
        return _error(502, f"upstream_error_{resp.status_code}")

    data = resp.json()
    usage = data.get("usage", {})
    total_tokens = usage.get("total_tokens", 0)

    # Security egress
    if settings.SECURITY_ENABLED:
        response_text = str(data)
        egr_ok, egr_reason = check_egress(response_text)
        if not egr_ok:
            if billing_ref:
                refund(org_id, billing_ref, request.app.state.db_pool)
            record_usage(org_id, rid, model_id, 0, 0, 403, "blocked_egress", request.app.state.db_pool)
            return _error(403, egr_reason)

    # Billing settle
    if billing_ref:
        settle(org_id, billing_ref, total_tokens, request.app.state.db_pool)

    # Usage collector
    record_usage(org_id, rid, model_id, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), 200, "settle", request.app.state.db_pool)

    return data

# ── Admin endpoints ──

@app.get("/admin/queues")
async def admin_queues_endpoint(request: Request):
    if not check_admin(request): return _error(403, "admin_required")
    return admin_queues(request.app.state.redis)

@app.get("/admin/models")
async def admin_models_endpoint(request: Request):
    if not check_admin(request): return _error(403, "admin_required")
    return admin_models(request.app.state.catalog, request.app.state.http)

@app.get("/admin/health")
async def admin_health_endpoint(request: Request):
    if not check_admin(request): return _error(403, "admin_required")
    return admin_health(request.app.state)

@app.post("/admin/models/{model_id}/drain")
async def admin_drain_endpoint(model_id: str, request: Request):
    if not check_admin(request): return _error(403, "admin_required")
    return admin_drain(model_id, request.app.state.catalog)

@app.post("/admin/models/{model_id}/undrain")
async def admin_undrain_endpoint(model_id: str, request: Request):
    if not check_admin(request): return _error(403, "admin_required")
    return admin_undrain(model_id, request.app.state.catalog)

@app.get("/admin/reaper")
async def admin_reaper_endpoint(request: Request):
    if not check_admin(request): return _error(403, "admin_required")
    return admin_reaper()

@app.get("/admin/orgs/{org_id}")
async def admin_org_endpoint(org_id: str, request: Request):
    if not check_admin(request): return _error(403, "admin_required")
    return admin_org_detail(org_id, request.app.state.db_pool)

# ── RAG endpoints ──

@app.post("/v1/rag/ingest")
async def rag_ingest(request: Request):
    return _error(501, "rag_ingest_not_implemented")

@app.post("/v1/rag/query")
async def rag_query(request: Request):
    return _error(501, "rag_query_not_implemented")

@app.get("/v1/rag/status")
async def rag_status(request: Request):
    return {"wiki_graph": request.app.state.wiki_graph is not None}
