# Aither MVP — AI Agent Integration Guide

## Overview

AI agents can access Aither models via BFF API using Bearer tokens.

## Quick Start

### 1. Get an API Token (admin creates via BFF)

```bash
# Login as admin
curl -c /tmp/cookies.txt -X POST \
  http://aither-bff.aither-inference.svc:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"yourpassword"}'

# Create agent token
curl -b /tmp/cookies.txt -X POST \
  http://aither-bff.aither-inference.svc:8000/api/v1/tokens \
  -H "Content-Type: application/json" \
  -d '{"name":"my-agent","scopes":["model:14b:chat","model:32b:completion"]}'

# Response includes raw token ONCE — save it!
```

### 2. Agent Calls

```bash
# List models
curl -H "Authorization: Bearer athr_xxx" \
  http://aither-bff.aither-inference.svc:8000/api/v1/models

# 14B Chat
curl -H "Authorization: Bearer athr_xxx" -X POST \
  http://aither-bff.aither-inference.svc:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"model":"14b","messages":[{"role":"user","content":"Hello!"}],"max_tokens":128}'

# 32B Completion
curl -H "Authorization: Bearer athr_xxx" -X POST \
  http://aither-bff.aither-inference.svc:8000/api/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"32b","prompt":"Hello","max_tokens":128}'

# 32B Chat (adapter over completion)
curl -H "Authorization: Bearer athr_xxx" -X POST \
  http://aither-bff.aither-inference.svc:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"model":"32b","messages":[{"role":"user","content":"Hello!"}],"max_tokens":128}'
```

## Rate Limiting

- Default: 10 requests per 60 seconds per token/IP
- Rate limit applies AFTER auth check
- Returns HTTP 429 when exceeded

## Response Codes

| Code | Meaning |
|---|---|
| 200 | Success |
| 401 | No auth / invalid token / revoked token |
| 403 | Insufficient scope |
| 429 | Rate limit exceeded |
| 503 | Auth backend unavailable (Redis) |

## Best Practices

1. **Store API tokens securely** — treat like passwords
2. **Create separate tokens per agent** — enable per-agent revocation
3. **Rotate tokens periodically** — create new, revoke old
4. **Use minimal scopes** — only grant necessary permissions
5. **Monitor token usage** — check `last_used_at` via list endpoint
