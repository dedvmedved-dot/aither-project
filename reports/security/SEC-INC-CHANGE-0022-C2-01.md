# SEC-INC-CHANGE-0022-C2-01 — Postgres Credential Exposure

**Incident ID:** SEC-INC-CHANGE-0022-C2-01
**Severity:** HIGH
**Date:** 2026-07-27
**Detected by:** External audit (ChatGPT)
**Affected commits:** 92e83e3, 24176f7

---

## Exposure

Hardcoded PostgreSQL DSN with credentials found in integration tests:

| File | Line | Status |
|---|---|---|
| `gateway/tests/integration/test_idempotency.py` | 26 | ✅ Fixed |
| `gateway/tests/integration/test_rate_limit_integration.py` | 33 | ✅ Fixed |
| `gateway/tests/integration/test_billing_pg.py` | 10 | ✅ Fixed |
| `scripts/check_db.py` | 5 | ✅ Fixed |
| `scripts/create_idempotency_tables.py` | 5 | ✅ Fixed |
| `manifests/gateway.py` | 13 | ✅ Fixed |
| `gateway/reaper.py` | 11 | ✅ Fixed |
| `gateway/gateway.py` | 24 | ✅ Fixed |

Affected pattern: `os.environ.get("PG_URL", "postgresql://postgres:<PASSWORD>@postgres.aiops.svc:5432/aither")`

## Containment Actions

1. ✅ **Credential rotated** — PostgreSQL password changed for `postgres` user
2. ✅ **Kubernetes Secret updated** — `aither-gateway-postgres` in `aither-inference` namespace
3. ✅ **Gateway restarted** — controlled rollout, 2/2 pods healthy with new credentials
4. ✅ **Old credential invalidated** — connection attempt with old password → `FATAL: password authentication failed`
5. ✅ **Working tree scanned** — zero remaining hardcoded `postgresql://` DSNs
6. ✅ **Git history identified** — commits `92e83e3` and `24176f7` introduced credentials
7. ✅ **All files fixed** — replaced `os.environ.get()` with `os.environ["PG_URL"]` (fail-fast)

## Verification

```
OLD: psql postgresql://postgres:***@postgres.aiops.svc:5432/aither → FATAL: password authentication failed
NEW: Gateway /ready → 200 OK, postgres=ok
```

## Git History

| Commit | Files |
|---|---|
| `92e83e3` | test_idempotency.py, test_rate_limit_integration.py |
| `24176f7` | test_admin_drain.py, test_idempotency.py, test_rate_limit_integration.py |

Credentials were introduced by subagent-created test files with hardcoded fallback DSNs.

## Credential Exposure

| Field | Value |
|---|---|
| Credential value exposed | NO (sanitized in report, masked in all output) |
| Old credential invalidated | YES |
| New Secret fingerprint | `aither-gateway-postgres` (rotated) |
| Gateway reconnect | OK (2/2 pods, /ready 200) |
| BFF reconnect | N/A (BFF uses Redis only) |
| History scan | 2 commits identified |
| Working tree scan | CLEAN (0 matches) |

## Remediation Policy

All tests must use `os.environ["PG_URL"]` — fail immediately if not set. No `os.environ.get()` with hardcoded fallback values allowed. Pre-commit secret scanning recommended via `gitleaks` or `detect-secrets`.
