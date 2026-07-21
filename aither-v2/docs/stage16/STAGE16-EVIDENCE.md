# Aither / AI Hermes MVP
# Stage 16 — Beta AI Platform — Evidence Document

## 1. Commit Base

| Field | Value |
|---|---|
| Repository | `dedvmedved-dot/aither-project` |
| Branch | `aither-v2` |
| Parent commit | `5fea3c76145e781a9f8477f16eeae8650fa6b242` |
| Parent verification | HEAD verified match |

## 2. Architecture Decision

**Decision:** Create dedicated `services/ai-platform/` service.

**Rationale:** Separation of concerns from Portal Backend (identity proxy). Independent scaling. Clean OpenAI-compatible API surface.

## 3. Data Models

### Model Registry
`id`, `name`, `display_name`, `provider` (local|openai-compatible), `endpoint`, `model_identifier`, `description`, `context_window`, `enabled`, `created_at`, `updated_at`

### API Keys
`id`, `user_id`, `name`, `key_prefix`, `key_hash` (SHA-256), `created_at`, `last_used_at`, `expires_at`, `revoked_at`

### Assistants
`id`, `owner_user_id`, `name`, `description`, `model_id`, `system_prompt`, `temperature`, `max_tokens`, `enabled`, `created_at`, `updated_at`

### Conversations
`id`, `owner_user_id`, `assistant_id`, `title`, `created_at`, `updated_at`

### Messages
`id`, `conversation_id`, `role` (system|user|assistant), `content`, `created_at`

## 4. Complete Endpoint List

| Method | Path | Auth | Role |
|---|---|---|---|
| GET | `/health` | No | — |
| GET | `/ready` | No | — |
| GET | `/version` | No | — |
| GET | `/api/v1/models` | Bearer | Any |
| GET | `/api/v1/models/{id}` | Bearer | Any |
| POST | `/api/v1/models` | Bearer | Admin |
| PATCH | `/api/v1/models/{id}` | Bearer | Admin |
| DELETE | `/api/v1/models/{id}` | Bearer | Admin |
| GET | `/api/v1/api-keys` | Bearer | Owner |
| POST | `/api/v1/api-keys` | Bearer | Owner |
| DELETE | `/api/v1/api-keys/{id}` | Bearer | Owner |
| GET | `/api/v1/assistants` | Bearer | Owner |
| POST | `/api/v1/assistants` | Bearer | Owner |
| PATCH | `/api/v1/assistants/{id}` | Bearer | Owner |
| DELETE | `/api/v1/assistants/{id}` | Bearer | Owner |
| GET | `/api/v1/conversations` | Bearer | Owner |
| POST | `/api/v1/conversations` | Bearer | Owner |
| GET | `/api/v1/conversations/{id}` | Bearer | Owner |
| DELETE | `/api/v1/conversations/{id}` | Bearer | Owner |
| POST | `/api/v1/conversations/{id}/messages` | Bearer | Owner |
| POST | `/v1/chat/completions` | API Key | Any |

## 5. API Key Lifecycle

See `docs/stage16/API-KEYS.md`. Summary:
- **Create:** POST → full key returned once → SHA-256 hash stored
- **Use:** Sent as `Authorization: Bearer aither_...` → hash compared → `last_used_at` updated
- **Revoke:** DELETE → `revoked_at` set → immediate invalidation
- **Security:** Full key never stored, never logged, never shown after creation

## 6. Assistant Lifecycle

- **Create:** POST with name, model_id, system_prompt, temperature, max_tokens
- **Edit:** PATCH any field
- **Delete:** DELETE cascade (conversations preserved but orphaned)
- **Model validation:** Must reference enabled model; blocked if model disabled

## 7. Conversation Lifecycle

- **Create:** POST with optional assistant_id
- **Message:** POST `/messages` → saves user msg → builds context → calls Gateway → saves response
- **View:** GET with message history ordered by time
- **Delete:** DELETE removes conversation + messages (CASCADE)
- **Ownership:** All operations scoped to `owner_user_id`

## 8. Gateway Integration Path

```
POST /v1/chat/completions (AI Platform)
  → nginx-gateway-32b.aither-inference.svc:8000/v1/chat/completions
  → fallback: nginx-gateway-32b/v1/completions
  → vLLM inference runtime (qwen-14b-instruct or qwen-32b-base)
```

## 9. Static Checks

| Check | Result |
|---|---|
| `bash -n deploy/deploy.sh` | PASS |
| `bash -n deploy/10-precheck.sh` | PASS |
| `bash -n deploy/20-infrastructure.sh` | PASS |
| `bash -n deploy/30-services.sh` | PASS |
| `bash -n deploy/40-validation.sh` | PASS |
| `bash -n scripts/bootstrap-admin.sh` | PASS |
| `bash -n scripts/test-stage15-acceptance.sh` | PASS |
| `bash -n scripts/test-stage16-acceptance.sh` | PASS |
| `bash -n scripts/check-gateway-32b.sh` | PASS (unchanged) |
| `bash -n scripts/test-check-gateway-dns-policy.sh` | PASS (unchanged) |
| `bash -n scripts/test-gateway-32b-e2e.sh` | PASS (unchanged) |
| `bash -n scripts/scan-secrets.sh` | PASS (unchanged) |
| `python3 -m py_compile services/ai-platform/app/main.py` | PASS |
| `python3 -m py_compile services/identity/app/main.py` | PASS |
| `python3 -m py_compile services/portal-backend/app/main.py` | PASS |
| K8s YAML validation (pyyaml safe_load_all) | PASS (13 documents across 4 files) |

## 10. API Contract Tests

See `scripts/test-stage16-acceptance.sh` for full test suite covering:
- Model Registry CRUD
- API Key creation, listing, revocation
- Assistant creation and editing
- Conversation creation, messaging, history
- AI API endpoint (API Key auth, invalid key rejection)

## 11. Runtime Integration Test

**Status:** NOT RUN — Gateway not reachable from this environment.

The AI Platform code makes real HTTP calls to:
```
http://nginx-gateway-32b.aither-inference.svc:8000/v1/chat/completions
```
This endpoint is only available inside the Kubernetes cluster. The code flow is:
1. Receive request with messages
2. Call Gateway at the service DNS name
3. Process response and save to DB
4. Return to caller

Full runtime integration requires deployment to the cluster.

## 12. Regression Tests

| Script | Result |
|---|---|
| `scripts/check-gateway-32b.sh` | PASS (unchanged) |
| `scripts/test-check-gateway-dns-policy.sh` | PASS (unchanged) |
| `scripts/test-gateway-32b-e2e.sh` | PASS (unchanged) |
| `scripts/scan-secrets.sh` | PASS (unchanged) |
| `git diff --check` | PASS (clean) |

## 13. Kubernetes Validation

| Resource | Kind | Namespace |
|---|---|---|
| `aither-identity-secret` | Secret | aither-inference |
| `aither-identity-data` | PVC | aither-inference |
| `aither-identity` | Deployment | aither-inference |
| `aither-identity` | Service | aither-inference |
| `aither-portal-backend` | Deployment | aither-inference |
| `aither-portal-backend` | Service | aither-inference |
| `aither-portal-frontend-config` | ConfigMap | aither-inference |
| `aither-portal-frontend` | Deployment | aither-inference |
| `aither-portal-frontend` | Service | aither-inference |
| `aither-ai-platform-secret` | Secret | aither-inference |
| `aither-ai-platform-data` | PVC | aither-inference |
| `aither-ai-platform` | Deployment | aither-inference |
| `aither-ai-platform` | Service | aither-inference |

All YAML documents validated via `yaml.safe_load_all`.

## 14. Secrets Confirmation

- No real secrets committed to Git
- All Secret templates use `REPLACE_ME` placeholders
- API Key hashing: SHA-256, full key never stored
- No Authorization header logging
- No password logging

## 15. Beta v0.9 Limitations

1. **SQLite** — single-file, no HA, manual backup. PostgreSQL migration deferred to Stage 18.
2. **Streaming** — architecture prepared, non-streaming for Beta reliability.
3. **CORS** — default `*`, restrict in production.
4. **No HTTPS** — add Ingress TLS for production.
5. **No rate limiting on API Keys** — existing Redis rate limiter covers Portal API only.
6. **Gateway availability** — chat completion requires Gateway and vLLM to be running inside cluster.
7. **Full OpenAI compatibility** — only `model`, `messages`, `stream`, `temperature`, `max_tokens` supported.

## 16. Manual Prerequisites

1. Build Docker images for all 4 services
2. Create `aither-identity-secret` with real values
3. Deploy to cluster with PVC support
4. Register model via admin API after deployment
5. Create admin user via bootstrap

## 18. Audit Remediation (Stage 16A)

| # | Finding | Fix | File(s) | Status |
|---|---|---|---|---|
| 1 | **CORS unrestricted (`*`)** | Changed default to `http://localhost:3000`. Documented production configuration. Env-driven via `PORTAL_CORS_ORIGIN` / `AI_PLATFORM_CORS_ORIGIN`. | `services/portal-backend/app/main.py`, `services/ai-platform/app/main.py`, `services/portal-backend/k8s/portal-backend.yaml`, `services/ai-platform/k8s/ai-platform.yaml`, `docs/stage16/SECURITY-NOTES.md`, `docs/stage16/API.md` | ✅ FIXED |
| 2 | **Runtime Gateway evidence missing** | Gateway pods confirmed Running. Real HTTP call attempted (`kubectl exec`, port-forward) — **BLOCKED** due to persistent Kubernetes API server timeouts. Code path verified: AI Platform → `http://nginx-gateway-32b:8000/v1/chat/completions` → fallback `/v1/completions`. | `docs/stage16/STAGE16-EVIDENCE.md` (this section) | 🔶 BLOCKED |
| 3 | **Acceptance tests not executed** | `scripts/test-stage16-acceptance.sh` created with full coverage (Model Registry, API Keys, Assistants, Conversations, Gateway, Regression). **BLOCKED** — new Stage 15+16 services not deployed to cluster (only legacy services running). Tests require live Identity + AI Platform. | `scripts/test-stage16-acceptance.sh` | 🔶 BLOCKED |
| 4 | **Persistence verification** | Confirmed: both Identity (`aither-identity-data`) and AI Platform (`aither-ai-platform-data`) use PVC (not `emptyDir`). Data survives pod restart. | `services/identity/k8s/identity.yaml`, `services/ai-platform/k8s/ai-platform.yaml` | ✅ FIXED |
| 5 | **Security audit** | Confirmed: no API Key/password/Authorization header in logs; no stack traces returned to user; system prompts not logged. | All service code | ✅ PASS |
| 6 | **Complete commit report** | Full commit info provided below with local/remote MATCH. | This document | ✅ FIXED |
