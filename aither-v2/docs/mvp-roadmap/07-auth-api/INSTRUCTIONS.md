# Stage 07.1 — Auth / API Token / Agent Access Baseline
## INSTRUCTIONS

### Purpose
Implement central auth layer in BFF for MVP:
- Admin login with session cookies
- API token management (create, list, revoke)
- AI agent access via Bearer tokens
- 32B chat adapter over completion endpoint
- User token isolation: user tokens NEVER forwarded to upstream

### Prerequisites
- Stage 06 completed (Redis + rate limiting)
- BFF deployed (v0.3.0+)
- Kubernetes secret `aither-bff-auth` created in namespace `aither-inference`

### Files changed
| Path | Purpose |
|---|---|
| tools/bff/app.py | BFF v0.4.0 with central auth, token management, 32B chat adapter |
| manifests/mvp-roadmap/05-bff/bff-mvp.yaml | Updated ConfigMap + Deployment with Secret env vars |
| manifests/mvp-roadmap/07-auth-api/bff-auth-secret.example.yaml | Example placeholder secret (never commit real values) |
| docs/mvp-roadmap/07-auth-api/ | Stage 07.1 reports and evidence |
| manifests/mvp-roadmap/07-auth-api/ | Stage 07.1 manifests |

### After deploy
1. Create Secret in cluster:
```
kubectl -n aither-inference create secret generic aither-bff-auth \
  --from-literal=ADMIN_USERNAME=admin \
  --from-literal=ADMIN_PASSWORD_HASH=$(echo -n '<password>' | sha256sum | cut -d' ' -f1) \
  --from-literal=SESSION_SECRET=<random_hex> \
  --from-literal=AUTH_TOKEN_HASH_SECRET=<random_hex> \
  --from-literal=BFF_14B_UPSTREAM_AUTH_TOKEN=<token> \
  --from-literal=BFF_32B_GATEWAY_AUTH_TOKEN=<token>
```
2. Apply manifest: `kubectl apply -f manifests/mvp-roadmap/05-bff/bff-mvp.yaml`
3. Verify: `curl http://aither-bff.aither-inference.svc:8000/health`

### Agent Access
```
curl -H "Authorization: Bearer athr_<token>" http://aither-bff.aither-inference.svc:8000/api/v1/models
curl -H "Authorization: Bearer athr_<token>" -X POST http://aither-bff.aither-inference.svc:8000/api/v1/chat \
  -H "Content-Type: application/json" -d '{"model":"14b","messages":[{"role":"user","content":"hello"}]}'
```
