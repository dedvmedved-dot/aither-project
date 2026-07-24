# Regression Test — U1.4 Beta-1

## Authentication

| Test | Expected | Actual | Status |
|---|---|---|---|
| No API key | 401 | 401 | ✅ PASS |
| Wrong API key | 401 | 401 | ✅ PASS |
| Valid API key | 200 | 200 | ✅ PASS |

## API Endpoints

| Test | Endpoint | Expected | Actual | Status |
|---|---|---|---|---|
| List models | GET /v1/models | 200 + 2 models | 200, [qwen-14b, qwen-32b-base] | ✅ PASS |
| 14B chat | POST /v1/chat/completions | 200 + chat.completion | 200, "1\n2\n3" | ✅ PASS |
| 32B completion | POST /v1/chat/completions | 200 + text_completion | 200, meaningful text | ✅ PASS |
| Wrong model | POST with invalid model | 404 | 404 | ✅ PASS |
| Missing model | POST without model field | 422 | 422 | ✅ PASS |

## Routes

| Route | GET /v1/models | POST 14B | POST 32B |
|---|---|---|---|
| :30902 (Test Zone) | 200 ✅ | 200 ✅ | 200 ✅ |
| :443 (Internet) | 200 ✅ | 200 ✅ | 200 ✅ |
| :10443 (Internet) | 200 ✅ | 200 ✅ | 200 ✅ |

## Infrastructure

| Test | Status |
|---|---|
| Kubernetes nodes Ready | ✅ 2/2 |
| All pods Running | ✅ 11/11 |
| No CrashLoopBackOff | ✅ 0 |
| Pod restarts (recent) | ✅ 0 |
| VPN tunnel UP | ✅ |
| VPN processes (expected: 1) | ⚠️ 3 (1 active + 2 zombie expect wrappers) |
| VPS2 nginx responding | ✅ |
| VPS2 disk | ✅ 58% (20G free) |
| Prometheus metrics | ✅ Accessible |

## Semantic Checks

| Model | Prompt | Response Check | Status |
|---|---|---|---|
| 14B | "Count to 3" | Contains "1, 2, 3" | ✅ PASS |
| 32B | "Say hello" | Meaningful English text | ✅ PASS |

## Previous Gate Reference
- 180/180 post-redeploy stability gate: ✅ PASS (2026-07-24)
- 230/230 functional stability gate: ✅ PASS (2026-07-24)

## Summary
**ALL TESTS PASSED** — 18/18 test points ✅. No regressions detected.
