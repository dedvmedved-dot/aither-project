# Stage 17 — Observability Architecture

## Overview

Stage 17 adds a comprehensive observability layer to Aither / AI Hermes MVP without modifying existing business logic. The observability stack consists of:

- **Prometheus** — Metrics collection and alerting
- **Grafana** — Dashboard visualization
- **Structured JSON logging** — All services emit structured logs
- **Fluent Bit** — Log aggregation (optional, via ConfigMap)

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Monitoring Stack                        │
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────────┐   │
│  │ Identity  │    │ Portal   │    │ AI Platform          │   │
│  │ Service   │    │ Backend  │    │ Service              │   │
│  │ :8000     │    │ :8080    │    │ :8100                │   │
│  │ /metrics  │    │ /metrics │    │ /metrics             │   │
│  └────┬─────┘    └────┬─────┘    └─────────┬────────────┘   │
│       │               │                     │                │
│       └───────────────┼─────────────────────┘                │
│                       │                                      │
│              ┌────────▼────────┐                             │
│              │   Prometheus    │                             │
│              │   (kube-prom)   │                             │
│              └────────┬────────┘                             │
│                       │                                      │
│              ┌────────▼────────┐    ┌──────────────────┐    │
│              │    Grafana      │    │  Alertmanager    │    │
│              │  (dashboards)   │    │  (alerts)        │    │
│              └─────────────────┘    └──────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Structured JSON Logs (stdout → Fluent Bit → ES)     │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Components Instrumented

| Service | Metrics | JSON Logs | Dashboard | Alerts |
|---|---|---|---|---|
| Identity Service | ✅ | ✅ | ✅ | ✅ |
| Portal Backend (BFF) | ✅ | ✅ | ✅ | ✅ |
| AI Platform | ✅ | ✅ | ✅ | ✅ |
| Gateway (nginx-gateway-32b) | ✅ (via nginx_exporter) | ✅ | ✅ | ✅ |
| vLLM (inference) | ✅ (via vLLM built-in) | ✅ | ✅ | ✅ |

## Data Flow

1. Each service exports `/metrics` on its HTTP port
2. Prometheus scrapes via `ServiceMonitor` (15s interval)
3. Alerts evaluated in Prometheus against configured rules
4. Grafana visualizes metrics from 5 dashboards
5. Structured logs go to stdout, aggregated via Fluent Bit

## Manifests

- `docs/stage17/k8s/servicemonitor.yaml` — ServiceMonitor + PrometheusRule
- `docs/stage17/k8s/configmaps.yaml` — Grafana dashboards, Prometheus rules, Fluent Bit config
