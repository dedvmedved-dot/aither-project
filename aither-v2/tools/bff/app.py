import os
import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
import httpx

# Real model IDs from vLLM /v1/models endpoints
MODEL_14B = "qwen-14b"
MODEL_32B = "qwen-32b-base"

CHAT_14B_URL = os.environ.get("BFF_14B_BASE_URL", "http://vllm-14b-instruct.aither-inference.svc:8000")
GATEWAY_32B_URL = os.environ.get("BFF_32B_GATEWAY_URL", "http://nginx-gateway-32b.aither-inference.svc:8000")
TIMEOUT = int(os.environ.get("BFF_REQUEST_TIMEOUT_SECONDS", "300"))

logger = logging.getLogger("aither-bff")

client: httpx.AsyncClient = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    client = httpx.AsyncClient(timeout=TIMEOUT)
    yield
    await client.aclose()

app = FastAPI(title="Aither BFF", version="0.2.0", lifespan=lifespan)

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
    return {"status": "ok"}


@app.post("/api/v1/chat")
async def chat(req: Request):
    body = await req.json()
    model = body.get("model", "")
    headers = await _headers(req)

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
