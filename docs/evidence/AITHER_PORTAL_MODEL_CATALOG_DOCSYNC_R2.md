# Aither Portal Model Catalog Docsync R2 — Hermes Execution Evidence

- task_id: `AITHER-PORTAL-MODEL-CATALOG-DOCSYNC-R2`
- mode: `PORTAL_STALE_MODEL_UI_CLEANUP`
- executor: `hermes`
- branch: `aither-v2`
- baseline_sha: `bb7da8160ace229b9da447c1c3879317d9bb60ad`
- HEAD at execution (Architect task-control commit): `4e3ebdfa84be87dced68e1eebc3ad8fc4bbfac6d`
- Execution completed UTC: `2026-08-24T08:46:06Z`
- result: **PASS**

---

## 1. Preflight

| Item | Value |
|------|-------|
| host / workdir | `/home/codex/aither-project` (repo owned by `codex`; executor root Hermes) |
| branch | `aither-v2` |
| worktree clean at start | YES (`git status --porcelain` empty) |
| `git rev-parse HEAD` | `4e3ebdfa84be87dced68e1eebc3ad8fc4bbfac6d` |
| baseline ancestor of HEAD | YES (`git merge-base --is-ancestor` → ANCESTOR_OK) |
| `git diff --name-only baseline..HEAD` | only `.agent/CURRENT_TASK.json` + `.agent/CURRENT_TASK.md` |
| `aither-portal` Deployment ready | `1/1` ready (generation 119, observed 119), pod `aither-portal-6c9dd7bcb9-9fzfd` `1/1 Running` restarts 0 |

Git invoked exclusively via `runuser -u codex -- git …` (no `safe.directory`; Hermes does not commit or push — host runner finalizes). Changes are left in the working tree, owned by `codex`, for the host runner to stage/commit/push.

## 2. Exact files changed (all within allowed_paths)

| Path | Change |
|------|--------|
| `aither-v2/services/portal-frontend/index.html` | removed 3 retired admin model-action buttons; replaced 2 retired tariff-card model strings with neutral truthful wording |
| `docs/evidence/AITHER_PORTAL_MODEL_CATALOG_DOCSYNC_R2.md` | this evidence |

No task-control files (`CURRENT_TASK.*`) modified. No `app.js`, `nginx.conf`, `styles.css`, `aither-portal-docs`, vLLM Deployments, Gateway, Identity, DB, Secrets, or reverse proxy touched.

## 3. Before/after — stale-string findings

### Admin "⚡ Действия" card (3 buttons, all retired IDs)

Before (line 318–320):
```
<button … onclick="window._adminAction('drain','qwen-14b')">Drain 14B</button>
<button … onclick="window._adminAction('undrain','qwen-14b')">Undrain 14B</button>
<button … onclick="window._adminAction('drain','qwen-32b-base')">Drain 32B</button>
```

After: all three buttons removed; card body is empty (no model-specific control remains, so no retired ID can be submitted).

### Tariff cards (2 strings)

| Tier | Before | After |
|------|--------|-------|
| Free | `🤖 qwen-14b только` | `🤖 Доступ к моделям определяется активным каталогом и тарифом` |
| Starter | `🤖 qwen-14b + qwen-32b` | `🤖 Доступ к моделям определяется активным каталогом и тарифом` |

`index.html` blob: `daf8e3e` → `124bbc4`; file `36135` → `35900` bytes.

## 4. How Admin controls were resolved and why

Read-only inspection of the current source/runtime contract determined that `/api/v1/admin/gateway/models/<model>/<action>` **cannot be proven to support the current active model IDs**, so the stale model-specific controls were **removed** (the task's "remove or disable" option), not replaced:

- `services/portal-backend/app/main.py` (`admin_gateway_drain` / `admin_gateway_undrain`) is a thin proxy to the Gateway's `/admin/models/{model}/drain|undrain`.
- The Gateway runtime catalog (`ConfigMap aither-gateway-catalog` in `aither-inference`) contains **only** `qwen-14b` and `qwen-32b-base` — both retired (their backends `vllm-14b-instruct.…` and `vllm-32b-gptq.…` are scaled `0/0`).
- The active pair `qwen3-32b` and `qwen3.8-27b` is **absent** from the Gateway catalog.
- The `aither-gateway` Deployment is `0/2` (not running).

Because the Gateway neither knows the current IDs nor is running, adding `qwen3-32b`/`qwen3.8-27b` drain controls would invent unproven functionality; leaving `qwen-14b`/`qwen-32b-base` controls would submit retired IDs. Removal is the only truthful resolution. Gateway routing/catalog was not modified (out of scope).

## 5. Tariff wording — why it is truthful

The retired strings were replaced with neutral wording that asserts no specific model entitlement that the current backend/runtime does not prove. "Доступ к моделям определяется активным каталогом и тарифом" ("model access is determined by the active catalog and tariff entitlement") names no retired model, does not invent a per-tier model mapping, and matches the actual runtime: the active chat catalog is exactly `qwen3-32b` + `qwen3.8-27b` and the tier controls request/token limits.

## 6. SHA-256 fingerprints

`index.html` (canonical repo → ConfigMap key → live `/`):

| Source | sha-256 |
|--------|---------|
| `aither-v2/services/portal-frontend/index.html` (working tree) | `c29d9d7856838ce7accac6acc00b37ba97797d98863cc0f18df60d186e8ba1e2` (35900 B) |
| `ConfigMap aither-portal-config` key `index.html` | `c29d9d7856838ce7accac6acc00b37ba97797d98863cc0f18df60d186e8ba1e2` |
| live `https://fb1.spb.ru:10443/` | `c29d9d7856838ce7accac6acc00b37ba97797d98863cc0f18df60d186e8ba1e2` |
| live `http://10.129.13.78:30080/` | `c29d9d7856838ce7accac6acc00b37ba97797d98863cc0f18df60d186e8ba1e2` |

All four byte-identical.

Other `aither-portal-config` keys preserved byte-for-byte (unchanged):

| key | sha-256 |
|-----|---------|
| app.js | `4d4211d30cf411865ba32af57b37bbe69b79eb7cbe8bc1887df13cf5fbb5c1be` |
| nginx.conf | `1aa8d01a533ff16fc2b7ed11226ea73c2484cdfc79008727963c074cc9982bce` |
| styles.css | `8471182055069271775f31cd65ca6ca75e85735744d7beb141ce628efc7f4626` |

Before (`index.html` key prior to this sync): `e6b1f707ab4589a18117827426093132d0968d31a69e40ccbf7e7e8923a2b4ce` (36135 B).

## 7. Live HTTP / fingerprint verification (unauthenticated/static)

| Endpoint | HTTP | sha-256 | matches repo + ConfigMap |
|----------|------|---------|--------------------------|
| `https://fb1.spb.ru:10443/` | 200 | `c29d9d78…` | YES |
| `http://10.129.13.78:30080/` | 200 | `c29d9d78…` | YES |

Retired identifiers absent from live canonical frontend (`index.html` + `app.js`):

| identifier | count (live) |
|------------|--------------|
| `qwen2.5-32b-instruct` | 0 |
| `qwen-14b` | 0 |
| `qwen-32b-base` | 0 |

Active pair still present in live canonical frontend: `qwen3-32b` (present), `qwen3.8-27b` (present) — `app.js` (9 / 7 occurrences respectively, live sha `4d4211d3…`), `index.html` header shows `Qwen3-32B · Qwen3.8-27B`.

## 8. `aither-portal` Ready state after sync

`1/1` ready (generation 119, observedGeneration 119), pod `aither-portal-6c9dd7bcb9-9fzfd` `1/1 Running`, restarts 0 (created `2026-08-18T12:44:40Z`, unchanged). Portal healthy; no restart or restart-count regression.

## 9. Deployment restart required?

**NO.** The ConfigMap volume projection refreshed on its own (kubelet re-synced `..data` symlink); live bytes already matched the corrected source without any Deployment restart. No `kubectl rollout restart` / `scale` / `delete` was issued against `aither-portal` or anything else.

## 10. Commands used (sanitized)

- `runuser -u codex -- git rev-parse HEAD / merge-base --is-ancestor / diff --name-only baseline..HEAD / status --porcelain / diff --check`
- `kubectl -n aither-inference get deploy,cm -o json` (Ready state, key sets, sha-256)
- `kubectl -n aither-inference create configmap aither-portal-config --from-file=<tmp> --dry-run=client -o yaml | kubectl apply -f -` (only `index.html` overwritten from canonical; `app.js`/`nginx.conf`/`styles.css` sourced from the current live ConfigMap, byte-identical)
- `kubectl -n aither-inference exec aither-portal-… -- sha256sum /usr/share/nginx/html/index.html` (volume projection verify)
- `curl -sk https://fb1.spb.ru:10443/` and `http://10.129.13.78:30080/` (unauthenticated, sha-256 compare)
- `sha256sum`, `python3` assertions from `validation_commands`

No Secret read/print/export. No login/authenticated chat performed (deferred to the Architect's final authenticated E2E). No API key created.

## 11–15. Required statements

- `BACKEND_MODEL_DEPLOYMENTS_CHANGED: NO`
- `GATEWAY_ROUTING_CHANGED: NO`
- `DOCS_CHANGED: NO`
- `SECRETS_EXPOSED: NO`
- `RUNTIME_MUTATIONS:` ConfigMap `aither-portal-config` updated (only the `index.html` key; the other three keys preserved byte-for-byte). No Deployment restart (not required — volume auto-projected).
- `RESULT: PASS` — live canonical Portal frontend no longer contains `qwen2.5-32b-instruct`, `qwen-14b`, or `qwen-32b-base`; tariff UI no longer claims retired models are available; admin UI can no longer submit retired model IDs; active pair `qwen3-32b` + `qwen3.8-27b` remains present; live `/` is byte-identical to canonical `index.html` and the active ConfigMap key on both endpoints; Portal Ready `1/1` with no new restart/error; only allowed repository paths changed; no backend/Gateway/Identity/DB/Secret/reverse-proxy/docs mutation.

STOP — the final authenticated E2E is the next acceptance step (not performed here; the Architect will independently audit R2).
