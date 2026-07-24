# Internal User Package — Aither AI Platform

## Quick Start

### 1. Get an API Key
Contact your administrator to receive an API key in format `aither_<prefix>_<secret>`.

### 2. List Available Models
```bash
curl -s https://fb1.spb.ru/v1/models \
  -H "Authorization: Bearer <your-api-key>"
```

### 3. Chat with 14B Model
```bash
curl -s -X POST https://fb1.spb.ru/v1/chat/completions \
  -H "Authorization: Bearer <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-14b-instruct",
    "messages": [{"role": "user", "content": "Hello, how are you?"}],
    "max_tokens": 100
  }'
```

### 4. Generate Text with 32B Model
```bash
curl -s -X POST https://fb1.spb.ru/v1/chat/completions \
  -H "Authorization: Bearer <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-32b-gptq",
    "messages": [{"role": "user", "content": "Write a short poem about AI"}],
    "max_tokens": 200
  }'
```

## Available Models

| Model | Type | Context | Best For |
|---|---|---|---|
| `qwen-14b-instruct` | Chat | 4096 tokens | Conversational AI, Q&A |
| `qwen-32b-gptq` | Text completion | 8192 tokens | Code generation, long-form text |

**Note:** The 32B model is a base completion model. Chat-style prompts are adapted automatically but may not follow instructions as precisely as the 14B model.

## API Reference
OpenAI-compatible endpoints:
- `GET /v1/models` — List available models
- `POST /v1/chat/completions` — Send chat completion request

Standard parameters: `model`, `messages`, `max_tokens`, `temperature`, `stream` (not yet supported).

## Access Points
| URL | Use |
|---|---|
| `https://fb1.spb.ru` | Primary (Internet) |
| `https://fb1.spb.ru:10443` | Secondary (Internet) |
| `http://10.129.13.78:30902` | Direct (internal network only) |

## Known Limitations
1. **No streaming** — responses are returned in full
2. **32B is not chat-native** — may produce unexpected formatting
3. **Rate limits** — 300 requests/minute per client
4. **No conversation history** — each request is independent
5. **Response times** — 14B: ~10s, 32B: ~0.5s

## FAQ

**Q: Why is the 14B model slower than 32B?**
A: The 14B model runs on a shared GPU with tensor parallelism. The 32B model runs on a single dedicated GPU with GPTQ optimization.

**Q: Can I use this from Python?**
A: Yes! Use the `openai` Python library with `base_url="https://fb1.spb.ru/v1"`.

**Q: Is my data stored?**
A: Messages are stored temporarily for the duration of request processing only. Conversations are not persisted across requests unless you maintain your own history.

## How to Report Bugs
Contact your system administrator with:
- The exact API call you made
- The response or error you received
- Timestamp of the request

## Support
For operational issues: contact the platform team.
For API questions: refer to this document or OpenAI API documentation.
