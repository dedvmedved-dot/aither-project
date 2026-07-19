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
| Gateway completion | evidence/32b-gateway-completion-result.json |
| Gateway chat blocked | evidence/32b-gateway-chat-blocked-422.txt |
| Gateway auth no token | evidence/gateway-auth-no-token.txt |
| Gateway auth wrong token | evidence/gateway-auth-wrong-token.txt |
| Gateway auth valid token | evidence/gateway-auth-valid-token.txt |
| Smoke benchmark | logs/benchmark-smoke.log |
| Streaming TTFT | logs/streaming-ttft-32b.log |

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
| Streaming supported | — | yes | PASSED |

## 4. Latency (streaming TTFT)

| Check | TTFT avg | Total avg | tokens/sec |
|---|---:|---:|---:|
| 32B completion (streaming) | 0.25s | 2.73s | — |

## 5. Response sanity

32B direct completion response: "France and the country's largest city. It is one of..." — coherent, non-empty, no stack trace. ✅

## 6. Findings

| ID | Finding | Status | Required action |
|---|---|---|---|
| 32B-CHAT-DIRECT-01 | Direct vLLM 32B chat endpoint returns HTTP 200; completion-only restriction is enforced at gateway level | OBSERVED / ACCEPTED FOR MVP | Keep gateway policy; verify in Stage 04 hardening |

## 7. Conclusion

Status: PASSED WITH FINDINGS
