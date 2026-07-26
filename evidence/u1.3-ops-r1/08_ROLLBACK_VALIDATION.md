# U1.3-OPS-R1 — ROLLBACK VALIDATION

**Evidence:** logs/09-rollback.log  
**Timestamp:** 2026-07-26T01:33:24Z

## Pre-Rollback State

| Property | Value |
|----------|-------|
| Current revision | 17 |
| Current image | `python:3.11-slim` |
| Revisions in history | 7–17 |

## New Revision Creation

| Step | Result |
|------|:------:|
| Patch deployment with annotation | ✅ EXIT_CODE=0 |
| Rollout status | ✅ successfully rolled out |
| New revision | **18** |

## Rollback Execution

| Step | Result |
|------|:------:|
| `kubectl rollout undo deployment/aither-bff` | ✅ rolled back |
| Rollout duration | <60s (3 wait cycles) |
| Post-rollback revision | **19** |

## Post-Rollback Verification

| Check | Expected | Actual | Status |
|-------|----------|--------|:------:|
| Revision incremented | >18 | 19 | ✅ |
| Image restored | `python:3.11-slim` | `python:3.11-slim` | ✅ |
| Rollback annotation | absent | `<absent>` | ✅ |
| Pod status | Running | Running | ✅ |
| All other deployments | Running | 10/10 Running | ✅ |

## Deployment Health (All Pods)

| Deployment | Ready | Status |
|------------|:-----:|:------:|
| aither-ai-platform | 1/1 | Running ✅ |
| aither-bff | 1/1 | Running ✅ |
| aither-identity | 1/1 | Running ✅ |
| aither-portal | 1/1 | Running ✅ |
| aither-portal-backend | 1/1 | Running ✅ |
| aither-portal-frontend | 1/1 | Running ✅ |
| aither-redis-rate-limit | 1/1 | Running ✅ |
| nginx-gateway-32b | 2/2 | Running ✅ |
| vllm-14b-instruct | 1/1 | Running ✅ |
| vllm-32b-gptq | 1/1 | Running ✅ |

## Summary

| Assertion | Result |
|-----------|:------:|
| New revision created (17→18) | ✅ |
| Rollback successful (18→19) | ✅ |
| Image restored (`python:3.11-slim`) | ✅ |
| Rollback annotation absent after undo | ✅ |
| Zero pod restarts post-rollback | ✅ |
| Cluster-wide health unaffected | ✅ |

**Rollback validation: PASS** ✅
