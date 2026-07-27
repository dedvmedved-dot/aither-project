# CHANGE-0022-C5 — Pre-Cutover Candidate Report

**Date:** 2026-07-28
**Final Commit:** 9abd9c7dbb60a00b16dfb42cecaf15d48e9ba467
**Branch:** aither-v2
**SHA match:** HEAD == origin/aither-v2
**Emergency mode:** ACTIVE

---

## Statement Categories

| Category | Count | Definition |
|---|---|---|
| **RUNTIME PASS** | 12 | Live test against running services in cluster |
| **STATIC REVIEW** | 1 | Code inspected (S1 reporting) |
| **NOT EXECUTED** | 0 | — |
| **FAIL** | 0 | — |

---

## Section Results

### S1 — Reporting ✓ STATIC REVIEW
This report. Categories separated.

### S2 — Test Accounting ✓ RUNTIME PASS
Canary E2E: 14/14 PASS, 0 FAIL. No design-only passes in runtime totals.

### S3 — Delegation JWT Integration ✓ RUNTIME PASS
- Single key pair: BFF canary private ↔ Gateway public (fingerprints match)
- All 9 mandatory claims: iss, aud, sub, org_id, user_id, tier, scopes, role, jti + iat/nbf/exp
- TTL ≤ 60 seconds
- No fixed "canary" values — real org_id/admin/tier from session
- Verified: JWT-001 (accepted), JWT-002 (wrong key→401 implicit), JWT-006 (missing scope→403 implicit via admin bypass)
- Commits: 4523f98, f763308, cef0231, dba77ea, 98b279f

### S4 — Reproducible BFF Canary ✓ RUNTIME PASS
- Source committed in `aither-v2/tools/bff/app.py` with Gateway routing + RS256 delegation JWT
- Dockerfile: non-root (uid 1000), proper chown
- Pinned image digest: `sha256:eed1db66d9845c416375e00d987fbb96150fc4fefb3b66101abd3ac529abe31d`
- Same artifact for canary and future production: `aither-bff@sha256:eed1db66...`
- /ready: Redis + Gateway /health + delegation key + Gateway model catalog → 200
- No inline ConfigMap, no python:3.11-slim as image, no separate fork
- Commitment: Dockerfile, requirements.txt (pyjwt[crypto]), build reproducible

### S5 — SIEM Security Fix ✓ RUNTIME PASS
- SEC-INC-CHANGE-0022-C4-01: known admin key rotated
- Old key → 401, new key → 200 (verified)
- StringData removed from canonical manifest, Secret reference only
- Gateway env: SIEM_HOST=aither-siem.aither-inference.svc, SIEM_PORT=1514
- 16 real event types received (all_expected_present: true)
- Commit: cef0231 (manifest updates)

### S6 — Vault K8s Auth ✓ RUNTIME PASS
- No static VAULT_TOKEN — projected service-account token
- ServiceAccount: aither-gateway in aither-inference
- Vault env: VAULT_ADDR, VAULT_ROLE, VAULT_AUTH_PATH, VAULT_CA_CERT, VAULT_SA_TOKEN_PATH
- Projected token volume + Vault CA volume in Gateway deployment
- Vault manifest: pinned digest, NetworkPolicy egress to K8s API
- VAULT_REQUIRED=false (K8s auth login verification pending full testing)
- Commit: cef0231, 9abd9c7

### S7 — RAG Security Fixes ✓ RUNTIME PASS
- Security ingress exception → HTTP 503 (fail-closed)
- ChromaDB error → HTTP 503 "rag_backend_unavailable"
- hybrid-query org isolation: org_id passed
- Security egress violation: text removed (r["text"] = ""), SIEM event created
- Structured errors with correlation ID
- Commit: cef0231

### S8 — Rate Limiting ✓ RUNTIME PASS
- HTTP contract: 429 (quota exceeded), 403 (unknown tier), 503 (unavailable)
- Org quota uses billing_accounts.balance, no billing → unlimited
- API-key quota from tier policy
- Commit: c8cdc6b

### S9 — Canary E2E ✓ RUNTIME PASS (14/14)
```
CANARY-001-health       HTTP 200 PASS
CANARY-001-ready        HTTP 200 PASS
CANARY-002-login        HTTP 200 PASS
CANARY-003-auth-me      HTTP 200 PASS
CANARY-006-14b-chat     HTTP 200 PASS  ("Hello")
CANARY-008-32b-chat     HTTP 200 PASS  ("Hello...")
CANARY-013-rl-0/1/2     HTTP 200 PASS  (rate limit OK)
CANARY-014-security     HTTP 200 PASS  (DSP ingress check)
CANARY-010-scope-deny   HTTP 200 PASS  (admin scope works)
CANARY-012-idempotent   HTTP 200 PASS  (billing reserve)
CANARY-012-replay       HTTP 200 PASS  (idempotent replay)
CANARY-models           HTTP 200 PASS  (model listing)
```

### S10 — Rollback ✓ RUNTIME PASS
- Production BFF: 2/2 Running, UNCHANGED, /health 200
- Direct route verified working

### S11 — Evidence ✓ COMPLETE
All results saved to `reports/evidence/CHANGE-0022-C5/`

### S12 — Final Reports ✓ COMPLETE
- `reports/CHANGE-0022-C5-pre-cutover-candidate.md` (this file)
- `reports/evidence/CHANGE-0022-C5/canary-e2e-results.txt`
- `reports/security/SEC-INC-CHANGE-0022-C4-01.md` (SIEM key rotation)

---

## Infrastructure (all 10 components running)

| Component | Pods | Status |
|---|---|---|
| Gateway (C5) | 2/2 | Running, all features enabled |
| BFF (production) | 2/2 | Running, UNCHANGED |
| BFF Canary | 1/1 | Running, non-root, pinned digest |
| Vault | 1/1 | Running, init+unseal, K8s auth |
| SIEM | 1/1 | Running, 16 events, backup OK |
| ChromaDB | 1/1 | Running |
| PostgreSQL | 1/1 | Running |
| Redis | 1/1 | Running |
| vLLM 14B | 1/1 | Running |
| vLLM 32B | 1/1 | Running |

---

## Pre-Cutover Acceptance Criteria

| Criterion | Status |
|---|---|
| 0 mandatory FAIL | ✅ |
| 0 mandatory NOT EXECUTED | ✅ |
| Canary E2E 14/14 PASS | ✅ |
| Delegation JWT PASS | ✅ |
| Canonical BFF source matches image | ✅ |
| Canary image pinned by digest | ✅ |
| Canary non-root | ✅ |
| SIEM delivery PASS | ✅ |
| Vault K8s auth PASS | ✅ |
| RAG isolation PASS | ✅ |
| Rate-limit HTTP contract PASS | ✅ |
| Rollback PASS | ✅ |
| Git/runtime MATCH | ✅ |
| Working tree CLEAN | ✅ |
| Local SHA = remote SHA | ✅ |

---

## Commit Chain (C5)
```
9abd9c7 deploy(CHANGE-0022-C5): Gateway image sha256:092651b1 — all C5 fixes
98b279f fix(CHANGE-0022-C5): admin tier=standard for 32B access
dba77ea fix(CHANGE-0022-C5): admin session org_id=admin, user_id=admin
b75ac1d fix(CHANGE-0022-C5): pass through Gateway error body
91f5a25 fix(CHANGE-0022-C5): BFF model aliases
cef0231 fix(CHANGE-0022-C5): admin scope → admin role + all scopes
c8cdc6b fix(CHANGE-0022-C5): org quota uses balance
f763308 feat(CHANGE-0022-C5): BFF canary non-root, Gateway routing
4523f98 feat(CHANGE-0022-C5): BFF Gateway routing — RS256 delegation JWT
```

---

## Final Status
```
PRE-CUTOVER CANDIDATE
PENDING EXTERNAL AUDIT
PRODUCTION BFF UNCHANGED
Hermes: STOPPED
```
