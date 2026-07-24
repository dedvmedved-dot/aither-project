# Stage 17 — Grafana Dashboards

## Dashboard Files

All dashboards are in `docs/stage17/grafana/` as JSON export files compatible with Grafana v8+.

| File | Title | Description |
|---|---|---|
| `dashboard-system-overview.json` | Aither — System Overview | Global view of all services |
| `dashboard-ai-platform.json` | Aither — AI Platform | AI-specific metrics and Gateway |
| `dashboard-gateway.json` | Aither — Gateway | Gateway request/error monitoring |
| `dashboard-identity.json` | Aither — Identity | Auth metrics and active users |
| `dashboard-portal.json` | Aither — Portal | Portal BFF metrics |

## Dashboard: System Overview

Panels:
1. **Service Uptime** — Stat panel showing all service uptime
2. **HTTP Requests Rate** — Requests per second by service
3. **HTTP Error Rate (5xx)** — Error rate by service
4. **P95 Latency (ms)** — Latency percentile by service
5. **Memory Usage (MB)** — RSS by service

## Dashboard: AI Platform

Panels:
1. **Active API Keys** — Stat gauge
2. **Active Conversations** — Stat gauge
3. **Gateway Requests Rate** — Requests per second to inference
4. **Gateway Error Rate** — Errors per second
5. **Request Latency (ms)** — P95/P50 latency
6. **HTTP Errors by Type** — Error breakdown

## Dashboard: Gateway

Panels:
1. **Request Rate** — Requests per second by status
2. **Error Rate** — Error requests per second
3. **Active Requests** — Current in-flight count

## Dashboard: Identity

Panels:
1. **Active Users** — Non-revoked sessions
2. **Request Rate** — Requests per second by endpoint
3. **Latency (ms)** — P95/P50 latency
4. **Login Errors** — Failed login rate

## Dashboard: Portal

Panels:
1. **Request Rate** — Requests per second by endpoint
2. **Latency (ms)** — P95/P50 latency
3. **HTTP Status Codes** — Response code breakdown

## Deployment

Dashboards can be deployed via:
1. **Grafana UI** — Import JSON file manually
2. **ConfigMap** — `docs/stage17/k8s/configmaps.yaml` (Grafana sidecar auto-provisioning)
3. **Grafana API** — `POST /api/dashboards/db`

### ConfigMap-based deployment

The `aither-grafana-dashboards` ConfigMap in `docs/stage17/k8s/configmaps.yaml` contains all 5 dashboards. When used with the Grafana sidecar dashboard reloader, dashboards appear automatically.
