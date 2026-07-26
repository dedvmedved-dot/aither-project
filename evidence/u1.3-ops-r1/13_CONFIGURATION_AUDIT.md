# U1.3-OPS-R1 — CONFIGURATION AUDIT

**Evidence:** logs/14-config-scan.log

## ConfigMaps (5)

| ConfigMap | Keys | Status |
|-----------|------|--------|
| aither-bff-config | 1 | ✅ |
| aither-portal-config | 4 (nginx.conf + index.html) | ✅ |
| aither-portal-frontend-config | 2 (nginx.conf + index.html) | ✅ |
| nginx-gateway-32b | 1 | ✅ |
| kube-root-ca.crt | 1 | System |

## Secrets (4, keys only)

| Secret | Keys |
|--------|------|
| aither-bff-auth | ADMIN_USERNAME, ADMIN_PASSWORD_HASH, SESSION_SECRET, AUTH_TOKEN_HASH_SECRET, BFF_14B_UPSTREAM_AUTH_TOKEN, BFF_32B_GATEWAY_AUTH_TOKEN |
| aither-identity-secret | 3 keys |
| aither-ai-platform-secret | 1 key |
| vllm-api-key | 1 key |

## Deployment Security

| Deployment | Uses ConfigMap | Uses Secret |
|------------|:---:|:---:|
| aither-ai-platform | — | vllm-api-key |
| aither-identity | — | aither-identity-secret |
| aither-bff | — | aither-bff-auth |

## Findings
- **No hardcoded passwords in ConfigMaps** ✅
- **No hardcoded API keys** ✅
- **All credentials via secretKeyRef** ✅
- **No test credentials found** ✅
- **Portal HTML contains athr_... as documentation examples only** ✅
