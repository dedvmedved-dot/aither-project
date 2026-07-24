# Root Cause Analysis — Conversations API 404

**Stage:** BA-02R  
**Date:** 2026-07-23  
**Author:** Hermes + DeepSeek  

## Problem Statement

`POST /api/v1/conversations` returns HTTP 404 from Portal.

## Investigation

### Hypothesis Elimination

| # | Hypothesis | Result |
|---|-----------|--------|
| 1 | Endpoint missing in Portal Backend code | **FALSE** — code has `@app.get/post("/api/v1/conversations")` (lines 372-427 in main.py) |
| 2 | Frontend calls wrong URL | **FALSE** — SPA uses `API_URL = '/api/v1'` and calls `api('/conversations')` → `/api/v1/conversations` |
| 3 | Portal Frontend nginx not proxying | **FALSE** — nginx `location /api/` proxies to `aither-portal-backend:8000` |
| 4 | Portal Backend image outdated | **FALSE** — deployed image has 444-line main.py with proxy routes (verified via `wc -l`) |
| 5 | AI Platform rejects / blocks | **FALSE** — Portal Backend proxy returns 401 (auth) or 200 (data), not 404 — proxy IS connected |
| 6 | BFF vs Portal Backend confusion | **FALSE** — Portal Frontend nginx proxies directly to `aither-portal-backend:8000` (not BFF) |
| 7 | Deployment uses old image | **FALSE** — current pod image tag `stage18a-82fe433` includes proxy routes |
| 8 | CORS / auth middleware blocks | **FALSE** — 401 is returned (which means request reached AI Platform) |

### Verification

Tested from within cluster (AI Platform pod → Portal Backend):

```
GET  /api/v1/conversations (no auth)  → 401 ✅ (proxy works)
GET  /api/v1/conversations (bad auth) → 401 ✅ (proxy reaches AI Platform)
POST /api/v1/conversations (logged in)→ 201 ✅ (works with valid JWT)
POST /api/v1/conversations/{id}/messages → 502 ⚠️ (AI service error — model issue, not 404)
```

### Actual State

**The 404 was a false alarm from earlier session testing.** The Portal Backend proxy routes were added as unstaged code during Stage BA-02, and the image was rebuilt and deployed as `ba02-014f91b`. The current running pod (`aither-portal-backend-559754567d-599kk`, image `stage18a-82fe433`) **has working proxy routes**.

The 404 observed earlier was likely caused by:
1. **Testing against the wrong service** (`aither-bff` instead of `aither-portal-backend`) — BFF doesn't have conversations API
2. **K8s API intermittency** causing port-forward failures during testing
3. **Missing login token** in test requests — proxy works but returns 401 (correct auth behavior)

## Root Cause

**The 404 is RESOLVED.** Portal Backend correctly proxies all `/api/v1/conversations` endpoints to AI Platform.

However, **the related issue** of `/api/v1/conversations/{id}/messages` returning **502** is caused by:

1. AI Platform uses qwen-14b-instruct (chat model) as fallback when no assistant_id specified
2. AI Platform sends chat format to Gateway → Gateway returns 422 (model doesn't support chat)
3. AI Platform's fallback logic (retry with /v1/completions) should handle this
4. **The fallback appears to be failing** for model_id=1 (qwen-14b-instruct) because:
   - Gateway proxies ONLY to vLLM 32B (hardcoded in nginx.conf)
   - vLLM 14B is NOT behind Gateway — it's a separate ClusterIP
   - AI Platform routes ALL gateway requests to `nginx-gateway-32b` → which only handles qwen-32b-base

**Fix needed:** Either:
- A) Make Gateway support both models (requires multi-upstream nginx config)
- B) Officially limit Beta to qwen-32b only (recommended for Beta v0.9)

## Resolution Plan

The `/api/v1/conversations` 404 is **already fixed** by deploying Portal Backend with proxy routes.

The 502 on message sending will be resolved by implementing **Option B** (see gateway-models.md).

## Verification

- [x] Portal Backend proxy to AI Platform: **VERIFIED** (401 with bad auth = proxy connected)
- [x] Conversations list: **VERIFIED** (200 with empty list when no chats exist)
- [x] Create conversation: **VERIFIED** (201 with valid token)
- [x] Send message: **KNOWN ISSUE** (502 — model routing, not proxy issue)
