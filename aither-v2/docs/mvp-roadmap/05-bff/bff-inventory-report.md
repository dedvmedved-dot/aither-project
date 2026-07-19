# BFF Inventory Report

Date: 2026-07-20 (Stage 05 Corrective 2 — status code propagation)
Executor: hermes@vps2
Repository branch: aither-v2
Commit: (this corrective commit)

## 1. Repository inventory

### tools/bff/ (source of truth)

| File | Description |
|---|---|
| tools/bff/app.py | FastAPI BFF application (Python) — status code propagation fix applied |
| tools/bff/Dockerfile | Docker build for BFF image |
| tools/bff/requirements.txt | Python dependencies |
| tools/bff/README.md | Documentation |

### manifests/mvp-roadmap/05-bff/

| File | Description |
|---|---|
| bff-mvp.yaml | Deployment + ConfigMap (with status code fix) + Service |

### docs/mvp-roadmap/05-bff/

| File | Description |
|---|---|
| bff-acceptance-report.md | Acceptance report with evidence |
| bff-routing-policy.md | Routing policy document |
| bff-security-notes.md | Security assessment (with status code propagation info) |
| bff-inventory-report.md | This inventory |
| evidence/ | 15 evidence files |
| logs/ | Runtime logs directory |

## 2. Kubernetes inventory

| Resource | Name | Detail |
|---|---|---|
| ConfigMap | aither-bff-config | app.py with Response(status_code=...) fix |
| Deployment | aither-bff | python:3.11-slim, 1 replica, ClusterIP |
| Service | aither-bff | ClusterIP :8000 |

## 3. BFF routing

| Route | Method | Status Code | Forwarded? |
|---|---|---|---|
| /health | GET | 200 | — |
| /api/v1/chat model=14b | POST | Upstream code (401 if no auth) | ✅ |
| /api/v1/chat model=32b | POST | 422 (blocked) | — |
| /api/v1/chat unknown | POST | 400 (blocked) | — |
| /api/v1/completions model=14b | POST | Upstream code (401 if no auth) | ✅ |
| /api/v1/completions model=32b | POST | Upstream code (401 if no auth) | ✅ via gateway |
| /api/v1/completions unknown | POST | 400 (blocked) | — |
| /api/v1/models | GET | 200 | — |

## 4. Status code propagation (Corrective 2)

Before fix (commit 0a2340f):
- 14B chat no auth → **HTTP 200** {"error":"Unauthorized"} ← wrong!
- 32B completion no auth → **HTTP 200** {"error":"auth required"} ← wrong!

After fix:
- 14B chat no auth → **HTTP 401** {"error":"Unauthorized"} ✅
- 32B completion no auth → **HTTP 401** {"error":"auth required"} ✅

Fix: changed `return await resp.aread()` to `return Response(content=..., status_code=resp.status_code, ...)`

## 5. Risks

- BFF chat 14B returns 401 when no auth (correct behaviour, but requires client to send API key)
- Valid token test for 32B completion not collected (VPN instability)
- No rate limiting (postponed to Stage 06)
- No NetworkPolicy (postponed to Stage 08)
- BFF is MVP-level, not production-hardened
