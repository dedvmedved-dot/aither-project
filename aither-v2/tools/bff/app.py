import os
import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

# --- Configuration ---
CHAT_14B_URL = os.environ.get(
    "BFF_14B_BASE_URL",
    "http://vllm-14b-instruct.aither-inference.svc:8000"
)
GATEWAY_32B_URL = os.environ.get(
    "BFF_32B_GATEWAY_URL",
    "http://nginx-gateway-32b.aither-inference.svc:8000"
)
TIMEOUT = int(os.environ.get("BFF_REQUEST_TIMEOUT_SECONDS", "300"))
API_KEY = os.environ.get("VLLM_API_KEY", "")
AUTH_HEADER = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}

logger = logging.getLogger("aither-bff")

# --- Shared HTTP client ---
client: httpx.AsyncClient = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    client = httpx.AsyncClient(timeout=TIMEOUT, headers=AUTH_HEADER)
    yield
    await client.aclose()

app = FastAPI(title="Aither BFF", version="0.1.0", lifespan=lifespan)

# --- Models ---
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

# --- Endpoints ---

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/v1/chat")
async def chat(req: ChatRequest):
    if req.model == "32b":
        raise HTTPException(
            status_code=422,
            detail="32B base model does not support chat. Use /api/v1/completions for 32B."
        )
    if req.model == "14b":
        url = f"{CHAT_14B_URL}/v1/chat/completions"
        body = req.model_dump()
        body["model"] = "qwen-14b"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown model: {req.model}")

    resp = await client.post(url, json=body)
    return resp.json()


@app.post("/api/v1/completions")
async def completions(req: CompletionRequest):
    if req.model == "32b":
        # Route through gateway to enforce policy
        url = f"{GATEWAY_32B_URL}/v1/completions"
        body = req.model_dump()
        body["model"] = "qwen-32b-base"
    elif req.model == "14b":
        url = f"{CHAT_14B_URL}/v1/completions"
        body = req.model_dump()
        body["model"] = "qwen-14b"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown model: {req.model}")

    resp = await client.post(url, json=body)
    return resp.json()


@app.get("/api/v1/models")
async def list_models():
    return {
        "models": [
            {"id": "14b", "name": "Qwen 14B Instruct", "type": "chat"},
            {"id": "32b", "name": "Qwen 32B Base", "type": "completion"},
        ]
    }

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000)
