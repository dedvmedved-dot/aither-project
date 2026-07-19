# TP=2 Decision Report

Date: 2026-07-19
Executor: hermes@vps2
Repository branch: aither-v2
Commit: (this commit)

## 1. Objective

Доказательно принять решение по Tensor Parallelism для MVP.

## 2. Definitions

| Term | Meaning |
|---|---|
| TP=1 | Одна модель выполняется на одной GPU |
| TP=2 | Одна модель разделяется между двумя GPU через Tensor Parallelism |
| NCCL | NVIDIA Collective Communications Library, механизм обмена между GPU |
| GPU limit | Kubernetes лимит `nvidia.com/gpu` для Pod |
| KV-cache | память под контекст/токены во время генерации |

## 3. Evidence

| Evidence | Path |
|---|---|
| Pods wide | evidence/vllm-pods-wide.txt |
| Deployments YAML | evidence/vllm-deployments-yaml.txt |
| Pods YAML | evidence/vllm-pods-yaml.txt |
| GPU limits | evidence/vllm-gpu-limits.txt |
| Tensor parallel grep | evidence/vllm-tensor-parallel-grep.txt |
| 14B logs | logs/vllm-14b-instruct-tensor-parallel.log |
| 32B logs | logs/vllm-32b-gptq-tensor-parallel.log |
| Stage 02 load summary | evidence/stage02-load-summary.txt |

## 4. Current observed configuration

| Parameter | 14B | 32B |
|---|---|---|
| Deployment | vllm-14b-instruct | vllm-32b-gptq |
| Pod | vllm-14b-instruct-7f6f784dcb-g2h5d | vllm-32b-gptq-7d6dc7c64-r82nh |
| Node | n7 (bootsmam-k8s-clnt01-n7-gpu) | n7 |
| GPU limit | 1 | 1 |
| Tensor parallel size | not explicitly set, interpreted as TP=1 | `--tensor-parallel-size "1"` |
| NCCL usage observed | yes (NCCL init in logs) | yes (NCCL init in logs) |
| Pod restarts | 0 | 0 |
| OOM observed | no | no |
| Stage 02 load passed | yes | yes |

## 5. TP=1 assessment for MVP

TP=1 уже доказал работоспособность inference-слоя по Stage 02:

| Metric | Result |
|---|---|
| Duration | 3607s |
| 14B requests | 330/330 |
| 32B requests | 330/330 |
| Gateway requests | 66/66 |
| HTTP errors | 0 |
| Timeouts | 0 |
| Pod restarts | 0 |
| GPU OOM | 0 |

Conclusion:

```
TP=1 is sufficient for MVP inference acceptance.
```

## 6. TP=2 advantages

| Advantage | Applicability to current MVP |
|---|---|
| More total VRAM for one model | Not required now |
| Larger context length | Not required now |
| Larger model support | Post-MVP |
| Higher throughput potential | Requires separate benchmark |
| Lower OOM risk for very large workloads | Not currently observed |

## 7. TP=2 risks

| Risk | Impact |
|---|---|
| NCCL errors | Can break model startup/inference |
| Multi-GPU scheduling complexity | Pod must get 2 GPUs on same node |
| Higher diagnostic complexity | More failure modes |
| Possible latency regression | Inter-GPU communication overhead |
| Reduced GPU availability | One model consumes 2 GPUs instead of 1 |
| No HA benefit | TP=2 does not provide failover |

## 8. Decision

Decision:

```
TP=1 ACCEPTED FOR MVP.
TP=2 POSTPONED TO POST-MVP OPTIMIZATION.
```

Status:

```
RISK ACCEPTED
```

## 9. Conditions to revisit TP=2

Revisit TP=2 if one or more conditions appear:

| Condition | Evidence required |
|---|---|
| CUDA OOM | logs/events |
| Need larger context length | product requirement |
| Need higher throughput | benchmark/SLA |
| Need larger model | model requirement |
| 32B no longer fits one GPU | pod logs/GPU memory |
| Concurrent usage exceeds TP=1 capacity | load test |

## 10. Findings

| ID | Finding | Status | Target stage |
|---|---|---|---|
| TP2-01 | TP=2 not required for MVP | RISK ACCEPTED | Post-MVP |
| TP2-02 | TP=2 does not improve HA | DOCUMENTED | Architecture notes |
| TP2-03 | TP=2 requires separate benchmark before production use | DOCUMENTED | Post-MVP |

## 11. Conclusion

Status:

```
PASSED
```

MVP recommendation:

```
Keep TP=1 for MVP. Do not enable TP=2 before Stage 11 RC1.
```
