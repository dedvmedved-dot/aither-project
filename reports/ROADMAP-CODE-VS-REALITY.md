# ROADMAP: КОД vs РЕАЛЬНОСТЬ — полная верификация

**Дата проверки:** 27.07.2026
**Метод:** Live-команды (kubectl, curl, nvidia-smi, ssh)
**Ревизия:** `4cf0847`

---

## Легенда

| Обозначение | Значение |
|---|---|
| ✅ | Да, есть |
| ❌ | Нет, отсутствует |
| ⚠️ | Частично / не подтверждено |
| 🔒 | Заблокировано (железо) |

---

## Этап 1: MVP (дни 1–7)

| # | Задача | ROADMAP | Код в репо | Работает сейчас | Детали |
|---|---|---|---|---|---|
| 1 | K8s + GPU Operator на n8 | ✅ | ✅ | ✅ | 2 узла Ready (N7, N8), GPU Operator Running |
| 2 | containerd + nvidia-runtime | ✅ | ✅ | ✅ | `runtimeClassName: nvidia` на обоих узлах |
| 3 | vLLM 14B загрузка и запуск | ✅ | ✅ | ✅ | Running на N8, TP=2, 20.2 GB/GPU |
| 4 | Tensor Parallelism (TP=2) | ✅ | ✅ | ⚠️ | 14B: TP=2 ✅; **32B: TP=1 (БАГ)** — `tensor-parallel-size=1` |
| 5 | Gateway (FastAPI + Redis RL) | ✅ | ✅ `gateway.py` | ⚠️ | Python Gateway отсутствует как под, только nginx-gateway-32b |
| 6 | Portal (SPA + BFF + SSE) | ✅ | ✅ `index.html`, `app.py` | ✅ | HTTP 200, /health: `{"status":"ok","version":"0.6.0-r7r7-c2-d18"}` |
| 7 | OAuth (GitHub, Google, Яндекс) | ✅ | ✅ `identity` | ✅ | 3 провайдера + LDAP, кнопки на странице логина |

---

## Этап 2: Биллинг и каталог (дни 8–10)

| # | Задача | ROADMAP | Код в репо | Работает сейчас | Детали |
|---|---|---|---|---|---|
| 8 | ЮKassa — пополнение баланса | ✅ | ✅ в BFF `app.py` | ⚠️ | Только dev-режим. Боевые `shopId`/`secretKey` не получены |
| 9 | Каталог моделей (YAML → Gateway) | ✅ | ✅ `catalog.yaml`, `catalog.py` | ❌ | Код есть. Python Gateway не задеплоен. BFF хардкодит модели |
| 10 | Второй узел n7 + 32B модель | ✅ | ✅ манифесты | ⚠️ | Узел Ready, 32B Running, но **TP=1** (не 2) |
| 11 | Фиксы портала (502/404/500) | ✅ | ✅ | ✅ | nginx SSE fix, org_id UUID→TEXT, 404→очистка localStorage |

---

## Этап 2.5: Авто-баланс + Grafana

| # | Задача | ROADMAP | Код в репо | Работает сейчас | Детали |
|---|---|---|---|---|---|
| 11a | Авто-баланс (100K + рефилл ×10) | ✅ | ✅ в `app.py` | ✅ | `ensurePersonalOrg()` в BFF, авто-пополнение |
| 11b | Grafana публичный доступ | ✅ | ✅ nginx конфиг | ❌ | Grafana недоступна. Prometheus отсутствует |

---

## Этап 3: Observability и продакшен

| # | Задача | ROADMAP | Код в репо | Работает сейчас | Детали |
|---|---|---|---|---|---|
| 12 | Observability — Grafana дашборд | ✅ | ✅ `grafana/*.json` | ❌ | Prometheus + Grafana не развёрнуты в кластере |
| 13 | ЮKassa боевой режим | ⬜ | ❌ | ❌ | Нет кредов. Только dev-режим. Требуется OWNER |
| 14 | AI Security Gateway | ✅ | ✅ `security.py`, `security_egress.py` | ❌ | Код есть. Python Gateway не задеплоен |
| 15 | Parsec на n7 (`max_ilev=63`) | ⬜ | ❌ | ❌ | `parsec=0` в GRUB. Не возвращён после установки ПО |
| 16 | Gateway в K8s (вынос из BFF) | ✅ | ✅ манифесты | ⚠️ | В K8s только nginx proxy. Python Gateway отсутствует |
| 16a | Портал: стабилизация | ✅ | ✅ `095afdc` | ✅ | OAuth fix, chat bugs, hljs, copy btn — применено в EMG-01 |

---

## Этап 4: RAG и кастомизация

| # | Задача | ROADMAP | Код в репо | Работает сейчас | Детали |
|---|---|---|---|---|---|
| 17 | RAG-подсистема (ChromaDB/wiki) | ✅ | ✅ `wiki_graph.py`, `hybrid_rag.py`, `wiki/` | ❌ | Код и wiki-страницы есть. Python Gateway не задеплоен. ChromaDB в aiops — CrashLoopBackOff |
| 18 | Fine-tuning пайплайн (LoRA) | ✅ | ✅ адаптер 209 MB на N8 | ❌ | vLLM-14b запущен **без** `--enable-lora`, `--lora-modules` |
| 19 | Cost-aware routing | ✅ | ✅ `catalog.py`, `catalog.yaml` | ❌ | Код есть. BFF использует хардкод-список моделей |
| 20 | Model playground (A/B) | ✅ | ✅ выпадающий список в `index.html` | ⚠️ | Есть в UI. Требует авторизации. Без Gateway — базовый выбор |

---

## Этап 5: Продакшен-класс

| # | Задача | ROADMAP | Код в репо | Работает сейчас | Детали |
|---|---|---|---|---|---|
| 21 | Multi-tenant изоляция | ⬜ | ❌ | ❌ | Нет ResourceQuota. NetworkPolicy одна (`vllm-ingress`) |
| 21a | Тарифные планы | ✅ | ✅ SQL `subscription_tiers` | ⚠️ | Код в BFF. Без Python Gateway — rate limits не tier-based |
| 22 | VPS3 Failover | ✅ | ✅ конфиги VPS3 | ✅ | VPS3 (89.127.217.88) отвечает HTTP 200, nginx backup upstream |
| 23 | SaaS-портал (signup/login) | ✅ | ✅ в BFF | ⚠️ | Работает под авторизацией. Требует Gateway для биллинга |
| 24 | HA K8s Control Plane | ⬜ | ❌ | ❌ | Single control-plane (N8). Единая точка отказа |
| 25 | NVLink-мосты | 🔒 | 🔒 | 🔒 | Нет физических мостов. Заявка на закупку |
| 26 | Модели 70B+ | 🔒 | 🔒 | 🔒 | Нужны NVLink + NVSwitch + ≥4 GPU |

---

## Этап 5a: Требования руководства

| # | Задача | ROADMAP | Код в репо | Работает сейчас | Детали |
|---|---|---|---|---|---|
| 34 | Security Gateway Egress (ДСП) | ✅ | ✅ `security_egress.py` | ❌ | Код есть. Python Gateway не задеплоен |
| 35 | SIEM-интеграция (syslog CEF) | ✅ | ✅ в `security_egress.py` | ❌ | Код есть. Python Gateway не задеплоен |
| 36 | Vault-интеграция (PKI + политики) | ✅ | ✅ `vault.py` | ❌ | Код есть. Python Gateway не задеплоен |
| 37 | LLM-Wiki + гибридный RAG | ✅ | ✅ `wiki_graph.py`, `hybrid_rag.py`, `wiki/` | ❌ | Код и 11 wiki-страниц есть. Python Gateway не задеплоен |
| 23a | LDAP-аутентификация | ✅ | ✅ `ldap.ts` (187 строк) | ⚠️ | Эндпоинт `/auth/ldap` возвращает "LDAP not configured" |
| 38 | Профили безопасности org | ✅ | ✅ `policies.ts` (196 строк) | ⚠️ | Код в BFF. Без Gateway — политики не применяются |
| 39 | API Gateway management API | ✅ | ✅ `admin.py` (280 строк) | ❌ | Код есть. Python Gateway не задеплоен |
| 40 | TTFT-мониторинг | ✅ | ✅ `metrics.py` (140 строк) | ❌ | Код есть. Prometheus отсутствует. Python Gateway не задеплоен |
| 23b | Чат опционально | ✅ | ✅ в `policies.ts` | ⚠️ | Код в BFF. Функция `checkChatEnabled()` |

---

## Этап 6: Эксплуатация

| # | Задача | ROADMAP | Код в репо | Работает сейчас | Детали |
|---|---|---|---|---|---|
| 27 | Промышленная эксплуатация | ✅ | ✅ `production-runbook.md` (340 строк) | ⚠️ | Runbook есть. Мониторинг отсутствует. Алертов нет |
| 28 | Автомасштабирование (HPA) | ✅ | ❌ | ❌ | HPA не настроен. Prometheus Adapter отсутствует |
| 29 | CI/CD (GitHub Actions) | ✅ | ✅ `.github/workflows/ci.yml`, `deploy.yml` | ⚠️ | Workflow есть в репо. Авто-деплой не активирован (нужны Secrets) |
| 30 | API Gateway (внешний) | ✅ | ✅ `api-gateway.ts`, `openapi.yaml` | ⚠️ | Код в BFF. Требует авторизации. Swagger-спецификация есть |
| 31 | Аудит безопасности | ✅ | ✅ `security-audit-2026-07-11.md` | ⚠️ | 18 находок. Критические закрыты (fail2ban, UFW). Средние — backlog |
| 32 | Документация пользователей | ✅ | ✅ `user-guide.md` (790 строк) | ✅ | 18 MD-файлов в портале `/docs/`. `charset=utf-8` |

---

## Этап 7: Закрытый контур

| # | Задача | ROADMAP | Код в репо | Работает сейчас | Детали |
|---|---|---|---|---|---|
| 33 | Офлайн-пакет развёртывания | ✅ | ✅ `offline-deploy/` (45 файлов, 60 KB) | ⚠️ | Файлы есть. `make deploy` и `make test` не проверены на чистой Astra Linux |

---

## СВОДНАЯ СТАТИСТИКА

| Статус | Количество задач | % |
|---|---|---|
| ✅ Работает (код есть + задеплоено) | **10** | 22% |
| ⚠️ Частично (код есть, не задеплоено / не проверено) | **26** | 58% |
| ❌ Отсутствует (нет кода, не работает) | **7** | 16% |
| 🔒 Заблокировано (железо) | **2** | 4% |
| **Всего** | **45** | 100% |

---

## КЛЮЧЕВЫЕ НАХОДКИ

### Критические (блокируют работу)

| # | Проблема | Влияние |
|---|---|---|
| 1 | **Python Gateway отсутствует как под** | 12+ функций не работают: каталог, RAG, security, billing, admin, metrics, vault, siem |
| 2 | **32B TP=1** (вместо 2) | Модель на одном GPU. N7 GPU#1 простаивает. Производительность ниже |
| 3 | **Prometheus + Grafana отсутствуют** | Нет мониторинга GPU, vLLM, инфраструктуры. Нет алертов |
| 4 | **LoRA не загружен** | `--enable-lora` отсутствует в vLLM-14b. Адаптер astra-14b не используется |

### Средние (ограничивают функциональность)

| # | Проблема | Влияние |
|---|---|---|
| 5 | ЮKassa dev-режим | Нет реальных платежей |
| 6 | Parsec отключен на N7 | Снижение безопасности ОС |
| 7 | HPA отсутствует | Нет автомасштабирования |
| 8 | Нет ResourceQuota | Нет multi-tenant изоляции |
| 9 | HA Control Plane отсутствует | Единая точка отказа |

### Низкие (косметика/оптимизация)

| # | Проблема | Влияние |
|---|---|---|
| 10 | Alertmanager отсутствует | Нет уведомлений о сбоях |
| 11 | HTTPS самоподписанный | Нет доверенного сертификата |
| 12 | 32B дубликат на N8 | 19 GB wasted |
| 13 | Stale pods (7 шт) | Замусоривание кластера |

---

## КОРЕНЬ ПРОБЛЕМЫ

**Центральный Python Gateway** (`gateway.py`) с 12+ модулями (catalog, RAG, security, billing, admin, metrics, vault, siem, wiki_graph, hybrid_rag) **не развёрнут как отдельный K8s под**. Архитектура была реорганизована: Gateway-функции частично перенесены в `aither-bff` и `aither-ai-platform`, но многие модули остались только в коде репозитория без деплоя.

Вместо Gateway сейчас работает `nginx-gateway-32b` — простой nginx reverse proxy к vLLM-32b.

---

*Верификация выполнена live-командами 27.07.2026. Не на основе документации.*
