# Aither Portal — Chat UI Notes

## Model Support

| Model | Type | Scope | Notes |
|---|---|---|---|
| 14B | Native chat | `model:14b:chat` | Direct BFF → vLLM 14B |
| 32B | Chat adapter over completion | `model:32b:chat-adapter` | BFF wraps 32B completion as chat interface |

## Important

- **32B is NOT native chat.** The Portal correctly labels it as "32B chat adapter over completion".
- Both models require session auth (admin login) or a valid Bearer token.
- Upstream errors (401 unauthorized, 502 bad gateway, 500 server error) are shown honestly in the chat UI.
- Chat requests go through Portal → BFF → upstream; Portal never contacts vLLM/Gateway directly.

## Message Format

The chat UI uses `POST /api/v1/chat` with standard messages format:

```json
{
  "model": "14b",
  "messages": [
    {"role": "user", "content": "Hello"}
  ]
}
```

## Known Limitations (MVP)

1. No conversation history persistence across page reloads
2. No streaming (blocking request-response)
3. No markdown rendering
4. No system prompt configuration
5. Upstream token is test-only — real upstream auth not configured
