# Qwen3.8 vLLM Compatibility Recovery Audit R1 (READ-ONLY)

## Task / Result
- task_id: `AITHER-URGENT-QWEN38-VLLM-COMPAT-RECOVERY-AUDIT-R1`
- executor: `hermes`
- mode: `READ_ONLY_RUNTIME_RECOVERY_AUDIT`
- baseline_sha: `14bf1cff8224ca48a3d453aaf099a71ab6d5ee4b`
- HEAD at audit: `198112dcc5494e67778f3bb4ea9f0e93dfd510a2` (branch `aither-v2`)
- baseline is ancestor of HEAD: YES (verified via `git merge-base --is-ancestor`)
- result: **PASS** (audit completed; establishes actual runtime state with evidence. This does NOT mean Qwen3.8 compatibility passed.)

## Timestamps
- audit execution: runner started `2026-08-23T05:02:52Z` (08:02:52 MSK)
- evidence collected: `2026-08-23T05:05Z` – `2026-08-23T05:14Z` UTC (08:05 – 08:14 MSK)
- prior BLOCK event (journal): `2026-08-23 07:41:49 MSK` (`04:41:49 UTC`)

## Runtime state summary
Baseline (pre-test) = n7 serves Qwen2.5 (`vllm-32b-instruct-awq`), n8 serves Qwen3 (`vllm-qwen3-32b-awq`).
Current = Qwen2.5 is scaled to 0 (NOT restored) and a temporary Qwen3.8 compatibility
deployment is running on n7 in its place. Qwen3 on n8 is unaffected.

---

## 1. n7 GPU processes, VRAM, driver, health
- Node `bootsmam-k8s-clnt01-n7-gpu` (10.129.13.77), `Ready=True`;
  MemoryPressure/DiskPressure/PIDPressure all `False`.
- Driver `590.48.01`, CUDA runtime `13.1`, GPU product `Quadro RTX 6000` (Turing, compute sm_75),
  2× GPU, 23040 MiB each; `nvidia.com/gpu` allocatable = 2.
- `nvidia-smi` (in-pod, 05:07 UTC):
  - GPU0: 19063 MiB / 23040 MiB used, util 0%, 34C, 61W/250W
  - GPU1: 19063 MiB / 23040 MiB used, util 0%, 35C, 64W/250W
- Both GPUs are held by the running Qwen3.8 compat pod (tensor-parallel 2). GPU util 0% = idle
  (no inference in flight). Process list shows "No running processes found" from the exec PID
  namespace (containerd PID-namespace isolation); VRAM residency is attributed to the compat pod.

## 2. `vllm-32b-instruct-awq` (Qwen2.5, n7)
- Deployment `spec.replicas=0`; `status.replicas`/ready/available all empty. **No pods running.**
- image `vllm/vllm-openai@sha256:6cf9808ca8810fc6c3fd0451c2e7784fb224590d81f7db338e7eaf3c02a33d33` (vLLM 0.8.5)
- args: `--served-model-name qwen2.5-32b-instruct`, TP=2, gpu-mem 0.90, max-model-len 65536, awq
- hostPath `/data/models/Qwen2.5-32B-Instruct-AWQ` (n7), nodeSelector `aither.io/inference-primary`
- `/health` → NOT available (no pod to query). **Qwen2.5 is NOT serving.**
- Scale-down evidence: event `ScalingReplicaSet ... vllm-32b-instruct-awq-7fbcb77c99 from 1 to 0`
  (~07:17 MSK / 04:17 UTC), `Killing` + `SuccessfulDelete` of pod `...-mr4qn`.

## 3. `vllm-qwen3-32b-awq` (Qwen3, n8)
- Deployment 1/1, pod `vllm-qwen3-32b-awq-86cb6c9845-n2xpg` Running on n8, restarts=0, Ready=True.
- image `vllm/vllm-openai@sha256:6cf9808...` (vLLM 0.8.5), hostPath `/data/models/Qwen3-32B-AWQ` (n8).
- `/health` (in-pod) → HTTP 200. **Unaffected and healthy.**

## 4. Cluster-wide search for `qwen38` / `qwen3.8` objects
`kubectl get all -A | grep -iE 'qwen38|qwen3\.8|compat'` finds (namespace `aither-inference`):
- Deployment `vllm-qwen38-27b-fp8-compat` — 1/1 Ready, 53m old
- Service `vllm-qwen38-27b-fp8-compat` — ClusterIP 10.104.189.139:8000, 53m old
- ReplicaSets: `767d6f8787`, `8bf9999f7`, `69dc96fd49`
- Pod `vllm-qwen38-27b-fp8-compat-69dc96fd49-fx6cl` — 1/1 Running on n7, restarts=0
- Deployment label `purpose=aither-urgent-qwen38-compat-n7-r1` → these are the **temporary test
  objects** created by the failed N7-R1 task and never deleted (rollback never ran).
- Historical temp pods (now gone): `qwen38-vllm0271-prepull`, `qwen38-vram-check` (see §5/§6).

## 5. `vllm/vllm-openai:v0.27.1` present on n7?
**YES.** Evidence:
- Event: `qwen38-vllm0271-prepull` "Successfully pulled image vllm/vllm-openai:v0.27.1"
  (image size 9 110 698 465 bytes) at ~07:14 MSK on n7.
- Docker Hub registry resolution (verified during audit): tag `v0.27.1` →
  digest `sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967`.
- The running compat pod uses exactly `vllm/vllm-openai@sha256:0a51ea5b...`, with pod events
  "Container image ... already present on machine" (n7). → v0.27.1's resolved digest is present
  and in use on n7 containerd.

## 6. Any vLLM 0.27.1 prep pod remaining?
**NO.** `qwen38-vllm0271-prepull` (killed 49m ago) and `qwen38-vram-check` (killed 47m ago) are
both deleted. The only qwen38 object with a running pod is the compat Deployment itself (§4).

## 7. Qwen3.8 local snapshot completeness
`/data/models/Qwen3.8-27B-FP8` (mounted read-only in the compat pod):
- `.safetensors` shards present: **66**
- expected (from `model.safetensors.index.json` `weight_map`): **66**
- missing: **0**
- total files in dir: 80 (includes config/tokenizer/index etc.); `weight_map` entries: 1606.
→ **Snapshot complete (66/66).**

## 8. Failure phase + restore failure reason (from safe logs, no secrets)
Journal `aither-hermes-exec@27-801328-1000.service` (06:41:22 → 07:41:29 MSK):

```
aither-hermes-root-exec[801346]: subprocess.TimeoutExpired: Command
  ['/usr/local/lib/hermes-agent/venv/bin/hermes', '-z', 'Read AGENTS.md, ...']
  timed out after 3600 seconds
aither-hermes-root-exec[801346]:   File ".../aither-hermes-root-exec", line 154, in main
    fail("BLOCKED_TIMEOUT")
aither-hermes-root-exec[801346]: BrokenPipeError: [Errno 32] Broken pipe
systemd[1]: aither-hermes-exec@27-801328-1000.service: Main process exited, code=exited, status=120/n/a
```

Runner summary (journal `aither-codex-runner.service`, 07:41:49 MSK):
`task failed: command exited with status 1; restore also failed: command exited with status 1` (BLOCKED).

Failure phase: the previous executor (AITHER-URGENT-QWEN38-VLLM-COMPAT-N7-R1) completed
preflight, image prepull, Qwen2.5 scale-down, temp Deployment creation, the FP8/Turing gate,
and positive+negative API tests, then entered **Phase 8 (optional context escalation,
max-model-len 8192→16384)**. The escalated pod required a ~327 s engine init and, combined with
the earlier phases, the H2 bridge hard cap of 3600 s (`subprocess.run(timeout=3600)`) expired.
The executor was killed by `BLOCKED_TIMEOUT` **before reaching Phase 9 (mandatory rollback:
delete temp objects, restore Qwen2.5, verify)**.

Restore failure reason: host supervisor `restore_after_failed_executor` runs
`git reset --hard <start_head>` then `git clean -fd` as user `codex`. `git clean -fd` fails
(status 1) because an **untracked, root-owned directory** exists in the worktree:
- `aither-v2/manifests/models/` — `drwx------ root root` (mode 0700), created Aug 22 14:26
- containing `qwen38-27b-fp8.yaml` — `-rw------- root root` (mode 0600)
- `git status`/`git clean` as `codex` report:
  `warning: could not open directory 'aither-v2/manifests/models/': Permission denied`
- `git clean -fd --dry-run` (as codex): "Would remove aither-v2/manifests/models/" but cannot
  traverse it → non-zero exit on the real clean.
This file was left by a prior root-Hermes executor run **outside `allowed_paths`** (a leaked
manifest artifact). It is the direct cause of "restore also failed".

## 9. Qwen2.5 scaled to 0? Qwen3.8 compat pod started? (with non-secret logs)
- Qwen2.5 was scaled to 0: YES (event `...-7fbcb77c99 from 1 to 0`; `spec.replicas=0`; no pods).
- Qwen3.8 compat pod started: YES, via 3 ReplicaSet iterations:
  1. `767d6f8787` — `FailedCreate`: "maximum cpu usage per Container is 8, but limit is 16"
     (initial manifest had CPU limit 16 > LimitRange max 8).
  2. `8bf9999f7` — pod created + started (CPU limit corrected to 8), later superseded.
  3. `69dc96fd49` (current) — `FailedCreate` warnings: "exceeded quota: aither-quota,
     requested: requests.memory=48Gi, used: 100800Mi, limited: 140Gi", then pod `fx6cl` created
     and started (~07:36 MSK).
- Compat pod non-secret startup/error log highlights:
  - `init engine (profile, create kv cache, warmup model) took 327.49 s`
  - `GPU KV cache size: 75,776 tokens`; `Maximum concurrency for 16,384 tokens per request: 4.62x`
  - `Free memory on device (21.66/21.97 GiB) on startup ... Actual usage is 15.64 GiB ...`
    → **no OOM** at max-model-len 16384.
  - `Starting vLLM server on http://0.0.0.0:8000`; `/health` → HTTP 200.
  - Only benign warnings (non-fatal): `use_fast` deprecation; `min_frames`/`max_frames`
    undocumented kwargs; `generation_config.json` sampling override. No Traceback/OOM/crash.
  - FP8/Turing (sm_75) compatibility gate: **PASSED** (weights loaded successfully, no crash).

## 10. Runtime classification
**DEGRADED_REQUIRES_CORRECTION**

The baseline was NOT restored: Qwen2.5 (`vllm-32b-instruct-awq`, production
`model:qwen2.5:chat`) is scaled to 0, and the temporary Qwen3.8 compatibility Deployment+Service
(`purpose=aither-urgent-qwen38-compat-n7-r1`) is running on n7, occupying both n7 GPUs.
A separate worktree leak (root-owned `aither-v2/manifests/models/`) also broke the supervisor's
restore step. Note: the Qwen3.8 compatibility TEST itself succeeded (FP8 loaded at
max-model-len 16384 without OOM) — the degradation is purely the **un-rolled-back test state**,
not a test failure.

## 11. Recommended smallest corrective step (NOT executed here)
Restore the baseline in a single corrective task:
1. Delete the temporary objects: `kubectl -n aither-inference delete deploy vllm-qwen38-27b-fp8-compat`
   and `delete svc vllm-qwen38-27b-fp8-compat`.
2. `kubectl -n aither-inference scale deploy vllm-32b-instruct-awq --replicas=1`; verify pod Ready
   and `/health` → 200.
3. Fix the worktree leak so the supervisor restore can succeed: `chown -R codex:codex
   aither-v2/manifests/models/` and remove it (it is untracked and outside any allowed path).

Also recommended for the harness (separate, not part of runtime restore): run long blocking
operations (large image prepull, model engine init) outside the 3600 s H2 executor timeout, and
ensure the executor cannot leave root-owned files in the worktree.

## SECRETS_EXPOSED: NO
