# Corrected RC2 Documentation — Correction Register

**Date:** 2026-07-23  
**Branch:** aither-v2  
**Purpose:** Register of false, misleading, or contradictory claims identified in RC2 documentation and their corrections.

---

## Correction Table

| Finding ID | Previous claim | Correct status | Source document | Required correction |
|------------|---------------|----------------|-----------------|-------------------|
| RC2R-CORR-001 | 20 requests partially confirm 1000-request stability ("Hermes 20x at 0.47s avg, 100% success") | 1000-request test NOT COMPLETED | `reports/rc2/production-readiness.md`, `evidence/rc2/stability/results.txt` | Remove "partial confirmation" language. 20 requests are not a valid sample for production stability. |
| RC2R-CORR-002 | 24h stability acceptable or implied | 24-hour long run NOT EXECUTED | `reports/rc2/production-readiness.md` | Remove any implied completion of long-duration stability testing. |
| RC2R-CORR-003 | GO for Production v1.0 | NO-GO; PROD-READY-01 OPEN | `reports/rc2/production-readiness.md` | Remove "GO" / "Production v1.0 Released" statements. Replace with FAILED status and NOT APPROVED designation. |
| RC2R-CORR-004 | SQLite database lock is transient and acceptable | Defect observed; remediation exists locally but is not yet accepted by external audit | `evidence/rc2/validation-log.txt` | The "database is locked" error is a confirmed defect, not acceptable. SQLite fix exists in working tree but has not been committed or audited. |
| RC2R-CORR-005 | Security acceptable for v1.0 | TLS absent; browser security headers not committed or runtime-verified | `reports/rc2/production-readiness.md` | Security headers added to local nginx.conf but not deployed or tested. TLS remains absent. Security cannot be declared acceptable. |
| RC2R-CORR-006 | Monitoring/alerting sufficient | Monitoring incomplete; automated alerting absent | `reports/rc2/production-readiness.md` | No Prometheus/Grafana deployed. No Alertmanager configured. Basic health endpoints exist but no automated alerting. |

---

## Detailed Corrections

### RC2R-CORR-001: 20/1000 Request Confusion

**Location:** `reports/rc2/production-readiness.md`, `evidence/rc2/stability/results.txt`

**Original text:** "Stability: Hermes 20x at 0.47s avg, 100% success"

**Correction:** ✗ REMOVED. 20 requests are NOT a partial confirmation of 1000. The RC2 report incorrectly labelled Hermes 20x as evidence of production stability. This has been struck from all RC2R documents.

### RC2R-CORR-002: 24h Long Run

**Location:** `reports/rc2/production-readiness.md`

**Original text:** Implied completion of long-duration stability testing.

**Correction:** No 24-hour long run was ever executed. Any claim of long-duration stability is unsupported.

### RC2R-CORR-003: Production GO

**Location:** `reports/rc2/production-readiness.md`

**Original:** Contained a "GO" recommendation despite known limitations.

**Correction:** Removed all "GO" / "Production v1.0 Released" statements. Replaced with:

```
Stage RC2: FAILED
Production status: NOT APPROVED
Valid designation: Internal Pilot Release Candidate (not approved for public production access)
```

### RC2R-CORR-004: SQLite Database Lock

**Location:** `evidence/rc2/validation-log.txt`

**Original text:** "Root cause of 500: SQLite `database is locked` — transient concurrent write issue. WAL mode confirmed enabled. Retry would succeed."

**Correction:** The "database is locked" error is a confirmed defect, not an acceptable transient condition. WAL mode alone does not prevent write contention — `busy_timeout` and retry logic are required. A fix exists in the local working tree (timeout=10, busy_timeout=10000, retry_on_lock decorator) and has been deployed to runtime as image `rc2r-sqlite-fix`, but has not been committed, audited, or accepted by external review.

### RC2R-CORR-005: Security Assessment

**Location:** `reports/rc2/production-readiness.md`

**Original:** Security not explicitly audited; accepted as sufficient.

**Correction:** Security findings:

| Finding | Severity | Status |
|---------|----------|--------|
| No TLS on user-facing endpoint | CRITICAL | NOT RESOLVED (requires ingress/CA/proxy) |
| No security headers on Portal Frontend | MEDIUM | PENDING (added to local nginx.conf, not committed or deployed) |
| CORS configured as `http://localhost:3000` | MEDIUM | RESOLVED (configurable via env var) |
| No rate limiting on Gateway | HIGH | RESOLVED (committed at 30r/m, burst=5) |
| No HSTS | MEDIUM | NOT RESOLVED (requires HTTPS endpoint) |

### RC2R-CORR-006: Monitoring and Alerting

**Location:** `reports/rc2/production-readiness.md`

**Original:** "Monitoring: ⚠️ BASIC — Prometheus metrics built-in; no Grafana dashboards. Alerting: ❌ NONE"

**Correction:** Monitoring is limited to built-in Prometheus metrics endpoints. No Prometheus server, Grafana dashboards, or Alertmanager are deployed. Automated alerting is completely absent. This is insufficient for production operations and remains an open finding.

---

## Release Notes Correction

`docs/releases/v1.0.md` has been corrected from "Production v1.0" to "Internal Pilot Release Candidate". Detailed corrections:

- **Release classification:** Internal Pilot Release Candidate
- **Public production approval:** NOT GRANTED
- **Production v1.0:** NO-GO
- **PROD-READY-01:** OPEN
- **Scope:** Internal pilot only. No SLA, no uptime guarantee, no public access.
- **Incomplete criteria documented:** SQLite, security headers, TLS, monitoring, 1000-request test, 24h long run, infrastructure stability

---

## Conclusion

All identified RC2 contradictions are recorded in this correction register.
The original RC2 reports and evidence remain unchanged.

For governance and release decisions, the corrected statuses in this
register supersede the specific contradictory RC2 conclusions listed above.

Local RC2R reports and evidence remain pending controlled review.
They are not connector-verified and do not yet supersede RC2 evidence.

Only this committed correction register supersedes the specific false
or misleading RC2 conclusions identified by Finding IDs RC2R-CORR-001
through RC2R-CORR-006.
