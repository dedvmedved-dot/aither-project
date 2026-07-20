# Aither Portal — API Token User Guide

## What is an API Token?

API tokens allow AI agents and external tools to access Aither models through the BFF API without requiring interactive login.

## Token Format

```
athr_<random_secret>
```

Example (redacted): `athr_...REDACTED`

## Creating Tokens

1. Log into the Portal
2. Go to Tokens page
3. Enter a name (e.g., "my-agent")
4. Select scopes (comma-separated)
5. Click "Create"
6. **Copy the raw token immediately** — it will not be shown again

## Scopes

| Scope | Access |
|---|---|
| `model:14b:chat` | Chat with 14B model (native) |
| `model:32b:completion` | Completions with 32B model |
| `model:32b:chat-adapter` | Chat with 32B (adapter over completion) |
| `tokens:read` | List tokens |
| `tokens:create` | Create new tokens |
| `tokens:revoke` | Revoke existing tokens |

## Using Tokens

```bash
# List models
curl -H "Authorization: Bearer athr_<token>" http://<portal>/api/v1/models

# Chat 14B
curl -X POST -H "Authorization: Bearer athr_<token>" \
  -H "Content-Type: application/json" \
  -d '{"model":"14b","messages":[{"role":"user","content":"Hello"}]}' \
  http://<portal>/api/v1/chat

# Chat 32B (adapter)
curl -X POST -H "Authorization: Bearer athr_<token>" \
  -H "Content-Type: application/json" \
  -d '{"model":"32b","messages":[{"role":"user","content":"Hello"}]}' \
  http://<portal>/api/v1/chat

# Completions 32B
curl -X POST -H "Authorization: Bearer athr_<token>" \
  -H "Content-Type: application/json" \
  -d '{"model":"32b","prompt":"Once upon a time"}' \
  http://<portal>/api/v1/completions
```

## Security

- Raw tokens are NOT stored server-side after creation
- Raw tokens are NOT stored in browser localStorage/sessionStorage
- If a token is lost, revoke it and create a new one
- Tokens are hashed (HMAC-SHA256) before storage
