# Aither Platform — Техническое руководство по дорожной карте

**roadmap-manual.md** — детальное описание каждого этапа разработки платформы Aither.

**Дата:** 10.07.2026  
**Версия:** 1.0  
**Назначение:** Ознакомление технических специалистов, команд разработки и проектировщиков с процессом создания платформы.

---

## Оглавление

1. [Этап 1: MVP](#1-этап-1-mvp-дни-17)
2. [Этап 2: Биллинг и каталог](#2-этап-2-биллинг-и-каталог-дни-810)
3. [Этап 2.5: Авто-баланс и публичный доступ](#3-этап-25-авто-баланс-и-публичный-доступ-день-11)
4. [Этап 3: Observability и продакшен](#4-этап-3-observability-и-продакшен-дни-1114)
5. [Этап 4: RAG и кастомизация](#5-этап-4-rag-и-кастомизация-дни-1518)
6. [Этап 5: Продакшен-класс](#6-этап-5-продакшен-класс-недели-36)
7. [Этап 5a: Требования руководства](#7-этап-5a-требования-руководства-недели-711)
8. [Этап 6: Эксплуатация и развитие](#8-этап-6-эксплуатация-и-развитие-месяц-2)
9. [Этап 7: Пакет для закрытого контура](#9-этап-7-пакет-для-закрытого-контура)

---

## 1. Этап 1: MVP (дни 1–7)

### Описание

Создание минимально жизнеспособного продукта: одноузловой Kubernetes-кластер на GPU-сервере n8-gpu (bootsman-k8s-clnt01-n8-gpu) с одной LLM-моделью, API-шлюзом, порталом и OAuth-аутентификацией.

### Функционал

- Запуск LLM-инференса (Qwen 2.5 14B) на GPU через vLLM
- OpenAI-совместимый API через Gateway с rate limiting (Redis)
- Веб-портал (SPA + BFF) с чат-интерфейсом и SSE-стримингом
- OAuth-вход через GitHub, Google, Яндекс
- Мониторинг GPU-метрик

### Состав компонентов

| Компонент | Версия | Назначение |
|---|---|---|
| Kubernetes | 1.29 | Оркестрация контейнеров |
| containerd | 1.7 | Контейнерный runtime |
| NVIDIA GPU Operator | 24.6 | Управление GPU-драйверами |
| vLLM | 0.6.4 | Инференс-сервер |
| Qwen 2.5 14B Instruct | — | LLM-модель (~28 GB) |
| Gateway (Python/FastAPI) | custom | API-шлюз, rate limit |
| Redis | 7-alpine | Sliding window rate limiter |
| Портал (SPA + BFF) | custom | Веб-интерфейс |
| BFF (Node.js/Fastify) | 4.x | Бэкенд портала |

### Принцип действия

```
Клиент → nginx :10443 → BFF :3000 (JWT auth)
  → Gateway :30900 (rate limit, reserve)
  → vLLM :32293 (инференс)
  → Gateway (settle)
  → BFF → Клиент (SSE-стриминг)
```

1. Клиент авторизуется через OAuth (GitHub/Google/Яндекс)
2. BFF выдаёт JWT-токен, проверяет баланс организации
3. Gateway резервирует токены, проверяет rate limit (Redis sliding window)
4. Запрос отправляется в vLLM, ответ стримится обратно
5. Gateway финализирует списание токенов (settle)

### Физическая схема (MVP)

```
VPS2 (130.17.1.90)                  n8-gpu (40.51)
┌─────────────────────┐    VPN     ┌──────────────────────────┐
│ nginx :80            │←─────────→│ K8s (control-plane)      │
│   ├─ SPA (статика)   │           │                          │
│   └─ /api/* → BFF    │           │  ┌── Gateway :30900 ───┐ │
│                      │           │  │  FastAPI            │ │
│  BFF (Node.js :3000) │           │  │  Rate Limit (Redis) │ │
│  Fastify             │           │  └─────────────────────┘ │
│  OAuth + JWT         │           │            │             │
└──────────────────────┘           │  ┌── vLLM :32293 ─────┐ │
                                   │  │  Qwen 2.5 14B      │ │
                                   │  │  TP=2 (2×RTX6000)  │ │
                                   │  └─────────────────────┘ │
                                   │                          │
                                   │  Redis :6379             │
                                   └──────────────────────────┘
```

### Конфигурационные файлы

| Файл | Назначение |
|---|---|
| `k8s/vllm-14b/deployment.yaml` | Deployment vLLM 14B (TP=2, 2× GPU) |
| `k8s/gateway/deployment.yaml` | Gateway Deployment + Service NodePort :30900 |
| `k8s/redis/deployment.yaml` | Redis для rate limiting |
| `configs/vps1/aither-failover` | nginx :10443 → BFF |
| `configs/vps2/remote-configs.txt` | nginx, systemd BFF |

### Последовательность конфигурации

1. **GPU-узел:** установка NVIDIA-драйвера 570, containerd, nvidia-container-toolkit
2. **K8s:** `kubeadm init`, Flannel CNI, NVIDIA GPU Operator
3. **Модель:** загрузка Qwen2.5-14B-Instruct в `/mnt/models/`
4. **vLLM:** `kubectl apply -f k8s/vllm-14b/deployment.yaml`
5. **Redis + Gateway:** `kubectl apply -f k8s/redis/`, `kubectl apply -f k8s/gateway/`
6. **Портал:** `npm install && npm start` на VPS2, nginx reverse proxy
7. **Проверка:** `curl https://fb1.spb.ru:10443/v1/chat/completions`

### Взаимодействия со смежными объектами

| Компонент A | Компонент B | Протокол | Порт |
|---|---|---|---|
| BFF | Gateway | HTTP + JWT | 30900 |
| Gateway | Redis | Redis protocol | 6379 |
| Gateway | vLLM | HTTP (OpenAI API) | 32293 |
| nginx | BFF | HTTP (reverse proxy) | 3000 |
| BFF | PostgreSQL (VPS2) | SQL | 5432 |

### Потоки данных

```
[OAuth provider] → JWT claims → [BFF] → org_id + balance
[BFF] → POST /v1/chat/completions → [Gateway]
  → rate_limit_check(org_id, rpm=300, tpm=100000)
  → reserve_tokens(model, estimated_tokens)
  → POST /v1/chat/completions → [vLLM]
  ← SSE stream (tokens)
  → settle(reservation_id, actual_tokens)
  ← [BFF] ← SSE stream ← [Клиент]
```

---

## 2. Этап 2: Биллинг и каталог (дни 8–10)

### Описание

Подключение платёжной системы ЮKassa для монетизации, создание каталога моделей с декларативным описанием, добавление второго GPU-узла n7-gpu с 32B-моделью, исправление ошибок портала.

### Функционал

- Пополнение баланса через ЮKassa (тестовый режим)
- Каталог моделей: YAML-описание → динамический UI
- Двухузловой K8s-кластер: n8 (control-plane) + n7 (worker)
- Вторая модель: Qwen 2.5 32B GPTQ
- Автоматический выбор модели в UI на основе каталога

### Состав компонентов

| Компонент | Версия | Назначение |
|---|---|---|
| PostgreSQL 16 (K8s) | 16 | Биллинг: организации, пользователи, транзакции |
| ЮKassa API | v3 | Приём платежей |
| Каталог моделей | catalog.yaml | Декларативное описание моделей |
| vLLM 32B | 0.6.4 | Вторая модель (n7, 2× RTX 6000) |
| Qwen 2.5 32B GPTQ | — | ~20 GB, квантованная |

### Принцип действия

1. Пользователь пополняет баланс → ЮKassa → webhook → BFF → PostgreSQL
2. Gateway при старте загружает `catalog.yaml` → каталог моделей
3. BFF получает список моделей из Gateway → рендерит в UI
4. При выборе модели Gateway маршрутизирует запрос к нужному vLLM-бэкенду

### Физическая схема (этап 2)

```
VPS2 (130.17.1.90)           Cisco815          n8-gpu (40.51)
┌──────────────────┐    VPN   │    VLAN 308    ┌───────────────────────┐
│ nginx :80         │──────────┼──────────────→│ Gateway :30900        │
│ BFF :3000         │          │               │ vLLM 14B :32293       │
│ PostgreSQL :5432  │          │               │ Redis :6379           │
│ ЮKassa webhook    │          │               │ PostgreSQL :5432      │
└──────────────────┘          │               └───────────────────────┘
                              │
                              │               n7-gpu (40.50)
                              └──────────────→┌───────────────────────┐
                                              │ vLLM 32B :32294       │
                                              │  (worker node)        │
                                              └───────────────────────┘
```

### Конфигурационные файлы

| Файл | Назначение |
|---|---|
| `gateway/catalog.yaml` | Список моделей: имя, backend URL, лимиты, стоимость |
| `k8s/vllm-32b/deployment.yaml` | vLLM 32B GPTQ, TP=2, n7-gpu |
| `k8s/postgres/deployment.yaml` | PostgreSQL для биллинга |
| `db/migrations/006_org_id_text.sql` | Миграция: org_id как текст |
| `db/migrations/007_subscription_tiers.sql` | Таблица тарифных планов |
| `portal/.env` | YOOKASSA_SHOP_ID, YOOKASSA_SECRET |

### Последовательность конфигурации

1. **n7-gpu:** установка ОС, NVIDIA-драйвер, containerd, `kubeadm join`
2. **PostgreSQL:** создание БД `aither_billing`, миграции
3. **ЮKassa:** регистрация магазина, получение `shopId` + `secretKey`
4. **Каталог:** создание `catalog.yaml`, ConfigMap в K8s
5. **Gateway:** обновление образа с поддержкой мультимодельности
6. **Портал:** обновление UI — выбор модели из каталога

### Взаимодействия со смежными объектами

| Компонент A | Компонент B | Протокол | Данные |
|---|---|---|---|
| BFF | ЮKassa API | HTTPS REST | Платёж, webhook |
| Gateway | catalog.yaml | ConfigMap volume | Список моделей |
| Gateway | vLLM 14B | HTTP | Прокси запросов |
| Gateway | vLLM 32B | HTTP | Прокси запросов |
| Gateway | PostgreSQL (биллинг) | SQL | reserve/settle |

### Потоки данных

```
[Пользователь] → Пополнение → [ЮKassa] → webhook → [BFF] → [PostgreSQL]
                                                             → balance += amount

[Клиент] → выбор модели → [BFF] → GET /catalog → [Gateway] → [catalog.yaml]
[BFF] → POST /v1/chat/completions {model: "qwen2.5-32b"}
  → [Gateway] → routing.resolve("qwen2.5-32b")
  → backend = "http://vllm-qwen32b:8000"
  → reserve → POST /v1/chat/completions → [vLLM 32B]
  ← SSE stream ← settle ← [BFF]
```

---

## 3. Этап 2.5: Авто-баланс и публичный доступ (день 11)

### Описание

Автоматическое начисление стартовых токенов при регистрации, авто-пополнение при исчерпании, публикация Grafana-дашбордов через nip.io.

### Функционал

- Стартовый баланс 100 000 токенов при первой OAuth-регистрации
- Авто-пополнение ×10 при падении баланса ниже порога
- Публичный Grafana: `grafana.130.17.1.90.nip.io:30300`

### Состав компонентов

| Компонент | Версия | Назначение |
|---|---|---|
| Grafana | latest | Дашборды мониторинга |
| Prometheus | latest | Сбор метрик |
| nginx (VPS1) | — | Reverse proxy :10443 |

### Конфигурационные файлы

| Файл | Назначение |
|---|---|
| `configs/vps1/nginx-aither-failover.conf` | nginx → BFF + Grafana |
| `configs/vps2/aither-bff.service` | systemd unit для BFF |

---

## 4. Этап 3: Observability и продакшен (дни 11–14)

### Описание

Создание комплексной системы мониторинга (GPU, инференс, биллинг), расширение AI Security Gateway (DLP + Prompt Injection), вынос Gateway в отдельный K8s-под.

### Функционал

- Grafana-дашборд: GPU-метрики, throughput, биллинг, latency
- DLP-фильтр: детекция номеров карт, паспортов, СНИЛС, телефонов
- Prompt Injection-детектор: 23 EN + 6 RU паттернов
- Gateway как отдельный Deployment в K8s (не в BFF)
- mTLS между BFF и Gateway

### Состав компонентов

| Компонент | Версия | Назначение |
|---|---|---|
| Prometheus | latest | Сбор метрик |
| Grafana | latest | Дашборды |
| DCGM Exporter | 3.3 | NVIDIA GPU-метрики |
| Gateway mTLS | custom | Двухпортовый (:8080 HTTP + :8443 mTLS) |
| Vault PKI | — | Центр сертификации для mTLS |

### Физическая схема (этап 3)

```
VPS2                              n8-gpu (control-plane)
┌────────────────────┐           ┌─────────────────────────────┐
│ BFF :3000          │──mTLS───→│ Gateway :8443                │
│                    │           │   ├─ DLP ingress            │
│ PostgreSQL :5432   │           │   ├─ Prompt Injection       │
│ (пользователи)     │           │   ├─ Rate Limit (Redis)     │
└────────────────────┘           │   └─ vLLM proxy             │
                                 │                             │
                                 │ Prometheus :30909           │
                                 │ Grafana :30300              │
                                 │ DCGM Exporter               │
                                 │ PostgreSQL :5432 (биллинг)  │
                                 └─────────────────────────────┘
```

### Конфигурационные файлы

| Файл | Назначение |
|---|---|
| `gateway/security.py` | DLP ingress-фильтр |
| `gateway/security_egress.py` | Egress-фильтр (ДСП, ПДн) |
| `gateway/mtls_server.py` | mTLS-обёртка (:8443) |
| `k8s/monitoring/prometheus.yaml` | Prometheus Deployment + ConfigMap |
| `k8s/monitoring/grafana.yaml` | Grafana Deployment |

### Потоки данных (безопасность)

```
[Клиент] → [BFF] → mTLS → [Gateway]
  → DLP ingress: check for card numbers, SSN, passport, phone
  → Prompt Injection: 29 patterns (EN+RU)
  → if blocked: 403 + audit_log
  → else: → vLLM
  → DLP egress: check response for classified info
  → if blocked: strip sensitive data
  → else: → [BFF] → [Клиент]
```

---

## 5. Этап 4: RAG и кастомизация (дни 15–18)

### Описание

Создание гибридной RAG-подсистемы (Wiki Graph + ChromaDB через chroma-proxy), fine-tuning пайплайна (QLoRA), cost-aware routing и model playground для сравнения моделей.

### Функционал

- **Гибридный RAG:** Wiki Graph (keyword search, 8 страниц) + ChromaDB (векторный поиск, 322 чанка учебника)
- **chroma-proxy:** изолированный прокси (Deployment + Service :9000) с эмбеддингами all-MiniLM-L6-v2
- **Fine-tuning:** QLoRA 4-bit, адаптер `astra-14b` (rank=8, 65 MB)
- **Cost-aware routing:** автоматический выбор модели по сложности запроса
- **Model playground:** A/B сравнение 14B vs 32B

### Состав компонентов

| Компонент | Версия | Назначение |
|---|---|---|
| ChromaDB | 0.5.23 | Векторная БД (RAG) |
| chroma-proxy | custom (chromadb/chroma:0.5.23) | Текстовый прокси → эмбеддинги → ChromaDB |
| all-MiniLM-L6-v2 | — | Эмбеддинг-модель (384-мерные векторы) |
| Wiki Graph | LLM-Wiki, 8 стр. | Keyword search (Karpathy-style) |
| hybrid_rag.py | 184 строки | Гибридный поиск: wiki + chroma |
| chroma_proxy.py | 77 строк | HTTP-сервер внутри прокси |

### Принцип действия (гибридный RAG)

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

### Физическая схема (RAG)

```
n8-gpu                               n7-gpu
┌────────────────────┐              ┌──────────────────────────┐
│ Gateway            │──RAG POST──→│ chroma-proxy :9000       │
│   hybrid_rag.py ◄──┤              │   proxy.py               │
│   wiki_graph.py    │              │   all-MiniLM-L6-v2       │
│                    │              │          │               │
│ ConfigMap:         │              │   ChromaDB :8000         │
│   gateway-wiki     │              │   PVC 20 GB RWO          │
│   (8 .md files)    │              │   textbook (322 чанка)   │
└────────────────────┘              └──────────────────────────┘
```

### Конфигурационные файлы

| Файл | Назначение |
|---|---|
| `gateway/hybrid_rag.py` | Гибридный RAG: wiki + chroma-proxy |
| `gateway/wiki_graph.py` | LLM-Wiki: граф знаний |
| `scripts/chroma_proxy.py` | HTTP-прокси для ChromaDB |
| `k8s/chromadb/chroma-proxy.yaml` | ConfigMap + Deployment + Service :9000 |
| `k8s/chromadb/deployment.yaml` | ChromaDB 0.5.23 + PVC RWO |
| `wiki/*.md` | 8 страниц базы знаний |
| `scripts/ingest_textbook.py` | Чанковка и загрузка учебника |

### Последовательность конфигурации

1. **PVC:** создание `chromadb-data` (20 GB, RWO)
2. **ChromaDB:** `kubectl apply -f k8s/chromadb/deployment.yaml` (0.5.23, n7-gpu)
3. **chroma-proxy:** `kubectl apply -f k8s/chromadb/chroma-proxy.yaml`
4. **Инжест:** `kubectl exec deploy/chroma-proxy -- python3 /chroma/ingest_textbook.py`
5. **Wiki:** создание ConfigMap `gateway-wiki` из 8 .md-файлов
6. **Gateway:** обновление образа с `hybrid_rag.py`, env `CHROMA_PROXY_URL`

### Взаимодействия со смежными объектами

| Компонент A | Компонент B | Протокол | Данные |
|---|---|---|---|
| Gateway (hybrid_rag) | chroma-proxy | HTTP POST | query → top-K chunks |
| chroma-proxy | ChromaDB | Python API (chromadb) | query_texts → results |
| Gateway (wiki_graph) | ConfigMap gateway-wiki | Volume mount | 8 .md files |

### Потоки данных (RAG-запрос)

```
[Пользователь] → POST /api/v1/rag/query {query, top_k=5}
  → [BFF] → [Gateway]
  → hybrid_query(query, wiki_radius=1, top_k=5)
    ├─ wiki_graph.search(query)[:5]      → 5 keyword matches
    └─ chroma-proxy POST /query {query}   → 5 vector matches
  → combine + dedup + sort by relevance
  ← {query, wiki_results, chroma_results, combined}
  → [BFF] → [Клиент]
```

---

## 6. Этап 5: Продакшен-класс (недели 3–6)

### Описание

Переход к многоарендной архитектуре с изоляцией, тарифными планами, резервированием (VPS3 failover), SaaS-порталом и подготовкой к High Availability.

### Выполненные задачи

| Задача | Статус | Описание |
|---|---|---|
| **21a. Тарифные планы** | ✅ | Free/Standard/VIP/Enterprise с разными лимитами |
| **22. VPS3 Failover** | ✅ | Горячий резерв портала + Hermes-синхронизация |
| **23. SaaS-портал** | ✅ | Регистрация, биллинг-дашборды, админ-панель |
| **23a. LDAP-аутентификация** | ✅ | FreeIPA/ALD Pro |

### Запланированные задачи

| Задача | Статус | Описание |
|---|---|---|
| **21. Multi-tenant изоляция** | ⬜ | Namespaces, квоты на уровне K8s |
| **24. HA control plane** | ⬜ | 3 control-plane узла |
| **25. NVLink-мосты** | 🔒 | Заблокировано: нет физических мостов |
| **26. Модели 70B+** | 🔒 | Заблокировано: нужны NVLink + NVSwitch |

### Физическая схема (этап 5)

```
VPS1 (170.168.91.95)    VPS3 (89.127.217.88)    VPS2 (130.17.1.90)
┌──────────────┐        ┌──────────────┐        ┌──────────────────────┐
│ Hermes Agent │←──WG──→│ Hermes Agent │        │ nginx :80             │
│ nginx :10443 │        │ (резерв)     │        │ BFF :3000             │
│ (входная     │        │              │        │ PostgreSQL :5432      │
│  точка)      │        └──────────────┘        │ (пользователи, чаты)  │
└──────┬───────┘                                └──────────┬───────────┘
       │                                                   │
       │              Cisco815 ──── HuaweiHP               │
       │                   │           │                   │
       │            n8-gpu │     n7-gpu│                   │
       │  ┌────────────────┴───┐ ┌─────┴──────────────┐   │
       └─→│ Gateway :30900    │ │ vLLM 32B :32294    │   │
          │ vLLM 14B :32293   │ │ chroma-proxy :9000 │   │
          │ PostgreSQL :5432   │ │ ChromaDB :8000     │   │
          │ Redis :6379        │ │                    │   │
          │ Prometheus :30909 │ │                    │   │
          │ Grafana :30300    │ │                    │   │
          └───────────────────┘ └────────────────────┘   │
```

### Конфигурационные файлы

| Файл | Назначение |
|---|---|
| `portal/ldap.ts` | LDAP/ALD Pro аутентификация |
| `portal/policies.ts` | Политики доступа (org-level) |
| `db/migrations/007_subscription_tiers.sql` | Тарифные планы |
| `db/migrations/008_auth_tables_k8s.sql` | OAuth-таблицы |

---

## 7. Этап 5a: Требования руководства (недели 7–11)

### Описание

Реализация требований информационной безопасности и корпоративных стандартов: egress-фильтрация (ДСП), SIEM-интеграция (syslog CEF), Vault-интеграция (управление ключами), LLM-Wiki (граф знаний), LDAP-аутентификация.

### Выполненные задачи

| Задача | Статус | Описание |
|---|---|---|
| **34. Security Gateway Egress** | ✅ | ДСП-фильтр на выходе (classified data leak prevention) |
| **35. SIEM-интеграция** | ✅ | syslog CEF + security log storage |
| **36. Vault-интеграция** | ✅ | Внешняя генерация API-ключей + политики ИБ |
| **37. LLM-Wiki + гибридный RAG** | ✅ | Wiki graph search + ChromaDB (описано в этапе 4) |
| **23a. LDAP (FreeIPA/ALD Pro)** | ✅ | Корпоративная аутентификация |
| **38. Профили организаций** | ✅ | Security policy per org |
| **39. API Gateway mgmt API** | ✅ | Управление очередями, моделями, drain |
| **40. TTFT-мониторинг** | ✅ | Time To First Token в Prometheus |

### Принцип действия (egress DLP)

```
[Модель] → ответ с текстом
  → [Gateway: security_egress.py]
  → проверка на ДСП-маркеры, ПДн, classified patterns
  → если найдено: strip/block + audit_log + SIEM event
  → иначе: пропустить ответ
  → [BFF] → [Клиент]
```

### Принцип действия (Vault PKI)

```
[Gateway] → запрос сертификата → [Vault PKI]
  ← сертификат (TTL 30 дней)
[BFF] → mTLS handshake → [Gateway :8443]
  → client cert verification → JWT auth → vLLM
```

### Конфигурационные файлы

| Файл | Назначение |
|---|---|
| `gateway/security_egress.py` | Egress DLP-фильтр |
| `gateway/vault.py` | Vault PKI-интеграция |
| `wiki/entities/ai-gateway.md` | Wiki: описание AI Gateway |
| `wiki/entities/security-egress.md` | Wiki: egress security |
| `wiki/entities/siem-integration.md` | Wiki: SIEM syslog |

---

## 8. Этап 6: Эксплуатация и развитие (месяц 2+)

### Описание

Переход от пилотного проекта к промышленной эксплуатации: автомасштабирование (HPA), CI/CD-пайплайн, внешний API Gateway с документацией, полный аудит безопасности.

### Выполненные задачи

| Задача | Статус | Описание |
|---|---|---|
| **27. Промышленная эксплуатация** | ✅ | Pilot → Production: мониторинг, алерты, инцидент-менеджмент |
| **28. Автомасштабирование** | ✅ | K8s HPA по CPU/Memory, Gateway HPA (min=1, max=3) |
| **29. CI/CD** | ✅ | GitHub Actions → lint + авто-деплой |
| **30. API Gateway** | ✅ | Внешний доступ, OpenAI API, Swagger |
| **31. Аудит безопасности** | ✅ | Полное тестирование (penetration test) |
| **32. Документация** | ✅ | Внешняя документация (учебник 24 главы, ~780 стр.) |

### Состав компонентов

| Компонент | Версия | Назначение |
|---|---|---|
| HPA Gateway | autoscaling/v2 | Автомасштабирование (active reqs + rps) |
| HPA vLLM | autoscaling/v2 | По GPU-очереди |
| GitHub Actions | — | CI/CD: lint + deploy |
| Swagger UI | — | OpenAPI-документация |
| Учебное пособие | 24 гл., ~780 стр. | Техническая документация |

### Конфигурационные файлы

| Файл | Назначение |
|---|---|
| `k8s/hpa/gateway-hpa.yaml` | HPA для Gateway |
| `k8s/hpa/prometheus-adapter.yaml` | Prometheus → K8s metrics adapter |
| `docs/training-manual/*.md` | 24 главы учебного пособия |

---

## 9. Этап 7: Пакет для закрытого контура

### Описание

Создание самодостаточного офлайн-пакета (`offline-deploy/`) для развёртывания платформы в изолированном контуре без доступа в Интернет. Пакет включает: документацию, Ansible playbooks, K8s-манифесты, Docker-образы, Python/NPM-зависимости, скрипты эксплуатации и приёмо-сдаточные тесты.

### Функционал

- Полный цикл развёртывания одной командой: `make deploy` (Ansible)
- Автоматическая загрузка офлайн-зависимостей: `make offline-load`
- Приёмо-сдаточные тесты: `make test` (smoke + API + security + load)
- Админ-панель: CRUD организаций, пользователей, API-ключей, LDAP
- Документация: архитектура, деплой, админ, пользователь, безопасность

### Состав компонентов

| Компонент | Версия | Назначение |
|---|---|---|
| offline-deploy kit | 1.2.0 | Самодостаточный пакет развёртывания |
| Ansible | 2.16+ | Автоматизация деплоя |
| Docker images | см. images.txt | Все образы платформы |
| Python wheels | см. requirements.txt | Gateway-зависимости |
| NPM package | portal-offline.tgz | Собранный портал |

### Структура пакета (v1.2.0)

```
offline-deploy/
├── docs/           ← 8 документов (архитектура → upgrade)
├── playbooks/      ← 10 Ansible playbooks
├── k8s/            ← Все манифесты:
│   ├── gateway/    ←   Gateway (13 модулей, hybrid_rag)
│   ├── vllm-14b/   ←   vLLM 14B (TP=2)
│   ├── vllm-32b/   ←   vLLM 32B (TP=2)
│   ├── chromadb/   ←   ChromaDB 0.5.23 + chroma-proxy
│   ├── postgres/   ←   PostgreSQL 16
│   ├── redis/      ←   Redis 7
│   └── monitoring/ ←   Prometheus + Grafana
├── offline/        ← Офлайн-зависимости:
│   ├── docker/     ←   images.tar.gz
│   ├── pip/        ←   wheels + requirements.txt
│   ├── npm/        ←   portal-offline.tgz
│   └── models/     ←   transfer.sh + model-list.txt
├── scripts/        ← 7 скриптов эксплуатации
├── configs/        ← Эталонные конфигурации
└── tests/          ← 4 приёмо-сдаточных теста
```

### Физическая схема (целевая, этап 7)

См. полную схему: [physical-architecture-v2.svg](diagrams/physical-architecture-v2.svg)

### Конфигурационные файлы

| Файл | Назначение |
|---|---|
| `offline-deploy/VERSION` | Версия пакета (1.2.0) |
| `offline-deploy/Makefile` | make deploy / make test / make bundle |
| `offline-deploy/offline/docker/images.txt` | Список Docker-образов |
| `offline-deploy/offline/pip/requirements.txt` | Python-зависимости Gateway |
| `offline-deploy/playbooks/site.yml` | Главный Ansible playbook |

### Последовательность развёртывания (закрытый контур)

1. **Подготовка носителя:** `make bundle` на машине с интернетом
2. **Перенос:** флеш-носитель → целевая машина (Astra Linux)
3. **Загрузка:** `make offline-load` (Docker, pip, npm)
4. **Деплой:** `make deploy` (Ansible playbooks, ~1 час)
5. **RAG-инициализация:** инжест учебника в ChromaDB
6. **Проверка:** `make test` (smoke, API, security, load)

### Взаимодействия со смежными объектами

| Компонент | Взаимодействие |
|---|---|
| Ansible | SSH к целевым узлам, `kubectl apply`, `docker load` |
| K8s-манифесты | Взаимодействуют через K8s API (поды, сервисы, PVC) |
| Docker images | Локальный Docker daemon |
| Python wheels | `pip install --no-index` |
| NPM package | `npm install --offline` |

---

## Сводная таблица этапов

| Этап | Задач | Статус | Ключевой результат |
|---|---|---|---|
| 1. MVP | 7 | ✅ | Работающий инференс + портал + OAuth |
| 2. Биллинг + каталог | 4 | ✅ | Монетизация + мультимодельность |
| 2.5. Авто-баланс | 2 | ✅ | Стартовые токены + Grafana |
| 3. Observability | 5 | 🔄 | Мониторинг + DLP + mTLS |
| 4. RAG + кастомизация | 4 | ✅ | Гибридный RAG + LoRA + routing |
| 5. Продакшен-класс | 7 | 🔄 | Тарифы + failover + SaaS |
| 5a. Требования руководства | 9 | ✅ | DLP egress + SIEM + Vault + LDAP |
| 6. Эксплуатация | 6 | ✅ | HPA + CI/CD + учебник |
| 7. Закрытый контур | 7 | ✅ | offline-deploy v1.2.0 |
| **Итого** | **51** | **46/51** | **90% готовность** |

---

*Документ создан на основе ROADMAP.md, lab-journal.md и живой конфигурации платформы.*
