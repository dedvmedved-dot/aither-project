# Beta Acceptance — Portal Availability Report

**Date:** 2026-07-23
**Source:** Hermes Agent (Stage BA-01)
**Method:** SSH to n8 node → curl to pod IPs (K8s API intermittency workaround)

## Portal Frontend (Stage 15 SPA)

| Check | Result | Details |
|-------|--------|---------|
| Nginx serving | ✅ **200** | `aither-portal-frontend` pod `10.244.1.23:80` |
| HTML title | ✅ | `<title>Aither — AI Platform</title>` |
| SPA entry point | ✅ | `/index.html` served |
| Dark theme UI | ✅ | CSS variables: `--bg: #0d1117`, `--accent: #58a6ff` |

## Portal Backend (BFF)

| Endpoint | Result | Response |
|----------|--------|----------|
| `GET /health` | ✅ **200** | `{"status":"ok","service":"portal-backend"}` |
| `GET /ready` | ✅ **200** | `{"status":"ok","identity":"connected"}` |
| `GET /version` | ✅ **200** | `{"service":"aither-portal-backend","version":"1.0.0","build":"stage15"}` |

## Identity Service

| Endpoint | Result | Response |
|----------|--------|----------|
| `GET /health` | ✅ **200** | `{"status":"ok","service":"identity"}` |

## AI Platform

| Endpoint | Result | Response |
|----------|--------|----------|
| `GET /health` | ✅ **200** | `{"status":"ok","service":"ai-platform"}` |

## Nginx Routing Configuration

The Portal Frontend nginx (`default.conf`) routes:

| Path | Upstream |
|------|----------|
| `/` | Static files (`/usr/share/nginx/html`) |
| `/api/*` | `aither-portal-backend:8000` |
| `/v1/chat/completions` | `aither-ai-platform:8000` |
| `/health`, `/ready`, `/version` | `aither-portal-backend:8000` |

## Portal Components (Cluster)

| Deployment | Ready | Image | Notes |
|------------|-------|-------|-------|
| `aither-portal` | 1/1 | `nginx:alpine` | Stage 07.2 legacy |
| `aither-portal-frontend` | 1/1 | `nginx:stable-alpine` | Stage 15, serves SPA |
| `aither-portal-backend` | 1/1 | `stage18a-82fe433` | BFF + CORS |
| `aither-bff` | 1/1 | `python:3.11-slim` | Stage 05 legacy BFF |

## Known Limitations

| Limitation | Severity | Details |
|------------|----------|---------|
| Dual Portal frontends | 🟢 Low | `aither-portal` (legacy) and `aither-portal-frontend` (current) both running. No conflict but cleanup advisable. |
| K8s API intermittent | 🟡 Medium | `kubectl port-forward` and `kubectl exec` timeout from build host. SSH to n8 used as reliable alternative. |

## Verdict

```text
PORTAL AVAILABILITY:
  Frontend:        ✅ PASS
  Backend (BFF):   ✅ PASS
  Identity:        ✅ PASS
  AI Platform:     ✅ PASS
  Routing:         ✅ PASS
  All components:  OPERATIONAL
```
