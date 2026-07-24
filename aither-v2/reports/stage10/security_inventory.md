# Stage 10 — Security Inventory

## Task 4 — Security Measures in Git (Committed Only)

### Methodology
Only the committed state at HEAD (`519970f`) is examined. Local working tree changes are explicitly excluded.

---

## 1. TLS / HTTPS

| Status | Details |
|--------|---------|
| ❌ **NOT PRESENT** | No SSL certificate, no TLS listener, no `listen 443`, no `ssl_certificate` directive in any committed nginx config |

- Portal Frontend nginx (`services/portal-frontend/nginx.conf`): listens on `listen 80` only
- Gateway nginx (`03-vllm-14b-deploy/manifests/nginx-gateway-32b.yaml`): listens on port 8000 (plain HTTP)
- No Ingress or cert-manager manifests in Git

---

## 2. HSTS (HTTP Strict-Transport-Security)

| Status | Details |
|--------|---------|
| ❌ **NOT PRESENT** | Zero occurrences of `Strict-Transport-Security` or `max-age` in any committed file |

- HSTS requires TLS first, which is absent

---

## 3. CSP (Content-Security-Policy)

| Status | Details |
|--------|---------|
| ❌ **NOT PRESENT in Git** | Zero CSP headers in any committed nginx config |

- ⚠️ CSP exists in LOCAL working tree (`nginx.conf` — uncommitted change) but NOT in committed Git

---

## 4. X-Frame-Options

| Status | Details |
|--------|---------|
| ❌ **NOT PRESENT in Git** | Zero occurrences in committed nginx configs |

- ⚠️ `X-Frame-Options: DENY` exists in LOCAL working tree only

---

## 5. Referrer-Policy

| Status | Details |
|--------|---------|
| ❌ **NOT PRESENT in Git** | Zero occurrences in committed files |

- ⚠️ `Referrer-Policy: strict-origin-when-cross-origin` exists in LOCAL working tree only

---

## 6. Permissions-Policy

| Status | Details |
|--------|---------|
| ❌ **NOT PRESENT in Git** | Zero occurrences in committed files |

- ⚠️ `Permissions-Policy` exists in LOCAL working tree only

---

## 7. CORS (Cross-Origin Resource Sharing)

| **Where** | **Status** | **Details** |
|-----------|-----------|-------------|
| Portal Frontend nginx | ❌ NOT PRESENT | No CORS headers in committed `nginx.conf` |
| AI Platform (FastAPI) | ✅ PRESENT | `CORSMiddleware` configured in `app/main.py` — `AI_PLATFORM_CORS_ORIGIN` env var, default `http://localhost:3000` |
| Portal Backend (FastAPI) | ✅ PRESENT | `CORSMiddleware` configured in `portal-backend/app/main.py` |
| Gateway nginx | ❌ NOT PRESENT | No CORS headers |

- CORS is handled at the application layer (FastAPI middleware), not at the nginx level
- Both AI Platform and Portal Backend allow configurable origins via environment variables

---

## 8. Rate Limiting

| **Where** | **Status** | **Details** |
|-----------|-----------|-------------|
| Gateway nginx (active) | ✅ **PRESENT** | `limit_req_zone $binary_remote_addr zone=completions:10m rate=30r/m;` + `burst=5 nodelay` on `/v1/completions` |
| Python gateway (manifests/gateway.yaml) | ✅ PRESENT | `RATE_LIMIT=60` env var — but **not deployed** |
| Portal Frontend nginx | ❌ NOT PRESENT | No rate limiting configured |
| AI Platform | ❌ NOT PRESENT | No rate limiting in application code |

---

## Additional Security Observations

| Item | In Git? | Notes |
|------|---------|-------|
| API Key Hashing | ✅ | SHA-256 hashing confirmed in `main.py` |
| `runAsNonRoot` | ✅ | Set on AI Platform, Identity, nginx-gateway deployments |
| `allowPrivilegeEscalation: false` | ✅ | On nginx-gateway container |
| Capabilities drop | ✅ | `capabilities: { drop: ["ALL"] }` on nginx-gateway |
| `automountServiceAccountToken: false` | ✅ | On AI Platform and Portal Backend |
| ReadOnlyRootFilesystem | ❌ | Not set on any deployment |
| Network Policies | ⚠️ | One exists for vLLM (`vllm-network-policy.yaml`) but not enforced for other services |
| Health endpoints (auth-free) | ⚠️ | `/health` and `/ready` proxied without auth in portal-frontend nginx |
| X-XSS-Protection | ❌ | Not present in Git |

---

## Summary

| Security Measure | In Git | In Local (uncommitted) |
|-----------------|--------|----------------------|
| TLS | ❌ | ❌ |
| HSTS | ❌ | ❌ |
| CSP | ❌ | ✅ (nginx.conf) |
| X-Frame-Options | ❌ | ✅ (nginx.conf) |
| Referrer-Policy | ❌ | ✅ (nginx.conf) |
| Permissions-Policy | ❌ | ✅ (nginx.conf) |
| CORS (app-level) | ✅ | ✅ |
| Rate Limiting (gateway) | ✅ | ✅ |
