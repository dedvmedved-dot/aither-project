# Aither Portal — INSTRUCTIONS.md

## Overview

Stage 07.2 Portal provides a web UI for Aither MVP with:
- Admin login/logout via BFF
- API token management (create, list, revoke)
- Chat access to 14B (native) and 32B (adapter) models through BFF
- API Access / Agent guide
- System status panel

## Architecture

```
User Browser → aither-portal (nginx:alpine) → aither-bff:8000/api/v1/*
```

Portal uses **same-origin reverse proxy** — no direct calls to vLLM/Gateway/Redis.
All API traffic goes through nginx → `http://aither-bff:8000/api/v1/*`.

## Files

| File | Purpose |
|---|---|
| `tools/portal/index.html` | Portal HTML (all pages as SPA sections) |
| `tools/portal/styles.css` | Dark theme CSS |
| `tools/portal/app.js` | Portal logic — auth, tokens, chat, status |
| `tools/portal/nginx.conf` | nginx reverse proxy to BFF |
| `manifests/07-portal/portal-mvp.yaml` | ConfigMap + Deployment + Service |
| `docs/07-portal/portal-architecture.md` | Architecture documentation |
| `docs/07-portal/portal-acceptance-report.md` | Acceptance report |
| `docs/07-portal/portal-security-notes.md` | Security notes |
| `docs/07-portal/portal-user-guide.md` | User guide |
| `docs/07-portal/api-token-user-guide.md` | API token guide |
| `docs/07-portal/chat-ui-notes.md` | Chat UI notes |

## Key Design Decisions

1. **No OAuth** — MVP uses admin session auth.
2. **No raw token persistence** — raw token shown once, not stored in localStorage/sessionStorage.
3. **No direct vLLM/Gateway access** — portal routes exclusively through BFF.
4. **32B chat is adapter** — portal correctly labels 32B as "chat adapter over completion".
5. **Upstream errors shown honestly** — no hiding of 401/502/500 from upstream.
6. **ConfigMap-based deployment** — source files in `tools/portal/` must match ConfigMap.

## Deployment

```bash
kubectl apply -f manifests/mvp-roadmap/07-portal/portal-mvp.yaml
kubectl -n aither-inference rollout status deploy/aither-portal
```
