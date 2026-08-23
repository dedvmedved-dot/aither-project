# Qwen3.8 vLLM Compatibility Recovery Corrective R1

## Task / Result
- task_id: `AITHER-URGENT-QWEN38-VLLM-COMPAT-RECOVERY-CORRECTIVE-R1`
- executor: `hermes`
- mode: `BOUNDED_RUNTIME_RESTORE_WITH_FORENSIC_CAPTURE`
- branch: `aither-v2`
- baseline_sha: `228bbb6e2484f99aa8600c90724a57b79772c2a4`
- HEAD at execution: `268a3f3867eaa8174b70e1f3184eeb29952be848`
- baseline is ancestor of HEAD: **YES** (verified via `git merge-base --is-ancestor`)
- HEAD commit touches only `.agent/CURRENT_TASK.json` + `.agent/CURRENT_TASK.md` (verified via `git show --stat`)
- result: **BLOCKED** (Phase A/B/D completed; Phase C — Qwen2.5 restore — blocked by a pre-existing namespace LimitRange vs committed cpu-limit conflict, which is outside the authorized recovery scope)

## Timestamps
- execution window: `2026-08-23T05:41Z` – `2026-08-23T05:46Z` UTC (`08:41` – `08:46` MSK)
- evidence collected at: `2026-08-23T05:41` – `05:46` UTC

---

## Phase A — pre-cleanup compat state (captured BEFORE deletion)

### Deployment `vllm-qwen38-27b-fp8-compat`
- replicas: `1`, ready/available: `1/1`
- image: `vllm/vllm-openai@sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967`
  → matches the exact digest stated in the task (runtime digest confirmed).
- args: `--model /models/Qwen3.8-27B-FP8 --served-model-name qwen3.8-27b --tensor-parallel-size 2 --gpu-memory-utilization 0.90 --max-model-len 16384 --max-num-seqs 1 --dtype half --enforce-eager --reasoning-parser qwen3`
- resources: limits `{cpu: 8, memory: 64Gi, nvidia.com/gpu: 2}`, requests `{cpu: 8, memory: 48Gi, nvidia.com/gpu: 2}`
- nodeSelector: `aither.io/inference-primary: "true"`

### Pod `vllm-qwen38-27b-fp8-compat-69dc96fd49-fx6cl`
- node: `bootsmam-k8s-clnt01-n7-gpu` (n7)
- phase: `Running`, Ready: `True`, restarts: `0`
- imageID: `docker.io/vllm/vllm-openai@sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967`

### Service `vllm-qwen38-27b-fp8-compat`
- type: `ClusterIP`, IP `10.104.189.139`, port `8000/TCP`
- **no NodePort, no external exposure**; no Ingress objects exist in `aither-inference` (verified `kubectl get ingress`).

### ReplicaSets
- `69dc96fd49` (1/1 — current), `767d6f8787` (0/0), `8bf9999f7` (0/0)

### Health / model API
- `/health` → `HTTP 200`
- `/v1/models` → `id: "qwen3.8-27b"`, `max_model_len: 16384`, `root: /models/Qwen3.8-27B-FP8`

### Startup log proof (non-secret excerpts)
- `Loading safetensors checkpoint shards: 100% Completed | 66/66` → FP8 snapshot complete.
- `Your GPU does not have native support for FP8 computation but FP8 quantization is being used. Weight-only FP8 compression will be used leveraging the Marlin kernel.` → sm_75 (Turing) weight-only FP8 fallback confirmed.
- `Model loading took 14.46 GiB memory`.
- `Available KV cache memory: 2.67 GiB`; `GPU KV cache size: 75,776 tokens`; `Maximum concurrency for 16,384 tokens per request: 4.62x`.
- `init engine (profile, create kv cache, warmup model) took 327.49 s`.
- `Starting vLLM server on http://0.0.0.0:8000`; `Application startup complete`; `GET /health HTTP/1.1 200 OK`.
- Only benign `expandable_segments: memory mapping failed with OOM` CUDACachingAllocator warnings (non-fatal fallback). **No fatal CUDA / OOM / kernel error.**

### Optional single completion (pod already Ready; not an extension of the test)
- `POST /v1/chat/completions` (model `qwen3.8-27b`, `max_tokens: 16`) → `HTTP 200`, `usage.completion_tokens: 16`, `system_fingerprint: vllm-0.27.1-tp2-19fcd1d7`. `finish_reason=length` is the expected `max_tokens` cap.

### Qwen3.8 compatibility facts (observable at recovery time)
- 66/66 FP8 shards present; weights loaded on 2× Quadro RTX 6000 (sm_75) TP=2.
- vLLM `v0.27.1` in use (digest `0a51ea5b…`); model served at `max-model-len 16384` with `/health` 200 and a successful short completion → the FP8/Turing compatibility gate **passed** at test time.

---

## Phase B — temporary workload removed
Deleted in namespace `aither-inference` (and verified gone):
- `deployment.apps/vllm-qwen38-27b-fp8-compat` — deleted
- `service/vllm-qwen38-27b-fp8-compat` — deleted
- associated pods and ReplicaSets (owned by the Deployment) cascaded away; poll confirmed **0** remaining `qwen38`/`compat` objects.
- **n7 GPU release**: no inference pod requesting `nvidia.com/gpu` remains on n7; the 2 GPUs (node allocatable `2/2`) are released. (Remaining n7 pods are CPU-only infra: bff/gateway/identity/portal/portal-backend/portal-frontend/siem/chromadb/nginx-gateway-32b/gpu-feature-discovery.)

---

## Phase C — Qwen2.5 restore: BLOCKED

Action taken: `kubectl -n aither-inference scale deployment vllm-32b-instruct-awq --replicas=1` (accepted).

Observed: deployment `vllm-32b-instruct-awq` is `replicas=1, ready=0, unavailable=1`. The ReplicaSet
`vllm-32b-instruct-awq-7fbcb77c99` cannot create any pod. Events:

```
Warning FailedCreate  ... is forbidden: maximum cpu usage per Container is 8, but limit is 16
```

Root cause (pre-existing, not introduced by this task):
- Namespace `LimitRange` `aither-limits` (created `2026-08-17T19:46:17Z`) enforces `max.cpu: "8"` per container.
- The committed source manifest `aither-v2/deploy/vllm-32b-instruct-awq.yaml` (unchanged since commit `407cbe7`) declares `limits.cpu: "16"` (`requests.cpu: "8"`, `memory: 64Gi`, `nvidia.com/gpu: 2`).
- The previous Qwen2.5 pod had been running since before the LimitRange existed (grandfathered); the failed N7-R1 test scaled it to 0, so recreating it now triggers the admission constraint.

Not modified (out of authorized recovery scope): the deployment cpu limit, the `aither-limits` LimitRange, and any tracked source file. Resolving this requires an Architect-authorized change — either a source edit to `aither-v2/deploy/vllm-32b-instruct-awq.yaml` (cpu limit 16 → 8) or a `aither-limits` adjustment — neither of which is in `allowed_paths` or the task's enumerated Phase C mechanism ("scale to 1 replica").

- Qwen2.5 (`vllm-32b-instruct-awq`, production `model:qwen2.5:chat`) is therefore **NOT restored to 1/1 Ready**.
- Deployment left at `replicas=1` (literal Phase C instruction); the FailedCreate events preserve the blocker evidence.

### n8 Qwen3 verification (read-only, unaffected)
- Deployment `vllm-qwen3-32b-awq`: `1/1` Ready/available.
- Pod `vllm-qwen3-32b-awq-86cb6c9845-n2xpg` on `bootsman-k8s-clnt01-n8-gpu`, Ready=True, restarts=0.
- `/health` (in-pod) → `HTTP 200`.

---

## Phase D — worktree ownership leak removed

Leaked untracked artifact (root-owned, from a previous root executor, outside `allowed_paths`):
- path: `aither-v2/manifests/models/qwen38-27b-fp8.yaml`
  - uid/gid: `0/0` (root), mode `0600`, size `3101` bytes
  - sha256: `3f9541387c933de2b4c03ea4b0e4faa1b6b483129397e3c30e19182b73bcc020`
- parent dir: `aither-v2/manifests/models/` — uid/gid `0/0`, mode `0700`
- content: a Deployment + Service (`name: vllm-qwen38-27b-fp8`). References Secret `vllm-api-key` by name only (`secretKeyRef`); **no literal secret values present** (verified by scan).

Cleanup performed (minimal, no broad chown, no `safe.directory`):
- removed `aither-v2/manifests/models/qwen38-27b-fp8.yaml`
- removed the now-empty `aither-v2/manifests/models/` directory
- no tracked file touched.

Post-cleanup verification as user `codex`:
- `git status --porcelain` → empty (no more `Permission denied` warning)
- `git clean -fd --dry-run` → empty, exit code `0` (no permission error)
- no non-`codex`-owned files remain under `aither-v2/manifests/`

---

## Final runtime classification
**BLOCKED**

Completed: Phase A (forensic capture), Phase B (temp compat workload deleted, n7 GPUs released),
Phase D (root-owned untracked manifest removed, worktree clean for supervisor).
Blocked: Phase C — Qwen2.5 restore cannot complete because the committed `vllm-32b-instruct-awq`
manifest (`limits.cpu: 16`) violates namespace `LimitRange` `aither-limits` (`max.cpu: 8`); the fix
requires Architect authorization beyond this recovery task's scope.

n8 Qwen3-32B remains healthy (1/1, `/health` 200). Qwen3.8 weights and cached vLLM 0.27.1 image were
NOT deleted.

## SECRETS_EXPOSED: NO
