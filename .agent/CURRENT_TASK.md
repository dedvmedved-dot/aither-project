# AITHER URGENT — Qwen3.8 vLLM Compatibility Recovery Audit R1

## Goal
Read-only audit after `AITHER-URGENT-QWEN38-VLLM-COMPAT-N7-R1` returned BLOCKED with `restore also failed`.

## Rules
- Do not mutate runtime.
- Do not scale deployments.
- Do not create/delete Kubernetes objects.
- Do not read secret values.
- Do not change source or manifests.
- Create only `docs/evidence/QWEN38_VLLM_COMPAT_RECOVERY_AUDIT_R1.md`.

## Required checks
1. n7 GPU processes, VRAM, driver and health.
2. `vllm-32b-instruct-awq` Qwen2.5: desired/available replicas, pod state, node, restart count, `/health`.
3. n8 `vllm-qwen3-32b-awq`: desired/available replicas, pod state, restart count, `/health`.
4. Cluster-wide search for temporary objects named `vllm-qwen38-27b-fp8-compat` or containing `qwen38`/`qwen3.8`.
5. Whether `vllm/vllm-openai:v0.27.1` or its resolved digest is now present on n7/containerd.
6. Whether any vLLM 0.27.1 prep pod remains.
7. Qwen3.8 local snapshot remains complete: 66/66 expected shards, missing=0.
8. Inspect safe systemd/journal logs for the failed Hermes executor and identify exact failure phase and restore failure reason. Do not include secrets.
9. Determine whether Qwen2.5 was ever scaled to 0, whether a Qwen3.8 compatibility pod ever started, and if so capture the relevant non-secret startup/error logs.
10. Classify runtime as one of: SAFE_BASELINE_RESTORED / PARTIAL_TEST_SAFE / DEGRADED_REQUIRES_CORRECTION.
11. Recommend the smallest next corrective step. Do not execute it.

## PASS criterion
PASS means the audit itself completed and establishes the actual runtime state with evidence. It does not mean Qwen3.8 compatibility passed.

End evidence with `SECRETS_EXPOSED: NO|YES`.
