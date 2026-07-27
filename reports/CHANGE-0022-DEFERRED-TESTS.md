# CHANGE-0022 — DEFERRED TESTS

**Directive:** R7-R5-EMG-FM-01  
**Date:** 2026-07-28T02:30:00Z  

All tests below are **DEFERRED UNDER FORCE MAJEURE**, not cancelled.  
Each is **required before Gateway production cutover**.

---

## Canary E2E — Deferred

| ID | Test | Status | Acceptance | Blocking Cutover |
|----|------|--------|------------|------------------|
| CANARY-005 | delegation negative claims | DEFERRED UNDER FORCE MAJEURE | NOT GRANTED | YES |
| CANARY-007 | 14B streaming | DEFERRED UNDER FORCE MAJEURE | NOT GRANTED | YES |
| CANARY-009 | 32B streaming | DEFERRED UNDER FORCE MAJEURE | NOT GRANTED | YES |
| CANARY-010 | real scope deny | DEFERRED UNDER FORCE MAJEURE | NOT GRANTED | YES |
| CANARY-011 | billing reconciliation | DEFERRED UNDER FORCE MAJEURE | NOT GRANTED | YES |
| CANARY-012 | true idempotent replay | DEFERRED UNDER FORCE MAJEURE | NOT GRANTED | YES |
| CANARY-013 | actual rate-limit exceed | DEFERRED UNDER FORCE MAJEURE | NOT GRANTED | YES |
| CANARY-014 | exact security ingress deny | DEFERRED UNDER FORCE MAJEURE | NOT GRANTED | YES |
| CANARY-015 | security egress deny | DEFERRED UNDER FORCE MAJEURE | NOT GRANTED | YES |
| CANARY-016 | SIEM raw delivery | DEFERRED UNDER FORCE MAJEURE | NOT GRANTED | YES |
| CANARY-017 | Vault required validation | DEFERRED UNDER FORCE MAJEURE | NOT GRANTED | YES |
| CANARY-018 | RAG ingest/query/isolation | DEFERRED UNDER FORCE MAJEURE | NOT GRANTED | YES |
| CANARY-019 | Redis outage | DEFERRED UNDER FORCE MAJEURE | NOT GRANTED | YES |
| CANARY-020 | Gateway outage | DEFERRED UNDER FORCE MAJEURE | NOT GRANTED | YES |

## Integration — Deferred

| ID | Test | Status | Acceptance | Blocking Cutover |
|----|------|--------|------------|------------------|
| — | registered-user delegation | DEFERRED UNDER FORCE MAJEURE | NOT GRANTED | YES |
| — | external API-token delegation | DEFERRED UNDER FORCE MAJEURE | NOT GRANTED | YES |

## Resilience — Deferred

| ID | Test | Status | Acceptance | Blocking Cutover |
|----|------|--------|------------|------------------|
| — | Vault sealed/network failure | DEFERRED UNDER FORCE MAJEURE | NOT GRANTED | YES |
| — | RAG backend failure | DEFERRED UNDER FORCE MAJEURE | NOT GRANTED | YES |
| — | real rollback cycle | DEFERRED UNDER FORCE MAJEURE | NOT GRANTED | YES |

---

## Summary

- **Total deferred:** 19 tests
- **All required before Gateway production cutover:** YES
- **None cancelled:** All preserved with original IDs
- **Recovery:** See `reports/CHANGE-0022-RECOVERY-BACKLOG.md`
