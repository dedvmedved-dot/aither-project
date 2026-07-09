---
title: SIEM Integration
created: 2026-07-09
updated: 2026-07-09
type: entity
tags: [siem, security, operations]
sources: []
---

# SIEM Integration

Подсистема отправки событий безопасности в SIEM-систему.

## Каналы

1. **PostgreSQL** `security_events` — структурированное хранение всех событий
2. **JSON-логи** — ротация 30 дней, локальное хранение
3. **Syslog CEF** — стандартный формат для SIEM (local0.CRIT)

## Формат CEF

```
CEF:0|Aither|SecurityGateway|1.0|<event_id>|<event_name>|<severity>|
  msg=<message> src=<ip> org=<org_id> user=<user_id>
```

## Типы событий

- `auth_failure` — неудачная аутентификация
- `dlp_violation` — срабатывание DLP-фильтра ([[Security Ingress]])
- `egress_block` — блокировка ответа ([[Security Egress]])
- `rate_limit_exceeded` — превышение лимитов ([[Rate Limiting]])
- `heartbeat` — проверка живости (каждые 60s)

## Интеграция

Вызывается из [[AI Gateway]] после каждого события через
`log_security_event()`.
