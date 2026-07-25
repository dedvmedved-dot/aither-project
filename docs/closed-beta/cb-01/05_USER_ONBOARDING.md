# CB-01 User Onboarding Package

**Version:** Closed Beta RC (based on U1.4 release)
**Date:** 2026-07-25

---

## What is Aither?

Aither is an internal AI inference platform providing OpenAI-compatible API access to Qwen models (14B chat, 32B base).

---

## Connection Details

**Endpoint:** `https://fb1.spb.ru:443/v1`

**Authentication:** Bearer token (API key) in `Authorization` header:
```
Authorization: Bearer aither_XXXXXXXX_<secret>
```

---

## API Key Security

- 🔐 Store your key securely — never share it
- 🔐 Do NOT commit keys to Git or post in public channels
- 🔐 If compromised, request immediate revocation

---

## Quick Start

```bash
# List models
curl -sk https://fb1.spb.ru:443/v1/models \
  -H "Authorization: Bearer YOUR_KEY"

# Chat with 14B
curl -sk https://fb1.spb.ru:443/v1/chat/completions \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-14b","messages":[{"role":"user","content":"Hello!"}],"max_tokens":100}'

# Use 32B (base model)
curl -sk https://fb1.spb.ru:443/v1/chat/completions \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-32b-base","messages":[{"role":"user","content":"Continue: Once upon a time"}],"max_tokens":50}'
```

---

## Supported Models

| Model ID | Type | Context | Description |
|---|---|---|---|
| qwen-14b | Chat (instruct) | 4096 | General-purpose chat model |
| qwen-32b-base | Base (completion) | 4096 | Raw completion model |

---

## Supported Scenarios

- ✅ Chat conversations with 14B model
- ✅ Text completion with 32B base model
- ✅ Model listing and discovery
- ✅ Sequential API requests
- ✅ Personal API key authentication

---

## Unsupported / Known Limitations

- ❌ `POST /v1/completions` endpoint — use `/v1/chat/completions` instead
- ❌ Streaming responses (`stream: true`) — not yet supported
- ❌ Function calling / tool use
- ❌ Multi-turn conversation persistence (stateless API)
- ❌ Model fine-tuning
- ⚠️ 32B base model returns raw completions, not chat-formatted responses
- ⚠️ Rate limit: 300 requests/minute, burst 20
- ⚠️ Max ~4 concurrent 14B requests (GPU-queued, ~25s each under load)

---

## Usage Rules

- **Rate limit:** 300 req/min, burst 20
- **Max tokens:** 4096 context window
- **Concurrent requests:** Avoid flooding — 14B is GPU-queued
- **Expected response time:** 0.5–50s depending on load and model

---

## Reporting Issues

Send feedback to the project maintainer with:
1. Timestamp (UTC)
2. Model used
3. Request type and payload (without API key)
4. Expected vs actual result
5. HTTP status code
6. Error message (if any)

---

## Emergency Stop Criteria

The Closed Beta will be PAUSED immediately if:
- Critical security vulnerability is discovered
- API key leak is detected
- Repeated 5xx errors make the system unusable
- GPU failure without workaround
- >5 unresolved P1/P2 defects

---

## Support Contact

Project maintainer (via established communication channel).

---

## Onboarding Checklist

| ID | Delivered | Verified |
|---|---|---|
| BETA-USER-01 | PENDING | — |
| BETA-USER-02 | PENDING | — |
| BETA-USER-03 | PENDING | — |
| BETA-USER-04 | PENDING | — |
| BETA-USER-05 | PENDING | — |

---
*Delivery pending assignment of actual internal users.*
