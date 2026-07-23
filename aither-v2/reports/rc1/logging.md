# Structured Logging Report

**Stage:** RC1  
**Date:** 2026-07-23  
**File:** `reports/rc1/logging.md`

---

## Current Logging Implementation

All services use a custom `JSONFormatter` that outputs structured JSON log entries. Format is consistent across services.

### Standard Log Format

```json
{
  "timestamp": "2026-07-23T00:57:49.186987+00:00",
  "level": "INFO",
  "service": "aither-ai-platform",
  "message": "User created assistant id=5"
}
```

### Optional Enriched Fields

When available, additional fields are attached:

| Field | Description | Example |
|-------|-------------|---------|
| `request_id` | Correlates requests across services | `"req-abc123"` |
| `user_id` | Authenticated user | `"admin"` or `1` |
| `endpoint` | API path | `"/api/v1/conversations/{id}/messages"` |
| `duration_ms` | Request processing time | `"4520"` |
| `status_code` | HTTP response status | `200` |

## Per-Service Logging Analysis

### AI Platform
- ✅ JSON format with `JSONFormatter`
- ✅ Service label: `"aither-ai-platform"`
- ✅ Logs all Gateway errors with upstream response details
- ✅ Logs user actions (create assistant, create key, etc.)
- ❌ **Missing request_id per request** — no middleware attaches correlation ID
- ❌ **Metrics logged separately** — latency available via Prometheus but not in application logs

### Portal Backend
- ✅ JSON format with `JSONFormatter`
- ✅ Service label: `"aither-portal-bff"`
- ✅ Logs login attempts (success + failure)
- ❌ **Missing user_id on most log entries**
- ❌ **No per-request correlation ID**

### Identity
- ✅ JSON format
- ✅ Service label: `"aither-identity"`
- ✅ Basic request logging

### Gateway
- ❌ **nginx default format** — no structured JSON
- ❌ **No request logging** — access_log not configured in nginx.conf

## Gap Analysis

| Requirement | AI Platform | Portal Backend | Identity | Gateway |
|-------------|-------------|----------------|----------|---------|
| `timestamp` | ✅ | ✅ | ✅ | ⚠️ (nginx default) |
| `request_id` | ❌ | ❌ | ❌ | ❌ |
| `user_id` | ⚠️ (on events) | ❌ | ⚠️ | ❌ |
| `model` | ✅ | N/A | N/A | ⚠️ |
| `latency` | ✅ (Prometheus) | ✅ (Prometheus) | ❌ | ❌ |
| `status_code` | ⚠️ | ⚠️ | ❌ | ❌ |
| `endpoint` | ⚠️ (on events) | ⚠️ | ❌ | ❌ |

## Recommendations

### 1. Add request_id middleware (all FastAPI services)
```python
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    with contextlib.ExitStack() as stack:
        # Add to logging context
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

### 2. Enrich log records with request context
```python
log = logging.LoggerAdapter(log, {"request_id": request_id, "user_id": user_id})
```

### 3. Add structured logging to Gateway nginx
```nginx
log_format json_combined escape=json
    '{'
    '"timestamp":"$time_iso8601",'
    '"request_id":"$http_x_request_id",'
    '"method":"$request_method",'
    '"endpoint":"$uri",'
    '"status":$status,'
    '"latency":$request_time,'
    '"upstream":"$upstream_addr"'
    '}';
access_log /dev/stdout json_combined;
```

## Conclusion

✅ **JSON format established** across all Python services.  
⚠️ **Request correlation IDs missing** — manual tracing difficult across services.  
⚠️ **Gateway uses default nginx logging** — not structured.  
⚠️ **No user_id in Portal Backend logs.**

Recommendations are non-invasive and can be implemented incrementally.
