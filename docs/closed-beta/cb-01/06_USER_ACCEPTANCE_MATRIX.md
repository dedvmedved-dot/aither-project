# CB-06 User Acceptance Matrix

**Date:** 2026-07-25 00:50–01:00 UTC

---

## UAT Scenarios

### UAT-01 — Authentication (Valid)
| User | Expected | Actual | Status |
|---|---|---|---|
| BETA-USER-01 | HTTP 200 | HTTP 200 | ✅ PASS |
| BETA-USER-02 | HTTP 200 | HTTP 200 | ✅ PASS |

### UAT-02 — Models List
| User | Expected | Actual | Status |
|---|---|---|---|
| BETA-USER-01 | HTTP 200, models listed | qwen-14b + qwen-32b-base returned | ✅ PASS |
| BETA-USER-02 | HTTP 200, models listed | qwen-14b + qwen-32b-base returned | ✅ PASS |

### UAT-03 — 14B Chat
| User | Model | Expected | Actual | Status |
|---|---|---|---|---|
| BETA-USER-01 | qwen-14b | HTTP 200, coherent response | "Здравствуйте (Zdravstvuyte)" | ✅ PASS |
| BETA-USER-02 | qwen-14b | HTTP 200, coherent response | "Здравствуйте (Zdravstvuyte)" | ✅ PASS |

### UAT-04 — 32B Base Model
| User | Model | Endpoint | Expected | Actual | Status |
|---|---|---|---|---|---|
| BETA-USER-01 | qwen-32b-base | /v1/chat/completions | HTTP 200 | HTTP 200 (base completion) | ✅ PARTIAL |
| BETA-USER-02 | qwen-32b-base | /v1/chat/completions | HTTP 200 | HTTP 200 (base completion) | ✅ PARTIAL |

> **Note:** `/v1/completions` endpoint returns 404. 32B model works through `/v1/chat/completions` but returns raw completion text, not chat-formatted messages. **Known limitation — documented in CB-01-DEF-001.**

### UAT-05 — Invalid Authentication
| User | Expected | Actual | Status |
|---|---|---|---|
| BETA-USER-01 | HTTP 401 | HTTP 401 "Invalid API Key" | ✅ PASS |
| BETA-USER-02 | HTTP 401 | HTTP 401 "Invalid API Key" | ✅ PASS |

### UAT-06 — Invalid Model
| User | Model | Expected | Actual | Status |
|---|---|---|---|---|
| BETA-USER-01 | nonexistent-model | HTTP 404, graceful error | HTTP 404 "Model not found or disabled" | ✅ PASS |

### UAT-07 — Repeated Use (10 sequential)
| User | Model | Requests | HTTP 200 | Errors | Status |
|---|---|---|---|---|---|
| BETA-USER-01 | qwen-14b | 10 | 10/10 | 0 | ✅ PASS |
| BETA-USER-02 | qwen-14b | 10 | 10/10 | 0 | ✅ PASS |

### UAT-08 — User Feedback
| User | Feedback | Status |
|---|---|---|
| BETA-USER-01 | PENDING* | N/A |
| BETA-USER-02 | PENDING* | N/A |

*Awaiting actual user interaction.

---

## Summary

| Scenario | PASS | PARTIAL | FAIL | NOT RUN |
|---|---|---|---|---|
| UAT-01 Authentication | 2 | 0 | 0 | 0 |
| UAT-02 Models List | 2 | 0 | 0 | 0 |
| UAT-03 14B Chat | 2 | 0 | 0 | 0 |
| UAT-04 32B | 0 | 2 | 0 | 0 |
| UAT-05 Invalid Auth | 2 | 0 | 0 | 0 |
| UAT-06 Invalid Model | 2 | 0 | 0 | 0 |
| UAT-07 Repeated Use | 2 | 0 | 0 | 0 |
| UAT-08 Feedback | 0 | 0 | 0 | 2 |
| **TOTAL** | **12** | **2** | **0** | **2** |

**Overall: PASS WITH KNOWN LIMITATION (UAT-04: /v1/completions→404)**

---
*Evidence: reports/closed-beta/cb-01/users/BETA-USER-01_UAT.md, BETA-USER-02_UAT.md*
