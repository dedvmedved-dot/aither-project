# Target Endpoints — Stage U1.0

## External Access (fb1.spb.ru)

| Endpoint | Purpose | Auth | Backend Path |
|----------|---------|------|-------------|
| `https://fb1.spb.ru/` | Web Portal / Chat | Session | Portal Frontend → Portal Backend |
| `https://fb1.spb.ru/login` | Login page | Public | Portal Frontend (SPA) |
| `https://fb1.spb.ru/register` | Registration | Public | Portal Frontend → Portal Backend → AI Platform |
| `https://fb1.spb.ru/settings/api-keys` | API Key management | Session | Portal Frontend → Portal Backend → AI Platform |
| `https://fb1.spb.ru/docs` | API Documentation | Public | Portal Frontend → Portal Backend → AI Platform |
| `https://fb1.spb.ru/health` | Health check | None | Portal Frontend → Portal Backend |
| `https://fb1.spb.ru/api/v1/models` | List models | API Key / Session | Portal Frontend → Portal Backend → AI Platform |
| `https://fb1.spb.ru/api/v1/chat/completions` | Chat completions | API Key / Session | Portal Frontend → Portal Backend → AI Platform → LLM Gateway → vLLM |
| `https://fb1.spb.ru/api/v1/status` | API status | None | Portal Frontend → Portal Backend |

## Internal Access (10.129.13.78)

| Endpoint | Purpose | Backend Path |
|----------|---------|-------------|
| `https://10.129.13.78/` | Web Portal / Chat | Same as external |
| `https://10.129.13.78/login` | Login page | Same as external |
| `https://10.129.13.78/register` | Registration | Same as external |
| `https://10.129.13.78/settings/api-keys` | API Key management | Same as external |
| `https://10.129.13.78/docs` | API Documentation | Same as external |
| `https://10.129.13.78/health` | Health check | Same as external |
| `https://10.129.13.78/api/v1/models` | List models | Same as external |
| `https://10.129.13.78/api/v1/chat/completions` | Chat completions | Same as external |

## Deployment Sequence

1. **U1.1** — DNS, firewall, TLS certificate
2. **U1.2** — Ingress deployment and configuration
3. **U1.3** — Web Chat and API Key management verification
4. **U1.4** — OpenAI-compatible API endpoint verification
5. **U1.5** — User documentation
6. **U1.6** — E2E acceptance testing
7. **U1.7** — User onboarding
