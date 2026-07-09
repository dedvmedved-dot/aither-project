# 07-api-reference.md — API Reference

> Полная спецификация: `docs/api-reference.md` и `docs/openapi.yaml` в основном репозитории.

**Базовый URL:** `http://YOUR_PORTAL_IP/api/v1`  
**Аутентификация:** `Authorization: Bearer ***`

## Эндпоинты

### GET /api/v1/health
Проверка работоспособности портала.
```json
{"status":"ok","service":"aither-api","version":"1.0"}
```

### GET /api/v1/models
Список доступных моделей.
```json
{"data": [{"id": "qwen2.5-14b", "display_name": "Qwen 2.5 14B", "max_tokens": 4096}]}
```

### POST /api/v1/chat/completions
OpenAI-совместимый инференс.
```bash
curl -X POST http://YOUR_PORTAL_IP/api/v1/chat/completions \
  -H "Authorization: Bearer ***  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-14b","messages":[{"role":"user","content":"Hi"}]}'
```

**Параметры:**
| Параметр | Тип | Описание |
|---|---|---|
| model | string | ID модели |
| messages | array | История сообщений |
| max_tokens | int | Макс. токенов (по умолчанию: 2048) |
| temperature | float | Креативность (0-2, по умолчанию: 0.7) |
| stream | bool | SSE-стриминг (по умолчанию: false) |

**Коды ответов:**
| Код | Описание |
|---|---|
| 200 | Успех |
| 400 | Неверный запрос |
| 401 | Неверный API-ключ |
| 402 | Недостаточно средств |
| 403 | Заблокировано (DLP/инъекция) |
| 429 | Rate limit превышен |

## OpenAPI

Полная Swagger-спецификация: `docs/openapi.yaml` в репозитории.
