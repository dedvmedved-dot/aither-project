# Aither MVP — 32B Chat Adapter Notes

## Context

The 32B model (`qwen-32b-base`) is a base/completion model, NOT a chat model. It does not natively support chat format. In previous stages, 32B chat was blocked at BFF with HTTP 422.

## Stage 07.1 Decision

32B chat is now supported via an **adapter** over the completion endpoint:

```
POST /api/v1/chat model=32b
  -> BFF converts messages to completion prompt format
  -> Forwards to nginx-gateway-32b/v1/completions
  -> Returns completion response as chat response
```

## Prompt Template

```
<|user|>
Hello!
<|assistant|>
```

This is a simple but functional template for MVP. For production, use a proper chat template compatible with the base model's training format.

## Limitations

| Aspect | Status |
|---|---|
| Native 32B chat | NOT SUPPORTED (base model limitation) |
| Adapter quality | MVP-level — may produce suboptimal responses |
| Streaming | Inherits completion streaming (not native chat streaming) |
| Token counting | Uses completion token counting |
| System prompt | Not natively supported (injected as <|system|>) |

## Testing

```bash
# 32B chat via adapter
curl -H "Authorization: Bearer athr_xxx" -X POST \
  http://aither-bff.aither-inference.svc:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"model":"32b","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":50}'
```

## Future

If a chat-tuned 32B model becomes available:
- Remove adapter
- Point to native chat endpoint
- Update model type from "completion" to "chat"
- Update documentation

Until then, 32B chat = 32B completion via adapter. Never claim "native 32B chat" in documentation.
