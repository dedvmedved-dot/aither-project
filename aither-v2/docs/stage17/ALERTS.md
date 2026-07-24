# Stage 17 — Alert Rules

## Rule Files

Alert rules are defined in:
- `docs/stage17/prometheus/alert-rules.yaml` — PrometheusRule format
- `docs/stage17/k8s/servicemonitor.yaml` — PrometheusRule K8s resource

## Alert Rules

### Service Availability

| Alert Name | Severity | Condition | For | Description |
|---|---|---|---|---|
| `ServiceDown` | **critical** | `up == 0` | 1m | Service is unreachable |
| `ReadinessCheckFailed` | **critical** | `probe_success == 0` | 30s | Readiness probe failing |

### Error Rate

| Alert Name | Severity | Condition | For | Description |
|---|---|---|---|---|
| `HighErrorRate` | warning | 5xx rate > 5% of total | 5m | Elevated HTTP error rate |

### Latency

| Alert Name | Severity | Condition | For | Description |
|---|---|---|---|---|
| `HighLatency` | warning | P95 > 5s | 5m | High request latency |

### Gateway

| Alert Name | Severity | Condition | For | Description |
|---|---|---|---|---|
| `GatewayUnavailable` | **critical** | Gateway errors > 10/s | 2m | Inference Gateway failing |

### Storage

| Alert Name | Severity | Condition | For | Description |
|---|---|---|---|---|
| `PVCLowSpace` | warning | PVC usage > 85% | 5m | Persistent volume running low |

### Memory

| Alert Name | Severity | Condition | For | Description |
|---|---|---|---|---|
| `HighMemoryUsage` | warning | RSS > 500 MB | 5m | Service memory threshold exceeded |

## Alert Groups

| Group | Purpose |
|---|---|
| `aither-service-availability` | Core service health |
| `aither-error-rate` | HTTP error monitoring |
| `aither-latency` | Performance degradation |
| `aither-gateway` | Inference pipeline health |
| `aither-storage` | Disk capacity |
| `aither-memory` | Resource exhaustion |

## Deployment

Apply via:
```bash
kubectl apply -f docs/stage17/k8s/servicemonitor.yaml
```

Or export individual rules:
```bash
kubectl apply -f docs/stage17/prometheus/alert-rules.yaml
```
