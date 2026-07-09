---
title: Vault PKI
created: 2026-07-09
updated: 2026-07-09
type: entity
tags: [vault, security, auth, pki]
sources: []
---

# Vault PKI

Интеграция с HashiCorp Vault для внешнего управления API-ключами.

## Функции

- **Генерация ключей**: Vault PKI issue → API-ключи формата `ak-...`
- **Валидация**: Gateway проверяет ключ через Vault KV store
- **Политики ИБ**: права доступа (RPM, TPM, модели, IP-whitelist)
  хранятся в Vault и применяются на уровне [[AI Gateway]]

## Кэширование

Для снижения нагрузки на Vault используется двухуровневый кэш:

1. **Redis** (60s TTL) — горячий кэш в Gateway
2. **PostgreSQL** — персистентный fallback

## Архитектура потока

```
BFF → Vault PKI (issue key) → PostgreSQL cache
Gateway → Redis (60s TTL) → Vault KV (validate) → PG fallback
         └── apply policies: max_rpm, max_tpm, models, IP, expiry
```
