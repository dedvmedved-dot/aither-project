# Deployment Report — Stage BA-02R

**Stage:** BA-02R  
**Date:** 2026-07-23  
**Author:** Hermes + DeepSeek  

## Current Deployment State

### Pods

| Pod | Status | Node | Image | Notes |
|-----|--------|------|-------|-------|
| aither-ai-platform-5d89bdb6b5-7kh97 | ✅ Running | n8 (gpu) | `10.129.13.78:5000/aither-ai-platform:ba01r-fix` | With GATEWAY_API_KEY |
| aither-portal-backend-559754567d-599kk | ✅ Running | n8 (gpu) | `:stage18a-82fe433` | With proxy routes |
| aither-portal-frontend-f85dc7769-dlcll | ✅ Running | n7 | `:stage18a-82fe433` | nginx, SPA |
| aither-bff-656ff579b9-fccrq | ✅ Running | n7 | Stage 15 | Old BFF (not in use) |
| aither-identity-67b5994997-2jdvd | ✅ Running | n8 | `:stage18a-82fe433` | With fixed auth credentials |
| nginx-gateway-32b x2 | ✅ Running | n7 | nginx:alpine | Gateway to vLLM 32B |
| vllm-32b-gptq-7d6dc7c64-r82nh | ✅ Running | n7 | vLLM | qwen-32b-base, completion |
| vllm-14b-instruct-7f6f784dcb-g2h5d | ✅ Running | n7 | vLLM | qwen-14b-instruct (disabled in AI Platform) |
| aither-redis-rate-limit | ✅ Running | n7 | Redis | Rate limiting |

**Total: 11/11 pods Running**

### Services

| Service | Type | ClusterIP | Port |
|---------|------|-----------|------|
| aither-ai-platform | ClusterIP | 10.107.239.156 | 8000 |
| aither-portal-backend | ClusterIP | 10.100.101.65 | 8000 |
| aither-portal-frontend | ClusterIP | 10.105.195.81 | 80 |
| aither-portal | ClusterIP | 10.100.145.83 | 80 |
| aither-identity | ClusterIP | 10.105.189.202 | 8000 |
| aither-bff | ClusterIP | 10.106.87.155 | 8000 (unused) |
| nginx-gateway-32b | ClusterIP | 10.106.31.143 | 8000 |
| vllm-32b-gptq | ClusterIP | 10.99.3.103 | 8000 |
| vllm-14b-instruct | ClusterIP | 10.108.67.57 | 8000 |
| aither-redis-rate-limit | ClusterIP | 10.105.190.101 | 6379 |

## Changes Made in BA-02R

### 1. Model Management

**Before:** Both models enabled (qwen-14b-instruct, qwen-32b-gptq)  
**After:** qwen-14b-instruct disabled (`enabled=0`)  

**Method:** Direct SQLite update on AI Platform pod:
```sql
UPDATE models SET enabled=0, updated_at=datetime('now') WHERE id=1;
```

**Effect:** Portal Frontend will only show qwen-32b-gptq in models page. New assistants cannot be created with qwen-14b.

### 2. No Image Changes Required

Portal Backend proxy routes were already deployed (image `stage18a-82fe433` includes the conversations proxy code). No new image build needed for BA-02R.

## Architecture Decision

Implemented **Option B** (see `gateway-models.md`): Beta v0.9 supports **one model** (qwen-32b-base via vLLM 32B through Gateway). Multi-model support deferred to post-Beta.

## Known Infrastructure Issues

1. **K8s API intermittency** — `dial tcp 10.129.13.78:6443: i/o timeout` — affects kubectl from build host
2. **SSH passwordless key** — requires `-i` flag with specific key (`id_ed25519_n8`)
3. **No external DNS** — services accessible only via ClusterIP within cluster
