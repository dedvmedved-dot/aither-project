import os
import logging
import hashlib
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
import httpx
import redis.asyncio as redis_asyncio

# Real model IDs from vLLM /v1/models endpoints
MODEL_14B = "qwen-14b"
MODEL_32B = "qwen-32b-base"

CHAT_14B_URL = os.environ.get("BFF_14B_BASE_URL", "http://vllm-14b-instruct.aither-inference.svc:8000")
GATEWAY_32B_URL = os.environ.get("BFF_32B_GATEWAY_URL", "http://nginx-gateway-32b.aither-inference.svc:8000")
TIMEOUT = int(os.environ.get("BFF_REQUEST_TIMEOUT_SECONDS", "300"))

# Rate limiting settings
RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"
REDIS_URL = os.environ.get("REDIS_URL", "redis://aither-redis-rate-limit.aither-inference.svc:6379/0")
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60"))
RATE_LIMIT_MAX_REQUESTS = int(os.environ.get("RATE_LIMIT_MAX_REQUESTS", "10"))

logger = logging.getLogger("aither-bff")

client: httpx.AsyncClient = None
redis_client: redis_asyncio.Redis = None
redis_available = False


async def _rate_limit_key(req: Request) -> str:
    """Generate a safe rate limit key from Authorization header hash or client IP."""
    auth = req.headers.get("authorization") or req.headers.get("Authorization") or ""
    if auth:
        # Hash the token — never store raw token
        h = hashlib.sha256(auth.encode()).hexdigest()
        return f"rl:{h}"
    # Fallback to client IP
    forwarded = req.headers.get("x-forwarded-for", "")
    client_ip = forwarded.split(",")[0].strip() if forwarded else req.client.host if req.client else "unknown"
    return f"rl:ip:{client_ip}"


async def _check_rate_limit(req: Request) -> bool:
    """Check rate limit. Returns True if allowed, False if exceeded."""
    global redis_available
    if not RATE_LIMIT_ENABLED:
        return True
    if not redis_available:
        logger.warning("Redis unavailable — fail-open, allowing request")
        return True

    try:
        key = await _rate_limit_key(req)
        import time
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client, redis_client, redis_available
    client = httpx.AsyncClient(timeout=TIMEOUT)
    try:
        redis_client = redis_asyncio.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        redis_available = True
        logger.info("Redis connected at %s", REDIS_URL)
    except Exception as e:
        redis_client = None
        redis_available = False
        logger.warning("Redis unavailable at %s: %s — fail-open mode", REDIS_URL, str(e))
    yield
    if redis_client:
        await redis_client.aclose()
    await client.aclose()

app = FastAPI(title="Aither BFF", version="0.3.0", lifespan=lifespan)

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


async def _headers(req: Request) -> dict:
    h = {"Content-Type": "application/json"}
    if "authorization" in req.headers:
        h["Authorization"] = req.headers["authorization"]
    return h


@app.get("/health")
async def health():
    rl_status = "enabled" if RATE_LIMIT_ENABLED else "disabled"
    redis_s = "connected" if redis_available else "unavailable"
    return {"status": "ok", "rate_limit": rl_status, "redis": redis_s}


@app.post("/api/v1/chat")
async def chat(req: Request):
    body = await req.json()
    model = body.get("model", "")
    headers = await _headers(req)

    # Rate limit check before processing
    allowed = await _check_rate_limit(req)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")

    if model == "32b" or model == MODEL_32B:
        raise HTTPException(status_code=422, detail=f"{MODEL_32B} does not support chat. Use /api/v1/completions.")

    if model == "14b" or model == MODEL_14B:
        body["model"] = MODEL_14B
        url = f"{CHAT_14B_URL}/v1/chat/completions"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model}")

    async with client.stream("POST", url, json=body, headers=headers) as resp:
        content = await resp.aread()
        return Response(
            content=content,
            status_code=resp.status_code,
            media_type=resp.headers.get("content-type", "application/json"),
        )


@app.post("/api/v1/completions")
async def completions(req: Request):
    body = await req.json()
    model = body.get("model", "")
    headers = await _headers(req)

    # Rate limit check before processing
    allowed = await _check_rate_limit(req)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")

    if model == "32b" or model == MODEL_32B:
        body["model"] = MODEL_32B
        # Route through gateway to enforce policy
        url = f"{GATEWAY_32B_URL}/v1/completions"
    elif model == "14b" or model == MODEL_14B:
        body["model"] = MODEL_14B
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


@app.get("/api/v1/models")
async def list_models():
    return {
        "models": [
            {"id": "14b", "name": MODEL_14B, "type": "chat"},
            {"id": "32b", "name": MODEL_32B, "type": "completion"},
        ]
    }

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000)
