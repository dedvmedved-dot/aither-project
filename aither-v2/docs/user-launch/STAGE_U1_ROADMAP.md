# Stage U1 — Internal Pilot Readiness: Roadmap

## Track

```
Track A — User Launch
Priority: HIGHEST
```

## Stage Sequence

```
Stage U1 — Internal Pilot Readiness
  │
  ├── U1.0 — Governance и фиксация архитектуры доступа  ← CURRENT
  ├── U1.1 — DNS, сеть и TLS
  ├── U1.2 — Ingress и маршрутизация
  ├── U1.3 — Web Chat и управление API Key
  ├── U1.4 — OpenAI-compatible API для агентов
  ├── U1.5 — Руководство пользователя
  ├── U1.6 — End-to-End Acceptance
  └── U1.7 — Подключение первых пользователей
        │
        ▼
Stage U2 — Limited Beta
```

## Stage Descriptions

### U1.0 — Governance и фиксация архитектуры доступа (CURRENT)

- Define user access architecture
- Inventory current runtime and Git state
- Create endpoint matrix
- Define security baseline
- Document ADRs
- Create evidence reports

### U1.1 — DNS, сеть и TLS

- Configure DNS: `fb1.spb.ru` → `130.17.1.90`
- Acquire TLS certificate for `fb1.spb.ru` (Let's Encrypt)
- Internal TLS decision for `10.129.13.78`
- Firewall rules for external IP
- Network verification

### U1.2 — Ingress и маршрутизация

- Deploy Ingress controller (nginx-ingress or equivalent)
- Configure Ingress rules for Portal, Chat, and API
- Rate limiting at ingress layer
- Health endpoint exposure
- TLS termination configuration

### U1.3 — Web Chat и управление API Key

- Verify Web Chat functionality through Ingress
- API Key management UI and API accessible from external URL
- Registration flow (if required)
- Documentation page accessible
- Single routing path for `/v1/chat/completions`

### U1.4 — OpenAI-compatible API для агентов

- `/api/v1/chat/completions` route exposed and verified
- API Key authentication for agent access
- Models endpoint working
- Rate limiting applied
- Agent documentation

### U1.5 — Руководство пользователя

- User guide for Web Portal
- API reference for agents
- FAQ / troubleshooting guide
- Contact / support channel

### U1.6 — End-to-End Acceptance

- Full user journey test:
  1. Access portal via external URL
  2. Login
  3. Create API key
  4. Use Web Chat
  5. Access via OpenAI-compatible API
  6. Validate rate limiting
  7. Validate TLS
  8. Error scenarios

### U1.7 — Подключение первых пользователей

- Invite pilot users
- User onboarding
- Monitor usage
- Collect feedback

## Dependencies

- U1.3, U1.4, and U1.5 may be executed in parallel **only after** external acceptance of U1.2.
- U1.6 depends on U1.3, U1.4, and U1.5 being complete.
- U1.7 depends on U1.6 acceptance.

## Status Legend

| Status | Meaning |
|--------|---------|
| NOT STARTED | Work not yet begun |
| IN PROGRESS | Actively being worked on |
| AWAITING EXTERNAL AUDIT | Submitted for ChatGPT review |
| PASSED | Accepted by ChatGPT |
| PASSED WITH FINDINGS | Accepted with open findings |
| BLOCKED | Cannot proceed due to dependency or blocker |

## Current Statuses

| Stage | Status |
|-------|--------|
| U1.0 | AWAITING EXTERNAL AUDIT |
| U1.1 | NOT STARTED |
| U1.2 | NOT STARTED |
| U1.3 | NOT STARTED |
| U1.4 | NOT STARTED |
| U1.5 | NOT STARTED |
| U1.6 | NOT STARTED |
| U1.7 | BLOCKED BY STAGE U1 |
| U2 | BLOCKED BY STAGE U1 |
