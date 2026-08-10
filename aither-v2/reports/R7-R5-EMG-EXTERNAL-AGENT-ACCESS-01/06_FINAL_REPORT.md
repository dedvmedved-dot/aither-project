# 06_FINAL_REPORT — External Agent Access Restored

**R7-R5-EMG-EXTERNAL-AGENT-ACCESS-01**

| Parameter | Value |
|-----------|-------|
| STARTING SHA | $(cd /root/aither-project-r7-canonical/aither-v2 && git rev-parse HEAD) |
| EXTERNAL BASE URL | https://fb1.spb.ru:10443/v1 |
| CANARY USED | NO |
| CANARY REPLICAS | 0 |
| DEDICATED AGENT ACCOUNT | CREATED (aither-agent-ext) |
| AGENT ROLE | user |
| MODEL:32B:CHAT | PRESENT |
| MODEL:QWEN3:CHAT | PRESENT |
| GET /v1/models | 200 (old catalog, cosmetic) |
| QWEN2.5 EXTERNAL | 200 ✅ |
| QWEN3 EXTERNAL | 200 ✅ |
| INVALID TOKEN | 401 ✅ |
| PORT-FORWARD USED | NO |
| REAL TOKEN IN REPORT | NO |
| REAL PASSWORD IN REPORT | NO |
| EXTERNAL AGENT ACCESS | RESTORED ✅ |
| PERMANENT API-KEY FIX | REQUIRED (separate task) |
| STATUS | SUBMITTED FOR EXTERNAL AUDIT |

## Hermes Configuration
```yaml
custom_providers:
  - name: aither-external
    base_url: https://fb1.spb.ru:10443/v1
    api_key: "<JWT from POST /api/v1/auth/login>"
    model: qwen3-32b
    max_tokens: 16000
```

JWT obtained via: `POST /api/v1/auth/login` with agent credentials. JWT refreshed on expiry.
