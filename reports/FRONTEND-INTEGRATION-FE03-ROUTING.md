# FRONTEND-INTEGRATION-FE03-ROUTING
# ================================
# R7-R5-EMG-FE-03 | 2026-07-28

## Production Chat Route (ROLLED BACK)

```
Browser → Portal Nginx (fb1.spb.ru:10443) → Portal Backend → direct upstream

14B: Portal Backend → http://vllm-14b-instruct.aither-inference.svc:8000
32B: Portal Backend → http://nginx-gateway-32b.aither-inference.svc:8000
```

- Gateway is NOT in the chat path
- Server-side credentials from K8s Secret `aither-portal-upstream`
- Credentials never returned to browser
- No delegation JWT for chat

## Gateway Facade Routes (internal only)

Gateway is used for admin/billing/RAG facades only, NOT model routing:
- /api/v1/admin/* → Portal Backend → Gateway
- /api/v1/billing/* → Portal Backend → Gateway
- /api/v1/usage/* → Portal Backend → Gateway
- /api/v1/rag/* → Portal Backend → Gateway
- /api/v1/monitoring/* → Portal Backend → Gateway

## Nginx Configuration

- /api/v1/auth/me → direct to identity (bypasses portal-backend)
- /api/ → portal-backend (catch-all)
- Gateway Service: ClusterIP (not externally exposed)

## Session Security

- Every request validates: session exists, not revoked, not expired, user not disabled
- Logout revokes session by full token hash
- Disabled user → all sessions revoked
