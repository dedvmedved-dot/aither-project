# BFF Security Notes

## 1. Auth status

- BFF passes Authorization header to upstream services.
- No built-in auth in BFF itself (relies on gateway/VLLM_API_KEY).
- Stage for adding BFF-level auth: POSTPONED (not required for MVP).

## 2. Secret handling

- VLLM_API_KEY is not stored in BFF config.
- Client must provide Authorization header.
- No secrets committed to repository.

## 3. Request validation

- Nginx validates paths; unknown paths return 404.
- No request body validation at BFF level (delegated to vLLM/gateway).

## 4. Rate limiting

- POSTPONED to Stage 06 (Redis/BFF rate limiting).

## 5. Direct vLLM bypass risk

- Direct vLLM 32B chat bypass is accepted for MVP internal scope.
- BFF policy ensures user-facing traffic goes through gateway.
- Stage 07 Portal must enforce Portal → BFF only.

## 6. NetworkPolicy

- Not implemented (Flannel limitation).
- Deferred to Stage 08.

## 7. Known gaps

- BFF has no built-in auth.
- No rate limiting (Stage 06).
- No NetworkPolicy (Stage 08).
- BFF is MVP-level, not production-hardened.
