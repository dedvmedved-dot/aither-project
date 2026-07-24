# SECURITY-REVIEW.md

**Project:** Aither / AI Hermes MVP  
**Stage:** Stage 10 — RC1 Gate  
**Document:** Security Review  
**Date:** 2026-07-20

---

## 1. Purpose

Identify security vulnerabilities, credential exposure, and authorization gaps in the aither-v2 codebase.

## 2. Scope

All source files in the repository root. Focus on committed secrets, token handling, authentication, and error handling patterns.

## 3. Methodology

Manual code review of authentication flows, credential storage patterns, and configuration files. Search for hardcoded secrets, fallback defaults, and exposed infrastructure details.

## 4. Results

### 4.1 Committed Secrets (Critical)

| ID | Finding | Location | Impact |
|---|---|---|---|
| SEC-CRIT-01 | **Hardcoded JWT secret `"aither-dev-jwt-secret-2026"`** | `portal/bff/src/server.ts:13` | Token forgery, session hijacking |
| SEC-CRIT-02 | **Hardcoded JWT fallback `"aither-admin-secret"`** | `portal/server.ts:1458` | Admin token forgery, full Gateway control |
| SEC-CRIT-03 | **`JWT_SECRET` set to `"dev-jwt-secret-change-me"` in docker-compose.yml** | `portal/docker-compose.yml:27` | Session forgery in production |
| SEC-CRIT-04 | **Invite code `"aither-2026"` committed** | `portal/docker-compose.yml:30` | Unauthorized user registration |
| SEC-CRIT-05 | **Gateway admin JWT generated with hardcoded default secret** | `portal/server.ts:1458` | `ADMIN_JWT_SECRET` falls back to literal `"aither-admin-secret"` — not a placeholder, but a functional default |

### 4.2 Authorization

| Finding | Location | Assessment |
|---|---|---|
| BFF scope-based auth working correctly | `app.py:233-241` | ✅ PASSED — admin bypass, model:* scope required |
| User token NOT forwarded upstream | `app.py:247` | ✅ PASSED — internal credentials used |
| API tokens hashed with HMAC-SHA256 | `app.py:141` | ✅ PASSED — raw token never stored |
| Session cookies httponly+samesite=strict | `app.py:417-419` | ✅ PASSED |
| ✅ Session cookies NOT marked `secure` (HTTP-only env) | `app.py:420` | ⚠️ Accepted (internal network) |

### 4.3 Key and Credential Management

| Finding | Location | Assessment |
|---|---|---|
| BFF auth secrets use Kubernetes Secret (committed as example only) | `bff-auth-secret.example.yaml` | ✅ PASSED — example template, REPLACE_ME placeholders |
| No committed `kubeconfig` files | — | ✅ PASSED |
| No committed `.env` files beyond example templates | — | ✅ PASSED |
| Portal `docker-compose.yml` contains live credentials | `portal/docker-compose.yml:23-33` | ❌ FAILED — PG_PASSWORD, JWT_SECRET, INVITE_CODE all committed |

### 4.4 Error Handling

| Finding | Location | Assessment |
|---|---|---|
| Auth errors return generic messages | `app.py:353-356` | ✅ PASSED — "Invalid credentials" |
| Rate limit exceeded returns 429 with message | `app.py:572` | ✅ PASSED |
| 422 for 32B chat, 400 for unknown model | `app.py:604,641,663` | ✅ PASSED |
| Internal errors caught and logged | `app.py:105-108` | ✅ PASSED |

### 4.5 Other Security Observations

| Finding | Location | Severity |
|---|---|---|
| Portal uses `http://10.129.13.78:30900` hardcoded API URL | `portal/server.ts:12` | ⚠️ Minor — prevents environment portability |
| Core API URL `http://10.129.13.78:30900/v1` hardcoded | `portal/bff/src/server.ts:12` | ⚠️ Minor — same as above |
| `CORE_API` exposed in docker-compose | `portal/docker-compose.yml:31` | ⚠️ Minor — internal IP exposed |

## 5. Security Score

| Category | Status |
|---|---|
| Committed Secrets | ❌ FAILED (5 findings, 4 Critical) |
| Auth Implementation | ✅ PASSED |
| Token Handling | ✅ PASSED |
| Error/Info Leakage | ✅ PASSED |
| Secret Management | ⚠️ PARTIAL (portal docker-compose) |

## 6. Recommendations

1. **Immediate (Critical):** Remove or replace all hardcoded JWT secrets in `portal/bff/src/server.ts`, `portal/server.ts`, and `portal/docker-compose.yml`. Use environment variables only.
2. **Immediate (Critical):** Remove `INVITE_CODE` from `portal/docker-compose.yml`.
3. **Short-term:** Move portal configuration to a `.env` file not tracked by git.
4. **Short-term:** Add `secure: true` to session cookies once HTTPS is available.
5. **Short-term:** Add a `secrets-scan` step to CI pipeline (e.g., truffleHog or gitleaks).

## 7. Conclusion

The BFF and Gateway components have acceptable security for MVP internal scope. However, the Portal (`portal/` directory) contains **5 committed secrets** that must be addressed before production deployment. These are carryover items from a legacy portal implementation that predates the aither-v2 MVP structure.
