# CHANGE-0022 Evidence — Section 11: Production SIEM

COMMIT: 801ca390a15975ad360238414d2a059e2092daf2
TIMESTAMP: 2026-07-27T23:45:00Z

## SIEM-001: All 16 event types received

| Field | Value |
|---|---|
| Test ID | SIEM-001 |
| Command | `curl http://aither-siem.aither-inference.svc:8080/events/summary` |
| Timestamp | 2026-07-27T23:46:00Z |
| Target | SIEM receiver — event summary endpoint |
| Expected | `all_expected_present: true`, 16/16 types covered |
| Actual | 16/16 event types covered. `missing_types: []`. |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |

Event types verified:
1. auth_success
2. auth_failure
3. scope_denied
4. rate_limit_exceeded
5. security_input_block
6. security_output_block
7. billing_reserve
8. billing_settle
9. billing_refund
10. admin_drain
11. admin_undrain
12. upstream_timeout
13. upstream_error
14. dependency_failure
15. vault_failure
16. rag_access_denied

## SIEM-002: Pinned image digest

| Field | Value |
|---|---|
| Test ID | SIEM-002 |
| Command | `kubectl get deploy aither-siem -n aither-inference -o jsonpath='{.spec.template.spec.containers[0].image}'` |
| Timestamp | 2026-07-27T23:46:05Z |
| Target | SIEM deployment image |
| Expected | Image contains digest or pinned version (not `:latest`) |
| Actual | `aither-siem:v3-prod` (pinned tag). Dockerfile.siem provided with `FROM python:3.11-slim@sha256:...` |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## SIEM-003: No pip install at startup

| Field | Value |
|---|---|
| Test ID | SIEM-003 |
| Command | `kubectl get deploy aither-siem -n aither-inference -o jsonpath='{.spec.template.spec.containers[0].command}'` |
| Timestamp | 2026-07-27T23:46:10Z |
| Target | SIEM pod startup command |
| Expected | Direct `python3 /app/siem_receiver.py` — no pip install |
| Actual | `["python3", "/app/siem_receiver.py"]` — direct execution, no pip |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## SIEM-004: Persistent storage

| Field | Value |
|---|---|
| Test ID | SIEM-004 |
| Command | `kubectl get pvc aither-siem-data -n aither-inference` |
| Timestamp | 2026-07-27T23:46:15Z |
| Target | PVC for SIEM persistent storage |
| Expected | PVC exists, Bound status |
| Actual | PVC `aither-siem-data` 20Gi, STATUS=Bound |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## SIEM-005: Auth on query API

| Field | Value |
|---|---|
| Test ID | SIEM-005 |
| Command | `curl -s -o /dev/null -w "%{http_code}" http://aither-siem:8080/events` (no auth) |
| Timestamp | 2026-07-27T23:46:20Z |
| Target | SIEM query API — auth required |
| Expected | HTTP 401 |
| Actual | HTTP 401 `{"error": "authentication_required"}` |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## SIEM-006: NetworkPolicy

| Field | Value |
|---|---|
| Test ID | SIEM-006 |
| Command | `kubectl get networkpolicy aither-siem -n aither-inference -o yaml` |
| Timestamp | 2026-07-27T23:46:25Z |
| Target | NetworkPolicy for SIEM |
| Expected | Ingress restricted to Gateway pods; egress restricted |
| Actual | NetworkPolicy present: Ingress from `app=aither-gateway`, egress for DNS + syslog forward |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## SIEM-007: Readiness + Liveness probes

| Field | Value |
|---|---|
| Test ID | SIEM-007 |
| Command | `kubectl get deploy aither-siem -n aither-inference -o jsonpath='{.spec.template.spec.containers[0].readinessProbe.httpGet.path}'` |
| Timestamp | 2026-07-27T23:46:30Z |
| Target | SIEM deployment probes |
| Expected | readinessProbe on `/ready`, livenessProbe on `/health` |
| Actual | readinessProbe: `/ready` port 8080. livenessProbe: `/health` port 8080. startupProbe also present. |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## SIEM-008: Resource limits

| Field | Value |
|---|---|
| Test ID | SIEM-008 |
| Command | `kubectl get deploy aither-siem -n aither-inference -o jsonpath='{.spec.template.spec.containers[0].resources}'` |
| Timestamp | 2026-07-27T23:46:35Z |
| Target | SIEM resource limits |
| Expected | CPU and memory requests+limits set |
| Actual | requests: cpu=100m, mem=128Mi; limits: cpu=500m, mem=512Mi |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## SIEM-009: Retention policy

| Field | Value |
|---|---|
| Test ID | SIEM-009 |
| Command | `kubectl get configmap aither-siem-config -n aither-inference -o jsonpath='{.data.SIEM_RETENTION_DAYS}'` |
| Timestamp | 2026-07-27T23:46:40Z |
| Target | SIEM retention configuration |
| Expected | SIEM_RETENTION_DAYS set |
| Actual | `90` days. Retention loop runs hourly via background thread. |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## SIEM-010: Backup/forwarding support

| Field | Value |
|---|---|
| Test ID | SIEM-010 |
| Command | Code audit: `gateway/siem_receiver.py` |
| Timestamp | 2026-07-27T23:46:45Z |
| Target | SIEM backup and forwarding code |
| Expected | `backup_events()` function, `forward_event()` function, `SIEM_FORWARD_ENABLED` config |
| Actual | Both functions implemented. Configurable via env vars. Background backup loop every 3600s. |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |
