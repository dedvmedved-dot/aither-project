# U1.3-OPS — DEPLOYMENT VALIDATION

## Cluster State

| Deployment | Replicas | Available | Restarts |
|------------|----------|-----------|----------|
| aither-ai-platform | 1/1 | ✅ | 0 |
| aither-bff | 1/1 | ✅ | 0 |
| aither-identity | 1/1 | ✅ | 0 |
| aither-portal | 1/1 | ✅ | 0 |
| aither-portal-backend | 1/1 | ✅ | 0 |
| aither-portal-frontend | 1/1 | ✅ | 0 |
| aither-redis-rate-limit | 1/1 | ✅ | 0 |
| nginx-gateway-32b | 2/2 | ✅ | 0 |
| vllm-14b-instruct | 1/1 | ✅ | 0 |
| vllm-32b-gptq | 1/1 | ✅ | 0 |

## Probes

| Deployment | Readiness | Liveness |
|------------|-----------|----------|
| aither-ai-platform | GET /ready | GET /health |
| aither-bff | GET /health | GET /health |
| aither-identity | GET /ready | GET /health |
| aither-portal-backend | GET /ready | GET /health |
| aither-portal-frontend | GET / | GET / |
| aither-redis-rate-limit | redis-cli ping | redis-cli ping |
| nginx-gateway-32b | GET /health | GET /healthz |
| vllm-14b-instruct | GET /health | GET /health |
| vllm-32b-gptq | GET /health | GET /health |

## Restart Test

- **aither-bff rollout restart:** Completed in <60s ✅
- **aither-bff pod deletion:** New pod Ready in <10s ✅
- **aither-bff rollback:** Completed successfully ✅

## Log Validation

All deployments: 0 error lines in last 100 log lines ✅
