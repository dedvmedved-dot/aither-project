# Streaming TTFT Report

Date: 2026-07-19
Executor: hermes@vps2
Repository branch: aither-v2
Commit: (this commit)

## 1. Objective

Разделить TTFB и настоящий TTFT:
- TTFB = HTTP time_starttransfer;
- TTFT = time to first SSE data chunk when stream=true.

## 2. Evidence

| Evidence | Path |
|---|---|
| 14B TTFT JSONL | evidence/streaming-ttft-14b.jsonl |
| 32B TTFT JSONL | evidence/streaming-ttft-32b.jsonl |
| 14B TTFT log | logs/streaming-ttft-14b.log |
| 32B TTFT log | logs/streaming-ttft-32b.log |

## 3. Results

| Model | Endpoint | Stream supported | TTFT avg | TTFT min | TTFT max | Total avg | tokens/sec | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 14B | /v1/chat/completions | yes | 7.38s | 6.92s | 8.26s | 13.97s | 0.43 | PASSED |
| 32B | /v1/completions | yes | 0.25s | 0.11s | 0.53s | 2.73s | — | PASSED |

## 4. Findings

| ID | Finding | Status | Required action |
|---|---|---|---|
| — | 32B token/sec not calculated (parser needs fix for text completion delta) | MINOR | Fix streaming-ttft-test.py for text completion format |

## 5. Conclusion

Status: PASSED WITH MINOR FINDINGS
