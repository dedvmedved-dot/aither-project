# Stage 17 — Metrics Reference

## Service Metrics

### Identity Service (prefix: `identity_`)

| Metric | Type | Labels | Description |
|---|---|---|---|
| `identity_start_time_seconds` | Gauge | — | Unix timestamp of service start |
| `identity_http_requests_total` | Counter | method, endpoint, status_code | Total HTTP requests |
| `identity_http_request_duration_seconds` | Histogram | method, endpoint | Request latency |
| `identity_active_requests` | Gauge | — | Currently in-flight requests |
| `identity_memory_usage_bytes` | Gauge | — | Process RSS memory |
| `identity_active_users` | Gauge | — | Non-revoked sessions |
| `identity_errors_total` | Counter | type | Errors by type |

### Portal Backend (prefix: `portal_backend_`)

| Metric | Type | Labels | Description |
|---|---|---|---|
| `portal_backend_uptime_seconds` | Gauge | — | Service uptime |
| `portal_backend_http_requests_total` | Counter | method, endpoint, status_code | Total HTTP requests |
| `portal_backend_http_request_duration_seconds` | Histogram | method, endpoint | Request latency |
| `portal_backend_active_requests` | Gauge | — | Currently in-flight requests |
| `portal_backend_memory_usage_bytes` | Gauge | — | Process RSS memory |
| `portal_backend_errors_total` | Counter | type | Errors by type |

### AI Platform

| Metric | Type | Labels | Description |
|---|---|---|---|
| `uptime` | Gauge | — | Service uptime in seconds |
| `memory_usage_bytes` | Gauge | — | Process RSS memory |
| `active_requests` | Gauge | — | Currently in-flight requests |
| `active_api_keys` | Gauge | — | Non-revoked API keys |
| `active_conversations` | Gauge | — | Total conversations |
| `http_requests_total` | Counter | method, endpoint, status_code | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | method, endpoint | Request latency |
| `gateway_requests_total` | Counter | status | Gateway proxy requests |
| `gateway_errors_total` | Counter | type | Gateway errors by type |
| `errors_total` | Counter | type | Application errors by type |

## Kubernetes Metrics

The kube-prometheus stack also provides:

| Metric | Description |
|---|---|
| `up{service="..."}` | Service health/readiness |
| `kubelet_volume_stats_*` | PVC capacity/usage |

## Metric Naming Conventions

- Metrics follow Prometheus naming best practices
- Units in metric name where applicable (`_seconds`, `_bytes`, `_total`)
- Label cardinality limited by normalizing endpoint paths
