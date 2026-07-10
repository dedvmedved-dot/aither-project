# Changelog — Aither Platform

## v1.1 (10.07.2026)

### Исправления
- Gateway: многопоточный режим (ThreadingHTTPServer) — исправлены 502 ошибки в чатах при повторных запросах
- Портал: исправлен `highlightCode` (кнопка «Перейти» на тарифах)
- Портал: удалён дубликат `renderDashboard` (пустой дашборд)
- Портал: синхронизирована статика VPS2 → VPS1 (nginx кэшировал старую версию)

### Обновления конфигурации
- `k8s/gateway/deployment.yaml` — переписан под реальный K8s (namespace default, ConfigMap, delegation-key)
- `configs/nginx/nginx.conf` — актуальная схема с VPS1 (fb1.spb.ru:10443, /v1/, /grafana/)
- `configs/bff/.env.template` — реальные переменные (OAuth, PostgreSQL, делегирование)
- `scripts/health-check.sh` — проверка Portal API, Gateway, vLLM, Grafana, PostgreSQL

### Документация
- `docs/01-architecture.md` — актуальная схема с IP, портами, потоком запросов
- `docs/06-troubleshooting.md` — 7 новых записей на основе реальных инцидентов
- `README.md` — версия 1.1, обновлённый состав и архитектура
- `VERSION` → 1.1

---

## v1.0 (05.07.2026)

- Первый релиз офлайн-пакета
- 8 документов, K8s-манифесты, Ansible playbooks (заготовки)
- Скрипты эксплуатации, офлайн-зависимости, приёмо-сдаточные тесты
