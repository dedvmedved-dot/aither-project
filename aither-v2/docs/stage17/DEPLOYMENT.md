# Stage 17 — Deployment Guide

## Prerequisites

- Kubernetes cluster with Prometheus Operator (kube-prometheus-stack)
  - `ServiceMonitor` CRD
  - `PrometheusRule` CRD
  - Grafana with sidecar dashboard loader (optional)
- Services from Stage 15–16 deployed (Identity, Portal Backend, AI Platform) in namespace `aither-inference`

## Deployment Steps

### 1. Apply ServiceMonitor

```bash
kubectl apply -f docs/stage17/k8s/servicemonitor.yaml
```

This creates:
- `aither-stage17-services` ServiceMonitor — scrapes Stage 15–17 services (`app` label values: `aither-identity`, `aither-portal-backend`, `aither-ai-platform`, `aither-portal-frontend`) in namespace `aither-inference`

### 2. Apply ConfigMaps

```bash
kubectl apply -f docs/stage17/k8s/configmaps.yaml
```

This creates 3 ConfigMaps in namespace `aither-inference`:
- `aither-grafana-dashboards` — 5 dashboard JSON files (auto-provisioned via Grafana sidecar)
- `aither-prometheus-rules` — Alert rules in YAML format
- `aither-fluentbit-config` — Fluent Bit log aggregation config

### 3. Update Grafana Datasource

Ensure Grafana has a Prometheus datasource named `Prometheus` that points to the cluster's Prometheus server. This is typically configured during kube-prometheus-stack installation.

### 4. Verify Metrics Export

```bash
# Forward a service port (assuming identity is deployed)
kubectl port-forward -n aither-inference svc/aither-identity 8000:8000
# Verify metrics
curl http://localhost:8000/metrics | head -20
```

### 5. Verify Alerts

Alert rules are deployed via the ConfigMap `aither-prometheus-rules`. Apply them as a PrometheusRule when Prometheus operator is available:

```bash
kubectl apply -f docs/stage17/prometheus/alert-rules.yaml
```

### 6. Verify Dashboards

Check Grafana UI → Dashboards → "Aither — *" should appear (requires Grafana sidecar dashboard reloader reading the `aither-grafana-dashboards` ConfigMap).

## Rollback

```bash
kubectl delete -f docs/stage17/k8s/servicemonitor.yaml
kubectl delete -f docs/stage17/k8s/configmaps.yaml
```

This removes all observability resources without affecting service deployments.

## Manual Prerequisites

1. Prometheus Operator stack must be installed in the cluster
2. Grafana configured with Prometheus datasource
3. Grafana sidecar dashboard reloader enabled (if using ConfigMap method)
4. Fluent Bit or equivalent log shipper configured (optional)
