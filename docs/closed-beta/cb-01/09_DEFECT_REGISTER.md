# CB-09 Defect Register

**Date:** 2026-07-25

---

## Active Defects

### CB-01-DEF-001: /v1/completions endpoint returns 404

| Field | Value |
|---|---|
| **ID** | CB-01-DEF-001 |
| **Source** | Hermes agent testing |
| **Date** | 2026-07-25 |
| **Scenario** | UAT-04: 32B Completion |
| **Expected** | HTTP 200 via POST /v1/completions |
| **Actual** | HTTP 404 "Not Found" on both :443 and :10443 |
| **Severity** | P3 — Medium |
| **Priority** | P3 — Medium |
| **Reproducibility** | Always |
| **Workaround** | Use POST /v1/chat/completions with qwen-32b-base model. Returns completion-style text in chat format. |
| **Owner** | Unassigned |
| **Status** | NEW |
| **Blocks Beta** | No (workaround available) |

### CB-01-DEF-002: UAT-08 User Feedback not collected

| Field | Value |
|---|---|
| **ID** | CB-01-DEF-002 |
| **Source** | Hermes agent |
| **Date** | 2026-07-25 |
| **Scenario** | UAT-08: User Feedback |
| **Expected** | At least one feedback report per active user |
| **Actual** | No external human users assigned; feedback cannot be collected |
| **Severity** | P3 — Medium |
| **Priority** | P2 — High |
| **Reproducibility** | Procedural |
| **Workaround** | Assign actual internal users and collect feedback |
| **Owner** | Project management |
| **Status** | NEW |
| **Blocks Beta** | No (procedural, not technical) |

### CB-01-DEF-003: Observation window incomplete

| Field | Value |
|---|---|
| **ID** | CB-01-DEF-003 |
| **Source** | Hermes agent |
| **Date** | 2026-07-25 |
| **Scenario** | TASK 8: Observation Window |
| **Expected** | Full Closed Beta working cycle observation |
| **Actual** | ~10-minute technical validation only |
| **Severity** | P3 — Medium |
| **Priority** | P2 — High |
| **Reproducibility** | Procedural |
| **Workaround** | Extend observation to full working cycle after user assignment |
| **Owner** | Project management |
| **Status** | NEW |
| **Blocks Beta** | No (procedural) |

---

## Defect Summary

| Severity | Count |
|---|---|
| P1 Critical | 0 |
| P2 High | 0 |
| P3 Medium | 3 |
| P4 Low | 0 |

---

## Status: NO BLOCKING DEFECTS

All 3 defects are procedural or have workarounds. No P1/P2 technical defects exist. System is technically ready for Closed Beta.

---
*Status key: NEW → CONFIRMED → IN PROGRESS → FIXED → RETEST REQUIRED → VERIFIED | DEFERRED | REJECTED*
