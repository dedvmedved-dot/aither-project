# User Feedback Process

## How to Report an Issue

### Method
Send a message to the designated feedback channel with the following information:

### Required Information
1. **API endpoint** used (e.g., `/v1/chat/completions`)
2. **Model** used (qwen-14b-instruct or qwen-32b-gptq)
3. **Request parameters** (model, max_tokens, temperature)
4. **Expected behavior** — what should have happened
5. **Actual behavior** — what happened instead (error code, response text)
6. **Timestamp** — when the request was made (UTC)
7. **API key prefix** — first part of your key (e.g., `aither_<prefix>_...`)

### Example Report
```
Endpoint: POST /v1/chat/completions
Model: qwen-14b-instruct
Parameters: max_tokens=100, temperature=0.7
Expected: meaningful response in English
Actual: HTTP 502 Bad Gateway
Timestamp: 2026-07-25 14:30 UTC
Key prefix: aither_30a67d9d
```

## Priority Levels

| Priority | Definition | Response SLA | Examples |
|---|---|---|---|
| P1 — Critical | System completely unavailable | 1 hour | All models return 5xx, VPN down |
| P2 — High | Major feature broken | 4 hours | One model fails, auth broken |
| P3 — Medium | Minor issue with workaround | 24 hours | Slow response, specific prompt fails |
| P4 — Low | Cosmetic, documentation | 1 week | Typo in response, missing metadata |

## Defect Lifecycle

```
REPORTED → TRIAGED → IN_PROGRESS → FIXED → VERIFIED → CLOSED
                    ↘ WONTFIX (with reason)
                    ↘ DUPLICATE (linked to original)
```

### States
- **REPORTED:** Issue submitted by user
- **TRIAGED:** Priority and severity assigned by platform team
- **IN_PROGRESS:** Developer actively working on fix
- **FIXED:** Fix deployed to system
- **VERIFIED:** Original reporter confirms issue resolved
- **CLOSED:** Issue archived
- **WONTFIX:** Issue acknowledged but will not be fixed (with explanation)
- **DUPLICATE:** Same issue already reported

## Fix Verification
1. Developer deploys fix
2. Developer tests fix
3. Original reporter is notified
4. Reporter confirms within 48 hours
5. Issue marked VERIFIED → CLOSED

## Feedback Channels
- Primary: designated chat/email channel
- Urgent (P1 only): direct message to platform lead

## Escalation
If issue not addressed within SLA:
1. +50% over SLA: remind platform team
2. +100% over SLA: escalate to platform lead
3. +200% over SLA: escalate to project owner
