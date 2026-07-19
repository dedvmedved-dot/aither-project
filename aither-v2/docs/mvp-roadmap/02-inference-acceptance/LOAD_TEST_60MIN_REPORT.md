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
| Pods after | (pending — test running) |
| Events before | evidence/aither-inference-events-before.txt |
| Events after | (pending) |
| Benchmark log | (pending — test running) |
| GPU before | evidence/load-test-gpu-before.txt |
| GPU after | (pending) |

## 3. Test parameters

| Parameter | Value |
|---|---|
| Duration target | 60 minutes |
| Actual duration | IN PROGRESS (~24 min elapsed) |
| 14B endpoint | vllm-14b-instruct.aither-inference.svc:8000/v1/chat/completions |
| 32B endpoint | vllm-32b-gptq.aither-inference.svc:8000/v1/completions |
| Gateway endpoint | nginx-gateway-32b.aither-inference.svc:8000/v1/completions |
| Container image | curlimages/curl:8.10.1 |

## 4. Results

**Status: RUNNING** — Job `benchmark-load-60min` running since ~22:10 MSK. Expected completion: ~23:10 MSK.

Results will be collected after job completion.

## 5. Conclusion

Status: IN PROGRESS (will be updated after job completion)
