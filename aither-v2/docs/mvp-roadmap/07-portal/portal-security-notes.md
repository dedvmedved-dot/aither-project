# Aither Portal — Security Notes

## MVP Security Model

1. **Admin session auth** — login via username/password, session cookie stored by BFF.
2. **No raw token persistence** — raw API token shown once after creation; never stored in browser localStorage/sessionStorage.
3. **Same-origin proxy** — portal nginx proxies `/api/v1/*` to BFF; no CORS configuration needed.
4. **No direct backend access** — portal NEVER connects to vLLM, nginx-gateway, Redis, or Kubernetes API.
5. **Session cookie isolation** — cookies managed by BFF via `Set-Cookie` header through nginx proxy.

## What is NOT implemented (MVP scope)

| Feature | Status |
|---|---|
| OAuth | NOT IMPLEMENTED — OUT OF SCOPE |
| HTTPS/TLS | NOT CONFIGURED — MVP cluster-internal only |
| CSRF protection | NOT IMPLEMENTED — same-origin mitigates for MVP |
| Rate limiting per-UI | NOT CONFIGURED — BFF rate limiting covers API |
| Session timeout UI | NOT IMPLEMENTED — BFF session TTL active |
| Token encryption at rest | NOT CONFIGURED — Redis HMAC-hash only |
| Audit logging | NOT IMPLEMENTED |

## Security Guidelines

- Do NOT modify portal to store raw tokens in browser storage.
- Do NOT add direct vLLM/Gateway URLs to portal code.
- Do NOT commit raw API tokens, passwords, or secrets.
- Do NOT enable CORS for external origins without review.
