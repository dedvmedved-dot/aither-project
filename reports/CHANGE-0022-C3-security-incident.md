# CHANGE-0022-C3 Security Incident Report

**Date:** 2026-07-27
**Commit:** 801ca390a15975ad360238414d2a059e2092daf2
**Severity:** HIGH (pre-existing, now remediated)

## Executive Summary

CHANGE-0022-C3 addresses a HIGH-severity security finding: the Gateway rate limiter had a **fail-open** design where Redis unavailability caused rate limits to be silently bypassed. This finding was uncovered during CHANGE-0022-C2 audit and remediated in C3 with a full fail-closed redesign.

## Finding 1: Rate Limiter Fail-Open (SEC-2026-001)

**Severity:** HIGH
**CWE:** CWE-754 (Improper Check for Unusual or Exceptional Conditions)

### Description
In `gateway/gateway.py` (lines 690-691), the rate limiting exception handler contained:
```python
except Exception as e:
    pass  # Redis down: let request through
```

This meant that ANY Redis failure (network partition, OOM, crash, misconfiguration) would silently disable rate limiting, allowing unlimited requests through the Gateway.

### Impact
- Unlimited RPM/TPM consumption during Redis outages
- Billing bypass (requests processed without rate limit checks)
- Denial-of-service amplification vector
- Compliance violation (rate limits mandated by service tiers)

### Remediation (CHANGE-0022-C3)
Changed to fail-closed:
```python
except Exception as e:
    # FAIL-CLOSED: Redis down → deny (CHANGE-0022-C3)
    self._json(503, {"error": "rate_limit_unavailable",
        "detail": "Rate limiting backend unavailable. Request denied.",
        "tier": tier})
    return
```

### Verification
- RL-003: Redis unavailable → deny (503), not pass-through
- GW-RL-FC-01: Static analysis confirms no `pass` in Redis exception handlers

## Finding 2: Rate Limiter Fallback Safe Limits (SEC-2026-002)

**Severity:** MEDIUM
**CWE:** CWE-453 (Insecure Default Variable Initialization)

### Description
In `gateway/rate_limit.py` (lines 141-147), the tier loading function had hardcoded fallback limits:
```python
if not limits:
    if tier not in _tier_cache and db_pool is None:
        limits = {"rpm": 60, "tpm": 10000, ...}  # "safe" fallback
    else:
        limits = {"rpm": 300, "tpm": 100_000, ...}  # generous fallback
```

An attacker could: (a) cause PG unavailability, (b) use an unknown tier name, and (c) get generous rate limits (300 RPM, 100k TPM).

### Remediation
Complete removal of all fallback limits. Unknown tier or PG unavailable → explicit deny:
```python
if db_pool is None:
    return False, "rate_limit_unavailable_pg", {"tier": tier}
if limits is None:
    return False, "rate_limit_unknown_tier", {"tier": tier}
```

### Verification
- RL-001: Unknown tier → deny
- RL-002: PG unavailable → deny
- RL-004: grep confirms zero fallback limits in code

## Finding 3: RAG Endpoints Without Auth (SEC-2026-003)

**Severity:** MEDIUM
**CWE:** CWE-306 (Missing Authentication for Critical Function)

### Description
In `gateway/app.py`, the RAG endpoints (status, query, wiki-ingest) had no authentication:
```python
@app.get("/v1/rag/status")
async def rag_status(request: Request):
    if _rag_available and settings.rag_enabled:
        ...
    return {"ready": False, ...}
```

Any client could query RAG, check status, or perform wiki ingestion without any credential.

### Remediation
Added full auth pipeline on all 5 RAG endpoints:
1. `check_auth()` — JWT/API key validation
2. `_has_rag_scope()` — RAG scope required in credentials
3. `_check_tier_rag()` — Tier must have RAG enabled
4. Org isolation — per-org ChromaDB collections
5. Security ingress/egress — content filtering

### Verification
- RAG-001 through RAG-010: All 10 tests pass

## Finding 4: SIEM No Auth on Query API (SEC-2026-004)

**Severity:** LOW
**CWE:** CWE-200 (Exposure of Sensitive Information)

### Description
The temporary SIEM receiver had no authentication on query endpoints. Anyone with network access could list all security events, including sensitive data like org IDs, error details, and audit trails.

### Remediation
Added `SIEM_QUERY_AUTH=true` with `SIEM_ADMIN_KEY` Bearer token validation on all query endpoints (`/events`, `/events/count`, `/events/type/*`, `/events/search`). Health endpoint remains public.

### Verification
- SIEM-005: Unauthenticated query → 401

## Finding 5: Vault TLS Disabled (SEC-2026-005)

**Severity:** HIGH
**CWE:** CWE-319 (Cleartext Transmission of Sensitive Information)

### Description
Vault deployment had `tls_disable = "true"` — all communication including API key validation, policy reads, and unseal key transmission was in cleartext over the internal network.

### Remediation
- TLS enabled with cert/key from Kubernetes Secret `vault-tls`
- API address changed to `https://`
- Cluster address changed to `https://`
- Probes updated to use `scheme: HTTPS`

### Verification
- VAULT-001: TLS cert and key configured in listener

## Timeline

| Date | Event |
|---|---|
| 2026-07-27 | C2 audit identifies fail-open rate limiting |
| 2026-07-27 | C3 development begins |
| 2026-07-27 23:45 | All fixes committed (801ca390) |
| 2026-07-27 23:50 | Evidence documented |

## Sign-off

- [x] Security incident documented
- [x] All findings remediated
- [x] Evidence collected
- [ ] Security review (pending)
- [ ] Penetration test (pending — after deployment)
