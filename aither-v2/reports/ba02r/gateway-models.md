# Gateway Multi-Model Analysis

**Stage:** BA-02R  
**Date:** 2026-07-23  
**Author:** Hermes + DeepSeek  

## Current State

### Models Registered in AI Platform

| ID | Name | Model Identifier | Provider | Enabled | Type | Gateway Access |
|----|------|-----------------|----------|---------|------|---------------|
| 1 | qwen-14b-instruct | qwen/Qwen-14B-Instruct | local | ✅ | Chat | ❌ No Gateway route |
| 2 | qwen-32b-gptq | qwen-32b-base | local | ✅ | Completion | ✅ Via nginx-gateway-32b |

### Gateway Configuration

The Gateway (`nginx-gateway-32b`) is a single-upstream nginx that:
- Hardcodes upstream to `10.99.3.103:8000` (= vLLM 32B)
- Returns **422** on `/v1/chat/completions` (model doesn't support chat)
- Only proxies `/v1/completions`, `/health`, `/v1/models`
- Has **no route** to vLLM 14B (`vllm-14b-instruct:8000`, ClusterIP `10.108.67.57`)

### AI Platform Model Routing

AI Platform (`services/ai-platform/app/main.py`):
- Has ONE Gateway URL: `GATEWAY_URL = http://nginx-gateway-32b.aither-inference.svc:8000`
- All model queries go through this single Gateway
- Fallback logic: if `/v1/chat/completions` returns 422, retry with `/v1/completions`
- Fallback ONLY works for models behind the Gateway (currently only qwen-32b-base)
- qwen-14b-instruct fails because Gateway has no route to vLLM 14B

## Test Results

### Model 2: qwen-32b-base ✅

```
POST /api/v1/conversations/{id}/messages → 200
Response: "Bonjour!" (valid AI response)
Full flow: Portal → Backend → AI Platform → Gateway → vLLM 32B ✅
```

### Model 1: qwen-14b-instruct ❌

```
POST /api/v1/conversations/{id}/messages → 502
Detail: "AI service error"
Flow breaks at: AI Platform → Gateway (Gateway has no route to vLLM 14B)
```

## Architecture Decision

### Options Considered

#### Option A: Fix Gateway to support both models

**Requires:**
1. Add second upstream to nginx-gateway-32b config (`vllm-14b-instruct:8000`)
2. Add routing logic (location blocks by model name in URL)
3. Update AI Platform to use model-aware Gateway routing
4. Redeploy Gateway and AI Platform

**Risks:**
- Gateway becomes more complex (multi-upstream nginx)
- vLLM 14B API key must be shared or managed
- Gateway was designed for single-model (per its name: `nginx-gateway-32b`)
- Significant development and testing time

#### Option B: Limit Beta to single model (qwen-32b-base)

**Requires:**
1. Disable qwen-14b-instruct in AI Platform (set `enabled=0`)
2. Remove 14B from Portal UI (models page)
3. Update documentation
4. Document that Beta v0.9 supports **one model**: qwen-32b-base

**Benefits:**
- Simplified user experience (no model confusion)
- Matches current working architecture
- Gateway remains simple and reliable
- Faster time to Beta

## Decision: OPTION B

Officially limit Aither Beta v0.9 to a single model: **qwen-32b-base** (completion model via vLLM 32B).

### Rationale

1. **Gateway architecture** was designed as single-model proxy
2. **14B model** was never fully integrated through Gateway
3. **User-facing simplicity** — Beta users have one model, no confusion
4. **Maturity** — qwen-32b-base + Gateway has been validated through multiple test cycles
5. **Multi-model** can be added post-Beta as a "Phase 2" enhancement

### Implementation

1. Update AI Platform DB: `UPDATE models SET enabled=0 WHERE id=1`
2. Portal Frontend will automatically hide disabled models
3. Documentation updated in `docs/` and `reports/ba02r/`
4. All references to "multi-model" in Beta docs updated to single-model

### Future Plan (Post-Beta)

1. Create `nginx-gateway-multi` with multi-upstream support
2. Add model-aware routing: `/v1/completions/<model_name>`
3. Configure vLLM 14B API key sharing
4. Re-enable qwen-14b-instruct with proper Gateway routing
