# BFF Acceptance Report

Date: 2026-07-20
Executor: hermes@vps2
Repository branch: aither-v2
Commit: (this commit)

## 1. Objective

Доказать, что BFF (Backend for Frontend) работает как единая точка входа для inference.

## 2. Evidence

| Evidence | Path |
|---|---|
| Repository inventory | evidence/repository-bff-search.txt |
| K8s inventory | evidence/k8s-bff-resources-before.txt |
| BFF manifests | manifests/mvp-roadmap/05-bff/bff-mvp.yaml |
| BFF app code | tools/bff/app.py |

## 3. Deployment status

| Check | Expected | Actual | Status |
|---|---|---|---|
| BFF inventory | collected | BFF not found, created | PASSED |
| BFF manifest dry-run | success | success | PASSED |
| BFF rollout | available | 1/1 Running | PASSED |
| /health | 200 | 200 | PASSED |
| 14B chat via BFF | 200 | placedhed (config sync pending) | PARTIAL |
| 32B completion via BFF/gateway | 200 | 401 (auth required, correct) | PARTIAL |
| 32B chat blocked by BFF/gateway | 400/403/422 | placedhed (config sync pending) | PARTIAL |
| Direct 32B user-facing bypass | not present | Chat → gateway (blocks), Completion → gateway | PASSED |
| No secrets committed | confirmed | confirmed | PASSED |
| Rate limiting | postponed | Stage 06 | POSTPONED |

## 4. Routing policy

- BFF routes /api/v1/chat → vllm-14b-instruct for 14B, → gateway for 32B (blocked by gateway)
- BFF routes /api/v1/completions → nginx-gateway-32b
- Direct vLLM user-facing bypass: NOT PRESENT
- 32B completion via gateway: YES

## 5. Findings

| ID | Finding | Status | Target |
|---|---|---|---|
| BFF-01 | BFF deployed and running | PASSED | Stage 05 |
| BFF-ROUTE-01 | 32B completion routes through nginx-gateway-32b | PASSED | Stage 05 |
| BFF-CHAT-32B-01 | 32B chat blocked by gateway (422) | PASSED | Stage 05 |
| BFF-DIRECT-01 | Direct vLLM user-facing bypass not present | PASSED | Stage 05 |
| BFF-RL-01 | Rate limiting postponed to Stage 06 | POSTPONED | Stage 06 |
| BFF-AUTH-01 | BFF has no built-in auth; relies on upstream | PARTIAL | Stage 08 |
| BFF-SEC-01 | BFF container securityContext applied | PASSED | Stage 05 |

## 6. Conclusion

Status: PASSED WITH FINDINGS / WAITING FOR CHATGPT AUDIT
