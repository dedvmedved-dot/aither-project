# E2E Security Notes

## Token Security

1. Raw API tokens are shown only once on creation (in create response).
2. Token list returns metadata only (token_id, name, scopes, timestamps, status).
3. No raw tokens stored in localStorage or sessionStorage (Portal UI).
4. No raw tokens logged to console (Portal UI).
5. No raw tokens in Redis — only HMAC-SHA256 hash.
6. No raw tokens committed to GitHub — all redacted in evidence.

## Authentication

1. Admin session: cookie-based (httpx), Redis-backed (24h TTL).
2. API token: Bearer auth (athr_ prefix), HMAC-SHA256 hash stored.
3. User tokens NEVER forwarded to upstream — separate internal upstream tokens used.
4. Revoked tokens immediately blocked (401).

## Network Security

1. Portal exposed only through ClusterIP service (no public ingress).
2. Portal → BFF only — no direct vLLM/Gateway/Redis access.
3. BFF → vLLM 14B direct (internal cluster DNS).
4. BFF → Gateway 32B (internal cluster DNS) → vLLM 32B.
5. All upstream calls use internal auth tokens.

## Known Limitations

1. Upstream auth tokens are test-only (AUTH-UPSTREAM-VALID-01: PARTIAL).
2. No TLS between services (internal cluster, MVP scope).
3. No OAuth (deferred).
4. No audit logging of API token usage (future).
5. Redis key durability not production-grade (AUTH-TOKEN-PERSIST-01: PARTIAL).
