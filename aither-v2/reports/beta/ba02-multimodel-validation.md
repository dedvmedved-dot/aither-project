# Stage BA-02 — Multi-Model Validation Report

**Date:** 2026-07-23
**Status:** ⚠️ PARTIAL — 32B confirmed, 14B blocked by architecture

## Model Inventory

| UI Name (BFF) | Type | Registry ID (AI Platform) | vLLM Model | Status |
|---------------|------|--------------------------|------------|--------|
| qwen-14b | chat | qwen-14b-instruct → qwen/Qwen-14B-Instruct | qwen/Qwen-14B-Instruct | ⚠️ Requires API Key (14B vLLM) |
| qwen-32b-base | completion | qwen-32b-gptq → qwen-32b-base | qwen-32b-base | ✅ Fully working via Gateway |

## Model Identifier Consistency

| Layer | qwen-14b | qwen-32b |
|-------|----------|----------|
| BFF UI name | `qwen-14b` | `qwen-32b-base` |
| BFF type | `chat` | `completion` |
| AI Platform DB name | `qwen-14b-instruct` | `qwen-32b-gptq` |
| AI Platform model_identifier | `qwen/Qwen-14B-Instruct` | `qwen-32b-base` |
| vLLM served model | `qwen/Qwen-14B-Instruct` | `qwen-32b-base` |
| AI Platform API (via Gateway) | N/A (goes to 14B directly) | `qwen-32b-base` |

## 32B Validation

Request: `POST /v1/chat/completions` with `model: qwen-32b-gptq`
Result: HTTP 200, model `qwen-32b-base` responds
Latency: ~2s
Path: AI Platform → Gateway → vLLM (qwen-32b-base)

## 14B Limitation

The 14B model (qwen-14b-instruct) cannot be accessed through the current Gateway architecture:
- Gateway only proxies to vLLM 32B (ClusterIP: 10.99.3.103:8000)
- 14B vLLM (at `vllm-14b-instruct:8000`) also requires API Key
- AI Platform has no route to 14B vLLM — all requests go through Gateway → 32B

To enable 14B, one of these is needed:
1. Add 14B endpoint to AI Platform (separate from Gateway)
2. Add 14B route to Gateway nginx config
3. Provide 14B VLLM_API_KEY to AI Platform

## Conclusion

**MULTI-MODEL ACCEPTANCE: PARTIAL** — one of two models fully confirmed. The 32B model works end-to-end through AI Platform → Gateway → vLLM. The 14B model requires infrastructure changes beyond Beta scope.
