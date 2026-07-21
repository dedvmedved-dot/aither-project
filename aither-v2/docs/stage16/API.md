# Aither AI Platform — API Reference

## Models

### List Models
```http
GET /api/v1/models
Authorization: Bearer <token>
```
Response 200: Array of model objects.

### Get Model
```http
GET /api/v1/models/{id}
Authorization: Bearer <token>
```

### Create Model (Admin)
```http
POST /api/v1/models
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "name": "qwen-14b-instruct",
  "display_name": "Qwen 14B Instruct",
  "provider": "local",
  "model_identifier": "qwen-14b-instruct",
  "description": "Chat-optimized model",
  "context_window": 8192,
  "enabled": true
}
```

### Update Model (Admin)
```http
PATCH /api/v1/models/{id}
```

### Delete/Disable Model (Admin)
```http
DELETE /api/v1/models/{id}
```
Disables if used by assistants; deletes if unused.

## API Keys

### List Keys
```http
GET /api/v1/api-keys
Authorization: Bearer <token>
```
Returns prefix, dates, status — NOT full key.

### Create Key
```http
POST /api/v1/api-keys
Authorization: Bearer <token>
Content-Type: application/json

{"name": "My Key"}
```
Response includes `full_key` — shown once only.

### Revoke Key
```http
DELETE /api/v1/api-keys/{id}
Authorization: Bearer <token>
```

## Assistants

### List
```http
GET /api/v1/assistants
```

### Create
```http
POST /api/v1/assistants
{
  "name": "Assistant",
  "model_id": 1,
  "system_prompt": "...",
  "temperature": 0.7,
  "max_tokens": 2048
}
```

### Update
```http
PATCH /api/v1/assistants/{id}
```

### Delete
```http
DELETE /api/v1/assistants/{id}
```

## Conversations

### List
```http
GET /api/v1/conversations
```

### Create
```http
POST /api/v1/conversations
{"assistant_id": 1, "title": "Chat"}
```

### Get (with messages)
```http
GET /api/v1/conversations/{id}
```

### Delete
```http
DELETE /api/v1/conversations/{id}
```

### Send Message
```http
POST /api/v1/conversations/{id}/messages
{"content": "Hello"}
```
Returns AI response.

## AI API (OpenAI-Compatible)

### Chat Completions
```http
POST /v1/chat/completions
Authorization: Bearer aither_<prefix>_<secret>
Content-Type: application/json

{
  "model": "qwen-14b-instruct",
  "messages": [{"role": "user", "content": "Hello"}],
  "stream": false,
  "temperature": 0.7,
  "max_tokens": 2048
}
```

**Limitations vs OpenAI API:**
- Only `model`, `messages`, `stream`, `temperature`, `max_tokens` supported
- `stream: true` returns single SSE event (not true streaming for Beta v0.9)
- `functions`, `tools`, `response_format` not supported

## Error Format
```json
{"detail": "Human-readable message"}
```
