# AITHER URGENT — Qwen3.8 FP8 / vLLM 0.27.1 Compatibility Test on n7 R1

## 0. Goal

Prove or disprove that the already-downloaded official `Qwen/Qwen3.8-27B-FP8` snapshot can run on Aither node n7 with 2× Quadro RTX 6000 24 GiB (Turing sm_75) using vLLM 0.27.1 and TP=2.

This is NOT the permanent cutover. Do not change Portal catalog/routing/model contract. At task end, Qwen2.5 on n7 MUST be restored exactly to its pre-test serving state, regardless of PASS or FAIL.

Known verified model path on n7:
`/data/models/Qwen3.8-27B-FP8`
Verified snapshot revision:
`017b9c7af6b5689d5dd426a76e0bc077eb5ca20a`
Download verification result: 66/66 safetensors present, 0 missing, 0 truncated, DOWNLOAD_COMPLETE=YES.

## 1. Critical behavior rules

1. Work only in this task scope.
2. Do not continue D2/D3/E1/F1/F2 or other roadmap work.
3. Do not change n8 or the existing `vllm-qwen3-32b-awq` deployment; read-only health validation only.
4. Do not change Portal backend, nginx, Identity, Billing, DB, users, roles, scopes or API keys.
5. Do not read Kubernetes Secret values. Do not create credentials.
6. Do not modify NVIDIA driver, host CUDA, containerd configuration, GPU Operator, CNI or cluster control plane.
7. Do not install host packages.
8. Do not modify model files or model `config.json`.
9. Do not delete the 81 Hugging Face `.lock` cache files merely because they exist. They are not a failure condition.
10. Do not switch to AWQ/GPTQ/NVFP4 or another Qwen3.8 checkpoint if FP8 fails.
11. Do not create permanent source manifests. Temporary Kubernetes objects are allowed only for this compatibility test.
12. Hermes must not git add/commit/push/reset/clean/checkout/switch/merge/rebase/tag/ref-mutate. Host runner finalizes Git.
13. Repo changes are limited to `docs/evidence/QWEN38_VLLM_COMPAT_N7_R1.md`.
14. Evidence file must end owned by uid/gid 1000:1000.
15. If an unplanned condition is encountered, fail closed and restore Qwen2.5.

## 2. Phase A — preflight and rollback baseline

Before any runtime mutation collect:

- n7 GPU inventory, driver, compute capability, VRAM and processes;
- Qwen2.5 Deployment/ReplicaSet/Pod/Service state, replicas, image digest, args, node placement, volumes, readiness/liveness, restart count and `/health` status;
- n8 Qwen3-32B readiness and `/health` status;
- free disk space on n7;
- verify `/data/models/Qwen3.8-27B-FP8` still has 66 expected shards, 0 missing and the exact revision above;
- verify no Qwen3.8 Deployment/Pod/Service already exists.

Capture enough Qwen2.5 state to restore it exactly.

## 3. Phase B — vLLM 0.27.1 image preparation, BEFORE touching Qwen2.5

Target image:
`vllm/vllm-openai:v0.27.1`

Do NOT use `latest`.

Resolve and record the immutable image digest actually used.

Important timeout protection:
- Qwen2.5 MUST remain 1/1 Ready while the new image is being pulled.
- If vLLM 0.27.1 is not cached on n7, create a temporary non-GPU image-prepull Pod pinned to n7 with an overridden harmless sleep command so kubelet pulls the image independently.
- Wait only while Qwen2.5 remains untouched.
- If image pull cannot complete within the executor window, leave Qwen2.5 serving, remove the prep Pod only if safe, record BLOCKED/IMAGE_PULL_INCOMPLETE, and STOP. Never scale Qwen2.5 down before image readiness is proven.

After image is available on n7, delete the prep Pod and verify no prep workload remains.

Record:
- vLLM image tag and immutable digest;
- image pull result;
- image ID if visible;
- compatibility of container CUDA runtime with current n7 NVIDIA driver, without changing the driver.

If the image cannot run with the current driver: BLOCKED and STOP with no Qwen2.5 outage.

## 4. Phase C — controlled temporary GPU handover

Only after Phase B PASS:

1. Re-check Qwen2.5 health.
2. Scale ONLY `vllm-32b-instruct-awq` on n7 from 1 to 0.
3. Wait for the old pod to terminate and both n7 GPUs to be released.
4. Record free VRAM.
5. Do not modify n8.

From this point onward, every exit path MUST execute rollback in section 9.

## 5. Phase D — temporary Qwen3.8 compatibility workload

Create temporary objects in namespace `aither-inference`:

- Deployment: `vllm-qwen38-27b-fp8-compat`
- Service: `vllm-qwen38-27b-fp8-compat`
- ClusterIP only; do not expose NodePort/Ingress/external route.
- Pin to n7.
- Request exactly 2 GPUs.
- Mount hostPath `/data/models/Qwen3.8-27B-FP8` read-only as `/models/Qwen3.8-27B-FP8`.
- image: exact vLLM 0.27.1 digest proven in Phase B.

Initial baseline arguments:

`--model /models/Qwen3.8-27B-FP8`
`--served-model-name qwen3.8-27b`
`--tensor-parallel-size 2`
`--gpu-memory-utilization 0.90`
`--max-model-len 8192`
`--max-num-seqs 1`
`--dtype half`
`--enforce-eager`
`--reasoning-parser qwen3`

Do NOT add `--quantization fp8` blindly. First inspect the already-verified checkpoint `quantization_config`; prefer framework autodetection. Only use an explicit quantization flag if vLLM 0.27.1 requires it for this exact checkpoint and the reason is captured in evidence.

Do NOT use speculative decoding, MTP optimization, FP8 KV-cache, prefix caching, tool calling, multimodal/image requests, CUDA graph tuning, or long-context tuning in this R1 baseline.

## 6. Mandatory FP8/Turing compatibility gate

PASS requires evidence from actual startup that the official FP8 checkpoint is accepted on sm_75.

Expected architectural fact:
- Turing sm_75 has no native FP8 tensor cores.
- A successful test must identify the actual supported weight-only/fallback kernel/backend selected by vLLM for this checkpoint (for example Marlin-class W8A16 if that is what runtime selects).

Capture safe startup log lines showing:
- model architecture recognized;
- quantization recognized;
- tensor-parallel world size 2;
- selected FP8/fallback kernel/backend if reported;
- no unsupported-compute-capability, unsupported-kernel, illegal instruction, CUDA fatal, OOM or architecture-load error.

If FP8 checkpoint is not supported on sm_75: FAIL compatibility, perform rollback, STOP. Do not substitute another quantization.

## 7. Direct internal API tests

When temporary Service is Ready, test only inside cluster/direct ClusterIP path, with no external Portal changes.

Required:
- `GET /health` -> 200;
- `GET /v1/models` -> model `qwen3.8-27b` (if no API auth configured on the temporary isolated workload);
- short `POST /v1/chat/completions` -> 200;
- Russian prompt -> coherent response;
- English prompt -> coherent response;
- deterministic short code prompt -> valid response;
- `stream=false` -> valid completion;
- `stream=true` -> stream terminates correctly;
- invalid model -> controlled 4xx, no crash;
- over-limit request -> controlled 4xx, no crash.

No image input. No tool calling. No external API key.

Record warm-up separately, then minimum 3 steady-state short requests with:
- TTFT if available;
- end-to-end latency;
- output tokens/sec if available;
- GPU memory per GPU;
- GPU utilization;
- CPU RAM;
- pod restart count;
- vLLM GPU cache metric if exposed.

## 8. Optional context escalation

Only if 8192 is fully stable and VRAM reserve is measured:

- restart temporary compatibility workload at 16384;
- run one short smoke request and record VRAM.

32768 is optional only if 16384 leaves a clearly safe measured margin.

65536, 262144 and 1M are OUT OF SCOPE for this R1.

Context escalation failure is not necessarily model compatibility failure: record highest stable context and return to the last stable configuration before cleanup.

## 9. Mandatory rollback / cleanup — ALWAYS

Regardless of PASS, FAIL or BLOCKED after Phase C starts:

1. Delete temporary `vllm-qwen38-27b-fp8-compat` Deployment and Service.
2. Verify no Qwen3.8 compatibility Pod/ReplicaSet remains.
3. Restore `vllm-32b-instruct-awq` to exactly its preflight replica state (expected 1).
4. Wait for Qwen2.5 Ready=True.
5. Verify Qwen2.5 `/health` -> 200.
6. Verify n7 GPU processes/VRAM correspond to restored Qwen2.5 TP=2.
7. Verify Qwen3-32B on n8 remains Ready and `/health` -> 200.
8. Verify no temporary external exposure was created.

Do NOT remove the downloaded Qwen3.8 model files.
Do NOT remove the cached vLLM 0.27.1 image.

If Qwen2.5 cannot be restored, result MUST be `BLOCKED_ROLLBACK_FAILURE` and evidence must make that prominent.

## 10. Evidence

Create only:
`docs/evidence/QWEN38_VLLM_COMPAT_N7_R1.md`

Include:
- task/baseline/timestamps;
- preflight n7/n8 state;
- Qwen2.5 rollback baseline;
- model revision and shard verification;
- vLLM 0.27.1 exact digest and image preparation result;
- driver/container CUDA compatibility facts;
- temporary workload spec summary;
- startup log evidence;
- actual FP8/Turing backend/kernel evidence;
- Ready/health/model API evidence;
- all inference/negative tests;
- performance/VRAM table;
- highest stable context tested;
- cleanup evidence;
- Qwen2.5 restored evidence;
- n8 Qwen3 unchanged evidence;
- exact runtime mutations;
- `SECRETS_EXPOSED: NO`.

## 11. Result criteria

`PASS` only if ALL are true:

- official downloaded Qwen3.8 snapshot remains complete;
- vLLM 0.27.1 image is available on n7 and pinned by digest;
- model loads successfully on Turing sm_75 with TP=2;
- actual FP8/fallback backend is identified and supported;
- baseline 8192 is stable;
- direct internal chat completion succeeds;
- no fatal CUDA/OOM/kernel/architecture errors;
- temporary Qwen3.8 objects are removed;
- Qwen2.5 is restored 1/1 and healthy;
- n8 Qwen3-32B remains healthy;
- no Portal/catalog/routing/DB/credential changes;
- evidence complete;
- SECRETS_EXPOSED=NO.

On PASS: STOP. Do NOT perform permanent cutover. Permanent replacement/catalog/routing is a separate Architect-authorized task.
