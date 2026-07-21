# Stage 17 — Structured Logging

## Format

All services emit structured JSON logs to stdout with the following schema:

```json
{
  "timestamp": "2026-07-21T12:34:56.789000+00:00",
  "level": "INFO",
  "service": "aither-identity",
  "message": "Login: user='admin' (role=administrator)",
  "request_id": "abc123",
  "user_id": 1,
  "endpoint": "/v1/identity/auth",
  "duration_ms": 12.34,
  "status_code": 200
}
```

## Required Fields

| Field | Type | Always Present | Description |
|---|---|---|---|
| `timestamp` | string (ISO 8601) | ✅ | UTC timestamp |
| `level` | string | ✅ | DEBUG, INFO, WARNING, ERROR |
| `service` | string | ✅ | Service identifier |
| `message` | string | ✅ | Log message text |
| `request_id` | string | ✅ (when available) | Correlation ID |
| `user_id` | int | ✅ (when available) | Authenticated user ID |
| `endpoint` | string | ✅ (when available) | Request path |
| `duration_ms` | float | ✅ (when available) | Request duration |
| `status_code` | int | ✅ (when available) | HTTP response code |

## Service Identifiers

| Service | `service` Field |
|---|---|
| Identity Service | `aither-identity` |
| Portal Backend (BFF) | `aither-portal-bff` |
| AI Platform | `aither-ai-platform` |
| Gateway (nginx) | `nginx-gateway-32b` |
| vLLM | `vllm` |

## Sensitive Data Protection

The following are **never** logged:

| Data Type | Protected | Method |
|---|---|---|
| API Keys | ✅ | Never included in log messages |
| Bearer Tokens | ✅ | Never included in log messages |
| Passwords | ✅ | Only username logged on failure |
| System Prompts | ✅ | Never included in log messages |
| Full User Messages | ✅ (default) | Logged only in explicit DEBUG mode |
| Stack Traces | ✅ | Caught and wrapped as HTTPException |

## Log Levels

- **ERROR** — Service cannot process request (Gateway unreachable, DB failure)
- **WARNING** — Failed authentication, degraded dependency
- **INFO** — Successful operations (login, key creation, model registration)
- **DEBUG** — Detailed debugging (off by default, controlled by `*_LOG_LEVEL` env var)
