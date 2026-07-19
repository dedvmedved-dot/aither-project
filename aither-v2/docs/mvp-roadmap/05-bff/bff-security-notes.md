# BFF Security Notes

## 1. Auth status

- BFF passes Authorization header to upstream services (no modification).
- No built-in auth in BFF itself (relies on gateway/vLLM API key).
- Without Authorization header, upstream returns {"error":"Unauthorized"} or {"error":"auth required"}.
- Stage for adding BFF-level auth: POSTPONED (not required for MVP).

## 2. Secret handling

- VLLM_API_KEY is not stored in BFF config or code.
- Client must provide Authorization header.
- No secrets committed to repository (confirmed).

## 3. Request validation

- FastAPI validates model field against known models (14b, 32b).
- Unknown models return HTTP 400 before upstream call.
- 32B chat requests return HTTP 422 before upstream call (blocked at BFF level).
- Request body validation via Pydantic (ChatRequest, CompletionRequest schemas).
- No request body validation at BFF level for streaming responses (delegated to vLLM/gateway).

## 4. Rate limiting

- POSTPONED to Stage 06 (Redis/BFF rate limiting).

## 5. Direct vLLM bypass risk

- Direct vLLM 32B chat bypass: **NOT PRESENT** — BFF blocks 32B chat before upstream.
- Direct vLLM 32B completion bypass: **NOT PRESENT** — BFF routes only through nginx-gateway-32b.
- BFF policy ensures user-facing traffic goes through gateway for 32B.
- Stage 07 Portal must enforce Portal → BFF only.

## 6. Container securityContext

- runAsNonRoot: true (uid 1000)
- allowPrivilegeEscalation: false
- capabilities: drop: ["ALL"]
- Read-only root filesystem via ConfigMap volume mount
- Resource limits: 500m CPU, 512Mi memory

## 7. NetworkPolicy

- Not implemented (Flannel limitation).
- Deferred to Stage 08.

## 8. Known gaps

- BFF has no built-in auth.
- No rate limiting (Stage 06).
- No NetworkPolicy (Stage 08).
- BFF is MVP-level, not production-hardened.
- Valid token test for 32B completion not collected (VPN instability).
