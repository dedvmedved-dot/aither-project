# U1.3-OPS-R1 — SMOKE VALIDATION

**Evidence:** logs/13-smoke.log  
**Timestamp:** 2026-07-26T01:34:49Z

## Results

| Check | Zone | Result |
|-------|------|--------|
| /health | Internet (https://fb1.spb.ru:443) | HTTP 200 ✅ |
| /health | Test Zone (http://10.129.13.78:30080) | HTTP 200 ✅ |
| / (portal index) | Internet | HTTP 200 ✅ |
| / (portal index) | Test Zone | HTTP 200 ✅ |

## Deployment Status (final)

| Deployment | Ready | Available |
|------------|:-----:|:---------:|
| aither-ai-platform | 1/1 | ✅ |
| aither-bff | 1/1 | ✅ |
| aither-identity | 1/1 | ✅ |
| aither-portal | 1/1 | ✅ |
| aither-portal-backend | 1/1 | ✅ |
| aither-portal-frontend | 1/1 | ✅ |
| aither-redis-rate-limit | 1/1 | ✅ |
| nginx-gateway-32b | 2/2 | ✅ |
| vllm-14b-instruct | 1/1 | ✅ |
| vllm-32b-gptq | 1/1 | ✅ |

**Smoke: PASS** ✅
