---
title: AI Gateway
created: 2026-07-09
updated: 2026-07-09
type: entity
tags: [gateway, architecture, security]
sources: []
---

# AI Gateway

Центральный компонент платформы Aither, обеспечивающий приём и маршрутизацию
запросов к vLLM-моделям.

## Функции

- **Аутентификация**: JWT RS256 и API-ключи (`ak-...`), интеграция с [[Vault PKI]]
- **Rate Limiting**: Redis sliding-window, индивидуальные лимиты RPM/TPM per-org
- **Маршрутизация**: выбор модели по каталогу, учёт доступности GPU
- **Безопасность**: ingress DLP ([[Security Ingress]]), egress DSP-фильтр ([[Security Egress]])
- **Биллинг**: посекундный учёт токенов через [[Billing System]]
- **SIEM**: аудит-логи в формате CEF через [[SIEM Integration]]

## Архитектура

Запросы поступают через [[BFF]] с VPS2/VPS3, Gateway валидирует JWT/API-key,
проверяет лимиты в Redis, резервирует токены в [[PostgreSQL]], проксирует
запрос к [[vLLM Inference]], проверяет ответ через egress-фильтр,
возвращает клиенту.

## Эндпоинты

- `/v1/chat/completions` — OpenAI-совместимый chat
- `/v1/rag/query` — векторный поиск ([[ChromaDB]])
- `/v1/rag/hybrid-query` — гибридный поиск ([[ChromaDB]] + [[LLM-Wiki]])
- `/v1/rag/ingest` — загрузка документов
- `/v1/rag/wiki-ingest` — синхронизация wiki → ChromaDB
- `/health` — проверка состояния

## Модели безопасности

Gateway реализует трёхуровневую защиту:

1. **Ingress**: проверка prompt injection, DLP-паттерны
2. **Egress**: фильтр ДСП/ПДн/системных утечек на выходе
3. **Audit**: все события → PostgreSQL + syslog CEF → SIEM
