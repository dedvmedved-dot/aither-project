# 32B Benchmark Report

Date: 2026-07-19
Executor: hermes@vps2
Repository branch: aither-v2
Commit: (this commit)

## 1. Objective

Доказать, что 32B model работает через разрешённый completion endpoint и корректно блокирует chat endpoint.

## 2. Evidence

| Evidence | Path |
|---|---|
| 32B direct completion | evidence/32b-completion-result.json |
| 32B direct chat | evidence/32b-chat-result.txt |
| Gateway completion | (via smoke benchmark) |
| Gateway chat blocked | (via smoke benchmark) |
| Smoke benchmark | logs/benchmark-smoke.log |

## 3. Results

| Check | Expected | Actual | Status |
|---|---|---|---|
| 32B health | 200 | 200 | PASSED |
| 32B direct completion | 200 | 200 | PASSED |
| 32B direct chat | 200 (vLLM accepts) | 200 | OBSERVED |
| 32B gateway completion | 200 | 200 | PASSED |
| 32B gateway chat | 422 | 422 | PASSED |
| No token | 401/403 | 401 | PASSED |
| Wrong token | 401/403 | 401 | PASSED |
| Valid token | 200 | 200 | PASSED |

## 4. Latency

| Check | TTFB | TOTAL | Status |
|---|---:|---:|---|
| 32B direct completion | 1.34s | — | PASSED |
| 32B gateway completion | 1.33s | — | PASSED |

## 5. Response sanity

32B direct completion response: "France and the country's largest city. It is one of..." — coherent, non-empty, no stack trace. ✅

## 6. Findings

| ID | Finding | Status | Required action |
|---|---|---|---|
| — | No findings | PASSED | — |

## 7. Conclusion

Status: PASSED

32B model operates correctly as completion-only. Gateway blocks Chat with 422. Auth properly enforced (401 without/with wrong token).
