# Endpoint Matrix — Aither / AI Hermes MVP Internal Pilot

| ID | Purpose | External URL | Internal URL | Auth | Backend Service | Current Status | Target Status | Gap | Owning Stage |
|----|---------|-------------|--------------|------|----------------|---------------|--------------|-----|-------------|
| EP-01 | Web Portal / Chat | `https://fb1.spb.ru/` | `https://10.129.13.78/` | Session cookie | Portal Frontend (nginx:stable-alpine) → Portal Backend | GAP — no Ingress, no TLS | Ingress with TLS → nginx → static SPA | DNS, TLS, Ingress needed | U1.1, U1.2 |
| EP-02 | Login | `https://fb1.spb.ru/login` | `https://10.129.13.78/login` | Public (no auth) | Portal Frontend → Portal Backend → Identity Service | CURRENT AND TARGET (SPA route via index.html) | Same | None | U1.3 |
| EP-03 | Registration | `https://fb1.spb.ru/register` | `https://10.129.13.78/register` | Public | Portal Frontend → Portal Backend → AI Platform | GAP — /register route not in SPA | Implement registration form | Registration flow not built | U1.3 |
| EP-04 | API Key Management | `https://fb1.spb.ru/settings/api-keys` | `https://10.129.13.78/settings/api-keys` | Session required | Portal Frontend → Portal Backend → AI Platform | GAP — /settings/api-keys not in SPA nav | API Keys page (tokens-page in SPA) | SPA has tokens but not at this URL | U1.3 |
| EP-05 | Documentation | `https://fb1.spb.ru/docs` | `https://10.129.13.78/docs` | Public | Portal Frontend → Portal Backend → AI Platform (FastAPI auto-docs) | CURRENT (FastAPI `/api/v1/docs`) but at internal service path | Redirect or proxy to FastAPI Swagger docs | Expose docs through nginx | U1.3 |
| EP-06 | Health | `https://fb1.spb.ru/health` | `https://10.129.13.78/health` | Limited | Portal Frontend → Portal Backend | CURRENT AND TARGET (ngnix proxies /health → portal-backend) | Same with rate limiting | None | U1.2 |
| EP-07 | Models API | `https://fb1.spb.ru/api/v1/models` | `https://10.129.13.78/api/v1/models` | API Key or session | Portal Frontend → Portal Backend → AI Platform | CURRENT (via Portal Backend `/api/v1/models`) | Same | None | U1.4 |
| EP-08 | Chat Completions (user) | `https://fb1.spb.ru/api/v1/chat/completions` | `https://10.129.13.78/api/v1/chat/completions` | API Key or session | Portal Frontend → Portal Backend → AI Platform → LLM Gateway → vLLM | GAP — route exists in AI Platform but external path not configured | Full OpenAI-compatible API | Need Ingress + route exposure | U1.4 |
| EP-09 | API Status | `https://fb1.spb.ru/api/v1/status` | `https://10.129.13.78/api/v1/status` | Session not required | Portal Frontend → Portal Backend | CURRENT (Portal Backend `/api/v1/status`) | Same | None | U1.4 |
| EP-10 | FastAPI auto-docs (AI Platform) | `https://fb1.spb.ru/api/v1/ai/docs` | `https://10.129.13.78/api/v1/ai/docs` | Session required | Portal Backend → AI Platform | GAP — required auth, behind Portal Backend | Protected Swagger docs | Auth header forwarding needed | U1.4 |

## Notes

- All services use **ClusterIP** type — no external exposure exists today
- Portal Frontend nginx is the only component that proxies both `/api/` and `/v1/chat/completions`
- The dual path for `/v1/chat/completions` (direct nginx proxy + Portal Backend proxy) is a known architectural issue
- Health endpoint is proxied through nginx and Portal Backend — no direct backend exposure
- FastAPI auto-docs are available at `/api/v1/docs` (Portal Backend) and `/api/v1/ai/docs` (AI Platform)
