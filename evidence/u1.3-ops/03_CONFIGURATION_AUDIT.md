# U1.3-OPS — CONFIGURATION AUDIT

## Secrets in Kubernetes

| Secret | Type | Keys | Referenced By |
|--------|------|------|---------------|
| aither-bff-auth | Opaque | ADMIN_USERNAME, ADMIN_PASSWORD_HASH, SESSION_SECRET, AUTH_TOKEN_HASH_SECRET, BFF_14B_UPSTREAM_AUTH_TOKEN, BFF_32B_GATEWAY_AUTH_TOKEN | aither-bff (secretKeyRef) |
| aither-identity-secret | Opaque | 3 keys | aither-identity |
| aither-ai-platform-secret | Opaque | 1 key | aither-ai-platform |
| vllm-api-key | Opaque | 1 key | vllm deployments |

## ConfigMaps

| ConfigMap | Data Keys | Status |
|-----------|-----------|--------|
| aither-bff-config | 1 (config) | ✅ Valid |
| aither-portal-config | 4 (nginx.conf + index.html) | ✅ Valid |
| aither-portal-frontend-config | 2 (nginx.conf + index.html) | ✅ Valid |
| nginx-gateway-32b | 1 (nginx.conf) | ✅ Valid |

## Environment Variables

- **aither-bff:** All 6 credentials via secretKeyRef from aither-bff-auth ✅
- **aither-portal:** No env vars (static nginx serving) ✅
- **aither-portal-frontend:** No env vars (static nginx serving) ✅

## Git Scan

- `.env.example` in portal/: uses `change-me-to-...` placeholders ✅
- `.env.template` in offline-deploy/: template only ✅
- No `athr_` real tokens in committed files ✅
- Pre-commit hook: PASSED on all commits ✅

## Hardcoded Credentials

- K8s manifests: 0 hardcoded passwords ✅
- Source code: 0 hardcoded credentials ✅
- ConfigMaps: 0 hardcoded credentials ✅
