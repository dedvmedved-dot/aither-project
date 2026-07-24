# AI Assistants — Stage 16

## Schema

| Field | Type | Limits |
|---|---|---|
| `name` | TEXT (1–256) | Required |
| `description` | TEXT (0–2000) | Optional |
| `model_id` | INTEGER | Must reference enabled model |
| `system_prompt` | TEXT (0–32000 chars) | Not logged by default |
| `temperature` | REAL (0.0–2.0) | Default 0.7 |
| `max_tokens` | INTEGER (1–131072) | Default 2048 |
| `enabled` | BOOL | Default true |

## Ownership

- Each assistant belongs to one user (`owner_user_id`)
- User sees only their own assistants
- Admin can view all metadata (admin API)
- Deletion cascades to conversations?

## Model Selection

- Assistant must reference a valid, enabled model
- Changing model to a disabled model is blocked
- If model is disabled, assistant queries will fail with clear error

## System Prompt

- Maximum 32,000 characters
- Prepended to every conversation with this assistant
- Not included in application logs by default
- Shown as informational in UI before first message
