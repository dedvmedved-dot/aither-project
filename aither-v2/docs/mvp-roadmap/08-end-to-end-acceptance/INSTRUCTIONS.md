# Stage 08 — MVP End-to-End Runtime Acceptance

## Instructions

### Purpose

Verify the full MVP user/agent path:
```
User / Agent → Portal → BFF → Gateway / vLLM → model response
```

### Scope

- Portal accessibility and health
- Login/token lifecycle (create, list, revoke, blocked)
- 14B chat through BFF (auth → scope → upstream → response)
- 32B completion through BFF/Gateway
- 32B chat adapter through BFF
- Rate limiting after full auth stack
- No raw tokens/secrets in evidence/logs

### Gate

Stage 08 status before ChatGPT audit:
- If all model endpoints return HTTP 200 with real responses: COMPLETED BY HERMES
- If upstream auth blocks model responses (current state): PARTIAL / WAITING FOR CHATGPT AUDIT
- Never PASSED before ChatGPT audit

### Forbidden

- Do not change BFF/Portal/manifest code
- Do not change vLLM/GPU/TP/Gateway/Redis/OAuth/Monitoring
- Do not start Stage 09
- Do not write PASSED before ChatGPT audit
- Do not commit raw tokens/secrets
