# CHANGE-0022 — RECOVERY BACKLOG

**Directive:** R7-R5-EMG-FM-01  
**Date:** 2026-07-28T02:30:00Z  

All items below must be completed before Gateway production cutover can be authorized.  
CHANGE-0022 is **RECOVERY REQUIRED**, not closed.

---

## Blocking Items (Required Before Cutover)

### 1. Deferred Tests (19 items)
See `reports/CHANGE-0022-DEFERRED-TESTS.md` for full registry.
- 14 canary E2E tests (CANARY-005 through CANARY-020)
- 2 integration tests (registered-user, external API-token delegation)
- 3 resilience tests (Vault failure, RAG failure, rollback cycle)

### 2. Production Gateway Cutover
- Gateway must become primary routing path for all model traffic
- Production BFF must route through Gateway (currently direct to vLLM)
- Full cutover procedure with rollback plan

### 3. Vault Final Validation
- Vault K8s auth end-to-end with real projected SA token
- Vault sealed scenario
- Vault network failure scenario
- VAULT_REQUIRED=true enforcement

### 4. RAG Final Validation
- End-to-end ingest → query → hybrid pipeline
- Organization isolation verification
- DLP egress with actual sensitive content
- ChromaDB backend failure → fail-closed

### 5. SIEM Final Validation
- All 16 event types delivered from Gateway runtime
- Event retention and backup verification
- NetworkPolicy enforcement

### 6. Security Incident Closure
- SEC-INC-CHANGE-0022-C4-01: full history audit (deferred — no history rewrite)
- SEC-INC-CHANGE-0022-C5-01: full history audit (deferred — no history rewrite)

---

## Non-Blocking Items (Can Be Deferred Past Cutover)

### 1. Historical Exposure Cleanup (BLOCKED — history rewriting prohibited)
- Full git history audit for all credential exposures
- BFG/purge of old credentials from history
- Requires explicit Owner authorization for history rewrite

### 2. Performance / Scale Testing
- Load testing under production traffic patterns
- Gateway concurrency limits
- Redis connection pool sizing

---

## Recovery Trigger

CHANGE-0022 recovery is triggered only by explicit Owner directive.  
Hermes shall not self-initiate recovery.  
Emergency mode remains ACTIVE until recovery is complete and audited.
