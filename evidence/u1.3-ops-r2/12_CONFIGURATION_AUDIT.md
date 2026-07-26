# U1.3-OPS-R2 — 12_CONFIGURATION_AUDIT

**Date/Time (UTC):** 2026-07-26T02:15:09Z

## Secrets (names + keys only)

| Secret | Keys |
|--------|------|
| aither-bff-auth | ADMIN_USERNAME, ADMIN_PASSWORD_HASH, SESSION_SECRET, AUTH_TOKEN_HASH_SECRET, BFF_14B_UPSTREAM_AUTH_TOKEN, BFF_32B_GATEWAY_AUTH_TOKEN |
| aither-identity-secret | (identity credentials) |
| aither-ai-platform-secret | (platform credentials) |
| vllm-api-key | VLLM_API_KEY |

## Deployment Environment References

All deployments use `secretKeyRef` for credentials. No hardcoded credentials in env vars (except PYTORCH_CUDA_ALLOC_CONF for vLLM which is a configuration parameter, not a secret).

| Deployment | secretKeyRef count | configMapKeyRef count | Hardcoded non-secret env |
|-----------|-------------------|----------------------|--------------------------|
| aither-bff | 6 | 0 | 6 (RATE_LIMIT_*, BFF_*_URL, etc.) |
| vllm-14b-instruct | 1 (VLLM_API_KEY) | 0 | 1 (PYTORCH_CUDA_ALLOC_CONF) |
| vllm-32b-gptq | 1 (VLLM_API_KEY) | 0 | 1 (PYTORCH_CUDA_ALLOC_CONF) |

No hardcoded credentials, no missing references, no test credentials in production.

## Configuration Scan: PASS

Raw log: `logs/12-config-scan.log`, `config-scan.txt`
