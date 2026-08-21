# Source/Runtime Reconciliation D1-R1 — Hermes Execution Evidence

- Task: `AITHER-MVP-SOURCE-RUNTIME-RECONCILE-D1-R1`
- Mode: `NARROW_SOURCE_RUNTIME_RECONCILIATION`
- Executor: `hermes`
- Branch: `aither-v2`
- Baseline SHA: `f0e7aff2c46ab0f74a8ae3a5011c32a58f4145ac`
- HEAD (task-control): `7f6ffe9167b391a95719f8dd3f2985641e115891`
- Result: **PASS** — drift D1 closed: live primary portal nginx routing captured into source and secondary ConfigMap synced to canonical content. Only D1 scope touched; D2/D3 and all other drift untouched.

---

## 1. Preflight

| Item | Value |
|------|-------|
| hostname | `330133.fornex.cloud` |
| executor uid/gid | `0`/`0` (root Hermes; repo owned by `codex` uid 1000) |
| workdir | `/home/codex/aither-project` |
| `git rev-parse HEAD` | `7f6ffe9167b391a95719f8dd3f2985641e115891` |
| `git rev-parse --abbrev-ref HEAD` | `aither-v2` |
| `git status --porcelain` | clean (empty) at start |
| baseline ancestor of HEAD | YES (`f0e7aff2c46ab0f74a8ae3a5011c32a58f4145ac` is ancestor) |
| diff `baseline..HEAD` (name-only) | only `.agent/CURRENT_TASK.json` + `.agent/CURRENT_TASK.md` (the Architect handoff) |

Git was invoked exclusively via `runuser -u codex -- git …` (no `safe.directory`, no Git metadata write performed by Hermes).

## 2. INSPECT — before hashes

### 2.1 Live primary ConfigMap `aither-portal-config` key `nginx.conf` (READ ONLY)

- sha256: `1aa8d01a533ff16fc2b7ed11226ea73c2484cdfc79008727963c074cc9982bce`
- size: 3498 chars (3502 bytes UTF-8), trailing newline: YES
- Contains both external API route blocks: `location = /api/v1/models` (→ `http://aither-portal-backend:8000`) and `location = /api/v1/chat/completions` (→ `http://aither-portal-backend:8000/v1/chat/completions`, with `proxy_read_timeout 300s` / `proxy_connect_timeout 10s`).

### 2.2 Live secondary ConfigMap `aither-portal-frontend-config` key `nginx.conf`

- sha256 (before): `60ac3d6641a032c88c8955915a03c7cc3a65dd263d9ea015f8b243b41cb23b96`
- size: 2523 chars, trailing newline: YES
- Did NOT contain the external API route blocks.

### 2.3 Source `aither-v2/services/portal-frontend/nginx.conf`

- sha256 (before): `60ac3d6641a032c88c8955915a03c7cc3a65dd263d9ea015f8b243b41cb23b96`
- size: 2525 bytes
- Did NOT contain the external API route blocks (matched the secondary ConfigMap before reconciliation).

## 3. SOURCE OF TRUTH RECONCILIATION

- Wrote the full, unshortened working nginx content of live primary `aither-portal-config/nginx.conf` byte-for-byte into `aither-v2/services/portal-frontend/nginx.conf` (via `runuser -u codex -- cp` of the exact extracted value).
- After write, source sha256 == live primary sha256 (`1aa8d01a…`).
- No final-newline normalization was required: the exact extracted value already ended in a single trailing newline and matched byte-for-byte, so no normalization step was performed.
- `git diff --stat`: `aither-v2/services/portal-frontend/nginx.conf | 23 insertions(+)` — exactly the two external API route blocks added; no existing working route block removed.

## 4. SECONDARY RUNTIME RECONCILIATION

- Updated ONLY key `nginx.conf` of ConfigMap `aither-portal-frontend-config` (namespace `aither-inference`) to the canonical source content via `kubectl patch --type merge` with `{"data":{"nginx.conf":"<canonical>"}}`.
- Keys `index.html`, `app.js`, `styles.css` NOT modified (hashes unchanged — see table below).
- Controlled rollout: `kubectl rollout restart deployment/aither-portal-frontend`; `rollout status` returned `successfully rolled out`.
- `aither-portal` deployment was NOT restarted (its `aither-portal-config` was read-only and unchanged).
- Primary ConfigMap `aither-portal-config` was NOT modified (read-only during this task).

## 5. VALIDATE

### 5.1 Hash cross-check (all three copies)

| Copy | sha256 | Match |
|------|--------|-------|
| source `aither-v2/services/portal-frontend/nginx.conf` | `1aa8d01a533ff16fc2b7ed11226ea73c2484cdfc79008727963c074cc9982bce` | canonical |
| live `aither-portal-config/nginx.conf` | `1aa8d01a533ff16fc2b7ed11226ea73c2484cdfc79008727963c074cc9982bce` | YES |
| live `aither-portal-frontend-config/nginx.conf` | `1aa8d01a533ff16fc2b7ed11226ea73c2484cdfc79008727963c074cc9982bce` | YES |

### 5.2 Secondary ConfigMap key integrity

| Key | sha256 (before) | sha256 (after) | Changed? |
|-----|-----------------|----------------|----------|
| nginx.conf | `60ac3d66…` | `1aa8d01a…` | YES (intended) |
| index.html | `ae9d1285…` | `ae9d1285…` | NO |
| app.js | `45b41805…` | `45b41805…` | NO |
| styles.css | `84711820…` | `84711820…` | NO |

### 5.3 External API route block presence

Both `location = /api/v1/models` and `location = /api/v1/chat/completions` present (grep count = 2) in: source file, primary ConfigMap, secondary ConfigMap.

### 5.4 Deployments Ready

| Deployment | READY | DESIRED | AVAILABLE |
|------------|-------|---------|-----------|
| aither-portal | 1 | 1 | 1 |
| aither-portal-frontend | 1 | 1 | 1 |

### 5.5 HTTP checks (read-only, no credential created, no model inference)

| Target | Method | Result |
|--------|--------|--------|
| `http://10.129.13.78:30080/health` | GET | 200 `{"status":"ok","version":"0.6.0-r7r7-c2-d18"}` |
| `http://10.129.13.78:30080/api/v1/chat/completions` | POST no-auth | 401 `{"detail":"invalid_api_key: Bearer token required"}` (not 404/5xx) |
| `http://10.129.13.78:30080/api/v1/models` | GET no-auth | 401 `{"detail":"Authentication required"}` |
| `https://fb1.spb.ru:10443/health` | GET | 200 `{"status":"ok","version":"0.6.0-r7r7-c2-d18"}` (internet path reachable) |

## 6. No-mutation attestation and ownership gate

- Kubernetes: read-only `get` for inspection; single `patch` on ConfigMap `aither-portal-frontend-config` key `nginx.conf` only; single `rollout restart` on `aither-portal-frontend` only. No other `apply`/`patch`/`delete`/`edit`.
- `aither-portal-config` (primary) untouched; `aither-portal` deployment not restarted; Service selectors, BFF/Identity/billing/users/DB/models/CNI/control-plane/observability/backups untouched.
- D2/D3 not touched (no `bff-mvp.yaml` selector change, no bff app.py change, no image-tag/env/secret manifest change).
- No Secret value read. No API key/credential created. No DB mutation. No model inference.
- No Git write performed by Hermes (no add/commit/push/reset/checkout/merge/rebase). Host runner performs commit/push.
- No modification to `.agent/*`, `/root/.hermes`.
- No `safe.directory=*`, no generic sudo, no recursive chown/chmod.

## 7. Changed repository paths (ownership)

| Path | uid:gid | mode |
|------|---------|------|
| `aither-v2/services/portal-frontend/nginx.conf` | 1000:1000 | 664 |
| `docs/evidence/SOURCE_RUNTIME_RECONCILE_D1_R1.md` | 1000:1000 | 644 |

Ownership set on the exact two paths only; no recursive chown; repo root ownership unchanged.

## 8. Conclusion

Drift D1 is closed. The working external API nginx routing is now byte-identical across the canonical source (`aither-v2/services/portal-frontend/nginx.conf`), the live primary ConfigMap (`aither-portal-config/nginx.conf`), and the live secondary ConfigMap (`aither-portal-frontend-config/nginx.conf`). A fresh deployment from GitHub can now reproduce the external `/api/v1/models` + `/api/v1/chat/completions` routing. No out-of-scope changes were made; D2/D3 remain untouched for their own future tasks.

- `TASK_ID: AITHER-MVP-SOURCE-RUNTIME-RECONCILE-D1-R1`
- `DRIFT_CLOSED: D1`
- `SOURCE_HASH_MATCH_PRIMARY: YES`
- `SECONDARY_HASH_MATCH_SOURCE: YES`
- `EXTERNAL_API_ROUTES_PRESENT: YES (source + primary CM + secondary CM)`
- `PORTAL_HEALTH_200: YES`
- `UNAUTH_CHAT_401: YES`
- `OUT_OF_SCOPE_MUTATION: NONE`
- `D2_D3_TOUCHED: NO`
- `SECRET_VALUES_READ: NO`
- `CREDENTIAL_MUTATION: NONE`
- `DB_MUTATION: NONE`
- `HERMES_GIT_WRITE_USED: NO`
- `OWNERSHIP_GATE: PASS`
- `FINAL_GATE: PASS`

SECRETS_EXPOSED: NO
