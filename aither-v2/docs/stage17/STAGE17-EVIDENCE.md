# Stage 17 — Observability Evidence

## 1. New Files Created

### Services (Metrics + Logging)

| File | Change |
|---|---|
| `services/identity/app/main.py` | Added Prometheus metrics, structured JSON logging |
| `services/identity/requirements.txt` | Added `prometheus-client`, `psutil` |
| `services/portal-backend/app/main.py` | Added Prometheus metrics, structured JSON logging |
| `services/portal-backend/requirements.txt` | Added `prometheus-client`, `psutil` |
| `services/ai-platform/app/main.py` | Added Prometheus metrics, structured JSON logging, Gateway metrics |
| `services/ai-platform/requirements.txt` | Added `prometheus-client`, `psutil` |

### Dashboards (Grafana JSON)

| File | Description |
|---|---|
| `docs/stage17/grafana/dashboard-system-overview.json` | System-wide view |
| `docs/stage17/grafana/dashboard-ai-platform.json` | AI Platform-specific |
| `docs/stage17/grafana/dashboard-gateway.json` | Gateway monitoring |
| `docs/stage17/grafana/dashboard-identity.json` | Identity monitoring |
| `docs/stage17/grafana/dashboard-portal.json` | Portal BFF monitoring |

### Alert Rules

| File | Description |
|---|---|
| `docs/stage17/prometheus/alert-rules.yaml` | 6 alert groups, 8 alert rules |

### Kubernetes Manifests

| File | Resources |
|---|---|
| `docs/stage17/k8s/servicemonitor.yaml` | 2 ServiceMonitors, 1 PrometheusRule |
| `docs/stage17/k8s/configmaps.yaml` | 3 ConfigMaps (dashboards, rules, Fluent Bit) |

### Acceptance Tests

| File | Description |
|---|---|
| `scripts/test-stage17-observability.sh` | Observability acceptance tests |

### Documentation

| File | Description |
|---|---|
| `docs/stage17/ARCHITECTURE.md` | Observability architecture |
| `docs/stage17/METRICS.md` | Metrics reference |
| `docs/stage17/LOGGING.md` | Structured logging spec |
| `docs/stage17/DASHBOARDS.md` | Dashboard descriptions |
| `docs/stage17/ALERTS.md` | Alert rules reference |
| `docs/stage17/DEPLOYMENT.md` | Deployment guide |
| `docs/stage17/STAGE17-EVIDENCE.md` | This file |

## 2. Architecture Diagram

```
Identity Service        Portal Backend          AI Platform
   /metrics                /metrics               /metrics
       │                      │                      │
       └──────────────────────┼──────────────────────┘
                              │
                     ┌────────▼────────┐
                     │   Prometheus    │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │    Grafana      │
                     │ (5 dashboards)  │
                     └─────────────────┘

All services → Structured JSON Logs → stdout → Fluent Bit → ES
```

## 3. Metrics Implemented

### Identity Service (metric prefix: `identity_`)

- `identity_http_requests_total` (method, endpoint, status_code) — Counter
- `identity_http_request_duration_seconds` (method, endpoint) — Histogram
- `identity_active_requests` — Gauge
- `identity_memory_usage_bytes` — Gauge
- `identity_active_users` — Gauge
- `identity_errors_total` (type) — Counter
- `identity_start_time_seconds` — Gauge

### Portal Backend (metric prefix: `portal_backend_`)

- `portal_backend_http_requests_total` (method, endpoint, status_code) — Counter
- `portal_backend_http_request_duration_seconds` (method, endpoint) — Histogram
- `portal_backend_active_requests` — Gauge
- `portal_backend_memory_usage_bytes` — Gauge
- `portal_backend_errors_total` (type) — Counter
- `portal_backend_uptime_seconds` — Gauge

### AI Platform

- `http_requests_total` (method, endpoint, status_code) — Counter
- `http_request_duration_seconds` (method, endpoint) — Histogram
- `active_requests` — Gauge
- `memory_usage_bytes` — Gauge
- `active_api_keys` — Gauge
- `active_conversations` — Gauge
- `gateway_requests_total` (status) — Counter
- `gateway_errors_total` (type) — Counter
- `errors_total` (type) — Counter
- `uptime` — Gauge

## 4. Logged Fields

All services emit structured JSON with these fields:

| Field | Required | Example |
|---|---|---|
| `timestamp` | ✅ | `2026-07-21T12:34:56.789+00:00` |
| `level` | ✅ | `INFO` |
| `service` | ✅ | `aither-identity` |
| `message` | ✅ | `Login: user='admin'` |
| `request_id` | when available | `abc123` |
| `user_id` | when available | `1` |
| `endpoint` | when available | `/v1/identity/auth` |
| `duration_ms` | when available | `12.34` |
| `status_code` | when available | `200` |

## 5. Dashboards

| Dashboard | Panels | Purpose |
|---|---|---|
| System Overview | 5 | Global service health |
| AI Platform | 6 | AI platform metrics |
| Gateway | 3 | Gateway health |
| Identity | 4 | Auth monitoring |
| Portal | 3 | Portal BFF monitoring |

## 6. Alert Rules

| Rule | Severity | Condition |
|---|---|---|
| ServiceDown | critical | `up == 0` for 1m |
| ReadinessCheckFailed | critical | `probe_success == 0` for 30s |
| HighErrorRate | warning | 5xx > 5% for 5m |
| HighLatency | warning | P95 > 5s for 5m |
| GatewayUnavailable | critical | Error rate > 10/s for 2m |
| PVCLowSpace | warning | Usage > 85% for 5m |
| HighMemoryUsage | warning | RSS > 500MB for 5m |

## 7. Test Results

### Static Syntax Checks

| Check | Result |
|---|---|
| `bash -n scripts/test-stage17-observability.sh` | ✅ PASS |
| `python3 -m py_compile services/identity/app/main.py` | ✅ PASS |
| `python3 -m py_compile services/portal-backend/app/main.py` | ✅ PASS |
| `python3 -m py_compile services/ai-platform/app/main.py` | ✅ PASS |
| `git diff --check` | ✅ CLEAN |

### Dashboard JSON Validation

| Dashboard | Result |
|---|---|
| `dashboard-system-overview.json` | ✅ Valid JSON |
| `dashboard-ai-platform.json` | ✅ Valid JSON |
| `dashboard-gateway.json` | ✅ Valid JSON |
| `dashboard-identity.json` | ✅ Valid JSON |
| `dashboard-portal.json` | ✅ Valid JSON |

### Alert Rules Validation

| Check | Result |
|---|---|
| `alert-rules.yaml` YAML valid | ✅ PASS |

### K8s Manifests Validation

| Manifest | Result |
|---|---|
| `servicemonitor.yaml` | ✅ PASS (kubectl validation) |
| `configmaps.yaml` | ✅ PASS (kubectl validation) |

### Regression: Existing Scripts

| Script | Result |
|---|---|
| `scripts/check-gateway-32b.sh` | ✅ PASS (unchanged) |
| `scripts/test-check-gateway-dns-policy.sh` | ✅ PASS (unchanged) |
| `scripts/test-gateway-32b-e2e.sh` | ✅ PASS (unchanged) |
| `scripts/scan-secrets.sh` | ✅ PASS (unchanged) |
| `scripts/bootstrap-admin.sh` | ✅ PASS (unchanged) |
| `scripts/test-stage15-acceptance.sh` | ✅ PASS (unchanged) |
| `scripts/test-stage16-acceptance.sh` | ✅ PASS (unchanged) |

### Runtime Tests

| Check | Result | Reason |
|---|---|---|
| `/metrics` endpoint reachable | 🔶 NOT RUN | Services not deployed to cluster |
| JSON log format verified | ✅ PASS (code review) | All services use JSONFormatter |
| Secrets absence in logs | ✅ PASS (code review) | No API key/password/token logging |

## 8. Security Confirmation

| Concern | Status | Evidence |
|---|---|---|
| API Key absent from logs | ✅ PASS | Code audit: no `log.*api_key\|api.key` in any service |
| Authorization header absent from logs | ✅ PASS | Code audit: no `log.*authorization\|bearer` in any service |
| Password absent from logs | ✅ PASS | Code audit: only username logged on failure |
| System prompt absent from logs | ✅ PASS | Code audit: no `log.*system_prompt` in any service |
| Full user messages in logs | ✅ PASS (default) | Logged only in explicit DEBUG mode |
| Stack traces returned to user | ✅ PASS | All errors wrapped in HTTPException |

## 9. Limitations

1. **Runtime metrics export** — NOT RUN: services not deployed to cluster. `/metrics` endpoints are implemented and verified at code level.
2. **Full SSE streaming** — NOT implemented: streaming in OpenAI endpoint is a placeholder. Real SSE parsing requires Gateway support.
3. **vLLM metrics** — NOT directly instrumented: vLLM exports its own metrics which can be scraped separately.
4. **nginx metrics** — requires `nginx-vts-exporter` or similar. Services have their own metrics already.
5. **Fluent Bit** — ConfigMap provided but requires operational deployment.
6. **Alert routing** — Alertmanager configuration not provided (site-specific).
7. **Existing business logic** — ✅ Unchanged. No Stage 15/16 endpoints, models, or data were modified.
