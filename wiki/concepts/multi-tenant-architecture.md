---
title: Multi-Tenant Architecture
created: 2026-07-09
updated: 2026-07-09
type: concept
tags: [architecture, multi-tenant, security]
sources: []
---

# Multi-Tenant Architecture

Модель изоляции организаций в платформе Aither.

## Уровни изоляции

| Уровень | Компонент | Механизм |
|---|---|---|
| Аутентификация | [[AI Gateway]] | API-ключи `ak-...` с привязкой к `org_id` |
| Rate Limiting | [[Redis]] | Per-org sliding window (RPM/TPM) |
| Биллинг | [[Billing System]] | Per-org баланс и резервирование |
| Данные | [[PostgreSQL]] | Row-level: `org_id` в каждой таблице |
| Модели | [[vLLM Inference]] | Общая очередь, приоритет по тарифу |
| RAG | [[ChromaDB]] | Per-org коллекции (в разработке) |

## Тарифные уровни

- **Free**: 14B, 100 запросов/день, общая очередь
- **Standard**: 14B + 32B, 1000 запросов/день, приоритетная очередь
- **VIP**: все модели + [[LLM-Wiki]] RAG, 10K запросов/день, выделенные слоты
- **Enterprise**: on-premise, кастомные модели, SLA, [[SIEM Integration]]

## Принципы

- Каждый `org_id` изолирован на уровне данных
- Перекрёстный доступ невозможен без явного шаринга
- Все аудит-события содержат `org_id` для трассировки
