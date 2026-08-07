# MODEL CATALOG — Aither Platform

**Baseline SHA:** `39a8946143e7a38ceff9faabad024225acbf202e`  
**Date:** 2026-08-07

---

## Current Models

| Model | Model ID | Service/Manifest | Scope | API | Context status |
|-------|----------|-----------------|-------|-----|---------------|
| Qwen2.5-32B-Instruct-AWQ | `qwen2.5-32b-instruct` | `deploy/vllm-32b-instruct-awq.yaml` | `model:32b:chat` | `/v1/chat/completions` | 32K native; **observed:** PASS 30K, FAIL 34K |
| Qwen3-32B-AWQ | `qwen3-32b` | `deploy/vllm-qwen3-32b-awq.yaml` | `model:qwen3:chat` | `/v1/chat/completions` | 32K native + YaRN to 64K; **observed:** PASS 40K, FAIL 50K |

---

## Historical Models (decommissioned)

| Model | Model ID | Status |
|-------|----------|--------|
| Qwen2.5-14B-Instruct | `qwen-14b` | Scaled to 0 (n8), replaced by Qwen3-32B |
| Qwen2.5-32B-GPTQ-Int4 | `qwen-32b-base` | Scaled to 0 (n7), replaced by Qwen2.5-32B-AWQ |

---

## Model Details

### Qwen2.5-32B-Instruct-AWQ

| Parameter | Value |
|-----------|-------|
| Display name | Qwen2.5-32B-Instruct-AWQ |
| Architecture | Qwen2.5-32B-Instruct |
| Parameters | 32B |
| Quantization | AWQ 4-bit |
| Size | ~19 GB |
| Node | n7 (bootsmam-k8s-clnt01-n7-gpu) |
| GPU | 2× Quadro RTX 6000 (24 GB) |
| Tensor Parallel | 2 |
| Context (configured) | 65536 |
| Context (observed) | PASS at 30K, degradation at 34K |
| API | OpenAI-compatible `/v1/chat/completions` |
| Features | Chat, instruction following, tool calling |
| Thinking mode | N/A (not supported) |
| vLLM flags | `--enforce-eager`, `--enable-auto-tool-choice`, `--tool-call-parser hermes` |

### Qwen3-32B-AWQ

| Parameter | Value |
|-----------|-------|
| Display name | Qwen3-32B-AWQ |
| Architecture | Qwen3-32B |
| Parameters | 32B |
| Quantization | AWQ 4-bit |
| Size | ~19 GB |
| Node | n8 (bootsman-k8s-clnt01-n8-gpu) |
| GPU | 2× Quadro RTX 6000 (24 GB) |
| Tensor Parallel | 2 |
| Context (configured) | 65536 (with `VLLM_ALLOW_LONG_MAX_MODEL_LEN`) |
| Context extension | YaRN (rope_scaling) — REPORTED RUNTIME, not in tracked files |
| Context (observed) | PASS at 40K, degradation at 50K |
| API | OpenAI-compatible `/v1/chat/completions` |
| Features | Chat, instruction following, tool calling, thinking mode (disabled by default) |
| Thinking mode | Disabled in Portal via `chat_template_kwargs`; runtime patch in `tokenizer_config.json` |
| vLLM flags | `--enforce-eager`, `--enable-auto-tool-choice`, `--tool-call-parser hermes` |

---

## Performance Observations

> **Reported from 06–07.08.2026 session. Not a formal benchmark.**

| Test | Qwen2.5-32B | Qwen3-32B |
|------|-------------|-----------|
| Expanded biography answer | ~26 sec, 705 tokens | ~105 sec, 1590 tokens |
| Relative speed | 1× | ~4× slower |
| Answer quality | Good, plain text | Excellent, markdown structure |
| Formal benchmark | NOT PERFORMED | NOT PERFORMED |

---

## Hermes Integration

| Provider | Model | Port-forward | Config |
|----------|-------|-------------|--------|
| `aither-32b` | `qwen2.5-32b-instruct` | `9999→vllm-32b-instruct-awq:8000` | `max_tokens: 16000`, `compression: false` |
| `aither-qwen3-32b` | `qwen3-32b` | `9998→vllm-qwen3-32b-awq:8000` | `max_tokens: 16000`, `compression: false` |

Alternatively, external users connect through the Portal API at `https://fb1.spb.ru:10443/v1` with an `athr_` API key — no port-forward required.

---

## Aither Portal Integration

| Model ID | Portal URL | Scope required |
|----------|-----------|----------------|
| `qwen2.5-32b-instruct` | `https://fb1.spb.ru:10443/api/v1/chat` | `model:32b:chat` |
| `qwen3-32b` | `https://fb1.spb.ru:10443/api/v1/chat` | `model:qwen3:chat` |
