# Aither Platform — Пошаговый план: 59 задач от текущего состояния до ROADMAP 100%

**Реконсиляция (Reconciliation):** 2026-08-17
**Baseline SHA:** `8e97e1ed576ffbf7a8a3eeb067e0f1b8c6e83a98`
**Задача:** AITHER-MVP-ROADMAP-RECONCILIATION-R1 — ROADMAP_RECONCILIATION
**Область изменения:** только `ROADMAP-RECOVERY.md`. Исходный код, манифесты, рантайм, Kubernetes, БД, деплой, пакеты, секреты и конфигурация хостов НЕ изменялись.

> **Исторический снапшот (НЕ текущая истина):** 27.07.2026, HEAD `4cf0847`, «Выполнено 40/59 (68%)».
> Сохранён только как помеченная историческая справка. Актуальная консервативная оценка —
> в разделе «Сводка» ниже.

---

## Текущий контракт моделей (Current model contract)

| Точный ID модели | Scope | Статус |
|---|---|---|
| `qwen2.5-32b-instruct` | `model:qwen2.5:chat` | Канонический |
| `qwen3-32b` | `model:qwen3:chat` | Канонический |

- `model:32b:chat` — только legacy-совместимость; не вводить заново как дефолт эмитента.
- Устаревшие generic-метки размера модели выведены из роадмапа и заменены точными ID моделей
  либо модельно-нейтральными формулировками.
- Устаревшие имена переменных окружения upstream-маршрутизации сами по себе не меняют маршрутизацию.
- Развёрнутые модели: `vllm-32b-instruct-awq` (n7, TP=2) и `vllm-qwen3-32b-awq` (n8, TP=2).
  Прежние инференс-деплои (инструкционная модель на N8 и GPTQ-модель на N7) переведены в scale-to-0
  и заменены указанными выше.

---

## Легенда

| Статус | Обозначение |
|---|---|
| ✅ DONE | Выполнено (подтверждено аудитом или emergency-операциями) |
| ◐ PARTIAL | Частично выполнено / требует доводки |
| ⬜ OPEN | Не выполнено — действующая |
| 👤 OWNER_REQUIRED | Требует действия OWNER (ручное / браузер / учётные данные) |
| 🔒 HARDWARE_DEFERRED | Отложено — требуется железо / закупка |
| 🗑 SUPERSEDED | Снято — заменено более поздней принятой работой |
| 🚨 | Аварийный режим — требует stabilisation |
| ⚙️ | Требует изменения K8s/инфраструктуры |
| ✏️ | Требует изменения кода/файлов |
| ⏸️ | STOP после задачи — ждать команду |

---

# ЭТАП 1: MVP (дни 1–7) — 7/7 ✅

| # | Задача | ROADMAP | Статус | Коммит/Evidence |
|---|---|---|---|---|
| 1 | K8s + GPU Operator на N8 | #1 | ✅ | K8s v1.33.5, 2 узла, GPU Operator Running |
| 2 | containerd + nvidia-runtime | #2 | ✅ | `runtimeClassName: nvidia` на обоих узлах |
| 3 | vLLM: загрузка и запуск модели | #3 | ✅ | vLLM-деплой Running (исторически; текущие модели — `qwen2.5-32b-instruct`, `qwen3-32b`) |
| 4 | Tensor Parallelism (TP=2) | #4 | ✅ | TP=2 на обоих узлах (N7, N8) |
| 5 | Gateway (FastAPI + Redis RL) | #5 | ✅ | nginx-gateway (2 реплики), Redis |
| 6 | Portal (SPA + BFF + SSE) | #6 | ✅ | `aither-portal` NodePort 30080, aither-bff (2 реплики) |
| 7 | OAuth (GitHub, Google, Яндекс) | #7 | ✅ | `aither-identity` + 3 провайдера + LDAP |

---

# ЭТАП 2: Биллинг и каталог (дни 8–10) — 4/4 ✅

| # | Задача | ROADMAP | Статус | Коммит/Evidence |
|---|---|---|---|---|
| 8 | ЮKassa — пополнение баланса (dev-режим) | #8 | ✅ | `POST /api/v1/billing/topup`, dev-режим работает |
| 9 | Каталог моделей (YAML → Gateway) | #9 | ✅ | `catalog.yaml`, `GET /v1/models` → модели каталога |
| 10 | Второй узел N7 + вторая модель | #10 | ✅ | N7 worker (историч. GPTQ Int4 → заменён `qwen2.5-32b-instruct` AWQ, TP=2) |
| 11 | Фиксы портала (502/404/500) | #11 | ✅ | org_id UUID→TEXT, nginx SSE, 404 fix |

---

# ЭТАП 2.5: Авто-баланс + Grafana — 2/2 ✅

| # | Задача | ROADMAP | Статус | Коммит/Evidence |
|---|---|---|---|---|
| 12 | Авто-баланс (100K + рефилл ×10) | #11a | ✅ | `ensurePersonalOrg()` в BFF, авто-пополнение |
| 13 | Grafana публичный доступ | #11b | ✅ | `grafana.130.17.1.90.nip.io` |

---

# ЭТАП 3: Observability и продакшен — 6 задач

| # | Задача | ROADMAP | Статус | Коммит/Evidence |
|---|---|---|---|---|
| 14 | Observability — Grafana дашборд | #12 | ✅ | Prometheus + Grafana, GPU+vLLM дашборды, DCGM |
| 15 | D1: Alertmanager + Telegram-алерты 🚨 | NEW | ⬜ OPEN | Развернуть Alertmanager; правила GPU temp/mem, pod restarts; Telegram webhook. Нет принятого рантайм-свидетельства. |
| 16 | AI Security Gateway (расширенный) | #14 | ✅ | Prompt injection + DLP (29 паттернов) |
| 17 | D2: NTP-мониторинг 🚨 | NEW | ⬜ OPEN | Prometheus-алерт `node_timex_offset_seconds > 5`; проверка `chronyc tracking`. Нет принятого рантайм-свидетельства. |
| 18 | Gateway в K8s (вынос из BFF) | #16 | ✅ | nginx-gateway Deployment (2 реплики) |
| 19 | Портал: стабилизация (OAuth fix, chat bugs) | #16a | ✅ | `095afdc` — JS fix, closeModal, feedback, timeout — применено в EMG-01 |

---

# ЭТАП 4: RAG и кастомизация — 4/4 ✅

| # | Задача | ROADMAP | Статус | Коммит/Evidence |
|---|---|---|---|---|
| 20 | RAG-подсистема (Wiki-Graph, гибридный) | #17 | ✅ | Замена ChromaDB на Wiki-Graph RAG (Karpathy-style) |
| 21 | Fine-tuning пайплайн (LoRA) | #18 | ✅ | LoRA-адаптер (68.9 MB), PEFT-конвертер |
| 22 | Cost-aware routing | #19 | ✅ | `catalog.resolve()` — маршрутизация по моделям |
| 23 | Model playground (A/B сравнение) | #20 | ✅ | Выпадающий список моделей в портале |

---

# ЭТАП 5: Продакшен-класс — 10 задач

| # | Задача | ROADMAP | Статус | Коммит/Evidence |
|---|---|---|---|---|
| 24 | D3: Автоматические бэкапы (PostgreSQL + Redis) 🚨 | NEW | ⬜ OPEN | K8s CronJob `pg_dump` → PVC; `redis-cli BGSAVE` → PVC. Нет принятого рантайм-свидетельства. |
| 25 | Тарифные планы (Free/Standard/VIP/Enterprise) | #21a | ✅ | 4 тарифа, Redis-cached limits, model access control |
| 26 | VPS3 Failover (горячий резерв) | #22 | ✅ | VPS3 поднят, stateless BFF, SSH-туннель, nginx backup |
| 27 | SaaS-портал (signup/login/dashboard) | #23 | ✅ | Signup/login/billing/tiers/upgrade — VPS2+VPS3 |
| 28 | #13 ЮKassa боевой режим | #13 | 👤 OWNER_REQUIRED | Требует `shopId`+`secretKey` от OWNER; затем K8s Secret `yookassa-credentials` + ConfigMap + тестовый платёж. |
| 29 | #15 Parsec на N7 (`max_ilev=63`) | #15 | ⬜ OPEN | SSH на N7; GRUB `max_ilev=63 execstack=1`; плановая перезагрузка N7; проверка `parsec_status` и работы моделей после ребута. Нет принятого рантайм-свидетельства. |
| 30 | #21 Multi-tenant изоляция | #21 | ◐ PARTIAL | Часть NetworkPolicy-манифестов присутствует в репозитории; полный ResourceQuota на `aither-inference` и сквозная проверка связности не подтверждены рантаймом. |
| 31 | #24 HA K8s Control Plane | #24 | ⬜ OPEN | Оценка повышения N7 до control-plane; документирование ограничения 2-членного etcd. Не начато. |
| 32 | NVLink-мосты | #25 | 🔒 HARDWARE_DEFERRED | Нет физических мостов. Заявка на закупку. |
| 33 | Модели 70B+ | #26 | 🔒 HARDWARE_DEFERRED | Нужны NVLink + NVSwitch + ≥4 GPU. |

---

# ЭТАП 5a: Требования руководства — 9/9 ✅

| # | Задача | ROADMAP | Статус | Коммит/Evidence |
|---|---|---|---|---|
| 34 | Security Gateway Egress (ДСП-фильтр) | #34 | ✅ | `security_egress.py`, 29 паттернов |
| 35 | SIEM-интеграция (syslog CEF) | #35 | ✅ | CEF-форматтер, 3 канала логирования |
| 36 | Vault-интеграция (PKI + политики ИБ) | #36 | ✅ | `vault.py`, PKI для ключей, политики из Vault |
| 37 | LLM-Wiki + гибридный RAG | #37 | ✅ | Wiki-граф (315 строк), гибридный поиск |
| 38 | LDAP-аутентификация (FreeIPA/ALD Pro) | #23a | ✅ | `ldap.ts` (187 строк), `POST /auth/ldap` |
| 39 | Профили безопасности организаций | #38 | ✅ | 14 параметров per-org |
| 40 | API Gateway management API | #39 | ✅ | `admin.py` (280 строк), 7 admin endpoints |
| 41 | TTFT-мониторинг (Prometheus-метрики) | #40 | ✅ | 7 метрик: TTFT histogram, counters, gauge |
| 42 | Чат опционально (включение/отключение) | #23b | ✅ | `chat_enabled` в `org_policies` |

---

# ЭТАП 6: Эксплуатация — 6/6 ✅

| # | Задача | ROADMAP | Статус | Коммит/Evidence |
|---|---|---|---|---|
| 43 | Промышленная эксплуатация (runbook, health-check) | #27 | ✅ | Runbook (340 строк), `health-check.sh` |
| 44 | Автомасштабирование (K8s HPA) | #28 | ✅ | Prometheus Adapter, Gateway HPA 1→3 |
| 45 | CI/CD (GitHub Actions) | #29 | ✅ | `.github/workflows/ci.yml` + `deploy.yml` |
| 46 | API Gateway (внешний OpenAI-совместимый) | #30 | ✅ | `POST /api/v1/chat/completions`, Swagger |
| 47 | Аудит безопасности (пентест) | #31 | ✅ | 18 находок, критические закрыты |
| 48 | Документация для внешних пользователей | #32 | ✅ | `user-guide.md` (790 строк), 18 MD-файлов |

---

# ЭТАП 7: Закрытый контур — 1/1 ✅

| # | Задача | ROADMAP | Статус | Коммит/Evidence |
|---|---|---|---|---|
| 49 | Офлайн-пакет развёртывания | #33 | ✅ | `offline-deploy/` — 45 файлов, 60 KB |

---

# ЭТАП 8: АВАРИЙНАЯ СТАБИЛИЗАЦИЯ (EMG-01) — 5 задач 🚨

Реконсилировано против более позднего принятого восстановления рантайма (миграция моделей
`qwen2.5-32b-instruct` / `qwen3-32b`, восстановление внешнего агентского доступа).

| # | Задача | Статус | Коммит/Evidence |
|---|---|---|---|
| 50 | C1: N7 GPU#1 idle — диагностика и исправление 🚨 | 🗑 SUPERSEDED | Относилось к прежнему GPTQ-деплою на N7; снято миграцией на `qwen2.5-32b-instruct` (TP=2, n7). |
| 51 | C2: Верификация прежней инструкционной модели на N8 (availability probe) 🚨 | 🗑 SUPERSEDED | Прежняя модель на N8 переведена в scale-to-0 и заменена `qwen3-32b` (TP=2, n8). |
| 52 | C3: Очистка кластера (stale pods) 🚨 | ⬜ OPEN | Generic-гигиена кластера; нет принятого рантайм-свидетельства завершения. |
| 53 | C4: Node labels → Git 🚨 | 🗑 SUPERSEDED | Манифест `03-vllm-14b-deploy` стал историческим; текущие деплои используют собственные nodeSelector/nodeName. |
| 54 | C5: Удалить дубликат модели с N8 🚨 | 🗑 SUPERSEDED | Дубликат прежней GPTQ-модели на N8 снят в ходе миграции; текущая модель N8 — `qwen3-32b`. |

---

# ЭТАП 9: БЕЗОПАСНОСТЬ — 3 задачи

| # | Задача | Статус | Коммит/Evidence |
|---|---|---|---|
| 55 | E2: HTTPS (Let's Encrypt) 🔴 | 👤 OWNER_REQUIRED | Требует подтверждения управления доменом `fb1.spb.ru` OWNER'ом + выпуск/автопродление сертификата. HTTPS на `:10443` эксплуатируется, но процедура Let's Encrypt не подтверждена. |
| 56 | E3: Удалить dev-аккаунты из БД 🟡 | 👤 OWNER_REQUIRED | Мутация БД (DELETE) — вне прав исполнителя; требует решения/действия OWNER. |
| 57 | E1: Закрытие 14 исторических R6-блокеров 🟡 | ◐ PARTIAL | Частично: BFF race fix, model-switch strengthening, credential rotation, session invalidation (R7); позже REG-C/L/A — защита endpoints identity (в Git). Остаются deferred-элементы: Acceptance Matrix, Behavioral Compliance Checklist, fresh-clone, placeholder scan, final gate. |

---

# ЭТАП 10: UX И ФИНАЛИЗАЦИЯ — 2 задачи

| # | Задача | Статус | Коммит/Evidence |
|---|---|---|---|
| 58 | F1: Верификация 7 инвайт-кодов 🟢 | ⬜ OPEN | Для каждого из 7 кодов: регистрация → вход → чат (обе модели). Нет принятого рантайм-свидетельства. |
| 59 | F2: Оптимизация портала + финальный снапшот 🟢 | ⬜ OPEN | Минификация, gzip, кэширование статики, Lighthouse > 80, финальный снапшот. Не начато. |

---

# Дополнительный трек: автономное исполнение H0–H8 (завершено)

Выполнено ПОСЛЕ легаси-роадмапа (59 задач) и НЕ пересчитывает их нумерацию.
Итоговый результат: H8 final autonomous handoff gate — PASS (HERMES-INTEGRATION-H8-FINAL-AUTONOMOUS-HANDOFF-GATE).

| Этап | Содержание | Статус |
|---|---|---|
| H0 | Обнаружение топологии исполнения Hermes | ✅ DONE |
| H1 | Абстракция root-bridge executor + валидатор governance + framing моста | ✅ DONE |
| H2 | Разделение Git-идентичности (git как `codex`, Hermes как `root`) | ✅ DONE |
| H3 | Валидация committed implementation scope + E2E read-only канарейка | ✅ DONE |
| H4 | Sync-preserving retry governor + порядок governance-before-suppression | ✅ DONE |
| H5 | Валидация scheduler retry suppression | ✅ DONE |
| H6 | Валидация идемпотентности scheduler→Hermes | ✅ DONE |
| H7 | Активация persistent Hermes scheduler | ✅ DONE |
| H7B | Result-only feedback + безопасная публикация результата | ✅ DONE |
| H8 | Финальный гейт автономного handoff — PASS | ✅ DONE |

---

# СВОДКА (реконсилированная, 2026-08-17)

| Этап | Задач | ✅ DONE | ◐ PARTIAL | ⬜ OPEN | 👤 OWNER_REQUIRED | 🔒 HARDWARE_DEFERRED | 🗑 SUPERSEDED |
|---|---|---|---|---|---|---|---|
| 1. MVP | 7 | 7 | 0 | 0 | 0 | 0 | 0 |
| 2. Биллинг + каталог | 4 | 4 | 0 | 0 | 0 | 0 | 0 |
| 2.5. Авто-баланс + Grafana | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| 3. Observability + продакшен | 6 | 4 | 0 | 2 (D1, D2) | 0 | 0 | 0 |
| 4. RAG + кастомизация | 4 | 4 | 0 | 0 | 0 | 0 | 0 |
| 5. Продакшен-класс | 10 | 3 | 1 (#21) | 3 (D3, #15, #24) | 1 (#13) | 2 (#25, #26) | 0 |
| 5a. Требования руководства | 9 | 9 | 0 | 0 | 0 | 0 | 0 |
| 6. Эксплуатация | 6 | 6 | 0 | 0 | 0 | 0 | 0 |
| 7. Закрытый контур | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| 8. EMG-01 Stabilization 🚨 | 5 | 0 | 0 | 1 (C3) | 0 | 0 | 4 (C1, C2, C4, C5) |
| 9. Security | 3 | 0 | 1 (E1) | 0 | 2 (E2, E3) | 0 | 0 |
| 10. UX + Final | 2 | 0 | 0 | 2 (F1, F2) | 0 | 0 | 0 |
| **Итого** | **59** | **40** | **2** | **8** | **3** | **2** | **4** |

**Консервативная готовность (реконсилированная):**

- ✅ DONE: 40 (не менялись; подтверждены ранее аудитом или emergency-операциями).
- ◐ PARTIAL: 2 — #21 (multi-tenant изоляция), E1 (закрытие R6-блокеров).
- ⬜ OPEN: 8 — D1, D2, D3, #15 (Parsec), #24 (HA control-plane), C3 (stale pods), F1, F2.
- 👤 OWNER_REQUIRED: 3 — #13 (ЮKassa), E2 (HTTPS/Let's Encrypt), E3 (dev-аккаунты).
- 🔒 HARDWARE_DEFERRED: 2 — #25 (NVLink), #26 (модели 70B+).
- 🗑 SUPERSEDED: 4 — C1, C2, C4, C5 (сняты миграцией моделей).

Историческая цифра «40/59 = 68%» сохранена только как помеченный снапшот (см. шапку) и более
не является текущей истиной. Активная работа к RC1: **13 задач** (8 OPEN + 2 PARTIAL + 3 OWNER_REQUIRED);
плюс **2 HARDWARE_DEFERRED** вне RC1 и **4 SUPERSEDED**, выведенные из роадмапа.

---

# Обнаруженный дрейф репозитория

При реконсиляции выявлено: легаси-манифесты и каталоги (например, `03-vllm-14b-deploy/`,
конфиги `nginx-gateway-32b*`, а также README-секции с устаревшими именами моделей и переменными
окружения) всё ещё содержат устаревшие имена моделей. Это свидетельство дрейфа, НЕ основание
для изменения в рамках данной задачи. Требуется отдельная будущая задача по выравниванию
конфигурации; эти файлы в данной задаче НЕ изменяются.

---

# Предлагаемый критический путь к RC1 (на утверждение OWNER)

> Это ПРЕДЛОЖЕНИЕ на утверждение OWNER / Архитектора. Оно НЕ запускает следующую задачу.

Активные RC1-блокеры сгруппированы в крупные ограниченные гейты (не одно-командные STOP-задачи):

1. **GATE SEC-RC1 — закрытие безопасности.**
   - E1: довести closure R6-блокеров (Acceptance Matrix, Behavioral Compliance Checklist, fresh-clone, placeholder scan, final gate).
   - E2: выпуск/автопродление HTTPS-сертификата (OWNER: подтверждение управления доменом).
   - E3: удаление dev-аккаунтов (OWNER: решение о мутации БД).

2. **GATE OPS-RC1 — наблюдаемость и устойчивость.**
   - D1: Alertmanager + Telegram-алерты; D2: NTP-мониторинг; D3: автоматические бэкапы.
   - #21: довести multi-tenant изоляцию (ResourceQuota + NetworkPolicies + проверка связности).

3. **GATE INFRA-RC1 — укрепление узлов и HA.**
   - #15: Parsec на N7 (GRUB + плановая перезагрузка).
   - #24: оценка HA control-plane (принять решение о целесообразности).

4. **GATE BIZ-RC1 — биллинг и бета-финализация.**
   - #13: боевой режим ЮKassa (OWNER: `shopId`/`secretKey`).
   - F1: верификация инвайт-кодов; F2: оптимизация портала + финальный снапшот.

**Вне RC1 (требует отдельного решения Архитектора/OWNER о скоупе релиза):**
- #25 (NVLink-мосты) и #26 (модели 70B+) — HARDWARE_DEFERRED; не входят в RC1, пока не принято
  отдельное решение о расширении скоупа.
