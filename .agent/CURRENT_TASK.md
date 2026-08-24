# AITHER-PORTAL-MODEL-CATALOG-DOCSYNC-R2

## Role and authority

Executor: **Hermes only**.

This is a narrow corrective task issued by ChatGPT Architect after independent Connector audit of R1. R1 corrected the active chat catalog and the article `17_MODEL_USAGE_GUIDE.md`, but the canonical live Portal frontend still contains retired user-visible model identifiers in the Tariffs and Admin sections.

Do not use Codex. Do not expand scope.

## Baseline

- Repository: `dedvmedved-dot/aither-project`
- Branch: `aither-v2`
- Baseline / parent: `bb7da8160ace229b9da447c1c3879317d9bb60ad`
- R1 implementation is otherwise accepted as the basis for this correction.

## Proven defect

In canonical `aither-v2/services/portal-frontend/index.html` after R1:

1. Admin model action buttons still send retired IDs:
   - `qwen-14b`
   - `qwen-32b-base`
2. Tariff cards still display retired model names such as:
   - `qwen-14b`
   - `qwen-14b + qwen-32b`

These strings are user-visible or user-actionable and are incompatible with the current accepted active pair:

- `qwen3-32b`
- `qwen3.8-27b`

The active chat catalog and API-key scope implemented in R1 must remain unchanged:

- active models exactly `qwen3-32b`, `qwen3.8-27b`
- API-key scope `model:qwen3:chat`
- Qwen2.5 remains retired
- `docs/user-package/17_MODEL_USAGE_GUIDE.md` remains canonical and unchanged unless only read for verification

## Required implementation

### 1. Tariffs: remove retired model identifiers

Edit only `aither-v2/services/portal-frontend/index.html`.

Tariff cards MUST NOT hardcode `qwen-14b`, `qwen-32b`, `qwen-32b-base`, or Qwen2.5 as currently available models.

Do not invent entitlement semantics that are not proven by current backend/runtime configuration. Prefer neutral truthful wording such as access being determined by the active catalog and tariff entitlement, unless current source/runtime contract proves a more specific mapping.

The visible Portal must not imply that retired models are available.

### 2. Admin model actions: no retired IDs

Inspect the current source/runtime contract read-only to determine whether `/api/v1/admin/gateway/models/<model>/<action>` supports the current model IDs.

- If current IDs are supported, replace retired buttons with controls for `qwen3-32b` and `qwen3.8-27b`, preserving only operations actually supported by the current endpoint.
- If current IDs cannot be proven supported, remove or disable the stale model-specific controls rather than inventing functionality.

Under no condition may a Portal control submit `qwen-14b`, `qwen-32b-base`, Qwen2.5, or another retired ID.

### 3. Runtime sync

Synchronize only the canonical `index.html` into the active `aither-portal-config` ConfigMap in namespace `aither-inference`, preserving all other keys byte-for-byte.

Do not touch:
- vLLM Deployments or Services
- Gateway routing
- Portal Backend routing
- Identity
- DB
- Secrets
- reverse proxy
- `aither-portal-docs`
- superseded frontend artifacts

Restart `aither-portal` only if strictly required for the changed ConfigMap to become live. If projection updates live content without restart, do not restart.

### 4. Evidence

Create `docs/evidence/AITHER_PORTAL_MODEL_CATALOG_DOCSYNC_R2.md` containing at minimum:

- task ID, executor, baseline, execution HEAD
- exact changed paths
- before/after stale-string findings
- how Admin controls were resolved and why
- tariff wording chosen and why it is truthful
- SHA-256 of canonical `index.html`, ConfigMap key, and live `/`
- HTTP status for live Portal root in Internet endpoint `https://fb1.spb.ru:10443/` and Test Zone `http://10.129.13.78:30080/`
- proof the three retired identifiers are absent from live canonical frontend: `qwen2.5-32b-instruct`, `qwen-14b`, `qwen-32b-base`
- proof `qwen3-32b` and `qwen3.8-27b` remain present
- Portal Deployment Ready state and restart count
- runtime mutations
- explicit statements:
  - `BACKEND_MODEL_DEPLOYMENTS_CHANGED: NO`
  - `GATEWAY_ROUTING_CHANGED: NO`
  - `DOCS_CHANGED: NO`
  - `SECRETS_EXPOSED: NO`
  - `RESULT: PASS|FAIL`

No secret values, cookies, bearer tokens, passwords, or credentials may appear in evidence.

## Validation / PASS criteria

PASS only if all are true:

1. `index.html + app.js` contain no `qwen2.5-32b-instruct`.
2. `index.html + app.js` contain no `qwen-14b`.
3. `index.html + app.js` contain no `qwen-32b-base`.
4. Current pair `qwen3-32b` and `qwen3.8-27b` remains present in canonical active frontend.
5. Tariff UI no longer claims retired models are available.
6. Admin UI cannot submit retired model IDs.
7. Live `/` is byte-identical to canonical `index.html` and active ConfigMap key.
8. Portal remains Ready 1/1 with no new restart/error regression.
9. No backend model, Gateway, Identity, DB, Secret, reverse-proxy or docs mutation.
10. Only allowed repository paths changed.

## STOP condition

After evidence is written, stop. Do not run the final authenticated E2E in this task. ChatGPT Architect will independently audit R2 and only then publish the final E2E task.
