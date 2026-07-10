# 01-architecture.md — Архитектура платформы Aither (v1.2.0)

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
  │              └─ Gateway (K8s :30900) — резервирование, rate limit, безопасность, RAG
  │                     │
  │                     ├─ Redis (Rate Limiter)
  │                     ├─ PostgreSQL (биллинг)
  │                     ├─ vLLM 14B (n8, Qwen 2.5 14B, 2× RTX 6000)
  │                     ├─ vLLM 32B (n7, Qwen 2.5 32B, 2× RTX 6000)
  │                     └─ chroma-proxy :9000 (эмбеддинги all-MiniLM-L6-v2)
  │                            │
  │                            └─ ChromaDB :8000 (векторная БД, v0.5.23)
  │
  └─ / → Статика портала (index.html)
```

## Компоненты

| Компонент | Технология | Порт | Хост | Примечание |
|---|---|---|---|---|
| Портал (SPA) | Vanilla JS + SSE | 80 | VPS2 | |
| BFF | Node.js/Fastify | 3000 | VPS2 | |
| Gateway | Python/FastAPI | 30900 | K8s | 13 модулей, вкл. hybrid_rag |
| PostgreSQL | 16 | 5432/31113 | K8s | |
| Redis | 7-alpine | 6379 | K8s | |
| **chroma-proxy** | Python HTTP (chromadb/chroma:0.5.23) | 9000 | K8s (n7) | эмбеддинги внутри |
| ChromaDB | chromadb/chroma:0.5.23 | 8000 | K8s (n7) | PVC RWO |
| vLLM 14B | vllm-openai | 32293 | n8 | |
| vLLM 32B | vllm-openai | 32294 | n7 | |
| Prometheus | latest | 30909 | K8s | |
| Grafana | latest | 30300 | K8s | |

## RAG-архитектура (гибридный поиск)

```
Запрос пользователя
  │
  ▼
Gateway (hybrid_rag.py)
  │
  ├─ Wiki Graph (keyword search, 8 страниц)
  │     └─ поиск по ключевым словам + graph expansion
  │
  └─ chroma-proxy :9000 (POST /query)
        │
        ├─ all-MiniLM-L6-v2 → эмбеддинг запроса
        ├─ ChromaDB :8000 → поиск ближайших чанков
        └─ возвращает top-5 чанков с relevance score
              │
              ▼
        Комбинирование wiki + chroma → dedup → sort → top-K
```

Gateway НЕ имеет зависимостей chromadb/sentence-transformers — всё вынесено в chroma-proxy.

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
