# IMPLEMENTATION-AUDIT.md

**Project:** Aither / AI Hermes MVP  
**Stage:** Stage 10 — RC1 Gate  
**Document:** Implementation Audit  
**Date:** 2026-07-20

---

## 1. Purpose

Verify that the implemented system corresponds to the requirements declared in Stage 10 documents and that all core components are present and functional.

## 2. Scope

- BFF (Backend-for-Frontend): `tools/bff/app.py`, `manifests/mvp-roadmap/05-bff/bff-mvp.yaml`
- Portal: `tools/portal/`, `manifests/mvp-roadmap/07-portal/portal-mvp.yaml`
- Gateway: `manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml`
- Redis/Rate Limiting: `manifests/mvp-roadmap/06-rate-limiting/redis-rate-limit.yaml`
- Auth: `manifests/mvp-roadmap/07-auth-api/bff-auth-secret.example.yaml`
- Kubernetes manifests under `aither-v2/manifests/`

## 3. Methodology

Code review of source files, manifest inspection, cross-reference with Stage 10 document requirements (00–10).

## 4. Results

### 4.1 BFF Implementation

| Requirement | Status | Reference |
|---|---|---|
| FastAPI application with /health endpoint | ✅ Implemented | `app.py:367` |
| Auth middleware (session + Bearer token) | ✅ Implemented | `app.py:336` |
| Rate limiting (Redis-backed, fixed window) | ✅ Implemented | `app.py:87` |
| 14B chat routing | ✅ Implemented | `app.py:625` |
| 32B completion routing | ✅ Implemented | `app.py:653` |
| 32B chat adapter over completion | ✅ Implemented | `app.py:601` |
| Unknown model returns 400 | ✅ Implemented | `app.py:641` |
| User token NOT forwarded upstream | ✅ Implemented | `app.py:247` |
| HTTP 429 on rate limit exceeded | ✅ Implemented | `app.py:103` |
| Token creation with raw token shown once | ✅ Implemented | `app.py:449` |
| Token revocation | ✅ Implemented | `app.py:529` |
| Session-based admin login | ✅ Implemented | `app.py:382` |
| bff-mvp.yaml ConfigMap matches app.py | ✅ Verified | `bff-mvp.yaml:7-253` |

### 4.2 Portal Implementation

| Requirement | Status | Reference |
|---|---|---|
| Login page with session auth | ✅ Implemented | `index.html:27` |
| Token management UI (create/list/revoke) | ✅ Implemented | `index.html:41` |
| Chat UI with model selector | ✅ Implemented | `index.html:85` |
| API Guide page | ✅ Implemented | `index.html:117` |
| Status page | ✅ Implemented | `index.html:185` |
| Raw token shown once then dismissed | ✅ Implemented | `index.html:47` |
| Nginx reverse proxy to BFF | ✅ Implemented | `portal-mvp.yaml (nginx.conf)` |
| Same-site cookies (strict) | ✅ Implemented | `app.py:419` |

### 4.3 Gateway Implementation

| Requirement | Status | Reference |
|---|---|---|
| nginx-gateway-32b blocks /v1/chat/completions (422) | ✅ Implemented | `nginx-gateway-32b-hardened.yaml:17` |
| Completion proxy to vLLM 32B | ✅ Implemented | `nginx-gateway-32b-hardened.yaml:20` |
| Auth propagated from BFF | ✅ Implemented | `nginx-gateway-32b-hardened.yaml:24` |
| Hardware ClusterIP workaround | ⚠️ Runtime-only (not committed) | `nginx-gateway-32b-hardened.yaml:21` uses hostname |
| Image version tag (no digest) | ✅ Version tag accepted | `nginx-gateway-32b-hardened.yaml:54` (nginx:alpine) |

### 4.4 Redis / Rate Limiting

| Requirement | Status | Reference |
|---|---|---|
| Redis 7-alpine deployed | ✅ Implemented | `redis-rate-limit.yaml:23` |
| Rate limit window (60s) | ✅ Implemented | `app.py:50` |
| Rate limit max requests (10) | ✅ Implemented | `app.py:51` |
| Key uses SHA-256(token) or client IP | ✅ Implemented | `app.py:78` |
| No raw tokens in Redis | ✅ Implemented | `app.py:78-84` |
| Fail-open when Redis unavailable | ✅ Implemented | `app.py:91-92` |

### 4.5 Auth Implementation

| Requirement | Status | Reference |
|---|---|---|
| Admin login with Kubernetes Secret credentials | ✅ Implemented | `bff-auth-secret.example.yaml` |
| API token create/list/revoke | ✅ Implemented | `app.py:449-562` |
| Bearer token prefix `athr_` | ✅ Implemented | `app.py:62` |
| HMAC-SHA256 token hashing | ✅ Implemented | `app.py:141` |
| Session cookie with 24h TTL | ✅ Implemented | `app.py:410` |
| User token NOT forwarded upstream | ✅ Implemented | `app.py:247` |
| Scope-based model access control | ✅ Implemented | `app.py:233` |

## 5. Findings

| ID | Severity | Description |
|---|---|---|
| IMPL-CM-01 | Minor | Portal ConfigMap inline data makes source-of-truth verification difficult. Both `tools/portal/` source and `portal-mvp.yaml` must be kept in sync manually. |
| IMPL-CI-01 | Minor | GitHub CI workflow (`ci.yml`) validates gateway/ files but does NOT validate BFF (`tools/bff/app.py`) or Portal files. |
| IMPL-DEPLOY-01 | Major | `deploy.sh` references deployments (`vllm-qwen`, `vllm-qwen32b`) and namespaces that do not match the `aither-v2/` manifests which use `aither-inference` namespace. The deploy script was designed for a different deployment track. |
| IMPL-HOST-01 | Major | `nginx-gateway-32b-hardened.yaml` uses DNS hostname for upstream. On node n7 (MissingClusterDNS) this fails. Runtime fix (ClusterIP) not committed. |

## 6. Recommendations

1. Align deploy script namespaces with aither-v2 manifest structure.
2. Add CI checks for BFF and Portal Python/JS code.
3. Commit the ClusterIP workaround or fix ClusterDNS on n7.
4. Add linting/staging pipeline for `tools/bff/app.py` before ConfigMap rollouts.

## 7. Conclusion

The implemented system passes core functional requirements. Two Major findings exist regarding deploy alignment and DNS-dependent gateway configuration. Overall, the implementation is consistent with Stage 10 documentation scope.
