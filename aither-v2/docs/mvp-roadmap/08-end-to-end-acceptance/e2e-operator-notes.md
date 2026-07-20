# E2E Operator Notes

## Access

- Portal: `kubectl port-forward -n aither-inference svc/aither-portal 8080:80`
- BFF: `kubectl port-forward -n aither-inference svc/aither-bff 8000:8000`
- Redis: `kubectl port-forward -n aither-inference svc/aither-redis-rate-limit 6379:6379`

## Portal URLs

| Endpoint | Description |
|---|---|
| `/` | Portal UI (static HTML/CSS/JS) |
| `/health` | BFF health (no auth) |
| `/api/v1/auth/login` | Admin login (POST) |
| `/api/v1/auth/logout` | Admin logout (POST) |
| `/api/v1/auth/me` | Session check (GET) |
| `/api/v1/models` | Model list (auth) |
| `/api/v1/tokens` | Token CRUD (auth) |
| `/api/v1/chat` | Chat (14B native, 32B adapter) |
| `/api/v1/completions` | Completions (32B only) |

## Common Commands

```bash
# Login as admin
TOKEN=$(curl -s http://localhost:8080/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

# Create API token
curl -s http://localhost:8080/api/v1/tokens \
  -H 'Content-Type: application/json' \
  -d '{"name":"my-token","scopes":["model:14b:chat"]}'

# Chat with 14B
curl -X POST http://localhost:8080/api/v1/chat \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer athr_<your_token>' \
  -d '{"model":"14b","messages":[{"role":"user","content":"Hello"}]}'
```

## Known Issues

1. Upstream auth tokens are test-only — model endpoints return 401 internally.
   Fix: replace BFF_14B_UPSTREAM_AUTH_TOKEN and BFF_32B_GATEWAY_AUTH_TOKEN in Secret `aither-bff-auth`.
2. VPN instability affects kubectl access.
3. One nginx-gateway-32b replica in CrashLoopBackOff (one healthy replica running).
4. Portal is nginx:alpine (no python) — debugging requires Portal+BFF combined approach.
