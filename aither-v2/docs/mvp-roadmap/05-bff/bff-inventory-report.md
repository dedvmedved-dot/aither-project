# BFF Inventory Report

Date: 2026-07-20 (Stage 05 Corrective)
Executor: hermes@vps2
Repository branch: aither-v2
Commit: (this corrective commit)

## 1. Repository inventory

### tools/bff/ (source of truth)

| File | Description |
|---|---|
| tools/bff/app.py | FastAPI BFF application (Python) |
| tools/bff/Dockerfile | Docker build for BFF image |
| tools/bff/requirements.txt | Python dependencies |
| tools/bff/README.md | Documentation |

### manifests/mvp-roadmap/05-bff/

| File | Description |
|---|---|
| bff-mvp.yaml | Deployment + ConfigMap + Service (single file) |

### docs/mvp-roadmap/05-bff/

| File | Description |
|---|---|
| bff-acceptance-report.md | Acceptance report with evidence |
| bff-routing-policy.md | Routing policy document |
| bff-security-notes.md | Security assessment |
| bff-inventory-report.md | This inventory |
| evidence/*.txt / *.yaml | Evidence files (14 files total) |
| logs/ | Runtime logs directory |

## 2. Kubernetes inventory

### aither-inference namespace

| Resource | Name | Detail |
|---|---|---|
| ConfigMap | aither-bff-config | app.py embedded as ConfigMap data |
| Deployment | aither-bff | python:3.11-slim, 1 replica, ClusterIP |
| Service | aither-bff | ClusterIP :8000, selector app=aither-bff |

### Runtime state (as of 2026-07-20 02:30 MSK)

| Resource | Value |
|---|---|
| Pod name | aither-bff-5798d78b86-8jlsf |
| Status | 1/1 Running, 0 restarts |
| Image | python:3.11-slim |
| Command | pip install --user + exec python /app/app.py |
| Service ClusterIP | 10.106.87.155:8000 |

## 3. BFF routing

| Route | Method | Status |
|---|---|---|
| /health | GET | 200 (local) |
| /api/v1/chat model=14b | POST | 200 (→ vllm-14b-instruct) |
| /api/v1/chat model=32b | POST | 422 (blocked) |
| /api/v1/chat unknown | POST | 400 (blocked) |
| /api/v1/completions model=14b | POST | 200 (→ vllm-14b-instruct) |
| /api/v1/completions model=32b | POST | 200 (→ nginx-gateway-32b) |
| /api/v1/completions unknown | POST | 400 (blocked) |
| /api/v1/models | GET | 200 (static) |

## 4. Key changes from original deployment

| Aspect | Previous (commit 2ab4485) | Current |
|---|---|---|
| Implementation | Mixed: app.py (FastAPI) + nginx:alpine deployment | FastAPI only, consistent app.py = deployment |
| Deployment image | python:3.11-slim with pip install (existing) | python:3.11-slim with pip install **--user** |
| Root cause of CrashLoopBackOff | pip install as runAsUser=1000 without --user flag | Fixed with HOME=/tmp + --user |
| nginx:alpine | Referenced in outdated docs | Never was the actual deployment |
| Evidence | Minimal | 14 evidence files with test results |
| Routing policy | Described as "nginx reverse proxy" | Updated to FastAPI routing |

## 5. Risks

- BFF chat 14B returns 200 but upstream returns 401 (no auth token forwarded by default).
- 32B completion valid token test not collected (VPN instability).
- No rate limiting (postponed to Stage 06).
- No NetworkPolicy (postponed to Stage 08).
- BFF is MVP-level, not production-hardened.
