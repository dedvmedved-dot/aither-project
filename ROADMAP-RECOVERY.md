# Aither Platform — Пошаговый план: 59 задач от текущего состояния до ROADMAP 100%

**Дата:** 27.07.2026
**Текущий HEAD:** `4cf0847`
**Выполнено:** 40/59 (68%)
**Осталось:** 17 действующих + 2 заблокированных
**Принцип:** Одна строка = одна задача. После каждой — STOP, verify, commit. Существующий функционал не разрушать.

---

## Легенда

| Статус | Обозначение |
|---|---|
| ✅ | Выполнено (40 задач — подтверждено аудитом или emergency-операциями) |
| ⬜ | Не выполнено — действующая |
| 🔒 | Заблокировано (железо) |
| 🚨 | Аварийный режим — требует stabilisation |
| ⚙️ | Требует изменения K8s/инфраструктуры |
| ✏️ | Требует изменения кода/файлов |
| 👤 | Требует OWNER ACTION |
| ⏸️ | STOP после задачи — ждать команду |

---

# ЭТАП 1: MVP (дни 1–7) — 7/7 ✅

| # | Задача | ROADMAP | Статус | Коммит/Evidence |
|---|---|---|---|---|
| 1 | K8s + GPU Operator на N8 | #1 | ✅ | K8s v1.33.5, 2 узла, GPU Operator Running |
| 2 | containerd + nvidia-runtime | #2 | ✅ | `runtimeClassName: nvidia` на обоих узлах |
| 3 | vLLM 14B загрузка и запуск | #3 | ✅ | `vllm-14b-instruct` Running, FP16 28 GB |
| 4 | Tensor Parallelism (TP=2) | #4 | ✅ | TP=2 на 14B (N8) и 32B (N7) |
| 5 | Gateway (FastAPI + Redis RL) | #5 | ✅ | `nginx-gateway-32b` (2 реплики), Redis |
| 6 | Portal (SPA + BFF + SSE) | #6 | ✅ | `aither-portal` NodePort 30080, aither-bff (2 реплики) |
| 7 | OAuth (GitHub, Google, Яндекс) | #7 | ✅ | `aither-identity` + 3 провайдера + LDAP |

---

# ЭТАП 2: Биллинг и каталог (дни 8–10) — 4/4 ✅

| # | Задача | ROADMAP | Статус | Коммит/Evidence |
|---|---|---|---|---|
| 8 | ЮKassa — пополнение баланса (dev-режим) | #8 | ✅ | `POST /api/v1/billing/topup`, dev-режим работает |
| 9 | Каталог моделей (YAML → Gateway) | #9 | ✅ | `catalog.yaml`, `GET /v1/models` → 14B + 32B |
| 10 | Второй узел N7 + 32B модель | #10 | ✅ | N7 worker, `vllm-32b-gptq` GPTQ Int4 TP=2 |
| 11 | Фиксы портала (502/404/500) | #11 | ✅ | org_id UUID→TEXT, nginx SSE, 404 fix |

---

# ЭТАП 2.5: Авто-баланс + Grafana — 2/2 ✅

| # | Задача | ROADMAP | Статус | Коммит/Evidence |
|---|---|---|---|---|
| 12 | Авто-баланс (100K + рефилл ×10) | #11a | ✅ | `ensurePersonalOrg()` в BFF, авто-пополнение |
| 13 | Grafana публичный доступ | #11b | ✅ | `grafana.130.17.1.90.nip.io` |

---

# ЭТАП 3: Observability и продакшен — 6 задач

| # | Задача | ROADMAP | Статус | Действие |
|---|---|---|---|---|
| 14 | Observability — Grafana дашборд | #12 | ✅ | Prometheus + Grafana, GPU+vLLM дашборды, DCGM |
| **15** | **D1: Alertmanager + Telegram-алерты** 🚨 | **NEW** | **⬜** | ✏️⚙️ Развернуть Alertmanager. Правила: GPU temp>85°, GPU mem>95%, pod restarts>3. Telegram webhook через бота/Hermes. Проверить: тестовый алерт → Telegram. 📦 `infra(observability): deploy Alertmanager with Telegram alerts` ⏸️ |
| 16 | AI Security Gateway (расширенный) | #14 | ✅ | Prompt injection + DLP (29 паттернов) |
| **17** | **D2: NTP-мониторинг** 🚨 | **NEW** | **⬜** | ✏️ Добавить Prometheus алерт: `node_timex_offset_seconds > 5`. Проверить `chronyc tracking` на N7 и N8. 📦 `infra(observability): add NTP offset alert` ⏸️ |
| 18 | Gateway в K8s (вынос из BFF) | #16 | ✅ | `nginx-gateway-32b` Deployment (2 реплики) |
| 19 | Портал: стабилизация (OAuth fix, chat bugs) | #16a | ✅ | `095afdc` — JS fix, closeModal, feedback, timeout — применено в EMG-01 |

---

# ЭТАП 4: RAG и кастомизация — 4/4 ✅

| # | Задача | ROADMAP | Статус | Коммит/Evidence |
|---|---|---|---|---|
| 20 | RAG-подсистема (Wiki-Graph, гибридный) | #17 | ✅ | Замена ChromaDB на Wiki-Graph RAG (Karpathy-style) |
| 21 | Fine-tuning пайплайн (LoRA) | #18 | ✅ | LoRA `astra-14b` (68.9 MB), PEFT-конвертер |
| 22 | Cost-aware routing | #19 | ✅ | `catalog.resolve()` — маршрутизация 14B/32B |
| 23 | Model playground (A/B сравнение) | #20 | ✅ | Выпадающий список моделей в портале |

---

# ЭТАП 5: Продакшен-класс — 7 задач

| # | Задача | ROADMAP | Статус | Действие |
|---|---|---|---|---|
| **24** | **D3: Автоматические бэкапы (PostgreSQL + Redis)** 🚨 | **NEW** | **⬜** | ⚙️ Создать K8s CronJob: ежедневный `pg_dump` → PVC. Ежедневный `redis-cli BGSAVE` → PVC. Проверить восстановление. 📦 `infra(backup): daily PostgreSQL + Redis backup CronJobs` ⏸️ |
| 25 | Тарифные планы (Free/Standard/VIP/Enterprise) | #21a | ✅ | 4 тарифа, Redis-cached limits, model access control |
| 26 | VPS3 Failover (горячий резерв) | #22 | ✅ | VPS3 поднят, stateless BFF, SSH-туннель, nginx backup |
| 27 | SaaS-портал (signup/login/dashboard) | #23 | ✅ | Signup/login/billing/tiers/upgrade — VPS2+VPS3 |
| **28** | **#13 ЮKassa боевой режим** | **#13** | **⬜** | 👤✏️⚙️ **3 подзадачи:** (a) Получить `shopId`+`secretKey` от OWNER. (b) Создать K8s Secret `yookassa-credentials`. Обновить BFF ConfigMap: `IS_PRODUCTION=true`, `YOOKASSA_ENABLED=true`. (c) Тестовый платёж 1₽ → зачисление ~100 токенов. 📦 `feat(billing): enable YooKassa production mode` ⏸️ |
| **29** | **#15 Parsec на N7 (`max_ilev=63`)** | **#15** | **⬜** | ⚙️ SSH на N7. Убрать `parsec=0`, добавить `max_ilev=63 execstack=1` в GRUB. `update-grub`. Плановая перезагрузка N7. Проверить `parsec_status` и 32B после ребута. 📦 `infra(security): re-enable Parsec on N7 (max_ilev=63)` ⏸️ |
| **30** | **#21 Multi-tenant изоляция** | **#21** | **⬜** | ⚙️ **2 подзадачи:** (a) ResourceQuota на `aither-inference`. (b) NetworkPolicies: BFF→Gateway→vLLM, запрет cross-pod трафика. Проверить: связность не сломана. 📦 `infra(security): add ResourceQuota + NetworkPolicies` ⏸️ |
| **31** | **#24 HA K8s Control Plane** | **#24** | **⬜** | ⚙️ Оценить возможность повышения N7 до control-plane. `kubeadm join --control-plane` (если возможно). Задокументировать ограничение 2-членного etcd. 📦 `infra(k8s): promote N7 to control-plane for HA` ⏸️ |
| **32** | NVLink-мосты | #25 | 🔒 | Нет физических мостов. Заявка на закупку. |
| **33** | Модели 70B+ | #26 | 🔒 | Нужны NVLink + NVSwitch + ≥4 GPU. |

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

| # | Задача | Статус | Действие |
|---|---|---|---|
| **50** | **C1: N7 GPU#1 idle — диагностика и исправление** 🚨 | **⬜** | 🔍 `kubectl logs vllm-32b-gptq --tail=50`. Проверить `tensor_parallel_size` в логах vLLM. Если TP=1 — пропатчить деплоймент на TP=2, 2 GPU. `kubectl rollout restart`. Если TP=2 уже — зафиксировать limitation с evidence. 📦 `evidence/emg-01/c1-n7-gpu-idle.md` ⏸️ |
| **51** | **C2: Верификация 14B на N8 (availability probe)** 🚨 | **⬜** | 🔍 `python3 scripts/ops/http_availability_probe.py --target http://vllm-14b-instruct.aither-inference:8000 --count 240 --interval 1`. Ожидание: 240/240 HTTP 200, p95 < 5s. 📦 `evidence/emg-01/c2-14b-availability-probe.md` ⏸️ |
| **52** | **C3: Очистка кластера (stale pods)** 🚨 | **⬜** | ⚙️ `kubectl delete pod test-curl test-curl2 test-pf test-vllm test-vllm2 tmp-curl tmp-curl2 -n aither-inference`. `kubectl delete pod node-debugger-* -n default`. Проверить: 0 Completed/Error подов. 📦 `chore(emg-01): remove stale pods from cluster` ⏸️ |
| **53** | **C4: Node labels → Git** 🚨 | **⬜** | ✏️ Добавить `aither.io/vllm14b-primary: "true"` в nodeSelector манифеста `03-vllm-14b-deploy/manifests/vllm-deployment.yaml`. 📦 `infra(vllm-14b): persist N8 node label in deployment manifest` ⏸️ |
| **54** | **C5: Удалить дубликат 32B с N8 (19 GB)** 🚨 | **⬜** | ⚙️ `ssh root@10.129.13.78 'rm -rf /data/models/Qwen2.5-32B-GPTQ/'`. Проверить: 32B на N7 работает. 📦 `chore(emg-01): remove unused 32B model copy from N8` ⏸️ |

---

# ЭТАП 9: БЕЗОПАСНОСТЬ — 3 задачи

| # | Задача | Статус | Действие |
|---|---|---|---|
| **55** | **E2: HTTPS (Let's Encrypt)** 🔴 | **⬜** | 👤⚙️ Проверить текущий сертификат `fb1.spb.ru`. Подтвердить управление доменом у OWNER. `certbot certonly --nginx -d fb1.spb.ru`. Настроить авто-обновление. 📦 `infra(nginx): enable HTTPS with Let's Encrypt` ⏸️ |
| **56** | **E3: Удалить dev-аккаунты из БД** 🟡 | **⬜** | ⚙️ `SELECT user_id, login FROM portal_users WHERE oauth_provider='dev'`. `DELETE` — все, кроме `owner-r5`. Проверить: OAuth работает, admin работает. 📦 `fix(security): remove dev-test accounts` ⏸️ |
| **57** | **E1: Закрытие 14 исторических R6-блокеров** 🟡 | **⬜** | ✏️⚙️ Credential rotation evidence. Gitleaks classification fix (runtime, не эвристика). Model-switch contract restore. Probe contract complete (stats, concurrency, JUnit). Fresh-clone evidence. Acceptance Matrix. Behavioral Compliance Checklist. Placeholder Scan. Final gate script. Markdown files content. Final report fix. 📦 Серия commits: `evidence(r6): ...` ⏸️ |

---

# ЭТАП 10: UX И ФИНАЛИЗАЦИЯ — 2 задачи

| # | Задача | Статус | Действие |
|---|---|---|---|
| **58** | **F1: Верификация 7 инвайт-кодов** 🟢 | **⬜** | 🔍 Для каждого из 7 кодов: регистрация → вход → чат 14B → чат 32B. 7/7 успешно. 📦 `evidence/beta/invite-codes-verification.md` ⏸️ |
| **59** | **F2: Оптимизация портала + финальный снапшот** 🟢 | **⬜** | ⚙️ Минификация `index.html`, gzip в nginx, кэширование статики. Lighthouse > 80. Создать финальный снапшот `configs/snapshot-final/`. 📦 `perf(portal): minification + gzip + final snapshot` ⏸️ |

---

# СВОДКА

| Этап | Задач | ✅ | ⬜ | 🔒 |
|---|---|---|---|---|
| 1. MVP | 7 | 7 | 0 | 0 |
| 2. Биллинг + каталог | 4 | 4 | 0 | 0 |
| 2.5. Авто-баланс + Grafana | 2 | 2 | 0 | 0 |
| 3. Observability + продакшен | 6 | 4 | **2** (D1, D2) | 0 |
| 4. RAG + кастомизация | 4 | 4 | 0 | 0 |
| 5. Продакшен-класс | 7 | 3 | **3** (#13,#15,#21,#24) + D3 | **2** (#25,#26) |
| 5a. Требования руководства | 9 | 9 | 0 | 0 |
| 6. Эксплуатация | 6 | 6 | 0 | 0 |
| 7. Закрытый контур | 1 | 1 | 0 | 0 |
| 8. EMG-01 Stabilization 🚨 | 5 | 0 | **5** (C1–C5) | 0 |
| 9. Security | 3 | 0 | **3** (E1,E2,E3) | 0 |
| 10. UX + Final | 2 | 0 | **2** (F1,F2) | 0 |
| **Итого** | **59** | **40** | **17** | **2** |

**Готовность:** 40/59 = 68%. Осталось 17 действующих задач.

---

**Первая невыполненная задача: #50 (C1) — N7 GPU#1 idle. Жду команду.**
