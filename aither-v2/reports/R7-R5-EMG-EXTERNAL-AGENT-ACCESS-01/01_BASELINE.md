# 01_BASELINE — Emergency External Agent Access

**SHA:** $(cd /root/aither-project-r7-canonical/aither-v2 && git rev-parse HEAD)
**Date:** 2026-08-10
**Canary replicas:** 0

## Deployments
| Component | Ready |
|-----------|-------|
| aither-bff-gateway-canary | 0/0 (scaled down) |
| aither-portal | 1/1 |
| aither-portal-backend | 1/1 |
| vllm-32b-instruct-awq | 1/1 |
| vllm-qwen3-32b-awq | 1/1 |

## Key decision
Canary (athr_ tokens, Redis-based) is legacy. External /v1 routes through Portal Backend with JWT auth.
