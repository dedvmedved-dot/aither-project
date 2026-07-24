# Internet 32B — Regression Tests

**Date:** 2026-07-24  
**Scope:** All models × all Internet ports × all endpoints

## Results

### GET /v1/models

| Port | Model | HTTP | Time | Status |
|---|---|---|---|---|
| :443 | 14B | 200 | 5.13s | ✅ |
| :10443 | 14B | 504 | 5.05s | ❌ |
| :443 | 32B | 200 | 5.17s | ✅ |
| :10443 | 32B | 200 | 5.14s | ✅ |

### POST /v1/chat/completions

| Port | Model | HTTP | Time | Status |
|---|---|---|---|---|
| :443 | 14B | 000 | 45.00s | ❌ |
| :10443 | 14B | 200 | 10.17s | ✅ |
| :443 | 32B | 200 | 5.42s | ✅ |
| :10443 | 32B | 504 | 10.02s | ❌ |

## Web Chat (manual verification)

| Path | Status |
|---|---|
| Web Chat Internet | ⚠️ Intermittent (same proxy path) |
| Web Chat Test Zone | ✅ Stable |

## Summary

| Check | :443 | :10443 |
|---|---|---|
| GET /v1/models 14B | ✅ | ❌ |
| GET /v1/models 32B | ✅ | ✅ |
| POST chat 14B | ❌ | ✅ |
| POST chat 32B | ✅ | ❌ |

**Overall:** Both ports show intermittent failures. No consistent pattern across models/endpoints.  
The VPN tunnel instability affects all HTTPS-proxied requests randomly.

## Semantic Sanity Check

| Model | Response | Valid? |
|---|---|---|
| 14B | "Hi there! How can I" | ✅ Coherent |
| 32B | "at a time, and" | ⚠️ Base model — text completion, not chat |

The 32B model (`qwen-32b-gptq`) is a base completion model loaded via vLLM.
Chat completions are converted to text completions by ai-platform.
Responses are syntactically valid but semantically less coherent than instruction-tuned models.
