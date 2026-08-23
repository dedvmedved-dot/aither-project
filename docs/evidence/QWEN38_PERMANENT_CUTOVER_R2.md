# Qwen3.8 Permanent Cutover R2 — Hermes Execution Evidence

- task_id: `AITHER-URGENT-QWEN38-PERMANENT-CUTOVER-R2`
- executor: `hermes`
- mode: `PERMANENT_MODEL_CUTOVER_WITH_FAIL_CLOSED_ROLLBACK`
- branch: `aither-v2`
- baseline_sha: `85e1a83539327f981c9868190c66a0bbbd48c87f`
- HEAD at execution (Architect task-control commit): `14a0fcc1bbefa7feb6615ae9e4f0932b199abfe2`
- baseline is ancestor of HEAD: **YES** (verified via `git merge-base --is-ancestor`)
- HEAD commit touches only `.agent/CURRENT_TASK.json` + `.agent/CURRENT_TASK.md` (verified via `git show --stat`)
- result: **PASS** (permanent cutover of n7 from Qwen2.5 to Qwen3.8-27B-FP8 completed; n8 Qwen3-32B unchanged and healthy; Portal/external routing switched to exact-key map; portal-backend redeployed with immutable digest)

## SECRETS_EXPOSED: NO

---

## 1. Preflight

- Worktree clean at start (`git status` as `codex` → nothing to commit, working tree clean).
- Branch `aither-v2`, up to date with `origin/aither-v2` (fast-forward only, `git fetch --prune origin aither-v2`).
- baseline `85e1a835…` is ancestor of HEAD `14a0fcc1…`.
- Pre-cutover runtime state:
  - n7 `vllm-32b-instruct-awq` (Qwen2.5): `replicas=1 ready=1`, pod `vllm-32b-instruct-awq-64b4dfc657-l8sm9`, in-pod `/health` → HTTP 200.
  - n8 `vllm-qwen3-32b-awq` (Qwen3): `replicas=1 ready=1`, pod `vllm-qwen3-32b-awq-86cb6c9845-n2xpg`, in-pod `/health` → HTTP 200.
  - No temporary `*-compat` objects in namespace `aither-inference`.
  - vLLM 0.27.1 image digest `sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967` present/cached on n7 (confirmed by compat evidence R1 + immediate `Pulled … already present on machine` during this cutover).

## 2. Changed source files (all within allowed_paths)

| Path | Change |
|------|--------|
| `aither-v2/deploy/vllm-qwen38-27b-fp8.yaml` | NEW — permanent Deployment + ClusterIP Service |
| `aither-v2/services/portal-backend/app/main.py` | exact-key routing + active catalog |
| `aither-v2/services/portal-backend/k8s/portal-backend.yaml` | new immutable image + upstream URL/Secret refs |
| `aither-v2/canonical-image-digests.txt` | Qwen3.8 vLLM digest + new portal-backend digest |
| `docs/evidence/QWEN38_PERMANENT_CUTOVER_R2.md` | this evidence |

No task-control files modified. No Git metadata write performed by Hermes.

## 3. Before/after active model catalog

Before:
```
CURRENT_MODELS = {
    "qwen2.5-32b-instruct": {"scope": "model:qwen2.5:chat", "legacy_scope": "model:32b:chat", …},
    "qwen3-32b": {"scope": "model:qwen3:chat", …},
}
```
After:
```
CURRENT_MODELS = {
    "qwen3-32b": {"scope": "model:qwen3:chat", "display": "Qwen3-32B-AWQ"},
    "qwen3.8-27b": {"scope": "model:qwen3:chat", "display": "Qwen3.8-27B-FP8"},
}
```
Both active models use the existing `model:qwen3:chat` scope. Qwen2.5 and its `legacy_scope` (`model:32b:chat`) removed from active catalog, `_check_chat_entitlement` allowlist, `_check_api_key_entitlement`, and `/api/v1/models` scope filter.

## 4. Permanent Qwen3.8 manifest key parameters

- namespace `aither-inference`; Deployment/Service name `vllm-qwen38-27b-fp8`.
- pin to n7: `nodeSelector: aither.io/inference-primary: "true"`; `runtimeClassName: nvidia`; `serviceAccountName: vllm-sa`; `automountServiceAccountToken: false`.
- image exactly `vllm/vllm-openai@sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967` (v0.27.1).
- model hostPath `/data/models/Qwen3.8-27B-FP8` mounted read-only at `/model`.
- served model `qwen3.8-27b`; args: `--tensor-parallel-size 2 --gpu-memory-utilization 0.90 --max-model-len 16384 --max-num-seqs 1 --dtype half --enforce-eager --reasoning-parser qwen3` (+ `--host 0.0.0.0 --port 8000`). No `--quantization` flag (FP8 autodetected from checkpoint metadata). No speculative decoding / no CUDA graphs / no EAGLE/MTP.
- resources: requests `{cpu:8, memory:48Gi, nvidia.com/gpu:2}`, limits `{cpu:8, memory:64Gi, nvidia.com/gpu:2}` (CPU ≤ 8 per LimitRange, memory ≤ 64Gi).
- liveness/readiness/startup probes `/health` (startup failureThreshold 120).
- VLLM_API_KEY via `secretKeyRef` `vllm-api-key`/`VLLM_API_KEY` (by name only — value never read).

## 5. n7/n8 pod/deployment state (final)

| Deployment | replicas | ready | pod | node | restarts |
|------------|----------|-------|-----|------|----------|
| `vllm-qwen38-27b-fp8` | 1 | 1 | `vllm-qwen38-27b-fp8-5b4c7bdf57-qwdcq` | bootsmam-k8s-clnt01-n7-gpu | 0 |
| `vllm-qwen3-32b-awq` | 1 | 1 | `vllm-qwen3-32b-awq-86cb6c9845-n2xpg` | bootsman-k8s-clnt01-n8-gpu | 0 |
| `vllm-32b-instruct-awq` (Qwen2.5) | **0** | — | (none) | — | — |

Health checks: n7 Qwen3.8 `/health` → HTTP 200; n8 Qwen3 `/health` → HTTP 200.

## 6. Cutover sequence (fail-closed order)

1. All source changes prepared before disrupting n7.
2. `kubectl scale deployment vllm-32b-instruct-awq --replicas=0` → rolled out, `replicas=0`.
3. `kubectl apply -f aither-v2/deploy/vllm-qwen38-27b-fp8.yaml` → Deployment+Service created; pod scheduled on n7 (image already present, no pull).
4. First pod attempt entered `CrashLoopBackOff`: `api_server.py: error: unrecognized arguments: --disable-log-requests`. Root cause: vLLM v0.27.1 replaced `--disable-log-requests` with `--enable-log-requests|--no-enable-log-requests` (the flag was valid only on the legacy v0.8.5 manifests). Fix: removed `--disable-log-requests` and `--disable-fastapi-docs` from the permanent manifest to match the proven compatibility-run args; re-applied.
5. New pod `vllm-qwen38-27b-fp8-5b4c7bdf57-qwdcq` reached `1/1 Ready` (restarts=0). `/health` → HTTP 200. `/v1/models` → HTTP 401 (API-key gated; AUTH_REQUIRED for direct listing — served model proven from startup log).
6. n8 Qwen3 verified unchanged `1/1` and `/health` 200.

Rollback was NOT triggered: the only issue was a startup arg correction (manifest fixed, pod became healthy). Qwen2.5 source manifest (`aither-v2/deploy/vllm-32b-instruct-awq.yaml`) and model files are retained untouched as rollback asset; only its runtime replica count is 0.

## 7. Startup evidence — FP8 Marlin fallback / no fatal errors

From live pod log (non-secret excerpts):
- `non-default args: {… 'served_model_name': ['qwen3.8-27b'], 'reasoning_parser': 'qwen3', 'tensor_parallel_size': 2, 'gpu_memory_utilization': 0.9, 'max_num_seqs': 1, 'max_model_len': 16384, 'dtype': 'half', 'enforce_eager': True …}`
- `Initializing a V1 LLM engine (v0.27.1) … quantization=fp8 … speculative_config=None … served_model_name=qwen3.8-27b … max_seq_len=16384 … tensor_parallel_size=2` (FP8 autodetected; no speculative decoding).
- `Selected MarlinFP8ScaledMMLinearKernel for Fp8LinearMethod` → sm_75 (Turing) weight-only FP8 fallback confirmed.
- `Loading safetensors checkpoint shards: 100% Completed | 66/66` → snapshot complete.
- `Starting vLLM server on http://0.0.0.0:8000` / `Application startup complete` / `GET /health HTTP/1.1 200 OK`.
- Only benign non-fatal warnings: `min_frames`/`max_frames` Qwen3VL docstring notices, `Cannot use FA version 2 … compute capability >= 8` (FA2 unsupported on sm_75 → fallback), `expandable_segments: memory mapping failed with OOM` CUDACachingAllocator warnings. No Traceback / fatal CUDA OOM / kernel error.

## 8. Exact routing proof (source)

`aither-v2/services/portal-backend/app/main.py` now defines one exact-key routing map and a single resolver; all previous substring routing (`if "qwen3" in model_lower`, `elif "32b" in …`) was removed:

```
MODEL_UPSTREAM_URLS = {
    "qwen3-32b":  os.environ.get("UPSTREAM_QWEN3_32B_URL",  "http://vllm-qwen3-32b-awq.aither-inference.svc:8000"),
    "qwen3.8-27b": os.environ.get("UPSTREAM_QWEN38_27B_URL", "http://vllm-qwen38-27b-fp8.aither-inference.svc:8000"),
}
def _resolve_upstream(model):
    model_lower = model.lower().strip()
    if model_lower not in MODEL_UPSTREAM_URLS:
        raise HTTPException(status_code=404, detail=f"model_not_found: '{model}'")
    return MODEL_UPSTREAM_URLS[model_lower], MODEL_UPSTREAM_TOKENS[model_lower]
```

- `qwen3-32b` → `http://vllm-qwen3-32b-awq.aither-inference.svc:8000`
- `qwen3.8-27b` → `http://vllm-qwen38-27b-fp8.aither-inference.svc:8000`
- Unknown model → controlled `404 model_not_found` (external `/v1/chat/completions`, `_check_api_key_entitlement`, `_resolve_upstream`) or controlled `400 model_not_found` (Portal `/api/v1/chat`, `_check_chat_entitlement`); never routed to either backend.
- Applied in all active paths: `_chat_via_api_key` (API-key chat), `external_chat` (`/v1/chat/completions`), `chat_completions` (`/api/v1/chat` JWT). `_resolve_upstream` verified at runtime via in-image `import app.main` (correct `CURRENT_MODELS` and `MODEL_UPSTREAM_URLS` printed).
- Server-side upstream auth preserved via `secretKeyRef vllm-api-key/VLLM_API_KEY` for both `UPSTREAM_QWEN3_32B_TOKEN` and `UPSTREAM_QWEN38_27B_TOKEN` — no secret value read or embedded.

## 9. Portal backend rollout proof

- Image built from `aither-v2/services/portal-backend/` (Dockerfile + updated `app/main.py`), in-image `import app.main` returned `IMPORT_OK` with correct catalog/routing.
- Pushed to registry: `10.129.13.78:5000/aither-portal-backend:qwen38-cutover-r2`, immutable digest `sha256:b5a0c352243341abe9a602e666594525ff5f4dbd94d5a01a1f65b2243e58aa94`.
- Deployed via strategic-merge patch (image + 4 upstream env vars) to preserve pre-existing live env drift (SMTP/gateway/JWT/identity) that is outside this task's scope; `kubectl rollout status` → `successfully rolled out`.
- Pod `aither-portal-backend-6cdfd4c95c-7z8nc` `1/1 Running`, `/health` → HTTP 200, `/ready` → HTTP 200.

Note: `kubectl apply` of the full manifest conflicts with pre-existing live env drift (`IDENTITY_INTERNAL_API_SECRET` present as plaintext `value` in the live deployment while the tracked manifest declares `secretKeyRef aither-identity-secret`), producing a strategic-merge conflict. This drift is pre-existing (documented in `SOURCE_RUNTIME_DRIFT_AUDIT_R1.md`, deferred D2/D3) and out of scope; the tracked manifest remains the clean source-of-truth (identity via `secretKeyRef`), and the live deployment was updated surgically to apply exactly this task's changes.

## 10. Unauthenticated external API gates (Test Zone `http://10.129.13.78:30080`)

| Route | Method | Result |
|-------|--------|--------|
| `/api/v1/models` | GET (no auth) | HTTP 401 (auth failure, not 404/5xx) |
| `/api/v1/chat/completions` model=`qwen3-32b` | POST (no auth) | HTTP 401 `{"detail":"invalid_api_key: Bearer token required"}` |
| `/api/v1/chat/completions` model=`qwen3.8-27b` | POST (no auth) | HTTP 401 `{"detail":"invalid_api_key: Bearer token required"}` |

Auth is enforced before routing for both active models; no unauthenticated request reached the routing layer. Invalid-model behavior after auth is established by source proof (`model_not_found` 404/400, exact-key, no fallback). No authenticated E2E performed in this task (no API key created, no Identity secret accessed) — deferred to the separate narrow authenticated E2E gate.

## 11. Qwen2.5 rollback asset retained

- Source manifest `aither-v2/deploy/vllm-qwen38-27b-fp8.yaml` is new; `aither-v2/deploy/vllm-32b-instruct-awq.yaml` (Qwen2.5) is untouched in Git and its model files (`/data/models/Qwen2.5-32B-Instruct-AWQ`) are not deleted. Qwen2.5 is inactive only by runtime `replicas=0`.

## 12. PASS criteria mapping

1. n7 permanently serves `qwen3.8-27b` 1/1 healthy — YES (`vllm-qwen38-27b-fp8` 1/1, `/health` 200).
2. n8 continues serving `qwen3-32b` 1/1 healthy — YES.
3. Qwen2.5 not active, rollback asset retained — YES (`replicas=0`, source+files retained).
4. Active catalog exactly two Qwen3 models, both `model:qwen3:chat` — YES.
5. Exact model→upstream routing, no substring ambiguity/fallback — YES.
6. Portal backend healthy after source/runtime deployment — YES (`/health` 200, `/ready` 200, 1/1).
7. External unauthenticated routes fail for auth, not routing/service errors — YES (401/401/401).
8. No temporary compatibility objects — YES (no `*-compat` objects; only permanent `vllm-qwen38-27b-fp8`).
9. Only allowed paths changed, max one implementation commit — YES (5 paths, all allowed; one commit to be created by host supervisor).
10. `SECRETS_EXPOSED: NO` — YES.

## SECRETS_EXPOSED: NO
