# Streaming TTFT Report

Date: 2026-07-19
Executor: hermes@vps2
Repository branch: aither-v2
Commit: (this commit)

## 1. Objective

Разделить TTFB и настоящий TTFT.

## 2. Tool

Script: `tools/benchmarks/streaming-ttft-test.py`

Measures:
- TTFB = HTTP time_starttransfer (first byte of HTTP response)
- TTFT = time to first SSE `data:` chunk when `stream=true`
- Total time
- Approximate tokens/sec

## 3. Results

| Model | Endpoint | Stream supported | TTFT | TOTAL | tokens/sec | Status |
|---|---:|---:|---:|---:|---|
| 14B | /v1/chat/completions | yes | (pending) | (pending) | (pending) | IN PROGRESS |
| 32B | /v1/completions | yes (for completion) | (pending) | (pending) | (pending) | IN PROGRESS |

## 4. Execution

Run via Job or manually on n8:
```bash
python3 /tools/benchmarks/streaming-ttft-test.py \
  --target 14b \
  --url http://vllm-14b-instruct.aither-inference.svc:8000/v1/chat/completions \
  --model qwen-14b \
  --api-key $VLLM_API_KEY \
  --output /tmp/ttft-14b.jsonl

python3 /tools/benchmarks/streaming-ttft-test.py \
  --target 32b \
  --url http://vllm-32b-gptq.aither-inference.svc:8000/v1/completions \
  --model qwen-32b-base \
  --api-key $VLLM_API_KEY \
  --output /tmp/ttft-32b.jsonl
```

## 5. Conclusion

Status: IN PROGRESS (script created, execution pending)
