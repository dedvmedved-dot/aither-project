# 03_AUTH_CONTRACT — External API Authentication

## Current contract
- External `/v1/models` → Gateway (returns old catalog, cosmetic)
- External `/v1/chat/completions` → Portal Backend → JWT validation
- Bearer token: Identity JWT (not `aither_` API key)

## Emergency bridge
- Dedicated agent account: `aither-agent-ext`
- Role: user, org: default (active), tier: pro
- Scopes: `model:32b:chat`, `model:qwen3:chat`, `rag:query`
- Auth: POST `/api/v1/auth/login` → JWT → Bearer

## Defects registered
- REPO-DEFECT-EXTERNAL-API-AUTH-CONTRACT-001: WUI API keys are aither_ format, NOT compatible with JWT-auth /v1
- REPO-DEFECT-APIKEY-CONTRACT-002: API key scope selection in WUI not persisted/enforced
