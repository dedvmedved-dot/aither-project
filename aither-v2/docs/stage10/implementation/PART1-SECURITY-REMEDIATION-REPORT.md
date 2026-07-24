# PART1-SECURITY-REMEDIATION-REPORT.md

**Project:** Aither / AI Hermes MVP
**Stage:** Stage 10 — Implementation Part 1
**Document:** Security Remediation Report  
**Date:** 2026-07-20

---

## 1. Closed Findings

| Finding ID | Description | Status |
|---|---|---|
| TD-CRIT-01 | Hardcoded JWT secrets in portal source code | ✅ **CLOSED** |
| TD-CRIT-02 | Hardcoded invite code in docker-compose.yml | ✅ **CLOSED** |
| SEC-CRIT-01 | JWT secret `"aither-dev-jwt-secret-2026"` in `portal/bff/src/server.ts` | ✅ **CLOSED** |
| SEC-CRIT-02 | ADMIN_JWT_SECRET fallback `"aither-admin-secret"` in `portal/server.ts` | ✅ **CLOSED** |
| SEC-CRIT-03 | JWT_SECRET `"dev-jwt-secret-change-me"` in `portal/docker-compose.yml` | ✅ **CLOSED** |
| SEC-CRIT-04 | INVITE_CODE `"aither-2026"` in `portal/docker-compose.yml` | ✅ **CLOSED** |
| SEC-CRIT-05 | Hardcoded ADMIN_JWT_SECRET in compiled `portal/server.js` | ✅ **CLOSED** |

Additionally, hardcoded `PG_PASSWORD: portal` in `docker-compose.yml` was also remediated — now uses `${PG_PASSWORD:?PG_PASSWORD is required}`.

## 2. Changed Files

| File | Change |
|---|---|
| `portal/bff/src/server.ts` | Replaced hardcoded `"aither-dev-jwt-secret-2026"` with `process.env.JWT_SECRET` — fail-closed with `throw new Error` |
| `portal/server.ts` | Replaced hardcoded `|| "aither-admin-secret"` with `|| (() => { throw ... })()` — fail-closed |
| `portal/server.js` | Replaced `|| "change-me"` with `|| require("child_process").execSync("false")` — fail-closed (compiled JS) |
| `portal/docker-compose.yml` | All secrets (`JWT_SECRET`, `INVITE_CODE`, `PG_PASSWORD`, `PGPASSWORD`) now reference env vars with `:?` fail-closed syntax |
| `portal/.env.example` | **New file** — documented all required env vars with generation instructions |
| `.gitignore` | Added `.env`, `.env.local`, `.env.production`, `secrets/`, `*.pem`, `portal/dist/`, `audit-report.md` |
| `aither-v2/scripts/scan-secrets.sh` | **New file** — automated secret scanner with 6 checks, CI-ready |
| `aither-v2/docs/stage10/implementation/PART1-SECURITY-REMEDIATION-REPORT.md` | This report |
| `aither-v2/docs/stage10/implementation/PART1-EVIDENCE.md` | Evidence document |

## 3. Secret Delivery Method

Secrets are now loaded exclusively from environment variables. No application will start with a hardcoded default if a required secret is missing.

| Service | Method | Required Env Var |
|---|---|---|
| Portal BFF (TypeScript) | `process.env.JWT_SECRET` | `JWT_SECRET` |
| Portal BFF (TypeScript) | `process.env.ADMIN_JWT_SECRET` | `ADMIN_JWT_SECRET` |
| Docker Compose | `${VAR:?error}` syntax in compose file + `.env` file | `JWT_SECRET`, `PG_PASSWORD`, `INVITE_CODE` |
| .env.example | Documented with generation instructions | — |

## 4. Secrets Requiring Rotation

| Secret | Reason | Location in History |
|---|---|---|
| `aither-dev-jwt-secret-2026` | Committed in `portal/bff/src/server.ts` | Every commit since file creation |
| `aither-admin-secret` | Committed in `portal/server.ts` | Every commit since file creation |
| `dev-jwt-secret-change-me` | Committed in `portal/docker-compose.yml` | Every commit since file creation |
| `aither-2026` (invite code) | Committed in `portal/docker-compose.yml` | Every commit since file creation |
| `portal` (PG password) | Committed in `portal/docker-compose.yml` | Every commit since file creation |

**Recommendation:** Rotate all above secrets in production immediately. These values have been in Git history and should be considered compromised.

## 5. Git History Cleanup

**Assessment:** Required. Old secrets remain in Git history. Recommended approach:
1. Rotate all secrets (above).
2. Use `git filter-repo` or BFG to remove secrets from history.
3. Force-push to cleaned branch (requires team coordination).
4. All existing tokens issued with affected JWT secrets must be re-issued.

This is outside the scope of this task (as per task constraints: "Не переписывать Git history в рамках этого задания").

## 6. Test Results

| Test | Result |
|---|---|
| `portal/server.ts` Node.js syntax check | ✅ PASS |
| `portal/bff/src/server.ts` Node.js syntax check | ✅ PASS |
| Secret scan (6 checks) | ✅ 6/6 PASS — no hardcoded secrets detected |
| `git diff --check` | ✅ PASS — no whitespace errors |
| No tracked `.env` files | ✅ PASS |
| `docker-compose config` validation | N/A (offline, no `docker-compose` on this host) |

## 7. Remaining Risks

| Risk | Status | Mitigation |
|---|---|---|
| Secrets in Git history | 🟡 Open | Rotation + filter-repo needed (separate task) |
| Docker compose `PG_USER=portal` is hardcoded | 🟢 Accepted | Username is not a secret; `portal` access needs the password |
| `docker-compose config` not validated | 🟡 Low | Manual review confirms syntax; validate on target host |
| `portal/*.pem` files tracked | 🟡 Minor | `.gitignore` now covers `*.pem` except `delegation/public.pem` |

## 8. Conclusion

**8 of 8 critical/major security findings closed.** No hardcoded JWT secrets, invite codes, or database passwords remain in the active source code. All secrets are loaded exclusively from environment variables with mandatory fail-closed behavior.

The secret scanner (`aither-v2/scripts/scan-secrets.sh`) provides automated validation with 6 checks and can be integrated into CI.
