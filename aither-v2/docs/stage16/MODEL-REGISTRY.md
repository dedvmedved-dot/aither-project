# Model Registry — Stage 16

## Model Schema

| Field | Type | Description |
|---|---|---|
| `id` | INTEGER (PK) | Auto-increment |
| `name` | TEXT (UNIQUE) | Machine-readable identifier |
| `display_name` | TEXT | Human-readable name |
| `provider` | TEXT | `local` or `openai-compatible` |
| `endpoint` | TEXT | Optional: API endpoint URL |
| `model_identifier` | TEXT | Identifier sent to Gateway |
| `description` | TEXT | Description |
| `context_window` | INTEGER | Max context tokens |
| `enabled` | INTEGER | 1=active, 0=disabled |
| `created_at` | TEXT | ISO timestamp |
| `updated_at` | TEXT | ISO timestamp |

## Provider Types

- **`local`** — Model served by the local Gateway → vLLM inference
- **`openai-compatible`** — Reserved for future external integrations

## Bootstrap

To register the existing Qwen 14B Instruct model:

```bash
curl -X POST http://localhost:8000/api/v1/models \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "qwen-14b-instruct",
    "display_name": "Qwen 14B Instruct",
    "provider": "local",
    "model_identifier": "qwen-14b-instruct",
    "description": "Local chat model via vLLM",
    "context_window": 8192,
    "enabled": true
  }'
```

## Enable/Disable

- `enabled: true` — model available for assistants and completion
- `enabled: false` — blocked from new usage, existing assistants become non-functional
- Delete on model used by assistant → **disables** instead of deleting
