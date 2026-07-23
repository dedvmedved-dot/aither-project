# Stage 10A — RC2R Local Change Manifest

## Preamble

This document inventories all local (uncommitted) changes present in the working tree after Stage 10A preflight. It exists solely as a reference for the external auditor (ChatGPT) to decide how to handle these files. No local changes are committed in this stage.

---

## Modified Files (not staged)

### 1. `aither-v2/services/ai-platform/app/main.py`

| Field | Value |
|-------|-------|
| **Type** | Modified |
| **Purpose** | SQLite concurrency fix — add busy timeout, retry logic |
| **Origin** | RC2R remediation work (July 23, 2026) |
| **Applied to runtime?** | ✅ YES — deployed as image `10.129.13.78:5000/aither-ai-platform:rc2r-sqlite-fix` |
| **Evidence exists?** | ✅ YES — `evidence/rc2r/sqlite/pod-code-check.txt` confirms grep match in running pod |
| **Potential value** | HIGH — resolves "database is locked" errors on concurrent writes |
| **Risk** | LOW — minimal change (timeout + retry), WAL mode already active |
| **Recommendation** | REVIEW FOR FUTURE TASK |

**Changes:**
- `sqlite3.connect(DB_PATH)` → `sqlite3.connect(DB_PATH, timeout=10)`
- Added `PRAGMA busy_timeout=10000`
- Added `PRAGMA synchronous=NORMAL`
- Added `retry_on_lock` decorator (max_retries=5, linear backoff)
- Decorator applied to 11 write-heavy endpoints

---

### 2. `aither-v2/services/portal-frontend/nginx.conf`

| Field | Value |
|-------|-------|
| **Type** | Modified |
| **Purpose** | Add security headers (CSP, X-Frame-Options, Referrer-Policy, Permissions-Policy, X-Content-Type-Options) |
| **Origin** | RC2R remediation work (July 23, 2026) |
| **Applied to runtime?** | ❌ NO — only local file change; portal-frontend ConfigMap not updated |
| **Evidence exists?** | ❌ NO — local only |
| **Potential value** | MEDIUM — improves browser security, but TLS is prerequisite for several headers |
| **Risk** | LOW — headers are additive, would not break existing functionality |
| **Recommendation** | REVIEW FOR FUTURE TASK |

**Changes:**
- 6 new `add_header` directives in server block
- CSP: `default-src 'self'` with relaxed script/style for SPA

---

### 3. `aither-v2/docs/releases/v1.0.md`

| Field | Value |
|-------|-------|
| **Type** | Modified |
| **Purpose** | Correct release status from "Production v1.0" to "Internal Pilot RC2R" |
| **Origin** | RC2R remediation work (July 23, 2026) |
| **Applied to runtime?** | N/A — documentation only |
| **Evidence exists?** | ✅ YES — diff visible in `git diff` |
| **Potential value** | HIGH — resolves contradiction #2 from docs_consistency.md |
| **Risk** | LOW — documentation change only |
| **Recommendation** | REVIEW FOR FUTURE TASK |

---

## Untracked Files

### 4. `aither-v2/docs/rc2r-corrections.md`

| Field | Value |
|-------|-------|
| **Type** | Untracked |
| **Purpose** | Lists corrections to RC2 reports (5 contradictions identified) |
| **Origin** | RC2R remediation work |
| **Lines** | 79 |
| **Potential value** | MEDIUM — documents what was wrong in RC2 reports |
| **Risk** | LOW |
| **Recommendation** | EVIDENCE ONLY |

---

### 5. `aither-v2/reports/rc2r/` (7 files)

| File | Purpose |
|------|---------|
| `environment-baseline.md` | Full cluster state snapshot (2 nodes, 11 pods, GPU, network) |
| `kubernetes-stability.md` | K8s API 99/100 success, SSH 100/100, conntrack analysis |
| `sqlite-concurrency.md` | SQLite fix documentation and concurrency test results |
| `security-hardening.md` | Security headers, rate limiting, CORS assessment |
| `monitoring-alerting.md` | Monitoring base report |
| `production-readiness.md` | Production readiness assessment |
| `pass-fail-matrix.md` | PASS/FAIL matrix for all acceptance criteria |

| Field | Value |
|-------|-------|
| **Type** | Untracked (7 new files) |
| **Purpose** | RC2R remediation reports |
| **Origin** | RC2R remediation work |
| **Applied to runtime?** | N/A — documentation only |
| **Potential value** | HIGH — contains the only PASS/FAIL matrix and full RC2R assessment |
| **Risk** | MEDIUM — contains conclusions that should be verified by external audit |
| **Recommendation** | REVIEW FOR FUTURE TASK |

---

### 6. `aither-v2/evidence/rc2r/` (52 files, 10 subdirectories)

| Subdirectory | File Count | Content |
|-------------|-----------|---------|
| `backup-restore/` | 3 | Backup output, run log, restore test |
| `environment/` | 16 | Nodes, pods, GPU, disk, services, PV, PVC, deployments, ingress |
| `kubernetes/` | 3 | API server logs, 100-probe results, pods list |
| `load/` | 1 | Baseline benchmark |
| `network/` | 11 | Conntrack analysis, ping, SSH probes, TCP 6443 probes |
| `sqlite/` | 11 | Auth token, API key, concurrency test results, db baseline, pod code check |
| `alerts/` | 0 (empty) | Reserved for alerting evidence |
| `long-run/` | 0 (empty) | Reserved for 24h long-run evidence |
| `metrics/` | 0 (empty) | Reserved for metrics evidence |
| `screenshots/` | 0 (empty) | Reserved for screenshot evidence |

| Field | Value |
|-------|-------|
| **Type** | Untracked (52 new files) |
| **Purpose** | RC2R evidence collection |
| **Origin** | RC2R remediation work (July 23, 2026) |
| **Applied to runtime?** | N/A — evidence capture only |
| **Potential value** | HIGH — contains the only concrete evidence for K8s probes, conntrack, SQLite tests |
| **Risk** | MEDIUM — some evidence files reference runtime state that may have changed |
| **Recommendation** | REVIEW FOR FUTURE TASK |

---

### 7. `aither-v2/scripts/rc2r/` (4 files)

| File | Purpose |
|------|---------|
| `k8s-stability-test.sh` | Shell script for K8s API probe test |
| `sequential-1000-test.py` | Python script for 1000 sequential requests |
| `sequential-1000-test.sh` | Shell variant of 1000-request test |
| `sqlite-concurrency-test.py` | Python script for SQLite concurrent write test |

| Field | Value |
|-------|-------|
| **Type** | Untracked (4 new files) |
| **Purpose** | RC2R automated test scripts |
| **Origin** | RC2R remediation work |
| **Applied to runtime?** | Some executed (k8s probed 100x, SQLite concurrency tests run 8 iterations) |
| **Potential value** | HIGH — reproducible test scripts for future verification |
| **Risk** | LOW — scripts reference internal cluster addresses |
| **Recommendation** | REVIEW FOR FUTURE TASK |

---

## Summary

| # | Path | Type | Runtime? | Evidence? | Recommended Action |
|---|------|------|----------|-----------|-------------------|
| 1 | `services/ai-platform/app/main.py` | Modified | ✅ Deployed | ✅ pod-code-check.txt | REVIEW FOR FUTURE TASK |
| 2 | `services/portal-frontend/nginx.conf` | Modified | ❌ Not deployed | ❌ Local only | REVIEW FOR FUTURE TASK |
| 3 | `docs/releases/v1.0.md` | Modified | N/A (doc) | ✅ git diff | REVIEW FOR FUTURE TASK |
| 4 | `docs/rc2r-corrections.md` | Untracked | N/A (doc) | ✅ | EVIDENCE ONLY |
| 5 | `reports/rc2r/` (7 files) | Untracked | N/A (doc) | ✅ | REVIEW FOR FUTURE TASK |
| 6 | `evidence/rc2r/` (52 files) | Untracked | N/A (evidence) | ✅ | REVIEW FOR FUTURE TASK |
| 7 | `scripts/rc2r/` (4 files) | Untracked | Partial | ✅ | REVIEW FOR FUTURE TASK |

**Total local changes:** 3 modified + 1 doc + 7 reports + 52 evidence + 4 scripts = **67 files**
