"""Aither Gateway — FastAPI/ASGI. CHANGE-0022-C3."""
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
from rate_limit import check_rate_limit, estimate_tokens, check_org_quota, check_api_key_quota
from billing import (
    reserve, settle, refund, BillingResult,
    _compute_fingerprint, _clean_expired_idempotency,
    settle_and_complete, settle_and_complete_stream,
    _mark_idempotency_failed, get_replay_response,
)
from usage import record_usage
from security import check_security
from security_egress import check_egress, check_egress_streaming
from catalog import ModelEntry, load_catalog, resolve
from reaper import start_reaper
from metrics import metrics as mtr

# Conditional imports for optional features
_vault_available = False
_rag_available = False
try:
    from vault import vault_validate_key, vault_health, vault_login_and_check
    _vault_available = True
except ImportError:
    pass
try:
    from hybrid_rag import hybrid_query, wiki_ingest, wiki_status
    from wiki_graph import get_wiki_graph
    _rag_available = True
except ImportError:
    pass

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
    logger.info("Gateway CHANGE-0022-C3 starting")
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
        # Start idempotency cleanup thread
        threading.Thread(target=_idempotency_cleanup_thread, args=(app.state.db,), daemon=True).start()
    yield
    await app.state.http.aclose()
    await app.state.redis.aclose()
    if app.state.db: app.state.db.closeall()

def _idempotency_cleanup_thread(db_pool):
    """Periodically clean up expired idempotency records."""
    while True:
        time.sleep(3600)  # every hour
        try:
            deleted = _clean_expired_idempotency(db_pool)
            if deleted > 0:
                logger.info("Cleaned %d expired idempotency records", deleted)
        except Exception as e:
            logger.error("Idempotency cleanup error: %s", e)

app = FastAPI(title="Aither Gateway", version="3.0.0", lifespan=lifespan)

@app.middleware("http")
async def req_id_mw(request: Request, call_next):
    request.state.rid = request.headers.get("X-Request-ID", uuid.uuid4().hex[:8])
    resp = await call_next(request)
    resp.headers["X-Request-ID"] = request.state.rid
    return resp

def _err(c: int, m: str, **kw): return JSONResponse({"error": m, **kw}, status_code=c)

@app.get("/health")
async def health(): return {"status":"ok","service":"aither-gateway","change":"CHANGE-0022-C4"}

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

    # Upstream model health
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

    # Vault (critical if VAULT_REQUIRED)
    if settings.vault_enabled and settings.vault_required:
        try:
            vault_check = vault_login_and_check()
            deps["vault"] = vault_check
            if not vault_check.get("login") or not vault_check.get("policy_read"):
                critical_fail = True
        except Exception as e:
            deps["vault"] = {"reachable": False, "error": str(e)}
            critical_fail = True
    elif settings.vault_enabled:
        deps["vault"] = vault_health() if _vault_available else {"enabled": False, "status": "unknown"}
    else:
        deps["vault"] = "disabled"

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

# ── Model scope mapping (CHANGE-0022-C4, Section 3) ─────────────────────

_MODEL_SCOPE_MAP = {
    "qwen-14b": {"chat": "model:14b:chat", "completion": "model:14b:chat"},
    "qwen-32b-base": {"chat": "model:32b:chat-adapter", "completion": "model:32b:completion"},
}


def _model_required_scope(model_id: str, mode: str) -> str:
    """Return the required scope for a model/mode combination."""
    return _MODEL_SCOPE_MAP.get(model_id, {}).get(mode, "")


def _has_scope(ar, required_scope: str) -> bool:
    """Check if auth result has the required scope. Admin bypasses all."""
    if getattr(ar, "role", "") == "admin":
        return True
    scopes = getattr(ar, "scopes", [])
    if not isinstance(scopes, list):
        scopes = [scopes] if scopes else []
    return required_scope in scopes


async def _pipeline(model_id: str, messages: list, max_tokens: int, temperature: float, stream: bool, mode: str, request: Request):
    rid = request.state.rid
    token = request.headers.get("Authorization","").removeprefix("Bearer ").strip()

    # Auth
    ar = await check_auth(token, request.app)
    if ar.status != "ok":
        mtr.auth_denied(ar.reason)
        return _err(401, ar.reason)
    org_id, tier = ar.org_id, ar.tier

    # ── Scope enforcement (CHANGE-0022-C4, Section 3) ─────────────────
    required_scope = _model_required_scope(model_id, mode)
    if required_scope and not _has_scope(ar, required_scope):
        mtr.auth_denied("scope_denied")
        return _err(403, "scope_denied", required=required_scope,
                     scopes=getattr(ar, "scopes", []), model=model_id)
    # RAG scope check (only for /v1/rag/* — handled in RAG endpoints)

    # Model routing — with PG drain check
    model, route_error, route_code = route_model(model_id, request.app.state.catalog, tier, request.app.state.db)
    if not model:
        if route_code == 503:
            return _err(503, f"dependency_unavailable", detail=route_error)
        return _err(route_code or 403, route_error or "model_not_available", tier=tier, model=model_id)

    # Rate limit — FAIL-CLOSED: org quota + API-key quota + request rate limit
    if settings.rate_limit_enabled:
        est_tokens = estimate_tokens(messages, max_tokens)

        # 1. Organisation quota check (CHANGE-0022-C4 S4)
        ok_q, q_reason, _q = await check_org_quota(
            org_id, request.app.state.redis, request.app.state.db)
        if not ok_q:
            mtr.rate_limit_denied(tier)
            status_code = 403 if "unknown" in q_reason else 429
            return _err(status_code, q_reason)

        # 2. API-key quota check (CHANGE-0022-C4 S4)
        ok_k, k_reason, _k = await check_api_key_quota(
            token, request.app.state.redis, request.app.state.db)
        if not ok_k:
            mtr.rate_limit_denied(tier)
            return _err(429, k_reason)

        # 3. Per-request rate limit (RPM/TPM/daily)
        ok, reason, _details = await check_rate_limit(
            org_id, tier, request.app.state.redis, est_tokens,
            request.app.state.db, api_key=token, model_id=model_id)
        if not ok:
            mtr.rate_limit_denied(tier)
            status_code = 403 if "unknown_tier" in reason else (
                503 if "unavailable" in reason else 429)
            return _err(status_code, reason)

    # Security ingress
    if settings.security_enabled:
        try:
            sec_ok, sec_reason = check_security(messages)
            if not sec_ok: return _err(403, sec_reason)
        except Exception as e:
            logger.error("Security ingress exception: %s", e)
            return _err(503, "security_engine_error")

    # Billing reserve with org-scoped idempotency
    ref = None
    idem_key = request.headers.get("X-Idempotency-Key", rid)

    if settings.billing_enabled and request.app.state.db:
        # Compute request fingerprint for idempotency
        request_fingerprint = _compute_fingerprint({
            'messages': messages, 'model_id': model_id,
            'max_tokens': max_tokens, 'temperature': temperature,
            'stream': stream, 'mode': mode,
        })
        result, ref = reserve(org_id, max_tokens + 100, request.app.state.db,
                              idempotency_key=idem_key,
                              request_fingerprint=request_fingerprint,
                              model=model_id)

        if result == BillingResult.ALREADY_COMPLETED:
            # ── Replay: return original HTTP status + content-type + body (S5) ──
            replay = get_replay_response(idem_key, org_id, request.app.state.db)
            if replay is None:
                return _err(503, "replay_unavailable")
            rep_status, rep_ct, rep_body, rep_settle = replay
            if rep_settle == "DATABASE_ERROR":
                return _err(503, "billing_database_error")
            logger.info("Idempotency replay: org=%s key=%s status=%d", org_id, idem_key, rep_status)
            return JSONResponse(
                content=rep_body if isinstance(rep_body, dict) else {"replay": str(rep_body)},
                status_code=rep_status or 200,
                media_type=rep_ct or "application/json",
            )
        elif result == BillingResult.CONFLICT:
            return _err(409, "idempotency_conflict", detail="Same org+key, different payload")
        elif result == BillingResult.IN_PROGRESS:
            return _err(409, "idempotency_in_progress", detail="Request with this key is being processed")
        elif result == BillingResult.INSUFFICIENT_BALANCE:
            return _err(402, "insufficient_balance")
        elif result == BillingResult.DATABASE_ERROR:
            # DATABASE_ERROR must NOT return normal success
            return _err(503, "billing_database_error")
        elif result != BillingResult.SUCCESS:
            return _err(503, "billing_unavailable")

    # Upstream call
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
            return await _stream_response(upstream_url, payload, headers, org_id, rid, model_id, ref, idem_key, request)
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

    # Settle: use settle_and_complete with proper settlement result checking
    if ref:
        settle_result, settle_str = settle_and_complete(
            org_id, ref, total, request.app.state.db,
            ikey=idem_key, response_data=data,
        )
        if settle_result == BillingResult.DATABASE_ERROR:
            # DATABASE_ERROR must NOT return normal success
            logger.error("Settlement DATABASE_ERROR for org=%s ref=%s", org_id, ref)
            return _err(503, "settlement_error", detail="Database error during settlement")

    record_usage(request.app.state.db, org_id, rid, model_id,
                 usage_data.get("prompt_tokens", 0), usage_data.get("completion_tokens", 0),
                 total, "success")
    mtr.request_total(model_id, "200")
    mtr.tokens(model_id, usage_data.get("prompt_tokens", 0), usage_data.get("completion_tokens", 0))
    return data


async def _stream_response(url: str, payload: dict, headers: dict, org_id: str,
                           rid: str, model_id: str, ref, idem_key: str, request: Request):
    """Streaming with DLP holdback buffer (S6) + settlement-before-DONE (S7).

    S6 — Holdback buffer:
      - Don't deliver last HOLD_BACK chars of safe text
      - Merge held tail with next chunk before egress check
      - Reconstruct SSE chunks with only confirmed-safe text
      - On violation: NEVER deliver ANY byte of matched secret

    S7 — Settlement-first:
      - Don't send [DONE] until settle SUCCESS
      - On settlement failure: controlled error, reconciliation record, SIEM event
    """
    async def event_stream():
        usage_data = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        settled = False
        held_text = ""           # S6: held tail from previous chunk
        upstream_closed = False

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
                            # ── S7: DON'T send [DONE] yet — settle FIRST ──
                            break

                        try:
                            chunk_data = json.loads(chunk)

                            # ── S6: Egress check with holdback buffer ──
                            if settings.security_egress_enabled:
                                egr_ok, egr_reason, _, new_buffer, safe_text, new_held = \
                                    check_egress_streaming(
                                        chunk_data,
                                        sliding_buffer=held_text,
                                        org_id=org_id, request_id=rid, model=model_id,
                                        db_pool=request.app.state.db
                                    )
                                if not egr_ok:
                                    upstream_closed = True
                                    logger.warning("Stream egress violation: %s org=%s", egr_reason, org_id)
                                    if ref: refund(org_id, ref, request.app.state.db)
                                    yield f"data: {{\"error\":\"content_blocked\"}}\n\n"
                                    yield "data: [DONE]\n\n"
                                    return

                                held_text = new_held  # carry over for next iteration

                                # Reconstruct chunk with safe_text only
                                if safe_text:
                                    # Inject safe_text back into chunk delta
                                    choices = chunk_data.get("choices", [])
                                    if choices and "delta" in choices[0]:
                                        choices[0]["delta"]["content"] = safe_text
                                    elif choices and "message" in choices[0]:
                                        choices[0]["message"]["content"] = safe_text
                                    elif "text" in chunk_data:
                                        chunk_data["text"] = safe_text
                                    chunk = json.dumps(chunk_data)
                                else:
                                    # Nothing safe to release — skip this chunk
                                    # But accumulate usage if present
                                    cu = chunk_data.get("usage", {})
                                    if cu:
                                        usage_data["prompt_tokens"] += cu.get("prompt_tokens", 0)
                                        usage_data["completion_tokens"] += cu.get("completion_tokens", 0)
                                        usage_data["total_tokens"] += cu.get("total_tokens", 0)
                                    continue

                            # Accumulate usage
                            cu = chunk_data.get("usage", {})
                            if cu:
                                usage_data["prompt_tokens"] += cu.get("prompt_tokens", 0)
                                usage_data["completion_tokens"] += cu.get("completion_tokens", 0)
                                usage_data["total_tokens"] += cu.get("total_tokens", 0)

                        except json.JSONDecodeError:
                            pass

                        # S6: Yield ONLY after egress check + safe_text reconstruction
                        yield f"data: {chunk}\n\n"
                    else:
                        yield f"{line}\n"

                # ── S6: Final flush — release remaining held_text after final check ──
                if held_text and settings.security_egress_enabled:
                    final_ok, final_reason, _, _, _, _ = check_egress_streaming(
                        {"choices": [{"delta": {"content": ""}}]},
                        sliding_buffer=held_text,
                        org_id=org_id, request_id=rid, model=model_id,
                        db_pool=request.app.state.db,
                    )
                    if not final_ok:
                        logger.warning("Final flush violation: %s org=%s", final_reason, org_id)
                        if ref: refund(org_id, ref, request.app.state.db)
                        yield f"data: {{\"error\":\"content_blocked\"}}\n\n"
                        yield "data: [DONE]\n\n"
                        return
                    # Release remaining held text
                    yield f"data: {json.dumps({'choices': [{'delta': {'content': held_text}}]})}\n\n"

                # ── S7: Settle FIRST, THEN send [DONE] ──
                if ref and not upstream_closed:
                    settle_result, settle_str = settle_and_complete_stream(
                        org_id, ref, usage_data["total_tokens"],
                        request.app.state.db, ikey=idem_key,
                    )
                    if settle_result == BillingResult.DATABASE_ERROR:
                        logger.error("Stream settlement DATABASE_ERROR org=%s ref=%s", org_id, ref)
                        record_usage(request.app.state.db, org_id, rid, model_id,
                                     usage_data["prompt_tokens"], usage_data["completion_tokens"],
                                     usage_data["total_tokens"], "settlement_error")
                        yield f"data: {{\"error\":\"settlement_failed\",\"detail\":\"Database error during settlement\"}}\n\n"
                        yield "data: [DONE]\n\n"
                        return
                    settled = True

                # Only send [DONE] after successful settlement
                record_usage(request.app.state.db, org_id, rid, model_id,
                             usage_data["prompt_tokens"], usage_data["completion_tokens"],
                             usage_data["total_tokens"], "success")
                yield "data: [DONE]\n\n"

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


# ── Admin endpoints ─────────────────────────────────────────────────────

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
    for m in request.app.state.catalog:
        if m.id == mid:
            m.drained = True
            return {"drained": mid, "status": "ok"}
    raise HTTPException(404, "model_not_found")


@app.post("/admin/models/{mid}/undrain")
async def a_undrain(mid: str, request: Request):
    _admin(request)
    if request.app.state.db:
        conn = request.app.state.db.getconn()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE model_drain_state SET drained = false WHERE model_id = %s", (mid,))
            conn.commit()
        finally:
            request.app.state.db.putconn(conn)
    for m in request.app.state.catalog:
        if m.id == mid:
            m.drained = False
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


# ── Billing & Usage read endpoints ──────────────────────────────

async def _auth(request: Request):
    """Authenticate request and return AuthResult."""
    token = request.headers.get("Authorization","").removeprefix("Bearer ").strip()
    ar = await check_auth(token, request.app)
    if ar.status != "ok":
        raise HTTPException(401, detail="Authentication required")
    return ar

@app.get("/v1/billing/me")
async def billing_me(request: Request):
    """Get current user's billing balance from JWT org_id."""
    ar = await _auth(request)
    org_id = ar.org_id
    db_pool = request.app.state.db
    if not db_pool:
        raise HTTPException(503, detail="Database unavailable")
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT balance, reserved, tier FROM billing_accounts WHERE org_id=%s",
                (org_id,))
            row = cur.fetchone()
            if not row:
                return {"org_id": org_id, "balance": 0, "reserved": 0, "available": 0, "tier": "free"}
            balance, reserved, tier = row
            return {
                "org_id": org_id,
                "tier": tier or "free",
                "balance": int(balance or 0),
                "reserved": int(reserved or 0),
                "available": int(balance or 0) - int(reserved or 0),
            }
    finally:
        db_pool.putconn(conn)

@app.get("/v1/billing/me/ledger")
async def billing_ledger(request: Request, limit: int = 20):
    """Get billing ledger for current user's org."""
    ar = await _auth(request)
    org_id = ar.org_id
    db_pool = request.app.state.db
    if not db_pool:
        raise HTTPException(503, detail="Database unavailable")
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT amount, operation, reservation_id, balance_after, created_at "
                "FROM billing_ledger WHERE org_id=%s ORDER BY id DESC LIMIT %s",
                (org_id, min(limit, 100)))
            rows = cur.fetchall()
            return {
                "org_id": org_id,
                "ledger": [
                    {"amount": int(r[0]), "operation": r[1], "reference": r[2],
                     "balance_after": int(r[3]), "created_at": r[4].isoformat() if r[4] else None}
                    for r in rows
                ]
            }
    finally:
        db_pool.putconn(conn)

@app.get("/v1/usage/me")
async def usage_me(request: Request):
    """Get usage summary for current user's org."""
    ar = await _auth(request)
    org_id = ar.org_id
    db_pool = request.app.state.db
    if not db_pool:
        raise HTTPException(503, detail="Database unavailable")
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            # Total
            cur.execute(
                "SELECT count(*), coalesce(sum(amount),0) FROM billing_ledger "
                "WHERE org_id=%s AND operation='settle'", (org_id,))
            cnt, total_tokens = cur.fetchone()
            # Today
            cur.execute(
                "SELECT count(*), coalesce(sum(amount),0) FROM billing_ledger "
                "WHERE org_id=%s AND operation='settle' AND created_at > now() - interval '24 hours'",
                (org_id,))
            today_cnt, today_tokens = cur.fetchone()
            return {
                "org_id": org_id,
                "total_requests": cnt or 0,
                "total_tokens": int(total_tokens or 0),
                "requests_today": today_cnt or 0,
                "tokens_today": int(today_tokens or 0),
            }
    finally:
        db_pool.putconn(conn)

# ── Admin org billing ───────────────────────────────────────────

@app.get("/admin/orgs/{org_id}/billing")
async def admin_org_billing(org_id: str, request: Request):
    _admin(request)
    db_pool = request.app.state.db
    if not db_pool:
        raise HTTPException(503, detail="Database unavailable")
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT balance, reserved, tier FROM billing_accounts WHERE org_id=%s",
                (org_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, detail="Org not found")
            balance, reserved, tier = row
            return {
                "org_id": org_id,
                "tier": tier or "free",
                "balance": int(balance or 0),
                "reserved": int(reserved or 0),
                "available": int(balance or 0) - int(reserved or 0),
            }
    finally:
        db_pool.putconn(conn)


# ── RAG endpoints with FULL security pipeline (CHANGE-0022-C3) ─────────

def _has_rag_scope(ar) -> bool:
    """Check if auth result includes RAG scope."""
    if getattr(ar, "role", "") == "admin":
        return True
    for s in getattr(ar, "scopes", []):
        if "rag" in str(s).lower():
            return True
    return False


async def _check_tier_rag(tier: str, org_id: str, db_pool, redis) -> bool:
    """Check if tier allows RAG access."""
    try:
        if db_pool:
            conn = db_pool.getconn()
            try:
                cur = conn.cursor()
                cur.execute("SELECT rag_enabled FROM subscription_tiers WHERE tier_id = %s", (tier,))
                row = cur.fetchone()
                if row:
                    return bool(row[0])
            finally:
                db_pool.putconn(conn)
        return False
    except Exception as e:
        logger.warning("Tier RAG check failed: %s", e)
        return False


def _get_chroma():
    """Lazy ChromaDB HTTP client."""
    import chromadb
    return chromadb.HttpClient(
        host=settings.chroma_url.split("://")[1].split(":")[0] if "://" in settings.chroma_url else settings.chroma_url,
        port=int(settings.chroma_url.split(":")[-1]) if ":" in settings.chroma_url else 8000)


def _get_ef():
    """Lazy embedding function."""
    from chromadb.utils import embedding_functions
    return embedding_functions.ONNXMiniLM_L6_V2()


@app.get("/v1/rag/status")
async def rag_status(request: Request):
    """GET /v1/rag/status — full security pipeline."""
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    ar = await check_auth(token, request.app)
    if ar.status != "ok":
        return _err(401, ar.reason)
    org_id, tier = ar.org_id, ar.tier

    if not _has_rag_scope(ar):
        return _err(403, "rag_access_denied")

    if not await _check_tier_rag(tier, org_id, request.app.state.db, request.app.state.redis):
        return _err(403, "rag_not_available", tier=tier)

    if not _rag_available or not settings.rag_enabled:
        return _err(503, "rag_disabled")

    try:
        stats = wiki_status()
        return {"ready": True, "org_id": org_id, "tier": tier, **stats}
    except Exception as e:
        logger.error("RAG status error: %s", e)
        correlation_id = getattr(request.state, 'rid', uuid.uuid4().hex[:8])
        return _err(500, "rag_query_error", detail=str(e), correlation_id=correlation_id)


@app.post("/v1/rag/ingest")
async def rag_ingest(request: Request):
    """POST /v1/rag/ingest — auth + org isolation + security + SIEM."""
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    ar = await check_auth(token, request.app)
    if ar.status != "ok":
        return _err(401, ar.reason)
    org_id, tier = ar.org_id, ar.tier

    if not _has_rag_scope(ar):
        return _err(403, "rag_access_denied")

    if not await _check_tier_rag(tier, org_id, request.app.state.db, request.app.state.redis):
        return _err(403, "rag_not_available", tier=tier)

    if not _rag_available or not settings.rag_enabled:
        return _err(503, "rag_disabled")

    rid = request.state.rid

    try:
        body = await request.json()
        docs = body.get("documents", [])
        if not docs:
            return _err(400, "missing_documents")

        # Security ingress on document content (FAIL-CLOSED)
        if settings.security_enabled:
            try:
                for doc in docs:
                    sec_ok, sec_reason = check_security([{"role": "user", "content": doc.get("text", "")}])
                    if not sec_ok:
                        return _err(403, "security_violation", reason=sec_reason)
            except Exception as sec_err:
                logger.error("Security ingress check failed for RAG ingest: %s", sec_err)
                return _err(503, "rag_ingest_error", detail="Security ingress check failed", correlation_id=rid)

        # Add org_id to metadata for isolation
        for doc in docs:
            doc["metadata"] = doc.get("metadata", {})
            doc["metadata"]["org_id"] = org_id
            doc["metadata"]["tier"] = tier

        # Ingest into org-scoped ChromaDB collection
        chroma = _get_chroma()
        ef = _get_ef()
        coll_name = f"documents_{org_id}"
        coll = chroma.get_or_create_collection(coll_name)

        ids, texts, metadatas = [], [], []
        for doc in docs:
            ids.append(doc.get("id", str(uuid.uuid4())[:8]))
            texts.append(doc["text"])
            metadatas.append(doc.get("metadata", {"org_id": org_id}))

        embeddings = ef(texts)
        coll.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

        return {"ingested": len(docs), "ids": ids, "org_id": org_id, "collection": coll_name}
    except Exception as e:
        logger.error("RAG ingest error: %s", e)
        correlation_id = getattr(request.state, 'rid', uuid.uuid4().hex[:8])
        return _err(500, "rag_ingest_error", detail=str(e), correlation_id=correlation_id)


@app.post("/v1/rag/query")
async def rag_query_post(request: Request):
    """POST /v1/rag/query — full security pipeline with org isolation."""
    return await _rag_pipeline("query", request)


@app.post("/v1/rag/hybrid-query")
async def rag_hybrid_query(request: Request):
    """POST /v1/rag/hybrid-query — hybrid (semantic + wiki graph)."""
    return await _rag_pipeline("hybrid-query", request)


@app.post("/v1/rag/wiki-ingest")
async def rag_wiki_ingest(request: Request):
    """POST /v1/rag/wiki-ingest — wiki re-index."""
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    ar = await check_auth(token, request.app)
    if ar.status != "ok":
        return _err(401, ar.reason)
    org_id, tier = ar.org_id, ar.tier

    if not _has_rag_scope(ar):
        return _err(403, "rag_access_denied")

    if not await _check_tier_rag(tier, org_id, request.app.state.db, request.app.state.redis):
        return _err(403, "rag_not_available", tier=tier)

    if not _rag_available or not settings.rag_enabled:
        return _err(503, "rag_disabled")

    rid = request.state.rid

    try:
        result = wiki_ingest()
        return {"org_id": org_id, **result}
    except Exception as e:
        logger.error("Wiki ingest error: %s", e)
        return _err(500, "rag_ingest_error", detail=str(e), correlation_id=rid)


async def _rag_pipeline(mode: str, request: Request):
    """Shared RAG pipeline: auth → scope → tier → security ingress → query → security egress → SIEM."""
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()

    # 1. Auth
    ar = await check_auth(token, request.app)
    if ar.status != "ok":
        return _err(401, ar.reason)
    org_id, tier = ar.org_id, ar.tier

    # 2. Scope check
    if not _has_rag_scope(ar):
        return _err(403, "rag_access_denied")

    # 3. Tier check
    if not await _check_tier_rag(tier, org_id, request.app.state.db, request.app.state.redis):
        return _err(403, "rag_not_available", tier=tier)

    if not _rag_available or not settings.rag_enabled:
        return _err(503, "rag_disabled")

    # 4. Parse request
    try:
        body = await request.json()
        query = body.get("query", "")
        top_k = body.get("top_k", 5)
        if not query:
            return _err(400, "missing_query")
    except Exception:
        return _err(400, "invalid_json")

    # 5. Security ingress on query (FAIL-CLOSED: exception → 503)
    rid = request.state.rid
    if settings.security_enabled:
        try:
            sec_ok, sec_reason = check_security([{"role": "user", "content": query}])
            if not sec_ok:
                return _err(403, "security_violation", reason=sec_reason)
        except Exception as e:
            logger.error("Security ingress error: %s", e)
            return _err(503, "rag_query_error", detail="Security ingress check failed", correlation_id=rid)

    # 6. Execute query with ORG ISOLATION
    try:
        if mode == "hybrid-query":
            wiki_radius = body.get("wiki_radius", 1)
            results = hybrid_query(query, top_k=top_k, wiki_radius=wiki_radius, org_id=org_id)
        else:
            # Semantic search in org-scoped collection
            chroma = _get_chroma()
            ef = _get_ef()
            coll_name = f"documents_{org_id}"

            try:
                coll = chroma.get_collection(coll_name)
                count = coll.count()
                if count == 0:
                    results = []
                else:
                    q_embedding = ef(["query: " + query])
                    # Enforce org isolation at DB level via where clause
                    chroma_results = coll.query(
                        query_embeddings=q_embedding,
                        n_results=min(top_k, count),
                        where={"org_id": org_id})
                    results = [{
                        "id": id_, "text": doc, "metadata": meta,
                        "score": round(1 - float(dist), 4) if dist and float(dist) != 1 else 0
                    } for id_, doc, meta, dist in zip(
                        chroma_results["ids"][0],
                        chroma_results["documents"][0],
                        chroma_results.get("metadatas", [[{}] * len(chroma_results["ids"][0])])[0],
                        chroma_results.get("distances", [[1] * len(chroma_results["ids"][0])])[0])]
            except Exception as chroma_err:
                logger.error("ChromaDB error for org=%s: %s", org_id, chroma_err)
                return _err(503, "rag_backend_unavailable", detail="ChromaDB operation failed", correlation_id=rid)

        # 7. Security egress on retrieved context (FAIL-CLOSED: exception → 503, violation → text removal)
        if settings.security_egress_enabled:
            for r in results:
                try:
                    egr_ok, egr_reason, _ = check_egress(
                        {"choices": [{"message": {"content": r.get("text", "")}}]},
                        org_id=org_id)
                    if not egr_ok:
                        logger.warning("RAG egress violation org=%s: %s", org_id, egr_reason)
                        r["filtered"] = True
                        r["filter_reason"] = egr_reason
                        # Remove original text to prevent data leak
                        r["text"] = ""
                        r["redacted"] = True
                except Exception as egr_err:
                    logger.error("Security egress check failed org=%s: %s", org_id, egr_err)
                    return _err(503, "rag_query_error", detail="Security egress check failed", correlation_id=rid)

        return {
            "query": query, "results": results, "count": len(results),
            "org_id": org_id, "tier": tier, "mode": mode,
        }
    except Exception as e:
        logger.error("RAG %s error: %s", mode, e)
        return _err(500, "rag_query_error", detail=str(e), correlation_id=rid)


# ── Metrics ─────────────────────────────────────────────────────────────

if settings.metrics_enabled:
    try:
        from metrics import metrics as _metrics
        from fastapi.responses import PlainTextResponse

        @app.get("/metrics")
        async def metrics_endpoint():
            return PlainTextResponse(_metrics.prometheus_text(), media_type="text/plain; charset=utf-8")
    except ImportError as e:
        logger.warning("metrics module not available: %s", e)
