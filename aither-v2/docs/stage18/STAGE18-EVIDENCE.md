# Stage 18 — Runtime Deployment Evidence

## 1. Preflight

| Check | Value |
|---|---|
| HEAD | `709940f5c7fd37f2b3c26018f578c092858acbfc` |
| Branch | `aither-v2` |
| Working tree | Clean |
| Nodes | 2 (n7-gpu: Ready, n8-control-plane: Ready) |
| Cluster version | v1.33.13 |
| Container runtime | containerd 2.2.1 |
| Existing services | Gateway + vLLM + Redis (legacy) |

## 2. Docker Images Built

| Image | Tag | Size | Status |
|---|---|---|---|
| `aither-identity` | `stage15` | 232MB | ✅ Built |
| `aither-portal-backend` | `stage15` | 229MB | ✅ Built |
| `aither-ai-platform` | `stage16` | 231MB | ✅ Built |
| (Portal Frontend) | — | nginx:stable-alpine | ✅ Docker Hub |

## 3. Image Transfer to Cluster Nodes

| Image | n8 (control-plane) | n7 (gpu) | Method |
|---|---|---|---|
| `aither-identity:stage15` | 🔶 BLOCKED | 🔶 BLOCKED | SSH/K8s API timeout |
| `aither-portal-backend:stage15` | 🔶 BLOCKED | 🔶 BLOCKED | Same |
| `aither-ai-platform:stage16` | 🔶 BLOCKED | 🔶 BLOCKED | Same |

**Root Cause:** Severe network bandwidth limitation between build host (10.129.100.0/24) and cluster nodes (10.129.13.0/24). Kubernetes API server consistently times out on data transfers exceeding ~1MB. SSH connections also drop on large streams (>10MB).

## 4. Runtime Health

### Gateway (nginx) — verified from cluster

| Endpoint | Method | HTTP | Result |
|---|---|---|---|
| `http://nginx-gateway-32b:8000/healthz` | GET | 200 | ✅ Running |
| `http://nginx-gateway-32b:8000/v1/chat/completions` | GET | 422 | ✅ Proxies |
| `http://nginx-gateway-32b:8000/v1/completions` | GET | 400 | ✅ Proxies to vLLM |

### vLLM — verified

| Pod | Model | Ready | Metrics |
|---|---|---|---|
| `vllm-32b-gptq` | qwen-32b-4bit | ✅ 1/1 | ✅ built-in /metrics |
| `vllm-14b-instruct` | qwen-14b | ✅ 1/1 | ✅ built-in /metrics |

### Stage 15–17 Services

All BLOCKED — not deployed due to image transfer constraints.

## 5. Runtime Metrics

| Service | /metrics URL | HTTP | Result |
|---|---|---|---|
| Identity | `http://aither-identity:8000/metrics` | — | 🔶 BLOCKED |
| Portal Backend | `http://aither-portal-backend:8080/metrics` | — | 🔶 BLOCKED |
| AI Platform | `http://aither-ai-platform:8100/metrics` | — | 🔶 BLOCKED |
| Gateway | `http://nginx-gateway-32b:8000/metrics` | — | ❌ No endpoint (needs exporter) |

All /metrics endpoints verified at code level (Stage 17).

## 6. Prometheus

| Check | Status | Reason |
|---|---|---|
| kube-prometheus-stack installed? | ❌ | Not deployed in cluster |
| ServiceMonitor CRD exists? | ❌ | monitoring.coreos.com not installed |
| Targets UP? | — | N/A |
| Rules loaded? | — | N/A |

## 7. Grafana

| Check | Status | Reason |
|---|---|---|
| Grafana deployed? | ❌ | Not installed |
| Dashboards imported? | — | N/A |
| Datasource configured? | — | N/A |

Dashboard JSON files are prepared in `docs/stage17/grafana/` — 5 dashboards validated as valid JSON.

## 8. AI Runtime Verification (Chat)

| Step | Status | Reason |
|---|---|---|
| Identity Login | 🔶 BLOCKED | Identity service not deployed |
| Portal Backend proxy | 🔶 BLOCKED | Portal Backend not deployed |
| AI Platform → Gateway → vLLM | 🔶 BLOCKED | AI Platform not deployed |
| End-to-end chat | 🔶 BLOCKED | Core services not deployed |

Gateway → vLLM pipeline is independently verified as operational (existing pods).

## 9. Acceptance Tests

| Test Script | Result | Reason |
|---|---|---|
| `scripts/test-stage16-acceptance.sh` | 🔶 NOT RUN | Services not deployed |
| `scripts/test-stage17-observability.sh` | 🔶 NOT RUN | Services not deployed |
| Syntax check (bash -n) | ✅ PASS | Both scripts |
| Python compile (3 apps) | ✅ PASS | All 3 services |

## 10. Security Verification

| Concern | Method | Result |
|---|---|---|
| API Keys absent from logs | Code audit | ✅ PASS |
| Bearer Tokens absent from logs | Code audit | ✅ PASS |
| Passwords absent from logs | Code audit | ✅ PASS |
| CORS matches documentation | Code audit | ✅ PASS (Stage 17B fixed contradictions) |
| `/metrics` exposes sensitive data | Code audit | ✅ PASS |
| Secrets not in Git | Verification | ✅ PASS |

## 11. Regression

| Check | Result |
|---|---|
| `bash -n deploy/*.sh` (5 scripts) | ✅ ALL PASS |
| `bash -n scripts/*.sh` (8 scripts) | ✅ ALL PASS |
| `python3 -m py_compile` (3 apps) | ✅ ALL PASS |
| `git diff --check` | ✅ CLEAN |

## 12. Remaining Limitations

1. **🔶 Stage 15–17 services not deployed** — Blocked by Kubernetes API bandwidth limitation. Requires registry setup or network improvement.
2. **🔶 Prometheus + Grafana not installed** — Must be deployed separately (kube-prometheus-stack).
3. **🔶 NGINX Gateway lacks /metrics** — Needs `nginx-vts-exporter` or `prometheus-nginx-exporter` sidecar.
4. **🔶 Acceptance tests not executed** — Require running services.
5. **🔶 AI conversation not verified end-to-end** — Require Identity + AI Platform deployment.
6. **✅ All code artifacts prepared** — Images built, manifests correct, documentation complete, static checks pass.
