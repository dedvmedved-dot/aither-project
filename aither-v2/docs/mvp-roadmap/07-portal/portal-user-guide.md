# Aither Portal — User Guide

## Access

Portal is deployed as `aither-portal` service on port 80.
From within the cluster:
```bash
kubectl -n aither-inference port-forward svc/aither-portal 8080:80
# Then open http://localhost:8080
```

## Pages

### Login
- Username: `admin` (default)
- Password: set during deployment via `ADMIN_PASSWORD_HASH` in `aither-bff-auth` Secret
- Session persists via cookie managed by BFF

### Tokens
- **Create**: Enter name and scopes (comma-separated). Raw token shown ONCE.
- **Copy**: Click "Copy" button immediately. Token never shown again.
- **List**: Shows ID, name, scopes, status.
- **Revoke**: Click "Revoke" button. Cannot be undone.

### Chat
- **14B**: Native chat through BFF. Scope: `model:14b:chat`
- **32B**: Chat adapter over completion through BFF. Scope: `model:32b:chat-adapter`
- Upstream errors (401, 502, 500) shown honestly.

### API Guide
Documentation for agent/tool access via Bearer tokens.
