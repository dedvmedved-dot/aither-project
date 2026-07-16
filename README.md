# Aither Project

**Token‑as‑a‑Service** — платформа для продажи токенов к LLM через OpenAI‑совместимый API.

## Физическая схема

![Физическая схема Aither](docs/diagrams/physical-architecture-v4.svg)

## Статус — 🟢 Работает (демо-режим)

Чат с моделями, биллинг, админка и VPN-доступ к GPU-нодам восстановлены.
RAG (ChromaDB) — офлайн, Prometheus/Grafana — не запущены.

## Компоненты

| Компонент | Сервер | Тип запуска | Порт | Статус |
|---|---|---|---|---|
| **nginx** (SPA портала) | VPS2 | Docker | :80 | ✅ |
| **PostgreSQL** (portal) | VPS2 | Docker | :5432 | ✅ |
| **BFF** (Node.js, Fastify) | VPS2 | systemd | :3000 | ✅ |
| **vpn-cisco815** (tun1) | VPS2 | Docker | — | ✅ |
| **nginx** (прокси портала) | VPS3 | systemd | :80 | ✅ |
| **vpn-cisco815** (tun0) | VPS3 | Docker | — | ✅ |
| **Cisco 815** (OpenConnect VPN) | 95.137.2.98 | оборудование | :443 | ✅ |
| **Aither Gateway** (FastAPI) | n8 | systemd | :8080 | ✅ |
| **PostgreSQL** (aither) | n8 | systemd | :5432 | ✅ |
| **Redis 7** | n8 | systemd | :6379 | ✅ |
| **vLLM Qwen Coder 14B** | n8 | K8s pod | :30014 | ✅ |
| **vLLM Qwen 2.5 32B GPTQ** | n7 | процесс | :8000 | ✅ |
| **Wiki Graph** (LLM-Wiki) | n8 | /app/wiki | 6 стр. | ✅ |
| **ChromaDB** (векторный RAG) | n7 | K8s | :8000 | ❌ офлайн |
| **chroma-proxy** | n7 | K8s | :9000 | ❌ офлайн |
| **Prometheus + Grafana** | n7 | K8s | :30300 | ❌ не запущены |

## Инфраструктура

| Узел | IP | ОС | Роль | GPU |
|---|---|---|---|---|
| **VPS2** | 130.17.1.90 | Ubuntu 24.04 | Портал: BFF, nginx, PG, VPN Cisco | — |
| **VPS3** | 89.127.217.88 | Ubuntu 24.04 | Фронт: nginx прокси → VPS2, VPN Cisco | — |
| **Cisco 815** | 95.137.2.98 | — | VPN-сервер, маршрутизация 10.129.0.0/16 | — |
| **n8** | 10.129.13.78 | Astra Linux | K8s control-plane: Gateway, PG, Redis, vLLM 14B | 2× RTX 6000 |
| **n7** | 10.129.13.77 | Astra Linux | K8s worker: vLLM 32B GPTQ | 2× RTX 6000 |

## Сеть и туннели

```
Пользователь → VPS3 nginx :80 ──:3000──→ VPS2 BFF :3000
                                           │
                    ┌──────────────────────┤
                    ▼                      ▼
              VPS2 PG :5432        n8 Gateway :8080
                                        │
              ┌────────────┬────────────┼────────────┬────────────┐
              ▼            ▼            ▼            ▼            ▼
         n8 PG :5432  n8 Redis    n8 vLLM 14B   n7 vLLM 32B   Wiki (RAG)
                        :6379      :30014        :8000

═══════════════  VPN-туннели до GPU-нод  ═══════════════

  VPS2 vpn-cisco815 ──tun1 :443──→ Cisco 815 ──10.129.0.0/16──→ n7, n8
  VPS3 vpn-cisco815 ──tun0 :443──→ Cisco 815 ──10.129.0.0/16──→ n7, n8
```

## Доступ

| Ресурс | Адрес |
|---|---|
| Портал Aither | VPS3 :80 → VPS2 BFF |
| Админка | `admin@aither.local` / `Admin123!@#` |
| Gateway health | n8 :8080/health |
| vLLM 14B | n8 :30014 |
| vLLM 32B | n7 :8000 |

## Что починено (16 июля 2026)

- Redis на n8 — iptables блокировал порт :6379, удалён DROP
- Gateway — переведён с HTTPServer на ThreadingHTTPServer
- Админ-доступ — сброшен пароль admin@aither.local, роль super_admin
- VPN VPS3→Cisco — поднят Docker-контейнер с OpenConnect (tun0)
- Прямой доступ VPS3 → n7/n8 через Cisco VPN (без цепочки PVE→VPS2)
- Физическая схема — обновлена (v4), отражает реальное расположение

## Структура репозитория

```
aither-project/
│
├── 📄 README.md                    ← этот файл
├── 📄 ROADMAP.md                   ← дорожная карта (51 задача)
│
├── 📁 portal/                      ★ Портал: SPA + BFF + админка
│   ├── dist/server.js              — BFF (Fastify, :3000)
│   ├── static/                     — статика (фронтенд SPA)
│   │   ├── index.html              — чат-интерфейс
│   │   └── admin.html              — админ-панель
│   ├── docker-compose.yml          — Docker Compose (BFF + PG + nginx)
│   ├── nginx.conf                  — nginx :80 → :3000
│   └── db/                         — миграции БД портала
│
├── 📁 gateway/                     ★ API Gateway (Python)
│   ├── gateway.py                  — JWT, rate limit, billing, vLLM proxy
│   ├── hybrid_rag.py               — гибридный RAG: wiki + chroma-proxy
│   ├── wiki_graph.py               — LLM-Wiki: граф знаний
│   ├── security.py                 — DLP ingress
│   ├── security_egress.py          — Egress DLP
│   ├── catalog.py + catalog.yaml   — каталог моделей
│   ├── routing.py                  — маршрутизация к vLLM
│   ├── admin.py                    — админ-API
│   ├── metrics.py                  — Prometheus-метрики
│   ├── reaper.py                   — очистка резерваций
│   └── requirements.txt            — redis, pyjwt, psycopg2, pyyaml
│
├── 📁 k8s/                         ★ Kubernetes-манифесты
│   ├── gateway/                    — Gateway Deployment + Service
│   ├── vllm-14b/                   — vLLM 14B (n8)
│   ├── vllm-32b/                   — vLLM 32B (n7)
│   ├── chroma-proxy.yaml           — chroma-proxy + ChromaDB
│   └── monitoring/                 — Prometheus + Grafana
│
├── 📁 configs/                     ★ Конфигурации
│   ├── vps2/                       — BFF service, nginx
│   └── vps3/                       — nginx, VPN
│
├── 📁 offline-deploy/              ★ Офлайн-пакет (v1.2.0)
│   ├── playbooks/                  — Ansible playbooks
│   └── offline/                    — Docker images, pip wheels
│
├── 📁 docs/                        ★ Документация
│   ├── diagrams/                   — схемы (DOT, SVG, PNG, JPG)
│   ├── training-manual/            — учебное пособие (24 главы)
│   └── roadmap-manual.md           — дорожная карта
│
├── 📁 wiki/                        База знаний (6 страниц)
├── 📁 scripts/                     Скрипты деплоя
├── 📁 db/migrations/               Миграции БД
└── 📁 .github/workflows/           CI/CD
```
