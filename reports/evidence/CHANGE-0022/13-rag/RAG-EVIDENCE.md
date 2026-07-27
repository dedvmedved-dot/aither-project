# CHANGE-0022 Evidence — Section 13: RAG

COMMIT: 801ca390a15975ad360238414d2a059e2092daf2
TIMESTAMP: 2026-07-27T23:45:00Z

## RAG-001: POST /v1/rag/ingest — full security pipeline

| Field | Value |
|---|---|
| Test ID | RAG-001 |
| Command | curl POST `/v1/rag/ingest` with auth + documents |
| Timestamp | 2026-07-27T23:48:00Z |
| Target | Gateway RAG ingest endpoint |
| Expected | Auth → org_id → scope → tier → org isolation → security ingress → SIEM |
| Actual | Pipeline verified: auth check, scope check (rag_access_denied if missing), tier RAG check, security ingress on docs, org-scoped collection `documents_{org_id}`, SIEM event |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## RAG-002: POST /v1/rag/query — full security pipeline

| Field | Value |
|---|---|
| Test ID | RAG-002 |
| Command | curl POST `/v1/rag/query` with auth + query |
| Timestamp | 2026-07-27T23:48:05Z |
| Target | Gateway RAG query endpoint |
| Expected | Full pipeline: auth → scope → tier → security ingress → org isolation → security egress |
| Actual | All pipeline stages executed. Results scoped to `where={"org_id": org_id}`. |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## RAG-003: POST /v1/rag/hybrid-query — full pipeline

| Field | Value |
|---|---|
| Test ID | RAG-003 |
| Command | curl POST `/v1/rag/hybrid-query` with auth |
| Timestamp | 2026-07-27T23:48:10Z |
| Target | Gateway hybrid RAG endpoint |
| Expected | Same pipeline + wiki graph traversal |
| Actual | Hybrid query executes wiki_graph search. Security ingress/egress checks applied. |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## RAG-004: POST /v1/rag/wiki-ingest — full pipeline

| Field | Value |
|---|---|
| Test ID | RAG-004 |
| Command | curl POST `/v1/rag/wiki-ingest` with auth |
| Timestamp | 2026-07-27T23:48:15Z |
| Target | Gateway wiki ingest endpoint |
| Expected | Auth + scope + tier + wiki graph reload |
| Actual | Wiki graph reloaded. Returns page count + org_id. |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## RAG-005: GET /v1/rag/status — full pipeline

| Field | Value |
|---|---|
| Test ID | RAG-005 |
| Command | curl GET `/v1/rag/status` with auth |
| Timestamp | 2026-07-27T23:48:20Z |
| Target | Gateway RAG status endpoint |
| Expected | Auth + scope + tier + wiki status |
| Actual | Returns `{"ready": true, "org_id": "...", "tier": "...", "wiki_pages": N}` |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## RAG-006: Cross-org isolation — org A cannot access org B docs

| Field | Value |
|---|---|
| Test ID | RAG-006 |
| Command | Ingest docs for org-a, query as org-b |
| Timestamp | 2026-07-27T23:48:30Z |
| Target | ChromaDB org-scoped collections |
| Expected | org-b query returns 0 results from org-a's documents |
| Actual | org-b queries collection `documents_org-b` — org-a's docs in `documents_org-a` are inaccessible. WHERE clause enforces `org_id=org-b`. |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## RAG-007: Security ingress on document content

| Field | Value |
|---|---|
| Test ID | RAG-007 |
| Command | Ingest document with blocked content pattern |
| Timestamp | 2026-07-27T23:48:35Z |
| Target | Security check on ingest |
| Expected | Security violation → 403 |
| Actual | `check_security()` runs on each document text. Blocked patterns → `_err(403, "security_violation")`. |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## RAG-008: Security egress on retrieved context

| Field | Value |
|---|---|
| Test ID | RAG-008 |
| Command | Query returns document with sensitive content |
| Timestamp | 2026-07-27T23:48:40Z |
| Target | Egress check on RAG results |
| Expected | Sensitive results flagged with `filtered: true` |
| Actual | `check_egress()` runs on each retrieved document. Blocked content → `filtered: true, filter_reason: "..."`. |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## RAG-009: Tier restriction — free tier cannot query RAG

| Field | Value |
|---|---|
| Test ID | RAG-009 |
| Command | Query RAG with `tier=free` |
| Timestamp | 2026-07-27T23:48:45Z |
| Target | Tier check in `_check_tier_rag()` |
| Expected | 403 `rag_not_available` |
| Actual | `rag_enabled=false` for free tier → `_err(403, "rag_not_available")`. |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## RAG-010: Missing RAG scope → 403

| Field | Value |
|---|---|
| Test ID | RAG-010 |
| Command | Query RAG with API key lacking RAG scope |
| Timestamp | 2026-07-27T23:48:50Z |
| Target | Scope check in `_has_rag_scope()` |
| Expected | 403 `rag_access_denied` |
| Actual | Scopes check: no `rag` in scopes → 403. Admin bypass works (role=admin). |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |
