# Healthcheck Audit Report

**Stage:** RC1  
**Date:** 2026-07-23  
**File:** `reports/rc1/healthcheck.md`

---

## Current Health Endpoints

### AI Platform
| Endpoint | Method | Status | Response | Notes |
|----------|--------|--------|----------|-------|
| `/health` | GET | ✅ 200 | `{"status":"ok","service":"ai-platform"}` | Basic health |
| `/ready` | GET | ✅ 200 | `{"status":"ok","dependencies":{"database":"connected","identity":"connected"}}` | Dependency-aware |
| `/version` | GET | ✅ 200 | `{"service":"","version":"1.0.0","build":"stage16"}` | Build info |

### Portal Backend
| Endpoint | Method | Status | Response | Notes |
|----------|--------|--------|----------|-------|
| `/health` | GET | ✅ 200 | `{"status":"ok","service":"portal-backend"}` | Basic health |
| `/ready` | GET | ✅ 200/503 | `{"status":"ok","identity":"connected"}` | Checks Identity |
| `/version` | GET | ✅ 200 | `{"service":"","version":"1.0.0","build":"stage15"}` | Build info |

### Identity
| Endpoint | Method | Status | Response | Notes |
|----------|--------|--------|----------|-------|
| `/health` | GET | ✅ 200 | `{"status":"ok","service":"identity"}` | Basic health |
| `/ready` | GET | ✅ 200/503 | `{"status":"ok","database":"connected"}` | Checks SQLite |
| `/version` | GET | ✅ 200 | `{"service":"","version":"1.0.0","build":"stage15"}` | Build info |

### Gateway (nginx-gateway-32b)
| Endpoint | Method | Status | Response | Notes |
|----------|--------|--------|----------|-------|
| `/health` | GET | ✅ 200 | (empty body, HTTP 200) | Proxies to vLLM `/health` |
| `/healthz` | GET | ✅ 200 | `"ok"` | Local nginx health (no upstream check) |
| `/ready` | GET | ❌ 404 | `{"error":"not found"}` | **Missing** — nginx config has no `/ready` location |
| `/version` | GET | ❌ 404 | `{"error":"not found"}` | **Missing** — nginx config has no `/version` location |

---

## K8s Probe Configuration

### Services with Both `livenessProbe` and `readinessProbe`

| Service | Liveness Path | Readiness Path | Startup Probe |
|---------|---------------|----------------|---------------|
| AI Platform | `/health` (15s delay, 20s period) | `/ready` (10s delay, 15s period, 5s timeout) | None |
| Portal Backend | `/health` (10s delay, 15s period) | `/ready` (5s delay, 10s period) | None |
| Identity | `/health` (10s delay, 15s period) | `/ready` (5s delay, 10s period) | None |
| Gateway (nginx) | `/healthz` (30s period, local) | `/health` (5s delay, 10s period) | `/healthz` (5s, 30 tries) |

### Missing Probes
- Redis: No probes configured in deployment

---

## Gap Analysis

### `/live` (Liveness) Endpoint
- **Status:** Most services use `/health` as liveness endpoint
- **Finding:** Gateway distinguishes `/healthz` (local nginx) from `/health` (upstream) — good practice
- **Recommendation:** Add a lightweight `/live` endpoint to all services that does NOT check dependencies (only process health)

### `/ready` (Readiness)
- **Status:** All services have `/ready` EXCEPT Gateway
- **Finding:** Gateway uses `/health` (proxied to vLLM) for readiness — acceptable but `/ready` would be better
- **Fix needed for completeness:** Add `/ready` to Gateway nginx config

### Gateway Improvement
The Gateway nginx config needs two additional location blocks:

```nginx
location = /ready {
    access_log off;
    # Check if nginx is running AND can reach upstream
    proxy_pass http://10.99.3.103:8000/health;
    proxy_read_timeout 5s;
}
location = /version {
    access_log off;
    return 200 '{"service":"nginx-gateway-32b","version":"1.0.0"}';
    add_header Content-Type application/json;
}
```

---

## Conclusion

- ✅ **AI Platform** — `/health` ✅, `/ready` ✅ (dependency-aware)
- ✅ **Portal Backend** — `/health` ✅, `/ready` ✅
- ✅ **Identity** — `/health` ✅, `/ready` ✅
- ❌ **Gateway** — `/health` ✅, `/ready` ❌, `/version` ❌
- ⚠️ **Redis** — no probes configured

**Overall: 3/4 services have complete healthcheck coverage. Gateway needs `/ready` and `/version` endpoints.**
