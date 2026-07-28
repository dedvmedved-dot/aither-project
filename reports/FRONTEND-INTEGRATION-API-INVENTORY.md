# FRONTEND INTEGRATION — API INVENTORY

**Created:** 2026-07-28T09:57:00Z
**Commit:** ef41e0e
**Status:** Phase 1

## Inventory Summary

| Category | Endpoints | Tested | Partial | Missing |
|----------|-----------|--------|---------|---------|
| Auth | 3 | 3 | 0 | 0 |
| Models | 2 | 2 | 0 | 0 |
| Chat | 2 | 2 | 0 | 0 |
| API Keys | 3 | 3 | 0 | 0 |
| Conversations | 5 | 0 | 0 | 5 |
| Admin (Gateway) | 5 | 0 | 0 | 5 |
| Billing/Usage | 0 | 0 | 0 | 7 |
| RAG | 5 | 0 | 0 | 5 |
| Monitoring | 0 | 0 | 0 | 5 |
| **TOTAL** | **25** | **10** | **0** | **22** |

---

## Endpoint Details

### Auth

| # | Method | Path | Service | Auth | Role | Status |
|---|--------|------|---------|------|------|--------|
| 1 | POST | /api/v1/auth/login | Portal Backend | Bearer JWT | any | EXISTS AND TESTED |
| 2 | POST | /api/v1/auth/logout | Portal Backend | Bearer JWT | any | EXISTS AND TESTED |
| 3 | GET | /api/v1/auth/me | Portal Backend → Identity | Bearer JWT | any | EXISTS AND TESTED |

### Models

| # | Method | Path | Service | Auth | Role | Status |
|---|--------|------|---------|------|------|--------|
| 4 | GET | /api/v1/models | Portal Backend → Gateway | Bearer JWT | any | EXISTS AND TESTED |
| 5 | GET | /v1/models | Gateway | API Key / JWT | any | EXISTS AND TESTED |

### Chat

| # | Method | Path | Service | Auth | Role | Status |
|---|--------|------|---------|------|------|--------|
| 6 | POST | /api/v1/chat | Portal Backend → Gateway | Bearer JWT | any | EXISTS AND TESTED |
| 7 | POST | /v1/chat/completions | Gateway → vLLM | API Key | any | EXISTS AND TESTED |

### API Keys

| # | Method | Path | Service | Auth | Role | Status |
|---|--------|------|---------|------|------|--------|
| 8 | GET | /api/v1/tokens | Portal Backend → Gateway | Bearer JWT | any | EXISTS AND TESTED |
| 9 | POST | /api/v1/tokens | Portal Backend → Gateway | Bearer JWT | any | EXISTS AND TESTED |
| 10 | DELETE | /api/v1/tokens/{id} | Portal Backend → Gateway | Bearer JWT | any | EXISTS AND TESTED |

### Conversations (proxy to AI Platform)

| # | Method | Path | Service | Auth | Role | Status |
|---|--------|------|---------|------|------|--------|
| 11 | GET | /api/v1/conversations | Portal Backend → AI Platform | Bearer JWT | any | EXISTS NOT TESTED |
| 12 | POST | /api/v1/conversations | Portal Backend → AI Platform | Bearer JWT | any | EXISTS NOT TESTED |
| 13 | GET | /api/v1/conversations/{id} | Portal Backend → AI Platform | Bearer JWT | any | EXISTS NOT TESTED |
| 14 | POST | /api/v1/conversations/{id}/messages | Portal Backend → AI Platform | Bearer JWT | any | EXISTS NOT TESTED |
| 15 | DELETE | /api/v1/conversations/{id} | Portal Backend → AI Platform | Bearer JWT | any | EXISTS NOT TESTED |

### Admin — Gateway (requires Portal Backend facade)

| # | Method | Path | Service | Auth | Role | Status |
|---|--------|------|---------|------|------|--------|
| 16 | GET | /admin/queues | Gateway (direct) | X-Admin-Key | admin | EXISTS NOT TESTED — NEEDS FACADE |
| 17 | GET | /admin/models | Gateway (direct) | X-Admin-Key | admin | EXISTS NOT TESTED — NEEDS FACADE |
| 18 | POST | /admin/models/{mid}/drain | Gateway (direct) | X-Admin-Key | admin | EXISTS NOT TESTED — NEEDS FACADE |
| 19 | POST | /admin/models/{mid}/undrain | Gateway (direct) | X-Admin-Key | admin | EXISTS NOT TESTED — NEEDS FACADE |
| 20 | GET | /admin/health | Gateway (direct) | X-Admin-Key | admin | EXISTS NOT TESTED — NEEDS FACADE |
| 21 | GET | /admin/reaper | Gateway (direct) | X-Admin-Key | admin | EXISTS NOT TESTED — NEEDS FACADE |

### Billing/Usage — MISSING endpoints

| # | Method | Path | Service | Auth | Role | Status |
|---|--------|------|---------|------|------|--------|
| 22 | GET | /v1/billing/me | Gateway (NEW) | JWT/API Key | any | MISSING |
| 23 | GET | /v1/billing/me/ledger | Gateway (NEW) | JWT/API Key | any | MISSING |
| 24 | GET | /v1/usage/me | Gateway (NEW) | JWT/API Key | any | MISSING |
| 25 | GET | /v1/usage/me/daily | Gateway (NEW) | JWT/API Key | any | MISSING |
| 26 | GET | /admin/orgs/{id}/billing | Gateway (NEW) | X-Admin-Key | admin | MISSING |
| 27 | GET | /admin/orgs/{id}/ledger | Gateway (NEW) | X-Admin-Key | admin | MISSING |
| 28 | GET | /admin/orgs/{id}/usage | Gateway (NEW) | X-Admin-Key | admin | MISSING |

### RAG — Gateway (requires Portal Backend facade)

| # | Method | Path | Service | Auth | Role | Status |
|---|--------|------|---------|------|------|--------|
| 29 | GET | /v1/rag/status | Gateway | JWT/API Key | any | EXISTS NOT TESTED — NEEDS FACADE |
| 30 | POST | /v1/rag/query | Gateway | JWT/API Key | rag:query | EXISTS NOT TESTED — NEEDS FACADE |
| 31 | POST | /v1/rag/hybrid-query | Gateway | JWT/API Key | rag:query | EXISTS NOT TESTED — NEEDS FACADE |
| 32 | POST | /v1/rag/ingest | Gateway | JWT/API Key | rag:ingest | EXISTS NOT TESTED — NEEDS FACADE |
| 33 | POST | /v1/rag/wiki-ingest | Gateway (direct) | X-Admin-Key | admin | EXISTS NOT TESTED — NEEDS FACADE |

### Monitoring — MISSING

| # | Method | Path | Service | Auth | Role | Status |
|---|--------|------|---------|------|------|--------|
| 34 | GET | /api/v1/monitoring/summary | Portal Backend (NEW) | Bearer JWT | admin/operator | MISSING |
| 35 | GET | /api/v1/monitoring/models | Portal Backend (NEW) | Bearer JWT | admin/operator | MISSING |
| 36 | GET | /api/v1/monitoring/security | Portal Backend (NEW) | Bearer JWT | admin/operator | MISSING |
| 37 | GET | /api/v1/monitoring/billing | Portal Backend (NEW) | Bearer JWT | admin/operator | MISSING |
| 38 | GET | /api/v1/monitoring/dependencies | Portal Backend (NEW) | Bearer JWT | admin/operator | MISSING |

### Admin — User/Org Management (MISSING)

| # | Method | Path | Service | Auth | Role | Status |
|---|--------|------|---------|------|------|--------|
| 39 | GET | /api/v1/admin/users | Identity (NEW) | Bearer JWT | admin | MISSING |
| 40 | POST | /api/v1/admin/users | Identity (NEW) | Bearer JWT | admin | MISSING |
| 41 | PATCH | /api/v1/admin/users/{id}/role | Identity (NEW) | Bearer JWT | admin | MISSING |
| 42 | GET | /api/v1/admin/orgs | Portal Backend (NEW) | Bearer JWT | admin | MISSING |
| 43 | GET | /api/v1/admin/orgs/{id} | Portal Backend (NEW) | Bearer JWT | admin | MISSING |
| 44 | PATCH | /api/v1/admin/orgs/{id}/tier | Portal Backend (NEW) | Bearer JWT | admin | MISSING |
| 45 | POST | /api/v1/admin/orgs/{id}/credit | Portal Backend (NEW) | Bearer JWT | admin | MISSING |
| 46 | POST | /api/v1/admin/orgs/{id}/debit | Portal Backend (NEW) | Bearer JWT | admin | MISSING |

---

## Security Constraints

1. **No direct browser→Gateway** for /admin/*, /metrics, /v1/rag/wiki-ingest
2. **Admin key** in Kubernetes Secret only, never in browser JS
3. **org_id** always from authenticated identity, never from request body
4. **Delegation JWT** RS256, TTL ≤ 60s, iss=aither-portal-backend, aud=aither-gateway
5. All Gateway credentials in Portal Backend K8s Secrets
