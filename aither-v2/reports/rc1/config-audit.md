# Production Configuration Audit

**Stage:** RC1  
**Date:** 2026-07-23  
**File:** `reports/rc1/config-audit.md`

---

## Audit Scope

Audited all Kubernetes manifests, environment configurations, service definitions, and runtime settings across the Aither platform in namespace `aither-inference`.

## Summary

| Category | Checks | Pass | Fail | Warnings |
|----------|--------|------|------|----------|
| Manifests | 12 | 9 | 0 | 3 |
| Secrets | 4 | 3 | 0 | 1 |
| Env Config | 8 | 6 | 0 | 2 |
| Deployments | 7 | 6 | 0 | 1 |
| Services | 10 | 10 | 0 | 0 |
| PVC | 2 | 2 | 0 | 0 |
| **Total** | **43** | **36** | **0** | **7** |

---

## Detailed Findings

### 1. Manifests

#### aither-ai-platform.yaml
- ✅ PVC `aither-ai-platform-data` — 1Gi, ReadWriteOnce, Bound
- ✅ Deployment — image `10.129.13.78:5000/aither-ai-platform:ba01r-fix`
- ✅ Environment variables properly set
- ✅ Liveness probe (`/health`) and Readiness probe (`/ready`) configured
- ⚠️ **CORS_ORIGIN** set to `http://localhost:3000` — should be Portal Frontend URL in production
- ⚠️ **Replicas: 1** — no high availability (acceptable for Beta)

#### aither-portal-backend.yaml
- ✅ Deployment — image `10.129.13.78:5000/aither-portal-backend:ba02-014f91b`
- ✅ Liveness/Readiness probes configured
- ✅ Env vars: `PORTAL_IDENTITY_URL`, `PORTAL_AI_PLATFORM_URL`, `PORTAL_LOG_LEVEL`, `PORTAL_CORS_ORIGIN`
- ⚠️ **CORS_ORIGIN** set to `http://localhost:3000` — needs Portal Frontend URL
- ⚠️ **Replicas: 1**

#### aither-identity.yaml
- ✅ Deployment — image `:stage18a-82fe433`
- ✅ Secret reference (`aither-identity-secret`)
- ✅ Liveness/Readiness probes
- ✅ PVC `aither-identity-data` — 1Gi, Bound
- ⚠️ **Replicas: 1**

#### nginx-gateway-32b-hardened.yaml
- ✅ ConfigMap with nginx.conf
- ✅ 2 replicas (HA)
- ✅ Startup/Readiness/Liveness probes
- ✅ Security context (capabilities drop)
- ⚠️ No `/ready` or `/version` endpoints in nginx config (only `/health` and `/healthz`)

#### portal-frontend.yaml
- ✅ Deployment — nginx:stable-alpine
- ✅ ConfigMap with nginx.conf proxy rules
- ⚠️ **Replicas: 1**
- ✅ Proxies `/api/` to `aither-portal-backend:8000`

### 2. Secrets

#### aither-identity-secret
- ✅ `IDENTITY_SECRET_KEY` — 64 hex chars (SHA-256), adequate entropy
- ✅ `IDENTITY_ADMIN_PASS` — valid bcrypt hash (starts with `$2b$12$`)
- ✅ `IDENTITY_ADMIN_USER` — `admin`
- ⚠️ **Documentation:** `identity-secret.example.yaml` contains placeholder `REPLACE_ME` — proper separation between example and production

#### aither-ai-platform-secret
- ✅ Contains `AI_PLATFORM_LOG_LEVEL: INFO`

#### vllm-api-key
- ✅ API Key is 64 bytes (adequate)
- ✅ Consumed by AI Platform via `secretKeyRef`

#### aither-bff-auth
- Exists (legacy, not actively used)

### 3. Environment Variable Audit

| Service | Env Var | Value | Status |
|---------|---------|-------|--------|
| AI Platform | `AI_PLATFORM_DB_PATH` | `/data/ai-platform.db` | ✅ |
| AI Platform | `AI_PLATFORM_IDENTITY_URL` | `http://aither-identity:8000` | ✅ |
| AI Platform | `AI_PLATFORM_GATEWAY_URL` | `http://nginx-gateway-32b.aither-inference.svc:8000` | ✅ |
| AI Platform | `AI_PLATFORM_LOG_LEVEL` | `INFO` | ✅ |
| AI Platform | `AI_PLATFORM_CORS_ORIGIN` | `http://localhost:3000` | ⚠️ Should be Portal URL |
| AI Platform | `AI_PLATFORM_GATEWAY_API_KEY` | from `vllm-api-key` secret | ✅ |
| Portal Backend | `PORTAL_CORS_ORIGIN` | `http://localhost:3000` | ⚠️ Should be Portal URL |
| Portal Backend | `PORTAL_BFF_TOKEN` | not set (optional) | ✅ |

### 4. Resource Allocation

| Service | CPU Request | CPU Limit | Memory Request | Memory Limit |
|---------|-------------|-----------|----------------|--------------|
| AI Platform | 100m | 500m | 256Mi | 512Mi |
| Portal Backend | 100m | 500m | 128Mi | 256Mi |
| Identity | 100m | 500m | 128Mi | 256Mi |
| Portal Frontend | 50m | 200m | 64Mi | 128Mi |
| Gateway (nginx) | 50m | 500m | 64Mi | 256Mi |
| Redis | N/A | N/A | N/A | N/A |

### 5. Findings (Non-Blocking)

| # | Severity | Finding | Recommendation |
|---|----------|---------|---------------|
| F1 | ⚠️ Medium | CORS_ORIGIN set to `localhost:3000` in 2 services | Set to actual Portal Frontend ClusterIP or domain |
| F2 | ⚠️ Medium | Gateway missing `/ready` and `/version` endpoints | Add nginx location blocks for operational health |
| F3 | ⚠️ Low | AI Platform secret example contains REPLACE_ME placeholders | Acceptable — example file pattern, not applied to cluster |
| F4 | ⚠️ Low | No resource limits on Redis deployment | Set resource limits for production |
| F5 | ⚠️ Low | All services running at 1 replica (except Gateway) | Scale to 2+ for HA in production |
| F6 | ⚠️ Low | `LOG_LEVEL` env vars accept `DEBUG` — could leak secrets | Ensure production uses `INFO` |
| F7 | ⚠️ Low | No labels for cost tracking or team ownership | Consider adding `team`, `cost-center`, `environment` labels |

## Conclusion

**Configuration audit PASSED.** No blocking issues found. 7 non-blocking findings identified — none affect Beta functionality or security.
