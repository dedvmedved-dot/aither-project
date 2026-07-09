# 01-architecture.md — Архитектура платформы Aither

> Полная архитектура: см. `docs/user-guide.md` в основном репозитории.

## Обзор

```
Клиент (браузер / API)
  │
  ▼
Nginx (VPS2:80) — SPA + прокси
  │
  ├─ /api/* → BFF (Node.js :3000) — авторизация, чаты, биллинг
  │              │
  │              ├─ PostgreSQL (пользователи, чаты)
  │              └─ Gateway (K8s :30900) — резервирование, rate limit, безопасность
  │                     │
  │                     ├─ Redis (Rate Limiter)
  │                     ├─ PostgreSQL (биллинг)
  │                     ├─ vLLM 14B (n8, Qwen 2.5 14B, 2× RTX 6000)
  │                     └─ vLLM 32B (n7, Qwen 2.5 32B, 2× RTX 6000)
  │
  └─ / → Статика портала (index.html)
```

## Компоненты

| Компонент | Технология | Порт | Хост |
|---|---|---|---|
| Портал (SPA) | Vanilla JS + SSE | 80 | VPS2 |
| BFF | Node.js/Fastify | 3000 | VPS2 |
| Gateway | Python/FastAPI | 30900 | K8s |
| PostgreSQL | 16 | 5432/31113 | K8s |
| Redis | 7-alpine | 6379 | K8s |
| ChromaDB | latest | 8000 | K8s |
| vLLM 14B | vllm-openai | 32293 | n8 |
| vLLM 32B | vllm-openai | 32294 | n7 |
| Prometheus | latest | 30909 | K8s |
| Grafana | latest | 30300 | K8s |

## Поток запроса

1. Клиент → POST /api/v1/chat/completions (Bearer API-Key)
2. Nginx → BFF (JWT auth)
3. BFF → Gateway (reserve токенов)
4. Gateway → vLLM (инференс)
5. Gateway → BFF (settle + ответ)
6. BFF → Клиент (SSE-стриминг)

## Безопасность

- DLP: детекция номеров карт, паспортов, СНИЛС, телефонов
- Prompt Injection: 23 EN + 6 RU паттернов
- Rate Limiting: 60 RPM / 100K TPM на организацию
- JWT RS256 делегирование Portal → Gateway
