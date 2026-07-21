# Stage 18 — Runtime Validation Report

## Runtime Readiness Summary

| Service | Namespace | Service Exists | Deployment Exists | /health | /ready | /version | /metrics |
|---|---|---|---|---|---|---|---|
| Identity | `aither-inference` | ❌ | ❌ | — | — | — | — |
| Portal Backend | `aither-inference` | ❌ | ❌ | — | — | — | — |
| Portal Frontend | `aither-inference` | ❌ | ❌ | — | — | — | — |
| AI Platform | `aither-inference` | ❌ | ❌ | — | — | — | — |
| Gateway | `aither-inference` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| vLLM | `aither-inference` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**Note:** Stage 15–17 services were not deployed due to infrastructure constraints (Kubernetes API bandwidth limitations prevented large image transfers to cluster nodes). See BLOCKED status below.

## Gateway Runtime Verification

| Check | Endpoint | HTTP Status | Result |
|---|---|---|---|
| Gateway /healthz | `http://nginx-gateway-32b:8000/healthz` | 200 | ✅ Running |
| Gateway /v1/completions | `http://nginx-gateway-32b:8000/v1/completions` | 422 | ✅ Proxies to vLLM |

## vLLM Runtime Verification

| Check | Endpoint | HTTP Status |
|---|---|---|
| vLLM (32B) | `http://10.99.3.103:8000/health` | ✅ Running |
| vLLM (14B) | `http://10.108.67.57:8000/health` | ✅ Running |

## BLOCKED Items

### Deployment blocked — Kubernetes API bandwidth limitation

The connection between the build host and the Kubernetes API server (10.129.13.78:6443) has severe bandwidth constraints. Attempted transfer methods:

| Method | Result | Reason |
|---|---|---|
| `docker save \| ssh ctr import` | ❌ | SSH connection timeout on large data streams |
| `scp/rsync` | ❌ | Connection drops mid-transfer |
| `kubectl cp` | ❌ | API server i/o timeout on > 1MB transfers |
| `kubectl exec cat > file` | ❌ | Same timeout |
| Base64 chunked transfer (1MB chunks) | ⚠️ Some working | 1MB chunks transfer, but 54MB total would take ~30+ minutes per image |
| HTTP server + wget/curl | ❌ | No wget on nodes, curl also times out |

### Required fixes to enable deployment

1. Set up a container registry (Docker Registry v2, Harbor, or similar) reachable from cluster
2. Or improve network bandwidth between build host and cluster nodes
3. Or build images directly on cluster nodes

## What Would Be Validated

If deployment were possible, the following would be verified:

1. Identity `/health`, `/ready`, `/version`, `/metrics`
2. Portal Backend `/health`, `/ready`, `/version`, `/metrics`
3. AI Platform `/health`, `/ready`, `/version`, `/metrics`
4. Portal Frontend HTTP 200 on `/`
5. Login flow: Portal Frontend → Portal Backend → Identity
6. AI conversation: Portal → AI Platform → Gateway → vLLM
7. Prometheus metrics export
8. Acceptance tests (`scripts/test-stage16-acceptance.sh`, `scripts/test-stage17-observability.sh`)
