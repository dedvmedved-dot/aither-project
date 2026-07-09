# Changelog

## [1.0.0] — 11.07.2026

### Добавлено

- Пакет офлайн-развёртывания для закрытого контура
- K8s-манифесты: Gateway, vLLM 14B, vLLM 32B, PostgreSQL, Redis, ChromaDB
- Ansible playbooks для полного цикла (ОС → GPU → K8s → vLLM → Портал)
- Скрипты эксплуатации: health-check, backup/restore, ротация ключей
- Приёмо-сдаточные тесты: smoke, API, security
- Документация: архитектура, деплой, админ, пользователь, безопасность
- Офлайн-зависимости: docker save/load, pip download, npm pack

### Компоненты платформы

- Портал (SPA + BFF) — веб-интерфейс, OAuth, чаты, биллинг
- Gateway — Rate Limiter, AI Security (DLP + Prompt Injection), биллинг
- vLLM 14B + 32B — инференс на 2× RTX 6000 (TP=2)
- PostgreSQL — биллинг, пользователи, организации
- Redis — Rate Limiter (sliding window)
- ChromaDB — векторная БД для RAG
- Prometheus + Grafana — мониторинг GPU, инференса, биллинга
