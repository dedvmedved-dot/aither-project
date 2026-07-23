# Frontend Audit

**Stage:** BA-02R  
**Date:** 2026-07-23  
**Author:** Hermes + DeepSeek  

## Stack

- **Type:** Vanilla JavaScript SPA (no React/Vue)
- **File:** `services/portal-frontend/app.js` (single file)
- **Server:** nginx:stable-alpine
- **Deployment:** `aither-portal-frontend` (Pod IP: 10.244.1.23)

## SPA Architecture

```
index.html  ←  Skeleton (login form, nav, pages)
    ↓
app.js      ←  Application logic (API calls, state management, routing)
    ↓
styles.css  ←  Styling
```

## All Frontend API Calls

Base URL: `API_URL = '/api/v1'` → nginx `/api/` → `aither-portal-backend:8000`

| Component | Path | Method | Expected | Actual | Notes |
|-----------|------|--------|----------|--------|-------|
| Login | `/api/v1/auth/login` | POST | `{token, user}` | ✅ 200 | Stores token in localStorage |
| Logout | `/api/v1/auth/logout` | POST | 200 | ✅ 200 | Clears token |
| Dashboard | `/version` | GET | `{version}` | ✅ 200 | Direct fetch, not via api() |
| Dashboard | `/health` | GET | `{status: "ok"}` | ✅ 200 | Direct fetch, not via api() |
| Models | `/api/v1/models` | GET | Array of models | ✅ 200 | Requires auth |
| API Keys | `/api/v1/api-keys` | GET | Array of keys | ✅ 200 | Requires auth |
| API Keys | `/api/v1/api-keys/{id}` | DELETE | 200 | ✅ 200 | Requires auth |
| Assistants | `/api/v1/assistants` | GET | Array | ✅ 200 | Requires auth |
| Assistants | `/api/v1/assistants/{id}` | DELETE | 200 | ✅ 200 | Requires auth |
| Chats | `/api/v1/conversations` | GET | Array | ✅ 200 | Requires auth |
| Chat detail | `/api/v1/conversations/{id}` | GET | `{messages}` | ✅ 200 | Requires auth |
| Send message | `/api/v1/conversations/{id}/messages` | POST | `{content}` | ⚠️ 502 | Known issue (model routing) |
| Delete chat | `/api/v1/conversations/{id}` | DELETE | 200 | ✅ 200 | Requires auth |

## Authentication Flow

```javascript
// Login
const res = await api('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
});
authToken = res.data.token;
localStorage.setItem('aither_token', authToken);

// All subsequent calls
const headers = { 'Content-Type': 'application/json' };
if (authToken) headers['Authorization'] = 'Bearer ' + authToken;
const res = await fetch(API_URL + path, { ...opts, headers });
```

## Storage

- **Token:** `localStorage.getItem('aither_token')` — persists across page refreshes
- **No sessionStorage** used — token available after browser restart

## State Management

- `authToken` — loaded from localStorage on page load
- `currentUser` — set after login/me API call
- `currentChatId` — tracks active chat in Chats page
- `currentAssistantId` — tracks selection in assistant dropdown
- Pages shown/hidden via `classList.toggle('active')` — hash routing not used

## Key Observations

1. **2 direct fetch calls** (`/version`, `/health`) bypass the `api()` function — these go directly to nginx which proxies to Portal Backend
2. **No API key management UI** — user can create/delete keys but cannot input API key for direct OpenAI calls (this is by design — API keys are for external use)
3. **No chat title editing** in UI — conversations are created with empty title or server-generated
4. **Model selector** is not per-conversation — assistant is selected at creation time via dropdown
5. **No streaming** — messages are sent and response is awaited as full JSON

## Network Diagram (Frontend → Backend)

```
app.js: fetch('/api/v1/auth/login')
    → nginx: location /api/ { proxy_pass http://aither-portal-backend:8000; }
    → Portal Backend: @app.post("/api/v1/auth/login")
    → Identity: POST /v1/identity/auth

app.js: fetch('/api/v1/conversations')
    → nginx: location /api/
    → Portal Backend: @app.get("/api/v1/conversations")
    → AI Platform: GET /api/v1/conversations

app.js: fetch('/api/v1/conversations/{id}/messages')
    → nginx: location /api/
    → Portal Backend: @app.post("/api/v1/conversations/{id}/messages")
    → AI Platform: POST /api/v1/conversations/{id}/messages
    → Gateway: POST /v1/chat/completions (or /v1/completions)
    → vLLM
```

## Findings

1. ✅ All frontend API endpoints call the correct URLs
2. ✅ Auth token management is correct (localStorage, Bearer header)
3. ✅ No hardcoded backends in frontend code (all via nginx proxy)
4. ✅ UI properly shows/hides admin-only features (model create)
5. ⚠️ CSS class `bootsmam` in pod node names is a typo (should be `bootsman`) — cosmetic, no impact
6. ⚠️ No loading spinner for individual API calls (only global loading overlay)
