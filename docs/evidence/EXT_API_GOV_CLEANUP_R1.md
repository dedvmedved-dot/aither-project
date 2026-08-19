# EXT API Governance Cleanup R1 — Execution Evidence

- Task: `AITHER-MVP-EXT-API-GOV-CLEANUP-R1`
- Mode: `GOVERNANCE_CREDENTIAL_CLEANUP`
- Executor: `hermes`
- Branch: `aither-v2`
- Baseline SHA: `122684e8fc7caef859291df5f28f44f7f0ddb2ff`
- Start HEAD (task-control): `bd0552df639e416a6b2c18569ebcb40d6fd6da2a`
- Result: **PASS** (R2 temporary E2E API key id=21 revoked via supported API; no direct DB mutation; no other R2 credential/user mutation; external API undisturbed)

---

## 1. Preflight

| Item | Value |
|------|-------|
| hostname | `330133.fornex.cloud` |
| executor uid/gid | `0`/`0` (root Hermes; repo owned by `codex` uid 1000) |
| workdir | `/home/codex/aither-project` |
| `git rev-parse HEAD` | `bd0552df639e416a6b2c18569ebcb40d6fd6da2a` |
| branch | `aither-v2` |
| `git status --short` | clean (empty) |
| baseline ancestor of HEAD | YES (`122684e8…` is ancestor of `bd0552df…`) |

Git was invoked exclusively via `runuser -u codex -- git …` (no `safe.directory`). No git write was performed.

Identity/API service readiness: `aither-identity` pod `1/1 Running`; `aither-portal` `1/1 Running`; `aither-portal-backend` `1/1 Running`; `aither-bff` 2×`1/1 Running`; `vllm-32b-instruct-awq` and `vllm-qwen3-32b-awq` `1/1 Running`.

## 2. Identify key id=21 (supported API, admin JWT)

Login via supported Identity auth endpoint (`POST /v1/identity/auth`) as administrator (`id=1`, `username=admin`, `role=administrator`, `org_id=1`) → HTTP 200.

`GET /v1/identity/api-keys` (owner-scoped list) → HTTP 200. Key id=21 present and unambiguously matches the R2 artifact:

| Field | Value |
|-------|-------|
| id | 21 |
| name | `R2-E2E-test` |
| purpose | `api` |
| key_prefix | `aither_9LfU_uvnIrtyI` |
| scopes | `model:qwen2.5:chat`, `model:qwen3:chat` |
| owner user_id | 1 (`admin`, administrator) |
| created_at | `2026-08-18 13:55:03` |
| expires_at | `2026-09-17 13:55:03` (30 days) |
| last_used_at | `2026-08-18 14:00:16` |
| revoked_at (before) | `None` (active) |

This exactly matches the R2 evidence: name `R2-E2E-test`, prefix `aither_9LfU_uvnIrtyI`, scopes for both canonical models, 30-day expiry. No full key material was requested or printed.

## 3. Cleanup mutation (supported API only)

Exactly one credential mutation, via the supported revoke endpoint (no direct DB mutation):

- Method: `DELETE`
- Endpoint: `/v1/identity/api-keys/21` (Bearer admin JWT)
- HTTP status: `200`
- Response (non-secret): `{"message":"Key revoked","id":21,"status":"revoked"}`

No `DELETE`/`UPDATE`/`INSERT` SQL, no `psql`, no direct database write was performed. The SQLite store was only read (mode=ro) for confirmation/audit.

## 4. Post-cleanup state of id=21

- `GET /v1/identity/api-keys` → key 21 `status=revoked`, `revoked_at=2026-08-19 06:10:33`.
- Read-only DB confirmation: `revoked_at=2026-08-19 06:10:33`; active (non-revoked) count for id=21 is `0`.

Key id=21 is explicitly revoked/inactive and can no longer authenticate (introspect returns `active=false`, reason `revoked` for a revoked key).

## 5. Collateral mutation audit (R2 window ~2026-08-18 13:30–14:05 UTC)

Read-only inspection of Identity store tables (`api_keys`, `users`, `sessions`, `organisations`, `oauth_accounts`, `feedback`):

- **API keys**: only id=21 created in the R2 window; no other key create/delete/revoke attributable to R2. (id=20 `astramonitoring` was created `2026-08-18 10:26` — before the R2 window.)
- **Users**: no user created/deleted on/after `2026-08-18`.
- **Roles/scopes/passwords**: no role/scope change, no password reset attributable to R2 (no `updated_at` mutation trail exists; R2 was a diagnostic task).
- **Sessions**: R2 created only its two admin login sessions (id=228 `13:54:34`, id=229 `13:55:03`, both `user_id=1`, not revoked). No bulk session invalidation. Sessions id=230/231/232 (`2026-08-19 06:10:18/33/49`) are this cleanup task's own admin logins.
- **Organisations**: unchanged (only `default`, tier `pro`, active).
- **Invite codes**: no invite-code table in the store; no mutation possible/observed.

Conclusion: no additional unauthorized R2 credential/user mutation was found.

## 6. External API sanity check (no new key created)

Non-mutating checks only (no credential created for this task):

| Target | Check | Result |
|--------|-------|--------|
| `http://10.129.13.78:30080/` | GET | 200 |
| `http://10.129.13.78:30080/health` | GET | 200 `{"status":"ok","version":"0.6.0-r7r7-c2-d18"}` |
| `http://10.129.13.78:30080/api/v1/chat/completions` | POST no-auth | 401 `{"detail":"invalid_api_key: Bearer token required"}` |
| `https://fb1.spb.ru:10443/` | GET | 200 |
| `https://fb1.spb.ru:10443/health` | GET | 200 |
| `https://fb1.spb.ru:10443/api/v1/chat/completions` | POST no-auth | 401 `{"detail":"invalid_api_key: Bearer token required"}` |

Cleanup did not disturb the live external API. No full model inference was repeated (would require a new credential, which is out of scope).

## 7. OWNER REQUIRED action

No OWNER-required action remains for this task's scope — key id=21 was revoked through the supported API by the executor. (Out-of-scope, pre-existing: R2's "compromised key rotation" note refers to a separate, older exposed key and is not part of this cleanup.)

## 8. Repository evidence

Changed repository paths (read-only `git status`): exactly one new file —

```
docs/evidence/EXT_API_GOV_CLEANUP_R1.md
```

No other repository path was created or modified. `.agent/*` untouched. No Git metadata write performed.

## 9. Ownership gate

```
uid 1000 gid 1000 mode 644 docs/evidence/EXT_API_GOV_CLEANUP_R1.md
```

Ownership set on this exact path only; no recursive chown; repository root ownership unchanged; no `safe.directory=*`.

## 10. Final worktree state

- `git status --porcelain` → only `?? docs/evidence/EXT_API_GOV_CLEANUP_R1.md`
- HEAD unchanged (`bd0552df639e416a6b2c18569ebcb40d6fd6da2a`) — Hermes performed no Git write.

## Concluding fields

- `TASK_ID: AITHER-MVP-EXT-API-GOV-CLEANUP-R1`
- `KEY_21_IDENTIFIED: YES`
- `KEY_21_CLEANUP: PASS`
- `DIRECT_DB_MUTATION_USED: NO`
- `OTHER_R2_CREDENTIAL_MUTATIONS: NONE`
- `OTHER_R2_USER_MUTATIONS: NONE`
- `EXTERNAL_API_SANITY: PASS`
- `SECRET_VALUES_PRINTED: NO`
- `HERMES_GIT_WRITE_USED: NO`
- `OWNERSHIP_GATE: PASS`
- `FINAL_GATE: PASS`

SECRETS_EXPOSED: NO
