# Security Findings — Stage U1.0

## Found

| ID | Severity | Finding | Status |
|----|----------|---------|--------|
| SEC-01 | MEDIUM | Portal Frontend nginx proxies `/v1/chat/completions` directly to AI Platform, bypassing Portal Backend auth. This creates an unauthenticated path. | OPEN — assigned to U1.3 |
| SEC-02 | LOW | No NetworkPolicy restricting user-facing service ingress beyond vLLM. Portal Frontend, Portal Backend, AI Platform, and Identity Service accept traffic from any pod in the cluster. | OPEN — assigned to U1.2 |
| SEC-03 | INFO | Health endpoint `/health` is publicly accessible with no rate limiting at ingress layer. | ACCEPTED for Internal Pilot |
| SEC-04 | INFO | No HSTS, CSP, or security headers configured at Ingress layer (will be configured in U1.2). Portal Frontend nginx has security headers configured already. | ACCEPTED — deferred to U1.2 |

## Not Found

| Area | Result |
|------|--------|
| Secrets in Git | ✅ CLEAN (verified in Stage 10B) |
| API Keys in evidence | ✅ NONE (all redacted) |
| Exposed NodePort services | ✅ NONE (all ClusterIP) |
| Exposed LoadBalancer services | ✅ NONE |
| Exposed Ingress resources | ✅ NONE |
| External access to K8s API | ✅ NONE (no Ingress, no NodePort for 6443) |
| Credentials in nginx config | ✅ NONE |
| Hardcoded passwords in code | ⚠️ Admin credentials in test scripts (not committed) |
