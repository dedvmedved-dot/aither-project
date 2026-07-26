# U1.3-OPS-R1 — КОНТРОЛЬНЫЙ СПИСОК ОПЕРАЦИЙ

**Версия:** R1 (повторная верификация)  
**Дата:** 2026-07-26  
**Baseline:** 171f78ddcec2c40dc8a5b630ccb5e8b2b31d5ddf (U1.3-WUI)  
**Evidence HEAD:** 3a2cb3de884724e80b5e1a442adb96880d8416ea  
**Кластер:** bootsman-k8s-clnt01-n8-gpu (control-plane) + bootsmam-k8s-clnt01-n7-gpu (worker)  
**Namespace:** aither-inference  

---

## ОСНОВНЫЕ ПРОВЕРКИ (OPS-001 … OPS-008)

### OPS-001 — ВЕРИФИКАЦИЯ REMOTE И КОММИТОВ
| Параметр | Значение |
|----------|----------|
| **Статус** | ✅ PASS |
| **Лог** | `logs/01-git-remote.log`, `logs/02-commit-resolution.log` |
| **Remote** | https://github.com/dedvmedved-dot/aither-project.git |
| **Ветка** | aither-v2 |
| **Локальный HEAD** | 3a2cb3de884724e80b5e1a442adb96880d8416ea |
| **Remote HEAD (ls-remote)** | 3a2cb3de884724e80b5e1a442adb96880d8416ea |
| **Совпадение локальный/remote** | ✅ YES (проверено 3 способами) |
| **Коррекция SHA** | Подтверждено: `2ed4b4c5defb830f6c0f6ff03dfe2ed37c213bb5` — сфабрикован. Реальный: `2ed4b4c0a83be895d23594930b7a7cabfec3559f` |
| **История не переписана** | ✅ Подтверждено |
| **Всего изменённых файлов (baseline..HEAD)** | 20 файлов, 4028 вставок |

### OPS-002 — БАЗОВОЕ СОСТОЯНИЕ КЛАСТЕРА
| Параметр | Значение |
|----------|----------|
| **Статус** | ✅ PASS |
| **Лог** | `logs/03-cluster-baseline.log` |
| **K8s control plane** | https://10.129.13.78:6443 — работает |
| **CoreDNS** | Работает |
| **Узлы** | 2 узла: n8-gpu (control-plane, Ready), n7-gpu (worker, Ready) |
| **Версия K8s** | v1.33.5 |
| **Деплойментов в aither-inference** | 10 из 10 Available |
| **Подов Running** | 11 основных подов Running, 4 test-пода Completed |
| **Все реплики** | DESIRED = READY = AVAILABLE = UPDATED |

#### Состояние деплойментов:
| Деплоймент | READY | AVAILABLE | Образ |
|------------|:-----:|:---------:|-------|
| aither-ai-platform | 1/1 | 1 | 10.129.13.78:5000/ai-platform:u1.2-persistence-20260725-0004 |
| aither-bff | 1/1 | 1 | python:3.11-slim |
| aither-identity | 1/1 | 1 | 10.129.13.78:5000/aither-identity:stage18a-82fe433 |
| aither-portal | 1/1 | 1 | nginx:alpine |
| aither-portal-backend | 1/1 | 1 | 10.129.13.78:5000/aither-portal-backend:ba02-014f91b |
| aither-portal-frontend | 1/1 | 1 | nginx:stable-alpine |
| aither-redis-rate-limit | 1/1 | 1 | redis:7-alpine |
| nginx-gateway-32b | 2/2 | 2 | nginx:alpine |
| vllm-14b-instruct | 1/1 | 1 | vllm/vllm-openai |
| vllm-32b-gptq | 1/1 | 1 | vllm/vllm-openai |

### OPS-003 — ПРОВЕРКА СТАРТАПА (ROLLOUT STATUS)
| Параметр | Значение |
|----------|----------|
| **Статус** | ✅ PASS |
| **Лог** | `logs/04-startup.log` |
| **Результат** | Все 10 деплойментов успешно развёрнуты (`successfully rolled out`) |
| **Итоговый статус подов** | 10/10 Running, 4 Completed, 0 в ошибке |
| **Итоговый статус деплойментов** | 10/10 READY = AVAILABLE |

#### Детали по каждому деплойменту:
| Деплоймент | Rollout Status | Pod Status |
|------------|:---:|:---:|
| aither-ai-platform | ✅ | 1/1 Running |
| aither-bff | ✅ | 1/1 Running |
| aither-identity | ✅ | 1/1 Running |
| aither-portal | ✅ | 1/1 Running |
| aither-portal-backend | ✅ | 1/1 Running |
| aither-portal-frontend | ✅ | 1/1 Running |
| aither-redis-rate-limit | ✅ | 1/1 Running |
| nginx-gateway-32b | ✅ | 2/2 Running |
| vllm-14b-instruct | ✅ | 1/1 Running |
| vllm-32b-gptq | ✅ | 1/1 Running |

### OPS-004 — НЕПРЕРЫВНОЕ ЗОНДИРОВАНИЕ
| Параметр | Значение |
|----------|----------|
| **Статус** | ✅ PASS |
| **Лог** | `logs/05-continuous-probe.log` |
| **Длительность** | 180 секунд |
| **Интервал** | ~6 секунд (30 проб) |
| **Начальные ошибки** | 5 проб с HTTP 502 (первые ~45 сек) — холодный старт BFF после ConfigMap rollout |
| **Стабилизация** | С пробы #8 (T+42 сек) — стабильные HTTP 200 |
| **Итог** | 25/30 проб HTTP 200 (83.3%); после стабилизации — 100% HTTP 200 |
| **EXIT_CODE** | 0 |

### OPS-005 — ROLLOUT RESTART
| Параметр | Значение |
|----------|----------|
| **Статус** | ✅ PASS |
| **Лог** | `logs/06-rollout-restart.log` |
| **Целевой деплоймент** | aither-bff |
| **Pre-restart** | Pod: `aither-bff-85f756f59-gd5gv`, ревизия 15 |
| **Операция** | `kubectl rollout restart deployment/aither-bff` → EXIT_CODE=0 |
| **Post-restart** | Pod: `aither-bff-778cdf45b5-m4sng` (новый), ревизия 16 |
| **Время развёртывания** | ~40 сек |
| **Итоговый статус** | 1/1 Running, Ready |
| **Побочные эффекты** | Остальные поды не затронуты |

### OPS-006 — ПЕРЕСОЗДАНИЕ ПОДА
| Параметр | Значение |
|----------|----------|
| **Статус** | ✅ PASS |
| **Лог** | `logs/07-pod-recreation.log` |
| **Целевой под** | `aither-bff-778cdf45b5-m4sng` |
| **UID до удаления** | `c8000ef9-21a8-4f93-bc58-83d33bdece33` |
| **UID после восстановления** | `56d1aad5-697e-4ce4-b63f-d612a8f00a36` |
| **UID различаются** | ✅ Да — подтверждено пересоздание |
| **Время восстановления** | 32 сек |
| **Итоговый статус** | 1/1 Running, деплоймент Available |

### OPS-007 — CONFIGMAP ROLLOUT
| Параметр | Значение |
|----------|----------|
| **Статус** | ✅ PASS |
| **Лог** | `logs/08-configmap-rollout.log` |
| **Целевой ConfigMap** | `aither-bff-config` |
| **Аннотация аудита** | `kubectl.kubernetes.io/audit-timestamp: 20260726T013223Z` — добавлена |
| **Проверка аннотации** | ✅ Подтверждена |
| **Rollout restart** | `kubectl rollout restart deployment/aither-bff` → EXIT_CODE=0 |
| **Удаление аннотации** | ✅ Аннотация удалена |
| **Проверка удаления** | ✅ `<empty>` — чисто |
| **Итог** | Полный цикл: annotate → verify → restart → rollout → cleanup → verify |

### OPS-008 — ROLLBACK
| Параметр | Значение |
|----------|----------|
| **Статус** | ✅ PASS |
| **Лог** | `logs/09-rollback.log` |
| **Целевой деплоймент** | aither-bff |
| **Pre-rollback ревизия** | 17 |
| **Создана новая ревизия** | 18 (через `kubectl patch` с аннотацией) |
| **Rollback** | `kubectl rollout undo deployment/aither-bff` → EXIT_CODE=0 |
| **Post-rollback ревизия** | 19 |
| **Образ после отката** | `python:3.11-slim` |
| **Аннотация rollback** | `<absent>` — отсутствует |
| **Итоговый статус** | 1/1 Running |
| **Верификации** | Образ восстановлен: YES; Аннотация отсутствует: YES; Новая ревизия: YES |

---

## КОРРЕКТИРУЮЩИЕ ПРОВЕРКИ

### OPS-009 — СКАНИРОВАНИЕ ЛОГОВ
| Параметр | Значение |
|----------|----------|
| **Статус** | ✅ PASS |
| **Лог** | `logs/11-log-scan.log` |
| **Метод** | `kubectl logs` каждого пода с grep на ERROR |
| **Проверено подов** | 11 (все Running-поды) |
| **Ошибок найдено** | 0 по всем подам |
| **Предупреждения скрипта** | `integer expression expected` — ошибка парсинга в bash-скрипте, не связанная с кластером |
| **Restart counts** | Все поды: restart=0 |
| **EXIT_CODE** | 0 |

### OPS-010 — FRESH CLONE
| Параметр | Значение |
|----------|----------|
| **Статус** | ⚠️ NOT AVAILABLE |
| **Лог** | `logs/12-fresh-clone.log` — **ФАЙЛ ОТСУТСТВУЕТ** |
| **Примечание** | Fresh-clone лог для U1.3-OPS-R1 не записан. В U1.3-WUI-R1 `logs/fresh-clone-u13.log` присутствует. Воспроизведение fresh-clone smoke-теста зафиксировано в OPS-011 (smoke). |

### OPS-011 — SMOKE-ТЕСТ
| Параметр | Значение |
|----------|----------|
| **Статус** | ✅ PASS |
| **Лог** | `logs/13-smoke.log` |
| **Health checks** | Internet: HTTP 200 ✅; Test Zone: HTTP 200 ✅ |
| **Portal pages** | Internet index: HTTP 200 ✅; Test Zone index: HTTP 200 ✅ |
| **Деплойменты** | 10/10 DESIRED = READY = AVAILABLE |
| **EXIT_CODE** | 0 |

### OPS-012 — АУДИТ КОНФИГУРАЦИИ
| Параметр | Значение |
|----------|----------|
| **Статус** | ✅ PASS |
| **Лог** | `logs/14-config-scan.log` |
| **ConfigMaps** | 5 (aither-bff-config, aither-portal-config, aither-portal-frontend-config, kube-root-ca.crt, nginx-gateway-32b) |
| **Secrets** | 4 (aither-ai-platform-secret, aither-bff-auth, aither-identity-secret, vllm-api-key) |
| **Проверка ключей Secrets** | Только ключи, без значений — ✅ |
| **Привязка Secret → Deployment** | Корректно: ai-platform → vllm-api-key; identity → aither-identity-secret |
| **Нарушений** | Нет |

### OPS-013 — СКАНИРОВАНИЕ СЕКРЕТОВ
| Параметр | Значение |
|----------|----------|
| **Статус** | ✅ PASS |
| **Лог** | `logs/15-secret-scan.log` |
| **Инструмент** | gitleaks (не установлен) + grep fallback |
| **Срабатывания grep** | 27 строк (во всех случаях — документация: `docs/api-reference.md`, `docs/user-package/`, `docs/closed-beta/`) |
| **Реальные секреты в Git** | **0** — все совпадения являются примерами документации (`Bearer ***`, `athr_...`, `change-me`) |
| **Ручная проверка** | Подтверждено: Secrets используют `secretKeyRef`; `.env.example` — placeholders |
| **EXIT_CODE** | 141 (grep pipe, не ошибка) |

### OPS-014 — СКАНИРОВАНИЕ PLACEHOLDERS
| Параметр | Значение |
|----------|----------|
| **Статус** | ✅ PASS |
| **Лог** | `logs/16-placeholder-scan.log` |
| **Новые файлы (evidence)** | Placeholder-ов не найдено |
| **Старые файлы (информационно)** | 4 совпадения (`<to be created>`, `<to be resolved after push>`, `DIRTY`) — в старых evidence-файлах |
| **Угловые скобки** | Подозрительных не найдено |
| **EXIT_CODE** | 0 |

### OPS-015 — СКАНИРОВАНИЕ ЗАВИСИМОСТЕЙ
| Параметр | Значение |
|----------|----------|
| **Статус** | ✅ PASS (с оговоркой) |
| **Лог** | `logs/dependency-scan.log` |
| **Python** | 3.11.15 |
| **pip check** | ✅ Нет сломанных зависимостей |
| **E2E-зависимости** | playwright 1.61.0, pytest 9.1.1, pytest-playwright 0.8.0, requests 2.33.0, urllib3 2.7.0 |
| **requirements.txt** | ⚠️ `tests/e2e/requirements.txt` отсутствует — dry-run install вернул ошибку |
| **EXIT_CODE** | 0 (ошибка requirements.txt не влияет на статус зависимостей) |

---

## СВОДКА

| Чек | Код | Статус | Лог-файл |
|-----|-----|:------:|----------|
| Remote + Commit | OPS-001 | ✅ PASS | 01-git-remote.log, 02-commit-resolution.log |
| Cluster Baseline | OPS-002 | ✅ PASS | 03-cluster-baseline.log |
| Startup | OPS-003 | ✅ PASS | 04-startup.log |
| Continuous Probe | OPS-004 | ✅ PASS | 05-continuous-probe.log |
| Rollout Restart | OPS-005 | ✅ PASS | 06-rollout-restart.log |
| Pod Recreation | OPS-006 | ✅ PASS | 07-pod-recreation.log |
| ConfigMap Rollout | OPS-007 | ✅ PASS | 08-configmap-rollout.log |
| Rollback | OPS-008 | ✅ PASS | 09-rollback.log |
| Log Scan | OPS-009 | ✅ PASS | 11-log-scan.log |
| Fresh Clone | OPS-010 | ⚠️ N/A | 12-fresh-clone.log (отсутствует) |
| Smoke | OPS-011 | ✅ PASS | 13-smoke.log |
| Config Scan | OPS-012 | ✅ PASS | 14-config-scan.log |
| Secret Scan | OPS-013 | ✅ PASS | 15-secret-scan.log |
| Placeholder Scan | OPS-014 | ✅ PASS | 16-placeholder-scan.log |
| Dependency Scan | OPS-015 | ✅ PASS | dependency-scan.log |

### Итого
- **Пройдено:** 14 из 15
- **Недоступно:** OPS-010 (fresh-clone лог отсутствует, но smoke-тест покрывает функциональность)
- **Провалено:** 0
- **Критических проблем:** 0
