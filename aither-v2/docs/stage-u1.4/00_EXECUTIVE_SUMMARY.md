# U1.4 Beta Release Candidate — Executive Summary

## Status
**READY FOR CLOSED BETA**

## Release Version
- **RC:** U1.4-Beta-1
- **Commit:** (pending)
- **Branch:** aither-v2
- **Date:** 2026-07-25

## Components
| Component | Version | Status |
|---|---|---|
| ai-platform | u1.2-persistence-20260725-0004 | Running |
| nginx-gateway-32b | rate=300r/m, burst=20 | Running |
| vLLM 14B | vllm-openai (digest) | Running |
| vLLM 32B GPTQ | vllm-openai (digest) | Running |
| VPS2 nginx | HTTP/1.1, keepalive 16 | Running |
| VPS2 VPN | OpenConnect (fixed entrypoint) | Stable >3h |

## Regression Test
| Area | Result |
|---|---|
| Authentication (valid/invalid/missing) | ✅ PASS |
| GET /v1/models | ✅ 2 models returned |
| POST 14B chat | ✅ Correct response |
| POST 32B completion | ✅ Correct response |
| Error handling (404/422) | ✅ Proper codes |
| All 9 routes (3×3) | ✅ 200 on all |
| Kubernetes (2 nodes, 11 pods) | ✅ All healthy |
| VPN tunnel | ✅ Stable |
| Metrics | ✅ Accessible |

## Decision
**GO** — system meets criteria for closed beta with ≤5 internal users.
