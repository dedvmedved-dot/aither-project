# 60-Minute Load Test Report

Date: 2026-07-19
Executor: hermes@vps2
Repository branch: aither-v2
Commit: (this commit)

## 1. Objective

Проверить устойчивость 14B/32B inference backend под длительной нагрузкой 60 минут.

## 2. Evidence

| Evidence | Path |
|---|---|
| Pods before | evidence/load-test-pods-before.txt |
| Pods after | evidence/load-test-pods-after.txt |
| Events before | evidence/aither-inference-events-before.txt |
| Events after | evidence/load-test-events-tail.txt |
| Benchmark log | logs/benchmark-load-60min.log |
| 14B logs after | logs/vllm-14b-after-load-tail.log |
| 32B logs after | logs/vllm-32b-after-load-tail.log |
| GPU before | evidence/load-test-gpu-before.txt |
| GPU after | evidence/load-test-gpu-after.txt |

## 3. Test parameters

| Parameter | Value |
|---|---|
| Duration target | 60 minutes |
| Actual duration | **3607 seconds (~60 min 7 sec)** |
| 14B endpoint | vllm-14b-instruct.aither-inference.svc:8000/v1/chat/completions |
| 32B endpoint | vllm-32b-gptq.aither-inference.svc:8000/v1/completions |
| Gateway endpoint | nginx-gateway-32b.aither-inference.svc:8000/v1/completions |
| Gateway test frequency | Every 5 requests (~40s) |
| Container image | curlimages/curl:8.10.1 |
| Job status | **Complete (1/1)** |

## 4. Results summary

| Metric | 14B | 32B | Gateway |
|---|---:|---:|---:|
| Total requests | 330 | 330 | 66 |
| Success count | 330 | 330 | 66 |
| HTTP 2xx | 330 | 330 | 66 |
| HTTP 4xx | 0 | 0 | 0 |
| HTTP 5xx | 0 | 0 | 0 |
| Timeouts | 0 | 0 | 0 |
| Error rate | **0%** | **0%** | **0%** |

## 5. Pod stability

| Workload | Restarts before | Restarts after | Status |
|---|---:|---:|---|
| vLLM 14B | 0 | 0 | ✅ STABLE |
| vLLM 32B | 0 | 0 | ✅ STABLE |
| nginx-gateway-32b | 0 | 0 | ✅ STABLE |

## 6. GPU stability

| Metric | Before | After | Status |
|---|---|---|---|
| GPU 0 (14B) memory | — | 21105 MiB / 22502 MiB | ✅ |
| GPU 1 (32B) memory | — | 19143 MiB / 22502 MiB | ✅ |
| OOM observed | — | **NO** | ✅ |

## 7. BM-01 resolution

| ID | Previous status | Current status | Evidence |
|---|---|---|---|
| BM-01 | benchmark-endurance-60min Failed (82m) | **RESOLVED** — benchmark-load-60min completed successfully (60min, 0 errors) | logs/benchmark-load-60min.log, evidence/benchmark-load-60min-job-wide.txt |

## 8. Conclusion

Status: **PASSED**

All acceptance criteria met:
- ✅ duration >= 60 minutes (3607s)
- ✅ pod restarts = 0
- ✅ GPU OOM = 0
- ✅ 14B success rate = 100%
- ✅ 32B success rate = 100%
- ✅ HTTP 5xx = 0
- ✅ timeouts = 0
- ✅ benchmark log preserved
