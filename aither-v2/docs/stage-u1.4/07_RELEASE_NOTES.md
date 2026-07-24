# Aither AI Platform — Beta-1 Release Notes

## Version
**U1.4 Beta-1** | July 25, 2026

## About This Release
This is the first beta release of the Aither AI Platform, providing OpenAI-compatible API access to Qwen language models running on local GPU infrastructure.

## Supported Capabilities

### Models
| Model | Type | Context | Best For |
|---|---|---|---|
| `qwen-14b-instruct` | Instruction-tuned | 4,096 tokens | Conversational AI, Q&A, task completion |
| `qwen-32b-gptq` | Base completion | 8,192 tokens | Code generation, long-form text, creative writing |

### API Endpoints
- `GET /v1/models` — List available models
- `POST /v1/chat/completions` — Chat completion (both models)

### Authentication
- API key-based (format: `aither_<prefix>_<secret>`)
- Pass via `Authorization: Bearer <key>` header

### Access Points
- `https://fb1.spb.ru` — Primary (Internet)
- `https://fb1.spb.ru:10443` — Secondary (Internet)
- `http://10.129.13.78:30902` — Direct (internal network)

## Known Limitations

### Functional
1. **32B model is NOT chat-native** — responses use text_completion format, not chat.completion
2. **No streaming support** — all responses are returned in full (not token-by-token)
3. **No conversation history** — each request is independent; maintain your own history
4. **14B response time ~10 seconds** — due to tensor parallelism on shared GPU

### Operational
5. **No high availability** — single replica per service
6. **No automated backup** — data may be lost on pod restart
7. **vLLM restart takes 5-10 minutes** — plan maintenance accordingly
8. **Rate limit: 300 requests/minute** per client

### Security
9. **No audit logging** — request history is not persistent
10. **API keys cannot be recovered** — lost keys require new key creation

## Unsupported Scenarios
- Real-time streaming applications
- Production workloads requiring 99.9% uptime
- PII/sensitive data processing (no data handling policy yet)
- Fine-tuning or custom model deployment
- Multi-turn conversations without client-side history management

## Changes Since RC1
- VPN entrypoint fixed (eliminated periodic reconnection)
- Gateway rate limit increased (30→300 requests/minute)
- API error semantics improved (429 returned correctly instead of 502)
- Deployment automated with fail-closed health checks
- Operational runbooks created (startup, shutdown, backup, incident)

## Getting Started
See `docs/stage-u1.3/07_INTERNAL_USER_PACKAGE.md` for quick start guide.

## Reporting Issues
See `docs/stage-u1.4/05_FEEDBACK_PROCESS.md` for bug reporting process.

## Support
- Platform team: [contact information]
- Emergency (P1): direct message to platform lead
- Documentation: `docs/stage-u1.3/` and `docs/stage-u1.4/`
