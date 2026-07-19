# Aither BFF — Minimal MVP Backend for Frontend

## Purpose

BFF (Backend for Frontend) is the single user-facing backend for the Aither MVP.
Portal communicates only with BFF. BFF routes inference requests to the appropriate backend services.

## Architecture

```
Portal → BFF → nginx-gateway-32b (for 32B completion)
             → vllm-14b-instruct (for 14B chat)
```

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | /health | Health check |
| POST | /api/v1/chat | Chat completions (14B only; 32B blocked) |
| POST | /api/v1/completions | Text completions (32B via gateway) |
| GET | /api/v1/models | List available models |

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| BFF_14B_BASE_URL | http://vllm-14b-instruct.aither-inference.svc:8000 | 14B vLLM service |
| BFF_32B_GATEWAY_URL | http://nginx-gateway-32b.aither-inference.svc:8000 | 32B gateway |
| BFF_REQUEST_TIMEOUT_SECONDS | 300 | Upstream timeout |
| VLLM_API_KEY | (from secret) | API key for vLLM services |
