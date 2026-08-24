# Aither Portal Model Catalog Docsync R1 — Hermes Execution Evidence

- task_id: `AITHER-PORTAL-MODEL-CATALOG-DOCSYNC-R1`
- mode: `PORTAL_MODEL_CATALOG_DOCSYNC_RUNTIME_SYNC`
- executor: `hermes`
- branch: `aither-v2`
- baseline_sha: `f71ef8790737df3af19da323ee53cd4c456a5280`
- HEAD at execution (Architect task-control commit): `4ebdc67411da83478fd5b41f759509a1caddc7af` (committed `2026-08-24T06:26:00Z` UTC)
- Execution completed UTC: `2026-08-24T06:56:06Z`
- result: **PASS**

---

## 1. Preflight

| Item | Value |
|------|-------|
| host / workdir | `/home/codex/aither-project` (repo owned by `codex`; executor root Hermes) |
| branch | `aither-v2` |
| worktree clean at start | YES (`git status --porcelain` empty) |
| `git rev-parse HEAD` | `4ebdc67411da83478fd5b41f759509a1caddc7af` |
| baseline ancestor of HEAD | YES (`git merge-base --is-ancestor` → ANCESTOR_OK) |
| `git diff --name-only baseline..HEAD` | only `.agent/CURRENT_TASK.json` + `.agent/CURRENT_TASK.md` |
| `aither-portal` Deployment ready | `1/1` ready (generation 119, observed 119), pod `aither-portal-6c9dd7bcb9-9fzfd` `1/1 Running` restarts 0 |

Git invoked exclusively via `runuser -u codex -- git …` (no `safe.directory`, no Git metadata write by Hermes — Hermes does not commit or push; host runner finalizes).

## 2. Exact source files changed (all within allowed_paths)

| Path | Change |
|------|--------|
| `aither-v2/services/portal-frontend/index.html` | chat model selector now dynamic (disabled placeholder, no hardcoded options); chat label → active pair; send button `disabled` initially; app.js cache-bust `?v=final` → `?v=model-catalog` |
| `aither-v2/services/portal-frontend/app.js` | active-model catalog module; removed all Qwen2.5 paths/scopes; API-key UI → `model:qwen3:chat`; RAG label neutral; usage label session-derived |
| `docs/user-package/00_INDEX.md` | added document 17 row; replaced stale model summary with `qwen3-32b и qwen3.8-27b` |
| `docs/user-package/17_MODEL_USAGE_GUIDE.md` | NEW — canonical «Работа с моделями» source |
| `docs/evidence/AITHER_PORTAL_MODEL_CATALOG_DOCSYNC_R1.md` | this evidence |

No task-control files modified. No superseded frontend artifacts touched. Admin-panel drain buttons and tariff-card model text (`qwen-14b`/`qwen-32b-base`) were left untouched (out of scope: admin deployment controls / tariff descriptions, not the chat model catalog).

## 3. Before/after — model selector behavior

- Before: hardcoded `<select id="chat-model-select">` with two static `<option>`s (`qwen2.5-32b-instruct`, `qwen3-32b`); default `qwen2.5-32b-instruct`; send button always enabled; selector never refreshed from API.
- After: selector populated dynamically from authenticated `/api/v1/models`, filtered through the active allowlist (`qwen3-32b`, `qwen3.8-27b`); starts disabled with «Загрузка моделей…»; default active model `qwen3-32b`; on catalog-load failure the UI fails closed (selector + send button disabled, clear error) with no invented/retired fallback; session model restored on switch only if still in the active catalog (otherwise migrated to a valid active model); new chats use a valid active model.

## 4. Before/after — active model IDs and API-key scope behavior

- Before: active user journey referenced `qwen2.5-32b-instruct` (defaults, dashboard map, model-info panel, usage labels, RAG label) and emitted `model:qwen2.5:chat` from the API-key modal.
- After: only `qwen3-32b` and `qwen3.8-27b` appear in active code; API-key modal lists both Qwen3 models, both covered by a single `model:qwen3:chat` scope (deduplicated, never `model:qwen2.5:chat`); scope display maps `model:qwen3:chat` → `Qwen3 (qwen3-32b, qwen3.8-27b)`.

Display labels: `qwen3-32b` → `Qwen3-32B`, `qwen3.8-27b` → `Qwen3.8-27B`. Model-info panel derives only verified facts: `qwen3-32b` AWQ 4-bit, max-model-len 65536 (64K), N8 TP=2; `qwen3.8-27b` FP8, max-model-len 16384 (16K), N7 TP=2 (from live Deployment args).

## 5. 17_MODEL_USAGE_GUIDE.md — absent in GitHub before, canonical after

- Before: `docs/user-package/` in GitHub contained only `00_INDEX.md` … `16_AI_AGENT_CONNECTION_PRIMER.md`; `17_MODEL_USAGE_GUIDE.md` was absent from GitHub (live `aither-portal-docs` had a drifted/stale 17 key, sha `1207c363…`, 5427 bytes, with no canonical GitHub source).
- After: `docs/user-package/17_MODEL_USAGE_GUIDE.md` created (`b8daf72411b07a02132b0d12741f10ee34cacc0cae71345afeb6becced04644d`, 4674 bytes) and is now the canonical source; live `/docs/17_MODEL_USAGE_GUIDE.md` byte-identical to it.

## 6. ConfigMap key sets and SHA-256 fingerprints

`aither-portal-config` (namespace `aither-inference`), keys `app.js, index.html, nginx.conf, styles.css`:

| key | before (sha-256) | after (sha-256) |
|-----|------------------|-----------------|
| app.js | `3689164b5b21ac320c405b82d9694bce780d53bf4fca0a23d5d8addfc4ca945b` | `4d4211d30cf411865ba32af57b37bbe69b79eb7cbe8bc1887df13cf5fbb5c1be` |
| index.html | `ae9d12856976656094e6b480e71ffe958b16cde06b5e9bbdf7d77a7183c7f115` | `e6b1f707ab4589a18117827426093132d0968d31a69e40ccbf7e7e8923a2b4ce` |
| styles.css | `8471182055069271775f31cd65ca6ca75e85735744d7beb141ce628efc7f4626` | unchanged |
| nginx.conf | `1aa8d01a533ff16fc2b7ed11226ea73c2484cdfc79008727963c074cc9982bce` | unchanged |

All four keys byte-identical to `aither-v2/services/portal-frontend/*` after sync (verified programmatically).

`aither-portal-docs` (namespace `aither-inference`), 18 keys (`00_INDEX.md` … `17_MODEL_USAGE_GUIDE.md`) before and after — no key lost:

| key | before (sha-256) | after (sha-256) |
|-----|------------------|-----------------|
| 00_INDEX.md | `9705eac7e881ee03740cc0eff267a81a55a52c5decfce438bc2048e400d0ca23` | `17021d91cda5728c33d8445ab254febc35e22f54637a888e76f62457f1173efa` |
| 17_MODEL_USAGE_GUIDE.md | `1207c363b961438767ff4e0d148133e2f59aec04efc58f8eb41d5bf2886b86f5` | `b8daf72411b07a02132b0d12741f10ee34cacc0cae71345afeb6becced04644d` |
| 01_…16 (all) | unchanged | byte-identical (preserved) |

`aither-portal-frontend-config` NOT touched. Both active vLLM Deployments, Gateway/backend routing, Identity, DB, reverse proxy untouched.

## 7. Live HTTP / fingerprint verification (unauthenticated/static)

Both `https://fb1.spb.ru:10443` and `http://10.129.13.78:30080` returned identical results:

| Asset | HTTP | sha-256 | matches repo + ConfigMap |
|-------|------|---------|--------------------------|
| `/` (index.html) | 200 | `e6b1f707…` | YES |
| `/app.js?v=model-catalog` | 200 | `4d4211d3…` | YES |
| `/styles.css` | 200 | `84711820…` (16457 B) | YES (unchanged) |
| `/docs/17_MODEL_USAGE_GUIDE.md` | 200 | `b8daf724…` (4674 B) | YES |
| `/docs/00_INDEX.md` | 200 | `17021d91…` (5231 B) | YES |

Live code checks (index.html + app.js): `qwen3-32b` present, `qwen3.8-27b` present, `qwen2.5-32b-instruct` absent, `model:qwen2.5:chat` absent. Live article contains the exact active pair and `model:qwen3:chat`. No credentials/cookies/tokens were used.

## 8. `aither-portal` Ready state after sync

`1/1` ready (generation 119 observed), pod `aither-portal-6c9dd7bcb9-9fzfd` `1/1 Running`, restarts 0. Portal healthy.

## 9. Deployment restart required?

**NO.** ConfigMap volume projection refreshed on its own; live bytes already matched the corrected source without any Deployment restart. No `kubectl rollout restart` / `scale` / `delete` was issued against `aither-portal` (or anything else).

## 10. Commands used (sanitized)

- `runuser -u codex -- git rev-parse HEAD / merge-base --is-ancestor / diff --name-only baseline..HEAD / status --porcelain / diff --check`
- `kubectl -n aither-inference get deploy,svc,pods -o wide` and `get deploy aither-portal -o jsonpath=…` (image/ready/args)
- `kubectl -n aither-inference get cm aither-portal-config|aither-portal-docs -o json` (key sets + sha-256)
- `kubectl -n aither-inference create configmap aither-portal-config --from-file=… --dry-run=client -o yaml | kubectl apply -f -` (index.html, app.js, styles.css, nginx.conf)
- `kubectl -n aither-inference create configmap aither-portal-docs --from-file=<tmp> --dry-run=client -o yaml | kubectl apply -f -` (all 18 keys; 00 + 17 overwritten from canonical)
- `curl -sk https://fb1.spb.ru:10443/ …/app.js?v=model-catalog …/styles.css …/docs/17_MODEL_USAGE_GUIDE.md …/docs/00_INDEX.md` and same on `http://10.129.13.78:30080` (unauthenticated, sha-256 compare)
- `sha256sum`, `node --check app.js`, `python3` assertions from `validation_commands`

No Secret read/print/export. No API key created. No login/authenticated chat performed (deferred to final authenticated E2E). One non-secret env inspection of live Deployment args (served-model-name / max-model-len / quantization) was used solely to write truthful model detail; a credential-like plaintext value observed in that env dump was not recorded, reproduced, or used.

## 11–15. Required statements

- `BACKEND_MODEL_DEPLOYMENTS_CHANGED: NO`
- `GATEWAY_ROUTING_CHANGED: NO`
- `SECRETS_EXPOSED: NO`
- `RUNTIME_MUTATIONS:` ConfigMap `aither-portal-config` (updated), ConfigMap `aither-portal-docs` (updated) — only these two objects were changed; Deployment `aither-portal` was NOT restarted (no restart required).
- `RESULT: PASS` — canonical live frontend source corrected; live Portal bytes match corrected source; chat UI supports `qwen3-32b` and `qwen3.8-27b`; Qwen2.5 not selectable/default and no `model:qwen2.5:chat` path; API-key UI emits single `model:qwen3:chat` without duplicates; `17_MODEL_USAGE_GUIDE.md` exists in GitHub worktree and is canonical for the live article; live article byte-identical; `00_INDEX.md` references doc 17 and shows the active pair; no backend/Gateway/Identity/DB/Secret/reverse-proxy/secondary-frontend change; Portal healthy; no credential exposed.

STOP — authenticated E2E is the next acceptance step (not performed here).
