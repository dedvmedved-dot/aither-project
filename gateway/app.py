"""Aither Gateway — FastAPI/ASGI. CHANGE-0022-C2."""
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
from billing import reserve, settle, refund, BillingResult
from usage import record_usage
from security import check_security
from security_egress import check_egress
from catalog import ModelEntry, load_catalog, resolve
from token_estimator import estimate_tokens as _est_tok
from reaper import start_reaper
from metrics import metrics as mtr

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
    logger.info("Gateway CHANGE-0022-C2 starting")
    app.state.redis = aioredis.Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=True, socket_connect_timeout=2)
    try:
        app.state.db = psycopg2.pool.SimpleConnectionPool(settings.pg_min_conn, settings.pg_max_conn, settings.pg_url)
        logger.info("PostgreSQL pool: %d-%d connections", settings.pg_min_conn, settings.pg_max_conn)
    except Exception as e:
        logger.warning("PostgreSQL unavailable, using None pool: %s", e)
        app.state.db = None
    app.state.http = httpx.AsyncClient(timeout=httpx.Timeout(settings.upstream_timeout_seconds))
    app.state.catalog = load_catalog(settings.catalog_path)
    logger.info("Catalog: %d models", len(app.state.catalog))
    if settings.billing_enabled:
        threading.Thread(target=start_reaper, args=(app.state.db, app.state.redis), daemon=True).start()
    yield
    await app.state.http.aclose()
    await app.state.redis.aclose()
    if app.state.db: app.state.db.closeall()

app = FastAPI(title="Aither Gateway", version="2.0.0", lifespan=lifespan)

@app.middleware("http")
async def req_id_mw(request: Request, call_next):
    request.state.rid = request.headers.get("X-Request-ID", uuid.uuid4().hex[:8])
    resp = await call_next(request)
    resp.headers["X-Request-ID"] = request.state.rid
    return resp

def _err(c: int, m: str, **kw): return JSONResponse({"error": m, **kw}, status_code=c)

@app.get("/health")
async def health(): return {"status":"ok","service":"aither-gateway","change":"CHANGE-0022-C2"}

@app.get("/ready")
async def ready(request: Request):
    """Readiness: 503 if critical dependency is missing. No raw exceptions."""
    deps = {}
    critical_fail = False

    # Redis (critical)
    try:
        await request.app.state.redis.ping()
        deps["redis"] = "ok"
    except Exception:
        deps["redis"] = "unavailable"
        critical_fail = True

    # PostgreSQL (critical if billing_enabled)
    if settings.billing_enabled:
        try:
            if request.app.state.db:
                c = request.app.state.db.getconn()
                request.app.state.db.putconn(c)
                deps["postgres"] = "ok"
            else:
                deps["postgres"] = "not_configured"
                critical_fail = True
        except Exception:
            deps["postgres"] = "unavailable"
            critical_fail = True
    else:
        deps["postgres"] = "disabled"

    # Catalog (critical)
    deps["catalog"] = f"{len(request.app.state.catalog)} models" if request.app.state.catalog else "empty"
    if not request.app.state.catalog:
        critical_fail = True

    # Upstream model health — look up by model ID, not catalog index
    # Prohibit catalog[0]/catalog[1] — resolve by deterministic model IDs
    REQUIRED_MODELS = ["qwen-14b", "qwen-32b-base"]
    for mid in REQUIRED_MODELS:
        model = None
        for m in request.app.state.catalog:
            if m.id == mid:
                model = m
                break
        if model is None:
            deps[f"model_{mid}"] = "missing_from_catalog"
            critical_fail = True
            continue
        try:
            health_url = f"{model.upstream_url}{model.health_endpoint}"
            resp = await request.app.state.http.get(health_url, timeout=5)
            resp.raise_for_status()
            deps[f"model_{mid}"] = "ok"
        except Exception:
            deps[f"model_{mid}"] = "unavailable"
            critical_fail = True

    status_str = "degraded" if critical_fail else "ok"
    status_code = 503 if critical_fail else 200
    return JSONResponse({"status": status_str, "dependencies": deps}, status_code=status_code)

@app.get("/v1/models")
async def list_models(request: Request):
    return {"object":"list","data":[m.to_dict() for m in request.app.state.catalog]}

@app.post("/v1/chat/completions")
async def chat(req: ChatReq, request: Request):
    messages = [{"role":m.role,"content":m.content} for m in req.messages]
    return await _pipeline(req.model, messages, req.max_tokens, req.temperature, req.stream, "chat", request)

@app.post("/v1/completions")
async def comp(req: CompReq, request: Request):
    prompt_msgs = [{"role":"user","content":req.prompt}]
    return await _pipeline(req.model, prompt_msgs, req.max_tokens, req.temperature, req.stream, "completion", request)

async def _pipeline(model_id: str, messages: list, max_tokens: int, temperature: float, stream: bool, mode: str, request: Request):
    rid = request.state.rid
    token = request.headers.get("Authorization","").removeprefix("Bearer ").strip()

    # Auth
    ar = await check_auth(token, request.app)
    if ar.status != "ok":
        mtr.auth_denied(ar.reason)
        return _err(401, ar.reason)
    org_id, tier = ar.org_id, ar.tier

    # Model routing — with PG drain check (returns tuple: model, error, status)
    model, route_error, route_code = route_model(model_id, request.app.state.catalog, tier, request.app.state.db)
    if not model:
        if route_code == 503:
            return _err(503, f"dependency_unavailable", detail=route_error)
        return _err(route_code or 403, route_error or "model_not_available", tier=tier, model=model_id)

    # Rate limit — with conservative token estimate (Section 5, documented error bound)
    if settings.rate_limit_enabled:
        est_tokens = _est_tok(messages, max_tokens)  # conservative estimator, minimum ~22% overestimate
        ok, reason = await check_rate_limit(org_id, tier, request.app.state.redis, est_tokens, request.app.state.db)
        if not ok:
            mtr.rate_limit_denied(tier)
            return _err(429, reason)

    # Security ingress — messages list
    if settings.security_enabled:
        try:
            sec_ok, sec_reason = check_security(messages)
            if not sec_ok: return _err(403, sec_reason)
        except Exception as e:
            logger.error("Security ingress exception: %s", e)
            return _err(503, "security_engine_error")

    # Billing reserve
    ref = None
    idem_key = request.headers.get("X-Idempotency-Key", rid)
    if settings.billing_enabled and request.app.state.db:
        result, ref = reserve(org_id, max_tokens + 100, request.app.state.db, idem_key)
        if result != BillingResult.SUCCESS:
            if result == BillingResult.INSUFFICIENT_BALANCE:
                return _err(402, "insufficient_balance")
            return _err(503, "billing_unavailable")

    # Upstream call with actual stream flag
    payload = {"model": model.served_model_name, "max_tokens": max_tokens, "temperature": temperature, "stream": stream}
    if mode == "chat":
        payload["messages"] = messages
    else:
        payload["prompt"] = messages[0]["content"] if messages else ""

    headers = {"Content-Type":"application/json"}
    if settings.vllm_api_key: headers["Authorization"] = f"Bearer {settings.vllm_api_key}"

    try:
        upstream_url = f"{model.upstream_url}/v1/chat/completions" if mode=="chat" else f"{model.upstream_url}/v1/completions"
        if stream:
            return await _stream_response(upstream_url, payload, headers, org_id, rid, model_id, ref, request)
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
    usage_data = data.get("usage", {})
    total = usage_data.get("total_tokens", 0)

    # Security egress
    if settings.security_egress_enabled:
        try:
            egr_ok, egr_reason, _ = check_egress(data)
            if not egr_ok:
                if ref: refund(org_id, ref, request.app.state.db)
                return _err(403, egr_reason)
        except Exception as e:
            logger.error("Security egress exception: %s", e)
            if ref: refund(org_id, ref, request.app.state.db)
            return _err(503, "security_egress_error")

    if ref: settle(org_id, ref, total, request.app.state.db)
    record_usage(org_id, rid, model_id, usage_data.get("prompt_tokens",0), usage_data.get("completion_tokens",0), 200, "settle", request.app.state.db)
    mtr.request_total(model_id, "200")
    mtr.tokens(model_id, usage_data.get("prompt_tokens", 0), usage_data.get("completion_tokens", 0))
    return data


async def _stream_response(url: str, payload: dict, headers: dict, org_id: str, rid: str, model_id: str, ref, request: Request):
    """Real SSE streaming: forward chunks, check egress, settle at end."""
    async def event_stream():
        usage_data = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        settled = False
        try:
            async with request.app.state.http.stream("POST", url, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    if ref: refund(org_id, ref, request.app.state.db)
                    yield f"data: {{\"error\":\"upstream_error_{resp.status_code}\"}}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        chunk = line[6:]
                        if chunk == "[DONE]":
                            break
                        try:
                            chunk_data = json.loads(chunk)
                            # Egress check per chunk
                            if settings.security_egress_enabled:
                                egr_ok, egr_reason, _ = check_egress(chunk_data)
                                if not egr_ok:
                                    yield f"data: {{\"error\":\"content_blocked\"}}\n\n"
                                    if ref: refund(org_id, ref, request.app.state.db)
                                    yield "data: [DONE]\n\n"
                                    return
                            # Accumulate usage
                            cu = chunk_data.get("usage", {})
                            if cu:
                                usage_data["prompt_tokens"] += cu.get("prompt_tokens", 0)
                                usage_data["completion_tokens"] += cu.get("completion_tokens", 0)
                                usage_data["total_tokens"] += cu.get("total_tokens", 0)
                        except json.JSONDecodeError:
                            pass
                        yield f"data: {chunk}\n\n"
                    else:
                        yield f"{line}\n"
                yield "data: [DONE]\n\n"
                # Settle after stream completes
                if ref:
                    settle(org_id, ref, usage_data["total_tokens"], request.app.state.db)
                    settled = True
                record_usage(org_id, rid, model_id, usage_data["prompt_tokens"], usage_data["completion_tokens"], 200, "settle", request.app.state.db)
        except Exception as e:
            logger.error("Stream error: %s", e)
            if ref and not settled:
                refund(org_id, ref, request.app.state.db)
            yield f"data: {{\"error\":\"stream_error\"}}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )

# Admin
def _admin(request: Request):
    if not check_admin(request): raise HTTPException(403, "admin_required")

@app.get("/admin/queues")
async def a_queues(request: Request):
    _admin(request)
    active = getattr(request.app.state, "active_requests", 0)
    return {"queues": [], "active_requests": active}

@app.get("/admin/models")
async def a_models(request: Request):
    _admin(request)
    models_data = []
    for m in request.app.state.catalog:
        d = m.to_dict()
        d["drained"] = getattr(m, "drained", False)
        d["health"] = "serving" if not d.get("drained") else "drained"
        models_data.append(d)
    return {"models": models_data}

@app.post("/admin/models/{mid}/drain")
async def a_drain(mid: str, request: Request):
    _admin(request)
    # Persist drain state to PostgreSQL for cross-replica visibility
    if request.app.state.db:
        conn = request.app.state.db.getconn()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO model_drain_state (model_id, drained, drained_at) VALUES (%s, %s, NOW()) "
                "ON CONFLICT (model_id) DO UPDATE SET drained = true, drained_at = NOW()",
                (mid, True),
            )
            conn.commit()
        finally:
            request.app.state.db.putconn(conn)
    # Also update local catalog
    for m in request.app.state.catalog:
        if m.id == mid:
            m.drained = True
            logger.info("Model %s drained", mid)
            return {"drained": mid, "status": "ok"}
    raise HTTPException(404, "model_not_found")

@app.post("/admin/models/{mid}/undrain")
async def a_undrain(mid: str, request: Request):
    _admin(request)
    if request.app.state.db:
        conn = request.app.state.db.getconn()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE model_drain_state SET drained = false WHERE model_id = %s",
                (mid,),
            )
            conn.commit()
        finally:
            request.app.state.db.putconn(conn)
    for m in request.app.state.catalog:
        if m.id == mid:
            m.drained = False
            logger.info("Model %s undrained", mid)
            return {"undrained": mid, "status": "ok"}
    raise HTTPException(404, "model_not_found")

@app.get("/admin/health")
async def a_health(request: Request):
    _admin(request)
    return await ready(request)

@app.get("/admin/reaper")
async def a_reaper(request: Request):
    _admin(request)
    db_ok = request.app.state.db is not None
    return {"reaper": "running" if (db_ok and settings.billing_enabled) else "disabled", "db_available": db_ok}

@app.get("/v1/rag/status")
async def rag_status(request: Request):
    return {"ready": False, "message": "RAG backend not configured"}

# Metrics endpoint — singleton registry
if settings.metrics_enabled:
    try:
        from metrics import metrics as _metrics
        from fastapi.responses import PlainTextResponse
        @app.get("/metrics")
        async def metrics_endpoint():
            return PlainTextResponse(_metrics.prometheus_text(), media_type="text/plain; charset=utf-8")
    except ImportError as e:
        logger.warning("metrics module not available: %s", e)
