# OpenAI API Compatibility — Final Report

**Date:** 2026-07-23
**Project:** Aither / AI Hermes MVP
**Stage:** BA-01R — Beta Acceptance Recovery
**Status:** ✅ PASSED

---

## Root Cause Analysis

### Blocking Defect
AI Platform (`aither-ai-platform`) did not pass the vLLM API Key (`VLLM_API_KEY`) to the nginx-gateway-32b when forwarding chat completion requests.

### Chain of Failure
```
Client → POST /v1/chat/completions (with API Key) → AI Platform
  → Gateway /v1/chat/completions (HTTP 422 — 32B base has no chat)
  → Gateway /v1/completions (NO Authorization header)
  → vLLM 32B returns HTTP 401 ("auth required")
  → Gateway intercepts 401 → HTTP 401
  → AI Platform returns HTTP 502
```

### Root Cause Details
| Component | Issue |
|-----------|-------|
| **vLLM Secret** | Contains `VLLM_API_KEY` (64-char key). vLLM requires this in `Authorization: Bearer <key>` for every request. |
| **Gateway (nginx)** | `proxy_set_header Authorization $http_authorization` — forwards Authorization header to vLLM. Correctly configured. |
| **AI Platform code** | `get_gateway_client()` created `httpx.AsyncClient` with **no default headers**. Old code did not pass `GATEWAY_API_KEY`. |
| **AI Platform env** | `AI_PLATFORM_GATEWAY_API_KEY` was not set in the K8s Deployment. |
| **Model routing** | AI Platform sends `model_identifier: qwen-32b-gptq` to Gateway, but vLLM expects `qwen-32b-base`. Fixed by updating the DB. |

### Fix Applied
1. **Code change** (`services/ai-platform/app/main.py`): `get_gateway_client()` now reads `AI_PLATFORM_GATEWAY_API_KEY` env var and sets `Authorization: Bearer <key>` header in the httpx client.
2. **Deployment change** (`services/ai-platform/k8s/ai-platform.yaml`): Added `AI_PLATFORM_GATEWAY_API_KEY` env var from `vllm-api-key` secret.
3. **Deployment method**: New Docker image built (`10.129.13.78:5000/aither-ai-platform:ba01r-fix`) and pushed to cluster registry, then applied via `kubectl set image`.
4. **Model identifier fix**: Updated AI Platform SQLite DB: `qwen-32b-gptq` → `qwen-32b-base` (matches vLLM model ID).

---

## Test Results

### Test 1: `POST /v1/chat/completions` (Bearer token)
```
curl -X POST http://aither-ai-platform:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer aither_83de4e49_..." \
  -d '{"model":"qwen-32b-gptq","messages":[{"role":"user","content":"Say hello"}],"max_tokens":20}'

HTTP 200 OK
Response: {"id":"cmpl-...","object":"text_completion","model":"qwen-32b-base",
  "choices":[{"text":"Bonjour!"}],"usage":{"prompt_tokens":5,...}}
```
**Result:** ✅ PASSED

### Test 2: `POST /v1/chat/completions` (X-API-Key header)
```
curl -X POST ... -H "X-API-Key: aither_83de4e49_..." ...
HTTP 200 OK
```
**Result:** ✅ PASSED

### Test 3: `GET /api/v1/models` (admin token)
```
HTTP 200 OK
Models: qwen-14b-instruct (model_id: qwen/Qwen-14B-Instruct), qwen-32b-gptq (model_id: qwen-32b-base)
```
**Result:** ✅ PASSED

---

## Registered Models

| Name | Model Identifier | Provider | Enabled |
|------|-----------------|----------|---------|
| qwen-14b-instruct | qwen/Qwen-14B-Instruct | local | ✅ |
| qwen-32b-gptq | qwen-32b-base | local | ✅ |

---

## Verification Command
```python
import urllib.request, json
req = urllib.request.Request("http://aither-ai-platform:8000/v1/chat/completions")
req.method = "POST"
req.data = json.dumps({"model":"qwen-32b-gptq","messages":[{"role":"user","content":"test"}],"max_tokens":10}).encode()
req.add_header("Content-Type", "application/json")
req.add_header("Authorization", "Bearer aither_<your_key>")
resp = urllib.request.urlopen(req, timeout=30)
print(resp.status, json.loads(resp.read().decode()))
```

---

## Logs

AI Platform logs confirming fix:
```
INFO:httpx:HTTP Request: POST http://nginx-gateway-32b.aither-inference.svc:8000/v1/chat/completions "HTTP/1.1 422"
INFO:httpx:HTTP Request: POST http://nginx-gateway-32b.aither-inference.svc:8000/v1/completions "HTTP/1.1 200 OK"
```

Before fix: `"HTTP/1.1 401 Unauthorized"` after `/v1/completions`
After fix: `"HTTP/1.1 200 OK"` after `/v1/completions`

---

**Conclusion:** OpenAI API Compatibility fully restored. Both `/v1/chat/completions` and `/api/v1/models` return HTTP 200 with valid responses.
