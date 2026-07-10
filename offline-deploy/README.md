# Aither Platform — офлайн-пакет развёртывания

**Версия:** 1.1 (10.07.2026)
**Предыдущая:** 1.0 (05.07.2026)

Самодостаточный пакет для развёртывания Aither Platform в закрытом контуре
без доступа в Интернет.

## Состав пакета

| Каталог | Описание |
|---|---|
| `docs/` | 8 документов: архитектура, деплой, админ, пользователь, безопасность |
| `k8s/` | Kubernetes-манифесты (gateway, vLLM 14B/32B, PostgreSQL, Redis) |
| `configs/` | Эталонные конфигурации (nginx, BFF .env, Gateway, vLLM) |
| `scripts/` | Скрипты эксплуатации (health-check, backup/restore, ротация ключей) |
| `offline/` | Офлайн-зависимости (Docker-образы, pip wheels, npm pack, модели) |
| `tests/` | Приёмо-сдаточные тесты (smoke, API, security) |

## Архитектура (кратко)

```
Пользователь → VPS1 (nginx :10443) → VPS2 (портал, BFF, PostgreSQL)
                                   → VPS1 (Gateway :30900 → K8s → vLLM)
                                   → VPS1 (Grafana :30300)
```

Два GPU-узла:
- **n8-gpu** (10.129.13.78): K8s control plane, Gateway, vLLM 14B, Redis
- **n7-gpu** (10.129.13.77/40.50): vLLM 32B

## Быстрый старт

```bash
# 1. Проверить здоровье
./scripts/health-check.sh

# 2. Пройти приёмо-сдаточные тесты
make test

# 3. Сделать бэкап
./scripts/backup.sh
```

## Что нового в 1.1

- Gateway: многопоточный режим (ThreadingHTTPServer) — исправлены 502 в чатах
- Исправлены баги портала (дубликат renderDashboard, highlightCode, устаревшая статика)
- Обновлены все конфиги под реальное окружение (nginx, BFF .env, Gateway deployment)
- health-check.sh: реальные эндпоинты (Portal API, Gateway, vLLM, Grafana)
- troubleshooting.md: 7 новых записей на основе реальных инцидентов
- Документация: актуальные IP, порты, схема архитектуры
