# CB-01 Pre-Launch Baseline

**Stage:** CB-01 — Closed Beta Launch
**Date:** 2026-07-25 00:56 UTC
**Branch:** aither-v2
**Base commit:** d07011d65b648713fb97979765d0d0d1106c4911

---

## System State Verification

### Kubernetes
| Check | Status | Detail |
|---|---|---|
| Nodes | ✅ PASS | 2/2 Ready (n7-gpu, n8-gpu control-plane) |
| ai-platform | ✅ PASS | 1/1 Running, 0 restarts, 3h16m uptime |
| bff | ✅ PASS | 1/1 Running, 3d8h uptime |
| identity | ✅ PASS | 1/1 Running, 2d2h uptime |
| portal | ✅ PASS | 1/1 Running, 3d8h uptime |
| portal-backend | ✅ PASS | 1/1 Running, 2d uptime |
| portal-frontend | ✅ PASS | 1/1 Running, 3d8h uptime |
| redis-rate-limit | ✅ PASS | 1/1 Running, 3d8h uptime |
| nginx-gateway-32b | ✅ PASS | 2/2 Running, 4h25m uptime |
| vllm-14b-instruct | ✅ PASS | 1/1 Running, 5d15h uptime |
| vllm-32b-gptq | ✅ PASS | 1/1 Running, 5d15h uptime |
| Restart counts | ✅ PASS | All 0 (except flink-taskmanager in aiops namespace — unrelated) |

### VPS2 Edge (Docker)
| Check | Status | Detail |
|---|---|---|
| vpn-cisco | ✅ PASS | Up 6 hours |
| aither-failover-nginx | ✅ PASS | Up 5 hours, ports 443/10443/30901 listening |
| aither-registry | ✅ PASS | Up 3 days |

### VPN
| Check | Status | Detail |
|---|---|---|
| tun0 interface | ✅ PASS | UP, 10.129.100.53/32 |
| OpenConnect | ✅ PASS | Single process, connected |

### Network / TLS / DNS
| Check | Status | Detail |
|---|---|---|
| :443 (AI Platform) | ✅ PASS | HTTPS listening, nginx serving |
| :10443 (32B dedicated) | ✅ PASS | HTTPS listening |
| :30901 (Test Zone proxy) | ✅ PASS | HTTPS listening |
| :30902 (AI Platform NodePort) | ✅ PASS | NodePort available |
| TLS cert | ✅ PASS | fb1.spb.ru, cert.pem present |

### API
| Check | Status | Detail |
|---|---|---|
| GET /v1/models (valid key) | ✅ PASS | HTTP 200, returns qwen-14b + qwen-32b-base |
| GET /v1/models (no key) | ✅ PASS | HTTP 401, security enforced |
| GET /v1/models (invalid key) | ✅ PASS | HTTP 401 |
| POST /v1/chat/completions 14B | ✅ PASS | HTTP 200, coherent Russian response |
| POST /v1/chat/completions 32B | ✅ PASS | HTTP 200, base model responses |
| Invalid model | ✅ PASS | HTTP 404, proper error message |

### Data
| Check | Status | Detail |
|---|---|---|
| ai-platform.db | ✅ PASS | models: 2, api_keys: 21, conversations: 99, messages: 1013 |
| identity.db | ✅ PASS | users: 1 (admin) |
| Disk space | ✅ PASS | 20G free (58% used) |
| Memory | ✅ PASS | 6.1G available (7.8G total) |

### Repository
| Check | Status | Detail |
|---|---|---|
| Current commit | ✅ PASS | d07011d (U1.4 beta release candidate) |
| Branch | ✅ PASS | aither-v2 |
| Uncommitted changes | ✅ PASS | None (clean) |

---

## Beta Acceptance Checklist (from U1.4)

| Item | Status |
|---|---|
| DNS | PASS |
| TLS | PASS |
| VPN | PASS |
| Gateway | PASS |
| API | PASS |
| Models | PASS |
| Monitoring | PASS |
| Logs | PASS |
| Backup | PASS (created below) |
| Health | PASS |

---

## Summary

**All checks PASS. No blocking issues. System is ready for user access provisioning.**

---
*Evidence: reports/closed-beta/cb-01/01_PRE_LAUNCH_EVIDENCE.md*
