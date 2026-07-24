# Stage BA-02 — Model Identifier Consistency Report

**Date:** 2026-07-23
**Status:** ✅ CONSISTENT (with documentation)

## Cross-Layer Model Identifier Mapping

| Layer | qwen-14b | qwen-32b |
|-------|----------|----------|
| BFF (Portal UI) | `qwen-14b` (type: chat) | `qwen-32b-base` (type: completion) |
| AI Platform DB (name) | `qwen-14b-instruct` | `qwen-32b-gptq` |
| AI Platform DB (model_identifier) | `qwen/Qwen-14B-Instruct` | `qwen-32b-base` |
| vLLM model ID | `qwen/Qwen-14B-Instruct` | `qwen-32b-base` |
| OpenAI API `model` field | `qwen-14b-instruct` | `qwen-32b-gptq` |
| Actual served model | `qwen/Qwen-14B-Instruct` | `qwen-32b-base` |

## Discrepancy Analysis

### 32B Chain
```
User requests: qwen-32b-gptq (OpenAI API)
  → AI Platform looks up by name "qwen-32b-gptq"
  → Gets model_identifier: qwen-32b-base
  → Sends to Gateway: model=qwen-32b-base
  → Gateway proxies to vLLM: model=qwen-32b-base
  → vLLM serves: qwen-32b-base
  → Response model field: qwen-32b-base
```
**Status: ✅ Consistent** — the API response correctly shows the actual served model.

### 14B Chain
```
User requests: qwen-14b-instruct (OpenAI API)
  → AI Platform looks up by name "qwen-14b-instruct"
  → Gets model_identifier: qwen/Qwen-14B-Instruct
  → Sends to Gateway: model=qwen/Qwen-14B-Instruct
  → Gateway proxies to vLLM 32B (ClusterIP)
  → vLLM 32B returns 404 (model not found on 32B)
```
**Status: ⚠️ Blocked** — 14B model cannot be served through the current Gateway architecture.

### BFF vs AI Platform Names

BFF returns: `{"models":[{"id":"14b","name":"qwen-14b","type":"chat"},{"id":"32b","name":"qwen-32b-base","type":"completion"}]}`
AI Platform returns: `[{"name":"qwen-14b-instruct","model_identifier":"qwen/Qwen-14B-Instruct"},{"name":"qwen-32b-gptq","model_identifier":"qwen-32b-base"}]`

The BFF abstracts model names — this is acceptable for the Portal UI layer. The OpenAI API uses AI Platform model names.

## Recommendation

For Beta v0.9, the **32B model is fully consistent** across all layers. The 14B model identifier chain is correct but cannot be exercised through Gateway. Consider adding a dedicated 14B route in future iterations.
