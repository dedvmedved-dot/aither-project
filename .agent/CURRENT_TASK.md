# AITHER URGENT — Qwen3.8 Compatibility Recovery Corrective R1

## Goal
Restore n7 to the known-good pre-test state after `AITHER-URGENT-QWEN38-VLLM-COMPAT-N7-R1` timed out before rollback, while preserving forensic evidence that Qwen3.8 itself passed the FP8/Turing compatibility gate.

## Critical facts from accepted read-only audit
- Qwen3.8 official FP8 snapshot is complete (66/66 shards).
- vLLM 0.27.1 exact digest is present on n7.
- Qwen3.8 compat workload successfully loaded on 2× Quadro RTX 6000, sm_75, TP=2.
- max-model-len 16384 reached Ready, `/health` 200, no OOM/fatal CUDA/kernel error.
- Qwen2.5 was left scaled to 0 because the 3600 s H2 timeout fired before rollback.
- Temporary Deployment/Service `vllm-qwen38-27b-fp8-compat` remain on n7.
- An untracked root-owned `aither-v2/manifests/models/` directory prevents supervisor `git clean -fd` and caused `restore also failed`.

## Rules
1. This is a recovery task only. Do not continue permanent Qwen3.8 cutover, Portal routing/catalog, D2/D3/E1/F1/F2.
2. Do not modify n8 except read-only health verification.
3. Do not read Secret values or create credentials.
4. Do not modify DB, Identity, Billing, networking, GPU driver, containerd, CUDA, or model files.
5. Do not delete the downloaded Qwen3.8 weights or cached vLLM 0.27.1 image.
6. Preserve enough non-secret forensic evidence from the current running compat pod BEFORE deleting it: image digest, args, Ready state, `/health`, `/v1/models`, startup lines proving 16384 KV/cache init and absence of fatal CUDA/OOM; if safe, one short internal completion only if the pod is already ready. Do not extend the test.
7. Hermes must not git commit/push/reset/clean; host runner finalizes.
8. Repo output only `docs/evidence/QWEN38_VLLM_COMPAT_RECOVERY_CORRECTIVE_R1.md`.

## Phase A — capture current proof before cleanup
Record read-only:
- Qwen3.8 compat Deployment/Pod/Service state;
- exact image digest `vllm/vllm-openai@sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967` if runtime still matches;
- node n7, 2 GPU allocation, Ready/restarts;
- `/health` status;
- `/v1/models` served model;
- safe relevant startup log excerpts showing FP8 model load, TP=2, max-model-len 16384, KV cache capacity, engine init completion, server start, and no fatal CUDA/OOM/kernel failure.
Do not spend more than a few minutes on optional inference capture; recovery has priority.

## Phase B — remove temporary compatibility workload
Delete only in namespace `aither-inference`:
- Deployment `vllm-qwen38-27b-fp8-compat`
- Service `vllm-qwen38-27b-fp8-compat`
Wait until all associated pods/ReplicaSets are gone and both n7 GPUs are released.
Verify no external exposure/NodePort/Ingress was created.

## Phase C — restore Qwen2.5 baseline
Scale Deployment `vllm-32b-instruct-awq` to exactly 1 replica.
Wait for Ready=True.
Verify:
- pod scheduled on n7;
- restarts=0 or explain any restart count;
- `/health` -> 200;
- `/v1/models` identifies `qwen2.5-32b-instruct`;
- both n7 GPUs are held by Qwen2.5 TP=2;
- no Qwen3.8 temporary workload remains.
Verify n8 `vllm-qwen3-32b-awq` remains 1/1 Ready and `/health` 200.

## Phase D — repair worktree ownership leak safely
Target only the untracked leak identified by audit:
`aither-v2/manifests/models/`
containing `qwen38-27b-fp8.yaml`.

Before changing it, record metadata only (path, uid/gid, mode, file size/hash if readable without exposing secrets). This manifest must contain no secret values; do not print env/Secret data.

Because the directory/file are untracked and outside any accepted source publication, and were created by a previous root executor, remove the leaked artifact safely. Preferred approach:
- if needed, adjust ownership/permissions minimally so `codex` can remove it;
- delete only `aither-v2/manifests/models/qwen38-27b-fp8.yaml` and the now-empty `aither-v2/manifests/models/` directory;
- do not run broad `chown` on the repo;
- do not use `safe.directory=*`;
- do not delete any tracked file.

Then verify as user `codex`:
- `git status --porcelain` shows only the allowed evidence file before runner finalization;
- `git clean -fd --dry-run` no longer reports permission errors;
- no root-owned files/directories remain under the affected leaked path.

## Evidence
Create only:
`docs/evidence/QWEN38_VLLM_COMPAT_RECOVERY_CORRECTIVE_R1.md`

Include:
- task/timestamps;
- pre-cleanup compat state and proof;
- Qwen3.8 compatibility facts already observable at recovery time;
- exact deleted temporary K8s objects;
- n7 GPU release;
- Qwen2.5 restore evidence (1/1, health 200, model API);
- n8 Qwen3 health evidence;
- leaked path metadata and exact cleanup performed;
- `git clean -fd --dry-run` result as codex;
- final runtime classification;
- `SECRETS_EXPOSED: NO`.

## PASS criteria
PASS only if all are true:
- temporary Qwen3.8 Deployment/Service/Pods/ReplicaSets are gone;
- Qwen2.5 is restored 1/1 Ready on n7 and `/health` 200;
- Qwen3-32B remains healthy on n8;
- Qwen3.8 weights and vLLM 0.27.1 cache remain intact;
- root-owned leaked untracked manifest path is removed without touching tracked source;
- codex can run `git clean -fd --dry-run` without permission error;
- final repo changes are only the allowed evidence file plus host-runner-managed `.agent/EXECUTION_RESULT.json`;
- no secrets exposed.

On PASS: STOP. Do not start permanent cutover.
