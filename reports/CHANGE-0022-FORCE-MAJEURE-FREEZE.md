# CHANGE-0022 — FORCE MAJEURE FREEZE REPORT

**Directive:** R7-R5-EMG-FM-01  
**Date:** 2026-07-28T02:30:00Z  
**Emergency Mode:** ACTIVE  

---

## SHA Registry

| Ref | SHA |
|-----|-----|
| Previous (C5 final) | `28d9c13310a00022bb042b8db2f98d5ffde23701` |
| Freeze | `TO_BE_COMMITTED` |
| Remote (origin/aither-v2) | `28d9c13310a00022bb042b8db2f98d5ffde23701` |

---

## Production BFF

| Metric | Value |
|--------|-------|
| Replicas | 2/2 Ready |
| Routing | BFF → vLLM 14B directly; BFF → nginx proxy → vLLM 32B |
| Gateway cutover | NOT PERFORMED |
| Modified during freeze | NO |

---

## Gateway

| Metric | Value |
|--------|-------|
| Replicas | 2/2 Ready |
| Image | `aither-gateway:change-0022-c4-r6b` |
| Status | DEPLOYED, NOT PRIMARY |

---

## BFF Canary

| Metric | Value |
|--------|-------|
| Replicas | 0 (scaled to 0) |
| Status | FROZEN / ISOLATED |
| External access | NONE |

---

## Security Containment

| Incident | Action | Result |
|----------|--------|--------|
| SEC-INC-CHANGE-0022-C4-01 (SIEM admin key) | Key rotated 2026-07-28T01:30:00Z; old value `siem-admin-key-change-me-in-production` invalidated; `stringData` Secret removed from canonical manifest; replaced with documented Secret reference | COMPLETE |
| SEC-INC-CHANGE-0022-C5-01 (Canary credentials) | ADMIN_PASSWORD_HASH, SESSION_SECRET, AUTH_TOKEN_HASH_SECRET rotated 2026-07-28T02:30:00Z; literal values removed from `bff-gateway-canary.yaml`; replaced with `secretKeyRef` to `aither-bff-canary-secrets`; example manifest created | COMPLETE |

### Secret Scan Results

- `8c6976e5...` (old ADMIN_PASSWORD_HASH): **ABSENT** from all deploy manifests
- `change-0022-c5-canary-session` / `change-0022-c5-canary-auth`: **ABSENT** from all deploy manifests
- `siem-admin-key-change-me-in-production`: **ABSENT** from all deploy manifests
- `stringData` in `deploy/`: only in `.example.yaml` (documentation, no actual secrets)

---

## Working Tree

**Status:** DIRTY (freeze changes pending commit)  

**Modified files:**
- `aither-v2/deploy/canary/bff-gateway-canary.yaml` — literal credentials → secretKeyRef
- `aither-v2/deploy/siem/deployment.yaml` — stringData Secret removed → documented reference

**New files:**
- `aither-v2/deploy/canary/bff-canary-secrets.example.yaml` — example Secret (placeholders only)
- `reports/CHANGE-0022-FORCE-MAJEURE-FREEZE.md` — this report
- `reports/CHANGE-0022-DEFERRED-TESTS.md` — deferred test registry
- `reports/CHANGE-0022-RECOVERY-BACKLOG.md` — recovery backlog
- `reports/CHANGE-0022-RUNTIME-FREEZE.md` — runtime state snapshot

---

## Component Status After Freeze

| Component | Status |
|-----------|--------|
| Gateway code | PARTIALLY IMPLEMENTED |
| Gateway runtime | DEPLOYED, NOT PRIMARY |
| BFF canary | FROZEN / ISOLATED |
| Production BFF | UNCHANGED |
| Vault | DEPLOYED, FINAL VALIDATION DEFERRED |
| RAG | DEPLOYED, FINAL VALIDATION DEFERRED |
| SIEM | DEPLOYED, FINAL VALIDATION DEFERRED |
| CHANGE-0022 | RECOVERY REQUIRED |
| ROADMAP #5 | DEFERRED |

---

## Disposition

```
CHANGE-0022:     SAFELY FROZEN
ROADMAP #5:      DEFERRED UNDER FORCE MAJEURE
PRODUCTION BFF:  UNCHANGED
NEXT ROADMAP:    AUTHORIZED AFTER FREEZE COMMIT
```
