# Aither Project

**Token‑as‑a‑Service** — платформа для продажи токенов к LLM через OpenAI‑совместимый API.

## Физическая схема

![Physical Architecture](docs/diagrams/physical-architecture.svg)

## Статус — 90% готовности (46/51 задач)

| Этап | Задач | Выполнено |
|---|---|---|
| 1. MVP | 7 | ✅ 7 |
| 2. Биллинг + каталог | 4 | ✅ 4 |
| 3. Observability + продакшен | 5 | ✅ 3 |
| 4. RAG + кастомизация | 4 | ✅ 4 |
| 5. Продакшен-класс | 7 | ✅ 4 |
| 5a. Требования руководства | 9 | ✅ 9 |
| 6. Эксплуатация | 6 | ✅ 6 |
| 7. Закрытый контур | 7 | ✅ 7 |
| Прочее (LoRA, HPA, CI/CD) | 2 | ✅ 2 |

## Компоненты

| Компонент | Где | Статус |
|---|---|---|
| **vLLM 14B** (Qwen2.5-14B, TP=2) | n8, 2× RTX 6000 | ✅ 28 tok/s |
| **vLLM 32B** (Qwen2.5-32B-GPTQ, TP=2) | n7, 2× RTX 6000 | ✅ 35 tok/s |
| **LoRA astra-14b** (rank=8, 65 MB) | n8 | ✅ доменные знания |
| **API Gateway** (Python) | K8s (n8→n7) | ✅ HPA: 1%/70% CPU |
| **Portal BFF** (Node.js) | VPS2:3000 | ✅ |
| **Portal DB** (PostgreSQL 16) | VPS2:5432 | ✅ |
| **PostgreSQL 16** (биллинг) | K8s (n8) | ✅ |
| **Redis 7** (rate limiting) | K8s (n8) | ✅ |
| **ChromaDB** (RAG) | K8s (n8) | ✅ |
| **Prometheus + Grafana** | K8s (n7) | ✅ :30300 |
| **nginx** (HTTPS :10443) | VPS1 | ✅ |
| **nginx** (портал :80) | VPS2 | ✅ |
| **ЮKassa** | VPS2 | ⬜ тестовый режим |

## Инфраструктура

| Узел | Адрес | Роль | GPU |
|---|---|---|---|
| **VPS1** | 170.168.91.95 | Hermes, nginx, WireGuard | — |
| **VPS2** | 130.17.1.90 | Портал, BFF, БД | — |
| **Cisco 815** | 10.129.11.0/24 | VPN-терминатор | — |
| **n8** | 40.51 / 10.129.13.78 | K8s control-plane, vLLM 14B | 2× RTX 6000 |
| **n7** | 40.50 / 10.129.13.77 | K8s worker, vLLM 32B | 2× RTX 6000 |

## Сеть

```
VPS1 ←→ VPS2: WireGuard (wg0-wg1)
VPS2 → Cisco 815: VPN tun1
Cisco 815 → n7, n8: VLAN 308 (10.129.13.0/24)
n7 ↔ n8: Flannel VXLAN (10.244.0.0/16)
```

## Быстрый старт

```bash
# Портал: https://fb1.spb.ru:10443
# Grafana: http://grafana.130.17.1.90.nip.io
# API: https://fb1.spb.ru:10443/v1/chat/completions
```

## Структура репозитория

```
aither-project/
│
│  📄 README.md                ← этот файл
│  📄 ROADMAP.md               ← дорожная карта проекта
│  📄 lab-journal.md           ← лабораторный журнал (хронология всех изменений)
│  📄 brief.md                 ← исходное ТЗ на платформу
│  📄 status.md                ← сводка статуса задач
│
├── 📁 portal/                 ★ Код портала (SPA + BFF)
│   ├── 📄 server.ts           — BFF-сервер (Node.js/Express, порт 3000)
│   ├── 📄 package.json        — NPM-зависимости
│   ├── 📄 policies.ts         — политики доступа
│   ├── 📄 security.ts         — security middleware
│   ├── 📄 secrets.env         — секреты (PG_URL, JWT_SECRET, OAuth)
│   └── 📁 static/             — статика (фронтенд)
│       ├── 📄 index.html      — пользовательский чат-интерфейс
│       └── 📄 admin.html      — админ-панель (токены, организации)
│
├── 📁 gateway/                ★ API Gateway (Python, Docker-образ)
│   ├── 📄 Dockerfile          — сборка образа (python:3.12-slim)
│   ├── 📄 requirements.txt    — Python-зависимости
│   ├── 📄 gateway.py          — точка входа, роутинг, OpenAI API
│   ├── 📄 auth.py             — JWT-аутентификация
│   ├── 📄 billing.py          — списание токенов, баланс
│   ├── 📄 catalog.py          — каталог моделей (load_catalog)
│   ├── 📄 routing.py          — маршрутизация запросов к vLLM
│   ├── 📄 admin.py            — админ-API (очереди, мониторинг)
│   ├── 📄 dlp.py              — DLP-фильтрация (защита от утечек)
│   ├── 📄 rag.py              — RAG-подсистема (ChromaDB)
│   ├── 📄 delegation.py       — делегирование (JWT-подпись)
│   ├── 📄 usage-collector.py  — сборщик точной статистики использования
│   └── 📄 reservation-reaper.py — очистка просроченных резерваций
│
├── 📁 k8s/                    ★ Kubernetes-манифесты (живой кластер)
│   ├── 📁 gateway/
│   │   ├── 📄 deployment.yaml — Gateway Deployment (образ ghcr.io)
│   │   └── 📄 service.yaml    — Gateway Service (ClusterIP)
│   ├── 📁 vllm-14b/
│   │   ├── 📄 deployment.yaml — vLLM 14B (TP=2, LoRA, n8)
│   │   └── 📄 service.yaml    — vLLM 14B Service + NodePort :32293
│   ├── 📁 vllm-32b/
│   │   ├── 📄 deployment.yaml — vLLM 32B (TP=2, GPTQ, n7)
│   │   └── 📄 service.yaml    — vLLM 32B Service + NodePort :32294
│   └── 📁 hpa/
│       ├── 📄 gateway-hpa.yaml      — Gateway HPA (min=1, max=3)
│       ├── 📄 hpa.yaml              — vLLM HPA (общий)
│       ├── 📄 prometheus-adapter.yaml
│       ├── 📄 prometheus-config.yaml
│       └── 📄 adapter-config.yaml
│
├── 📁 configs/                ★ Эталонные конфигурации
│   ├── 📁 vps1/
│   │   ├── 📄 aither-failover       — nginx :10443 (основной вход)
│   │   └── 📄 gateway-proxy         — nginx :30900 → K8s Gateway
│   ├── 📁 vps2/
│   │   └── 📄 remote-configs.txt    — docker-compose, nginx, systemd BFF
│   ├── 📁 vps3/                     — альтернативный деплой (запасной)
│   ├── 📁 k8s/
│   │   ├── 📄 gateway-code.yaml     — эталонный ConfigMap кода Gateway (313 KB)
│   │   └── 📄 gateway-catalog.yaml  — эталонный каталог моделей
│   ├── 📁 bff/
│   │   └── 📄 .env.template         — шаблон переменных BFF
│   └── 📄 nginx-failover.conf       — запасной конфиг nginx
│
├── 📁 offline-deploy/         ★ Офлайн-пакет для закрытого контура (v1.1.0)
│   ├── 📄 README.md           — инструкция по развёртыванию
│   ├── 📄 VERSION             — версия пакета
│   ├── 📄 CHANGELOG.md        — история версий
│   ├── 📄 Makefile            — make deploy / test / bundle
│   ├── 📁 docs/               — документация (8 × .md)
│   ├── 📁 k8s/                — эталонные K8s-манифесты
│   ├── 📁 offline/            — офлайн-зависимости (docker, pip, npm, модели)
│   ├── 📁 scripts/            — скрипты эксплуатации (7 шт.)
│   ├── 📁 configs/            — эталонные конфигурации (шаблоны)
│   ├── 📁 playbooks/          — Ansible playbooks (10 шт.)
│   └── 📁 tests/              — приёмо-сдаточные тесты (4 шт.)
│
├── 📁 scripts/                Скрипты деплоя и эксплуатации
│   ├── 📄 deploy.sh           — деплой портала на VPS2
│   ├── 📄 health-check.sh     — проверка всех компонентов
│   ├── 📄 mount-iso-deploy.sh — развёртывание через BMC/ISO
│   ├── 📄 ks-node01.cfg       — Kickstart для n8
│   ├── 📄 ks-node02.cfg       — Kickstart для n7
│   └── 📄 portal-security-check.sh — аудит безопасности портала
│
├── 📁 db/                     Миграции БД
│   └── 📁 migrations/
│       ├── 📄 006_org_id_text.sql
│       ├── 📄 007_subscription_tiers.sql
│       └── 📄 008_auth_tables_k8s.sql
│
├── 📁 delegation/             Ключи делегирования
│   ├── 📄 private.pem         — приватный ключ (JWT-подпись)
│   └── 📄 public.pem          — публичный ключ
│
├── 📁 docs/                   Документация проекта
│   └── 📁 diagrams/
│       └── 📄 physical-architecture.svg — физическая схема (белый фон)
│
├── 📁 diagrams/               Архив схем (статьи, Graphviz)
│   └── *.dot, *.svg, *.png    — архитектура, GPU-стек, поток запросов
│
├── 📁 fine-tuning/            ★ LoRA-скрипты и джобы (QLoRA 4-bit)
│
├── 📁 wiki/                   База знаний Aither (LLM Wiki)
│
├── 📁 references/             Справочные материалы
│
└── 📁 archive/                Архив старых версий (память, профиль)
    └── 📁 Usage-Collector/    — статья про Usage Collector
```

## Дорожная карта

Подробно: [ROADMAP.md](ROADMAP.md)

Ближайшие задачи: #13 YooKassa → #15 Parsec → #27 Production → #28 HPA ✅ → #29 CI/CD ✅
