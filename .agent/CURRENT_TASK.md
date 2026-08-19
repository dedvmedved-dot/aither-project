# AITHER-MVP-EXT-API-GOV-CLEANUP-R1

## Goal
Close the governance violation introduced during `AITHER-MVP-EXT-API-CHAT-RECOVERY-R2` by revoking only the temporary API key created for E2E validation (`key id=21`), verifying that no other credential/user mutations were introduced by that task, and preserving the already verified working external API runtime.

## Baseline
- Branch: `aither-v2`
- Baseline SHA: `122684e8fc7caef859291df5f28f44f7f0ddb2ff`
- Prior technical result: external API runtime is functional and R2 host runner result is PASS.
- Governance defect: R2 evidence states Hermes created temporary API key `id=21` even though the R2 task had `database_write=false`.

## Critical behavior requirements
1. This task is cleanup/audit only. Do NOT repeat API recovery, redeploy workloads, restart pods, change manifests, change nginx, change models, or alter billing/users except the single temporary API key `id=21`.
2. Do NOT modify PostgreSQL directly. No SQL DELETE/UPDATE/INSERT. No psql mutation. Use only the existing supported Identity/API key lifecycle interface.
3. Mutation authority is limited to revoking/deleting exactly API key `id=21` if it still exists and is identifiable as the R2 temporary test key.
4. Do NOT create replacement keys. Do NOT rotate unrelated keys. Do NOT alter user accounts, roles, passwords, sessions, invite codes, quotas, scopes, billing, model access, or database schema.
5. Never print or commit any full API key, bearer token, password, cookie, secret, JWT, private key, or secret-bearing request dump.
6. If key `id=21` is already absent/revoked, prove that fact and do not mutate anything else.
7. If `id=21` no longer maps unambiguously to the R2 temporary key, STOP BLOCKED rather than touching another credential.
8. GitHub remains Source of Truth. Hermes must not perform git write operations; host runner owns result/commit/push.
9. Repository ownership handoff remains mandatory: every changed implementation path must finish uid/gid 1000:1000. No recursive chown, no repo-root ownership change, no `safe.directory=*`.

## Required execution order
PREFLIGHT -> IDENTIFY KEY 21 SAFELY -> REVOKE/DELETE VIA SUPPORTED API -> VERIFY ABSENCE/INACTIVE -> AUDIT OTHER R2 CREDENTIAL/USER MUTATIONS -> SANITY CHECK EXTERNAL API WITHOUT CREATING NEW KEY -> OWNERSHIP VERIFY -> EVIDENCE -> STOP.

## Preflight
Record safe evidence for:
- hostname/user/uid/pwd
- `git rev-parse HEAD`
- `git status --short`
- current branch
- relevant Identity/API service readiness

Worktree must be clean. Do not reset/clean/checkout/switch.

## Identify key id=21
Use the supported administrative Identity/API interface to inspect key metadata only. Record only non-secret fields sufficient to prove identity, such as:
- key id
- non-secret name/label if available
- prefix only if the product exposes a safe short prefix
- owner/user id if non-sensitive
- scopes
- created_at
- expires_at
- revoked/active state

Do not request or print the full key material.

The evidence from R2 indicates key id `21` was created as the temporary E2E key with scopes for both canonical models and 30-day expiry. If metadata does not safely match that R2 artifact, STOP BLOCKED.

## Cleanup mutation
Preferred order:
1. Use an existing supported API-key revoke endpoint if available.
2. Otherwise use the supported API-key delete endpoint.
3. Do not fall back to direct database mutation.

Perform exactly one credential mutation targeting id=21. Record method, endpoint shape without secret-bearing headers, HTTP status, and non-secret response summary.

## Verification
After cleanup, prove one of:
- key id=21 is absent; or
- key id=21 is explicitly revoked/inactive and cannot authenticate.

If a negative auth test can be performed without revealing the old full key, use a safe existing mechanism. Do not recover or print key material merely to test it.

## Audit for collateral R2 mutations
Using audit/event/history data and supported read-only APIs where available, determine whether the R2 execution introduced any other credential/user mutations near the R2 execution window.

At minimum inspect for:
- additional API-key creates/deletes/revokes attributable to R2
- user creation/deletion
- password reset/change
- role/scope changes
- session invalidation
- invite-code mutation

Do not expose secrets or personal data beyond minimal IDs/types/timestamps needed for evidence.

If evidence shows any additional unauthorized mutation, do NOT remediate it automatically unless it is unambiguously another R2-created disposable test artifact. Report BLOCKED with exact metadata and STOP.

## External API sanity check
Do not create a new key for this task.

Perform only non-mutating checks that require no new credential, such as:
- GET `/`
- GET `/health`
- no-auth POST `/api/v1/chat/completions` expected 401/403
- no-auth or otherwise safe metadata endpoint as appropriate

The purpose is only to prove cleanup did not disturb the live API. Do not repeat full model inference if it would require creating another credential.

## Repository evidence
Create exactly:
`docs/evidence/EXT_API_GOV_CLEANUP_R1.md`

The evidence must include:
- task/baseline/start HEAD
- preflight clean state
- safe metadata identifying key id=21
- cleanup method and result
- post-cleanup state of id=21
- collateral mutation audit result
- external API sanity result
- whether any OWNER REQUIRED action remains
- changed repository paths
- final ownership metadata
- final worktree state
- explicit final verdict

Required concluding fields:
- `TASK_ID: AITHER-MVP-EXT-API-GOV-CLEANUP-R1`
- `KEY_21_IDENTIFIED: YES|NO`
- `KEY_21_CLEANUP: PASS|BLOCKED|FAIL`
- `DIRECT_DB_MUTATION_USED: NO`
- `OTHER_R2_CREDENTIAL_MUTATIONS: NONE|FOUND|UNKNOWN`
- `OTHER_R2_USER_MUTATIONS: NONE|FOUND|UNKNOWN`
- `EXTERNAL_API_SANITY: PASS|BLOCKED|FAIL`
- `SECRET_VALUES_PRINTED: NO`
- `HERMES_GIT_WRITE_USED: NO`
- `OWNERSHIP_GATE: PASS|FAIL`
- `FINAL_GATE: PASS|BLOCKED|FAIL`

## Git/governance prohibitions
Hermes MUST NOT run git add/commit/push/pull/reset/clean/checkout/switch/merge/rebase/tag or modify refs/index/history. Read-only git commands are allowed. Hermes MUST NOT modify `.agent/*`.

## PASS gate
PASS only if:
- key id=21 is safely identified as the R2 temporary test key or proven already absent/revoked;
- id=21 is revoked/deleted through the supported API without direct DB mutation;
- no unrelated credential/user mutation is performed;
- collateral audit finds no additional unauthorized R2 mutation, or proves none with available evidence;
- external API remains healthy after cleanup;
- exactly the allowed evidence file is changed in Git;
- evidence path is uid/gid 1000:1000;
- no secret is printed or committed;
- Hermes performs no Git write.

Otherwise report BLOCKED/FAIL with evidence and STOP.
