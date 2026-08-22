# Qwen3.8 Failed Cutover — Recovery Audit R1 (READ-ONLY)

## Task / Result
- task_id: `AITHER-URGENT-QWEN38-RECOVERY-AUDIT-R1`
- executor: `hermes`
- mode: `READ_ONLY_RUNTIME_RECOVERY_AUDIT`
- baseline_sha: `4d2472ca1065dfcb011ac4d0150167423ea7a36a`
- HEAD at audit: `8d04e75c4ab2c87f2f5460a4f7fafde3fd3801f3` (branch `aither-v2`)
- baseline is ancestor of HEAD: YES (diff baseline..HEAD = only `.agent/CURRENT_TASK.json` + `.agent/CURRENT_TASK.md`)
- result: **PASS** (audit establishes actual runtime state with sufficient evidence for safe corrective)

## Timestamps (UTC)
- audit start (runner): `2026-08-22T12:37:22Z`
- evidence collected: `2026-08-22T12:40Z` – `2026-08-22T12:47Z`
- prior BLOCK event (journal): `2026-08-22T12:09:01Z` (15:09:01 MSK)

## n7 / n8 GPU state
### n7 (`bootsmam-k8s-clnt01-n7-gpu`, 10.129.13.77, Turing sm_75)
- 2× Quadro RTX 6000, 23040 MiB each
- GPU0: used 20545 MiB / free 1957 MiB, util 0%, temp 34C
- GPU1: used 20545 MiB / free 1957 MiB, util 0%, temp 35C
- processes: 2× `/usr/bin/python3` (TP=2), each ~20534 MiB → serving `vllm-32b-instruct-awq` (Qwen2.5)

### n8 (`bootsman-k8s-clnt01-n8-gpu`, 10.129.13.78, Turing sm_75)
- 2× Quadro RTX 6000, 23040 MiB each
- GPU0: used 20565 MiB / free 1937 MiB, util 0%
- GPU1: used 20565 MiB / free 1937 MiB, util 0%
- processes: 2× `/usr/bin/python3` (TP=2), each ~20554 MiB → serving `vllm-qwen3-32b-awq` (Qwen3)

## Namespace `aither-inference` — model-related inventory
Deployments (Ready):
- `vllm-32b-instruct-awq` 1/1 (Qwen2.5-32B-AWQ) — node n7
- `vllm-qwen3-32b-awq`    1/1 (Qwen3-32B-AWQ)    — node n8
- `vllm-14b-instruct`     0/0 (scaled to 0, pre-existing)
- `vllm-32b-gptq`         0/0 (scaled to 0, pre-existing)
- `nginx-gateway-32b`     0/2 (readiness 502, pre-existing, targets qwen-32b-gptq)

No Deployment / Service / Pod / ReplicaSet named `qwen38` / `qwen3.8` exists anywhere in the cluster
(`kubectl get deploy,rs,pod,svc -A | grep -iE 'qwen3\.8|qwen38'` → NONE FOUND).

## Qwen2.5 state (rollback baseline — intact)
- Deployment `vllm-32b-instruct-awq`: 1/1 Ready, node n7, restart count 0
- pod `vllm-32b-instruct-awq-7fbcb77c99-mr4qn`: Running since `2026-08-06T18:30:30+03:00`, Ready=True
- image: `vllm/vllm-openai@sha256:6cf9808ca8810fc6c3fd0451c2e7784fb224590d81f7db338e7eaf3c02a33d33` (vLLM 0.8.5)
- args: `--served-model-name qwen2.5-32b-instruct`, TP=2, gpu-mem 0.90, max-model-len 65536, awq
- hostPath: `/data/models/Qwen2.5-32B-Instruct-AWQ` (n7)
- Service `vllm-32b-instruct-awq` ClusterIP 10.104.6.135:8000, endpoint 10.244.1.222:8000
- `/health` → HTTP 200; `/v1/models` → HTTP 401 (VLLM_API_KEY enforced; not readable without auth)

## Qwen3-32B state (n8 invariant — unchanged)
- Deployment `vllm-qwen3-32b-awq`: 1/1 Ready, node n8, restart count 0
- pod `vllm-qwen3-32b-awq-86cb6c9845-n2xpg`: Running since `2026-08-10T12:00:28+03:00`, Ready=True
- image: `vllm/vllm-openai@sha256:6cf9808ca8810fc6c3fd0451c2e7784fb224590d81f7db338e7eaf3c02a33d33` (vLLM 0.8.5)
- args: `--served-model-name qwen3-32b`, TP=2
- hostPath: `/data/models/Qwen3-32B-AWQ` (n8)
- Service `vllm-qwen3-32b-awq` ClusterIP 10.100.53.110:8000, endpoint 10.244.0.252:8000
- `/health` → HTTP 200; `/v1/models` → HTTP 401 (VLLM_API_KEY)

## Qwen3.8 residual state (PARTIAL)
- No Deployment/Service/Pod/ReplicaSet (verified cluster-wide).
- Model directory `/data/models/Qwen3.8-27B-FP8` EXISTS on n7: 22 GiB, 57 `.safetensors` shards on disk.
- `model.safetensors.index.json` references **66** shards; **8 shards MISSING**:
  `mtp.safetensors`, `outside.safetensors`, `layers-6/7/8/9/61/63.safetensors` → download INCOMPLETE.
- **Orphaned download process STILL RUNNING on n7**:
  `root 3291298 /usr/bin/python3 /usr/local/bin/hf download Qwen/Qwen3.8-27B-FP8 --revision 017b9c7af6b5689d5dd426a76e0bc077eb5ca20a --local-dir /data/models/Qwen3.8-27B-FP8`
  (started 14:21 MSK, elapsed ≈ 1h26m at 15:46 MSK; actively writing `layers-7.safetensors` at 15:46:25 MSK).
- Model metadata (`config.json`):
  - `architectures: ["Qwen3_5ForConditionalGeneration"]`, `model_type: qwen3_5` — MULTIMODAL (vision tower, 64 language layers + MTP).
  - `quantization_config: {quant_method: fp8, fmt: e4m3, weight_block_size: [128,128], activation_scheme: dynamic}`.
  - Implication: FP8 block-quantized (Marlin-class) multimodal model — the exact Turing sm_75 compatibility risk flagged in the cutover task §7.
- Image `vllm/vllm-openai:v0.27.1`: **NOT present** (no tag 0.27.1, and the manifest digest
  `sha256:c2f3b1b964e47809b722b5e75b61b1e7b39a50f70388cf2bf2418f16a9f31da2` is NOT in n7 containerd).
  Running vLLM is 0.8.5 (`sha256:6cf9808...`).

## Safe endpoint status codes (read-only, no auth / no inference)
- Qwen2.5 `/health` (in-pod) → 200
- Qwen3 `/health` (in-pod) → 200
- Qwen2.5 `/v1/models` → 401 `{"error":"Unauthorized"}` (VLLM_API_KEY)
- Qwen3 `/v1/models` → 401 `{"error":"Unauthorized"}` (VLLM_API_KEY)
- Test Zone `http://10.129.13.78:30080/health` → 200
- Test Zone `http://10.129.13.78:30080/api/v1/models` → 401 `{"detail":"Authentication required"}`
- Prod `https://fb1.spb.ru:10443/health` → 200
- Authenticated inference NOT performed (as required).

## Failure / restore-failure findings (root cause)
Journal `aither-hermes-exec@*` (2026-08-22 14:15–15:10 MSK), non-secret excerpt:

```
aither-hermes-root-exec[604267]: subprocess.TimeoutExpired: Command
  ['/usr/local/lib/hermes-agent/venv/bin/hermes', '-z', 'Read AGENTS.md, ...'] 
  timed out after 3600 seconds
aither-hermes-root-exec[604267]: File ".../aither-hermes-root-exec", line 154, in main
    fail("BLOCKED_TIMEOUT")
aither-hermes-root-exec[604267]: BrokenPipeError: [Errno 32] Broken pipe
systemd[1]: aither-hermes-exec@24-604246-1000.service: Main process exited, code=exited, status=120/n/a
```

Most probable cause chain:
1. Hermes executor (root) began the cutover and launched a blocking `hf download` of the
   ~27B FP8 model on n7 (started 14:21 MSK).
2. The download exceeded the H2 bridge's hard timeout of **3600 s** (`subprocess.run(..., timeout=3600)`).
3. At 15:09:01 MSK the root-exec killed/timed-out the Hermes subprocess (`subprocess.TimeoutExpired`),
   then tried to emit `BLOCKED_TIMEOUT` but the observer socket was already closed →
   `BrokenPipeError [Errno 32]` → non-zero exit.
4. The `hf download` child was ORPHANED and is still running (not in the killed process group).
5. Runner recorded `task failed: command exited with status 1; restore also failed: command exited with status 1`.

Restore-failure interpretation: the executor was terminated by timeout mid-task, so its rollback path
never completed; the "restore" command also returned non-zero. However, Qwen2.5 was **never** scaled
down (pod Running since Aug 6, restart count 0), so no runtime degradation actually occurred — the
cutover failed before the controlled replacement (§8) mutated the serving state.

Pre-existing, unrelated observations: `aither-gateway` (0/2, readiness 503) and `nginx-gateway-32b`
(0/2, readiness 502) — both 25–34 days old, tied to `qwen-32b-gptq` being scaled to 0; not caused by
the Qwen3.8 cutover.

## Runtime classification
**PARTIAL_CUTOVER_SAFE** — Qwen3.8 partial exists (incomplete model download + live orphaned
`hf download` process on n7), while Qwen2.5 and Qwen3 services remain healthy and no Qwen3.8 is serving.

## Corrective actions (NOT executed here — read-only audit)
1. Terminate the orphaned `hf download` process on n7 (PID 3291298) and verify no further partial writes.
2. Decide path with Owner/Architect:
   a. Resume/complete the Qwen3.8-27B-FP8 download to `/data/models/Qwen3.8-27B-FP8` (missing 8 shards), then
      pull `vllm/vllm-openai:v0.27.1` (pinned digest) and run the FP8/sm_75 compatibility gate; OR
   b. Remove the partial model and keep clean Qwen2.5 baseline.
3. Fix the harness so long downloads are not run as blocking subprocesses under the 3600 s H2 timeout
   (e.g. run download via `nohup`/systemd transient on the node, or raise/decouple the timeout), and ensure
   child processes are reaped on executor termination.
4. Prove Qwen3_5 multimodal FP8 (Marlin-class block-quant) compatibility on Turing sm_75 before any
   catalog/routing cutover; fail-closed otherwise.

## SECRETS_EXPOSED: NO
