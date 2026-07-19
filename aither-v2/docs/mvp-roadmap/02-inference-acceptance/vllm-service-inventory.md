# vLLM Service Inventory

Date: 2026-07-19
Executor: hermes@vps2
Repository branch: aither-v2
Commit: (this commit)

## 1. Objective

Зафиксировать фактическую конфигурацию 14B и 32B inference services.

## 2. Evidence

| Evidence | Path |
|---|---|
| Pods | evidence/vllm-pods-wide.txt |
| Services | evidence/vllm-services.txt |
| Deployments | evidence/vllm-deployments.txt |
| Endpoints | evidence/vllm-endpoints.txt |
| 14B logs | logs/vllm-vllm-14b-instruct-tail.log |
| 32B logs | logs/vllm-vllm-32b-gptq-tail.log |

## 3. Model inventory

| Field | 14B | 32B |
|---|---|---|
| Deployment name | vllm-14b-instruct | vllm-32b-gptq |
| Pod name | vllm-14b-instruct-7f6f784dcb-g2h5d | vllm-32b-gptq-7d6dc7c64-r82nh |
| Node | n7 (bootsmam-k8s-clnt01-n7-gpu) | n7 |
| Service name | vllm-14b-instruct | vllm-32b-gptq |
| Service DNS | vllm-14b-instruct.aither-inference.svc:8000 | vllm-32b-gptq.aither-inference.svc:8000 |
| Port | 8000 | 8000 |
| Endpoint allowed | /v1/chat/completions | /v1/completions |
| Endpoint blocked | — | /v1/chat/completions (gateway: 422) |
| Model path/name | qwen-14b | qwen-32b-base |
| Quantization | None (FP16/bf16, cpu-offload 10G) | GPTQ 4-bit |
| Tensor parallel size | 1 | 1 |
| GPU limit | 1 | 1 |
| Readiness status | Running 1/1 | Running 1/1 |
| Restart count | 0 | 0 |
| API key required | Yes (VLLM_API_KEY) | Yes (VLLM_API_KEY) |

## 4. Current restrictions

| Restriction | Status | Evidence |
|---|---|---|
| 32B chat endpoint blocked (gateway) | PASSED (HTTP 422) | logs/benchmark-smoke.log |
| 32B completion endpoint allowed | PASSED (HTTP 200) | logs/benchmark-smoke.log |
| 14B chat endpoint allowed | PASSED (HTTP 200) | logs/benchmark-smoke.log |
| Gateway auth (no token) | PASSED (HTTP 401) | logs/benchmark-smoke.log |
| Gateway auth (wrong token) | PASSED (HTTP 401) | logs/benchmark-smoke.log |
| Gateway auth (valid token) | PASSED (HTTP 200) | logs/benchmark-smoke.log |

## 5. Findings

| ID | Finding | Status | Target stage |
|---|---|---|---|
| BM-01 | benchmark-endurance-60min previously Failed | OBSERVED | Stage 02 |
| GW-01 | gateway has 2/3 ImagePullBackOff pods | OBSERVED | Stage 04 |

## 6. Conclusion

Status: PASSED WITH FINDINGS
