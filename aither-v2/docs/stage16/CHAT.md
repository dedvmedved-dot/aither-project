# Chat — Stage 16

## Architecture

```
User types message
  → Portal Frontend POST /api/v1/conversations/{id}/messages
  → Portal Backend proxies to AI Platform
  → AI Platform:
      1. Saves user message to SQLite
      2. Builds message array (system prompt + history + new message)
      3. Looks up model from assistant config
      4. Sends to Gateway (nginx-gateway-32b)
      5. Gateway proxies to vLLM
      6. Receives response
      7. Saves assistant response to SQLite
      8. Returns response to browser
```

## Conversations

- Each conversation has an owner (user_id)
- Conversations can be linked to an assistant
- Title is auto-generated or user-supplied
- Messages are ordered by `created_at`

## Storage

- All messages stored in SQLite `messages` table
- Foreign key: `conversation_id` with `ON DELETE CASCADE`
- User can delete own conversations
- No access to other users' conversations (ownership check)

## Gateway Integration

- Primary: `POST /v1/chat/completions` (OpenAI-compatible)
- Fallback: `POST /v1/completions` (if Gateway returns 422)
- Timeout: 300s (configurable)
- Errors: 502 (Gateway unavailable), 504 (timeout)
- No internal stack traces in error responses

## Streaming

Beta v0.9: Non-streaming completion. Architecture prepared for SSE streaming.
The `/v1/chat/completions` endpoint accepts `stream: false` only for reliable operation.

## Error Scenarios

| Scenario | Response |
|---|---|
| Gateway unreachable | 502, detail message |
| Gateway timeout | 504, detail message |
| Model disabled/invalid | 503, clear message |
| Empty response | Returned as-is from Gateway |
| Gateway returns error | 502 with HTTP status relayed |
