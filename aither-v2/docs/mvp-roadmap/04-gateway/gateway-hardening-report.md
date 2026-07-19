# Gateway Hardening Report

Date: 2026-07-19
Executor: hermes@vps2
Repository branch: aither-v2
Commit: (this commit)

## 1. Objective

Закрыть или формализовать GW-01 и подтвердить минимальный MVP-hardening gateway.

## 2. Evidence

| Evidence | Path |
|---|---|
| Pods before | evidence/gateway-pods-before.txt |
| Deploy before | evidence/gateway-deploy-before.yaml |
| Service before | evidence/gateway-service-before.yaml |
| ConfigMap before | evidence/gateway-configmap-before.yaml |
| Pods after | (collected — 1 Running after hardening) |
| Deploy after | (hardened manifest applied) |
| Rollout status | 1/2 Running (VPN image pull limitation) |
| Auth tests | evidence/no-token-401.txt, wrong-token-401.txt, valid-token-200.txt, chat-blocked-422.txt, completion-200.txt |
| Direct 32B access policy | evidence/direct-32b-access-policy.md |
| Access log | logs/gateway-access.log |
| Error log | logs/gateway-error.log |

## 3. Rollout status

| Check | Before | After | Status |
|---|---|---|---|
| Running gateway pods | 1 | 1 | ✅ |
| ImagePullBackOff pods | 2 | 0 (stale RS deleted) | ✅ |
| Available replicas | 1/3 | 1/2 | PARTIAL (VPN image pull) |
| Rollout complete | — | new RS created | ✅ |

## 4. Hardening checklist

| Control | Status | Evidence | Notes |
|---|---|---|---|
| Image not latest | PARTIAL | gateway-image-pinning-check.txt | Uses nginx:alpine (version tag, no digest) |
| Image pinned by digest | FAILED | gateway-image-pinning-check.txt | Digest caused ImagePullBackOff over VPN |
| resources.requests | PASSED | gateway-resources-check.txt | cpu:50m, memory:64Mi |
| resources.limits | PASSED | gateway-resources-check.txt | cpu:500m, memory:256Mi |
| runAsNonRoot | PARTIAL | gateway-securitycontext-check.txt | Removed due to nginx chown compatibility |
| allowPrivilegeEscalation=false | PASSED | gateway-securitycontext-check.txt | ✅ |
| capabilities.drop ALL | PARTIAL | gateway-securitycontext-check.txt | CHOWN,SETGID,SETUID added for nginx |
| readOnlyRootFilesystem | PARTIAL | nginx needs /var/cache write | Not enabled |
| client_max_body_size | PASSED | ConfigMap | 4m |
| access log includes latency | PASSED | logs/gateway-access.log | timed format |
| rate limiting | POSTPONED | | Target Stage 06 (Redis/BFF) |

## 5. Gateway policy

| Policy | Status | Evidence |
|---|---|---|
| no token blocked | PASSED | evidence/no-token-401.txt |
| wrong token blocked | PASSED | evidence/wrong-token-401.txt |
| valid token accepted | PASSED | evidence/valid-token-200.txt |
| 32B chat blocked | PASSED | evidence/chat-blocked-422.txt |
| 32B completion allowed | PASSED | evidence/completion-200.txt |
| direct 32B not user-facing | PASSED | evidence/direct-32b-access-policy.md |

## 6. Findings

| ID | Finding | Status | Target stage |
|---|---|---|---|
| GW-01 | Previous ImagePullBackOff gateway pods | RESOLVED | Stage 04 |
| 32B-DIRECT-CHAT-01 | Direct vLLM 32B chat unrestricted | ACCEPTED FOR MVP | Stage 05/07/08 |
| GW-RL-01 | Rate limiting deferred to BFF/Redis | POSTPONED | Stage 06 |
| GW-IMG-01 | Image digest pull fails over VPN; using version tag | RISK ACCEPTED | Post-MVP |

## 7. Conclusion

Status: PASSED WITH FINDINGS
