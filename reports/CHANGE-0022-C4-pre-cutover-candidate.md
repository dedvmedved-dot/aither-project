# CHANGE-0022-C4 — Pre-Cutover Candidate Report

**Date:** 2026-07-28  
**Commit:** 05f2e11340377b12079f6d4a6da0baa2e68b7d6f  
**Branch:** aither-v2  
**Remote:** origin/aither-v2  
**Change-ID:** CHANGE-0022-C4  
**Emergency mode:** ACTIVE  
**Production BFF cutover:** NOT AUTHORIZED  

---

## Statement Categories

| Category | Definition |
|---|---|
| **STATIC REVIEW** | Code inspected, design verified — NOT a runtime test |
| **UNIT PASS** | Isolated function/module test passed |
| **INTEGRATION PASS** | Multi-component test with real dependencies passed |
| **RUNTIME PASS** | Live test against running Gateway in cluster |
| **E2E PASS** | Full end-to-end: client → canary → Gateway → model |
| **NOT EXECUTED** | Test planned but not run |
| **FAIL** | Test failed |

STATIC REVIEW is NOT counted as runtime PASS.

---

## Section Summary (14 sections)

### S1 — Reporting ✓
This report. Categories separated, SHAs factual.

### S2 — Production BFF Canary (IN PROGRESS — subagent)
Rewrite canary YAML: delete inline ConfigMap, use actual production BFF source/Dockerfile/image.

### S3 — Gateway Scopes ✓ RUNTIME DEPLOYED
- Added `_model_required_scope()` mapping: qwen-14b→model:14b:chat, qwen-32b-base→model:32b:chat-adapter or model:32b:completion
- Added `_has_scope()` with admin bypass
- Scope check BEFORE routing/rate-limit/billing
- Missing scope → HTTP 403
- Commit: 81bdce2

### S4 — Rate Limiting ✓ RUNTIME DEPLOYED
- Org quota check (`check_org_quota`) before per-request RL
- API-key quota check (`check_api_key_quota`)
- Per-request RL passes api_key + model_id
- HTTP contract: 403 for unknown tier, 503 for unavailability, 429 for exceeded
- Commit: 81bdce2

### S5 — HTTP Idempotency ✓ RUNTIME DEPLOYED
- Added `get_replay_response()`: fetches original HTTP status, Content-Type, body from DB
- ALREADY_COMPLETED returns `JSONResponse` with original status, content-type, body
- DATABASE_ERROR check: never returns normal success on DB error
- Commit: 81bdce2

### S6 — Streaming DLP Holdback ✓ RUNTIME DEPLOYED
- `check_egress_streaming` returns (ok, audit, new_buffer, safe_text, held_text)
- HOLD_BACK=50 chars: holds tail, merges with next chunk
- SSE chunks reconstructed with safe_text only
- Final flush: release remaining held_text after final check
- Violation: NO byte of matched secret delivered
- Commit: 81bdce2

### S7 — Streaming Settlement ✓ RUNTIME DEPLOYED
- [DONE] sent ONLY after settle SUCCESS
- Settlement DATABASE_ERROR → controlled error message + [DONE]
- No successful completion announced on failure
- Commit: 81bdce2

### S8 — SIEM Runtime (IN PROGRESS — subagent)

### S9 — Vault (IN PROGRESS — subagent)

### S10 — RAG Backend (IN PROGRESS — subagent)

### S11 — BFF Canary E2E (PENDING)

### S12 — Rollback Test (PENDING)

### S13 — Evidence (IN PROGRESS)

### S14 — Pre-Cutover Acceptance (PENDING)

---

## Current State

| Gate | Status |
|---|---|
| Production BFF | UNCHANGED |
| Gateway image | sha256:c7f5217d809f (S3-S7 deployed) |
| Git working tree | CLEAN |
| Local SHA = Remote SHA | YES (05f2e11) |
| S3-S7 runtime | DEPLOYED, healthy |
| SIEM/Vault/RAG | PENDING subagent completion |
| BFF canary | PENDING subagent completion |

---

*Report generated as working document. Will be finalized after all subagents complete.*
