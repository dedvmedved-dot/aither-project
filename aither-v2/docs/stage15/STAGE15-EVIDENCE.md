# Aither / AI Hermes MVP
# Stage 15 — User Portal & Identity — Evidence Document

## Overview

Stage 15 implements the first user-facing web portal and identity foundation
for Aither / AI Hermes MVP.

## Components Created

| Component | Location | Technology |
|---|---|---|
| **Identity Service** | `services/identity/` | Python FastAPI + SQLite + bcrypt |
| **Portal Backend (BFF)** | `services/portal-backend/` | Python FastAPI (proxying layer) |
| **Portal Frontend** | `services/portal-frontend/` | Nginx + HTML/CSS/JS SPA |

## New API Endpoints

### Identity Service (10 endpoints)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | No | Health check |
| GET | `/ready` | No | Readiness + DB check |
| GET | `/version` | No | Version info |
| POST | `/v1/identity/bootstrap` | No | Create initial admin (one-shot) |
| POST | `/v1/identity/auth` | No | Login |
| POST | `/v1/identity/logout` | Bearer | Logout (revoke token) |
| GET | `/v1/identity/me` | Bearer | Current user info |
| GET | `/v1/identity/users` | Admin | List all users |
| POST | `/v1/identity/users` | Admin | Create user |
| GET | `/v1/identity/status` | No | Service status |

### Portal Backend (6 endpoints)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | No | Health check |
| GET | `/ready` | No | Readiness check |
| GET | `/version` | No | Version info |
| POST | `/api/v1/auth/login` | No | Login (proxied) |
| POST | `/api/v1/auth/logout` | Bearer | Logout (proxied) |
| GET | `/api/v1/auth/me` | Bearer | Current user (proxied) |
| GET | `/api/v1/status` | No | Aggregated status |

## Files Created

### Services

| File | Description |
|---|---|
| `services/identity/app/main.py` | Identity service implementation |
| `services/identity/requirements.txt` | Python dependencies |
| `services/identity/Dockerfile` | Container build |
| `services/identity/k8s/identity.yaml` | K8s Secret, Deployment, Service |
| `services/portal-backend/app/main.py` | Portal Backend implementation |
| `services/portal-backend/requirements.txt` | Python dependencies |
| `services/portal-backend/Dockerfile` | Container build |
| `services/portal-backend/k8s/portal-backend.yaml` | K8s Deployment, Service |
| `services/portal-frontend/index.html` | SPA entry point |
| `services/portal-frontend/styles.css` | SPA styles |
| `services/portal-frontend/app.js` | SPA application logic |
| `services/portal-frontend/nginx.conf` | Nginx reverse proxy config |
| `services/portal-frontend/Dockerfile` | Container build |
| `services/portal-frontend/k8s/portal-frontend.yaml` | K8s ConfigMap, Deployment, Service |

### Scripts

| File | Description |
|---|---|
| `scripts/bootstrap-admin.sh` | First admin creation (bcrypt + API call) |
| `scripts/test-stage15-acceptance.sh` | Acceptance tests (9 checks) |

### Documentation

| File | Description |
|---|---|
| `docs/stage15/PORTAL.md` | Portal architecture and components |
| `docs/stage15/AUTH.md` | Authentication, roles, security model |
| `docs/stage15/API.md` | Complete REST API reference |
| `docs/stage15/STAGE15-EVIDENCE.md` | This evidence document |

## K8s Resources Added

All in namespace `aither-inference`:

| Resource | Name |
|---|---|
| Secret | `aither-identity-secret` |
| Deployment | `aither-identity` |
| Service | `aither-identity` |
| Deployment | `aither-portal-backend` |
| Service | `aither-portal-backend` |
| ConfigMap | `aither-portal-frontend-config` |
| Deployment | `aither-portal-frontend` |
| Service | `aither-portal-frontend` |

## Script Verification

| Check | Result |
|---|---|
| `bash -n scripts/bootstrap-admin.sh` | ✅ PASS |
| `bash -n scripts/test-stage15-acceptance.sh` | ✅ PASS |
| `python3 -m py_compile services/identity/app/main.py` | ✅ PASS |
| `python3 -m py_compile services/portal-backend/app/main.py` | ✅ PASS |
| K8s YAML validation (pyyaml safe_load_all) | ✅ 8/8 documents valid |

## Existing Project Impact

| Aspect | Status |
|---|---|
| Gateway runtime | ✅ **UNCHANGED** |
| Inference pipeline (vLLM) | ✅ **UNCHANGED** |
| Existing K8s manifests | ✅ **UNCHANGED** (new resources only) |
| Existing acceptance tests | ✅ **UNCHANGED** |
| Existing scripts | ✅ **UNCHANGED** |
| Stage 14 deploy framework | ✅ **COMPATIBLE** — deploy/deploy.sh can be extended to include new manifests |

## Compatibility with Stage 14

The new services follow the same conventions as existing MVP manifests:
- Namespace: `aither-inference`
- Labels: `app`, `stage`
- Health/readiness probes
- Resource limits
- No `automountServiceAccountToken`

To include Stage 15 services in the automated deployment, add to
`deploy/30-services.sh`:

```bash
apply_manifest "${PROJECT_ROOT}/services/identity/k8s/identity.yaml" "Identity Service"
apply_manifest "${PROJECT_ROOT}/services/portal-backend/k8s/portal-backend.yaml" "Portal Backend"
apply_manifest "${PROJECT_ROOT}/services/portal-frontend/k8s/portal-frontend.yaml" "Portal Frontend"
```

And add identity readiness check to `deploy/40-validation.sh`.

## Security

- Passwords stored as bcrypt hashes (12 rounds)
- No plaintext passwords in logs
- `automountServiceAccountToken: false` on all pods
- Token-based authentication (Bearer scheme)
- Session tracking with revocation support
- Bootstrap one-shot protection
- Secrets managed via Kubernetes Secrets (REPLACE_ME placeholders, not real values)
