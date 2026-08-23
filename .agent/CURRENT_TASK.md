# AITHER URGENT — Restore Qwen2.5 on n7 by aligning CPU limit with namespace LimitRange R1

## Goal
Restore the baseline Qwen2.5 service on n7 after the Qwen3.8 compatibility test, using the smallest source/runtime change proven necessary by the prior recovery evidence.

## Known blocker
Namespace `aither-inference` has LimitRange `aither-limits` with per-container `max.cpu: 8`.
Committed manifest `aither-v2/deploy/vllm-32b-instruct-awq.yaml` requests `cpu: 8` but sets `limits.cpu: 16`, so new pods are rejected.

## Required actions
1. Verify current blocker is still exactly the LimitRange CPU admission failure and no new blocker exists.
2. Change ONLY `resources.limits.cpu` for container `vllm` in `aither-v2/deploy/vllm-32b-instruct-awq.yaml` from `"16"` to `"8"`.
3. Do not modify requests.cpu, memory, GPU count, model args, image, service, probes, nodeSelector, LimitRange, namespace quota, Secret refs, n8, Portal, Identity, Billing, routing or Qwen3.8 files.
4. Apply the corrected manifest to namespace `aither-inference`.
5. Ensure deployment `vllm-32b-instruct-awq` has replicas=1.
6. Wait for pod Ready=True and rollout complete.
7. Verify `/health` HTTP 200 from the restored pod.
8. Verify `/v1/models` reports `qwen2.5-32b-instruct` using an existing authorized runtime path without exposing credentials. If auth prevents this without secret access, record AUTH_REQUIRED and do not read secrets; `/health` remains mandatory.
9. Verify both n7 GPUs are allocated to the restored Qwen2.5 pod and there are no `qwen38`/`compat` temporary objects.
10. Verify n8 `vllm-qwen3-32b-awq` remains 1/1 Ready and `/health` 200.
11. Verify worktree clean and no non-codex-owned files under repo paths touched.

## Evidence
Create only `docs/evidence/QWEN25_N7_RESTORE_LIMITRANGE_R1.md` plus the single authorized manifest edit.

Evidence must include before/after CPU resource stanza, admission event before fix, apply/rollout result, pod/node/restart state, health result, GPU allocation, absence of qwen38 temp objects, n8 health, git diff summary, and `SECRETS_EXPOSED: NO`.

## PASS criteria
PASS only if Qwen2.5 is 1/1 Ready on n7, `/health`=200, the only source change is cpu limit 16→8, no Qwen3.8 temp objects remain, n8 Qwen3 remains healthy, worktree is clean, and no secret is exposed.

On PASS: STOP. Do not restart Qwen3.8 and do not perform permanent cutover in this task.
