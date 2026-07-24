# Stage 10 — Local Changes Report

## Task 2 — Restore Clean Baseline

### Baseline Commit
`75931e6f68530d59fadd15061796bbc1a67c1f9a`

### Current HEAD
`519970f1a9e544487be0d57f95f85be1379a7915`  
(2 commits ahead of baseline: `65c8b33` docs(v1.0), `519970f` docs(rc2))

### Working Tree Status
**DIRTY** — 3 modified files + 4 untracked paths

---

## 1. Modified Files (not staged, not committed)

### a) `aither-v2/docs/releases/v1.0.md`
**Diff:** +21 / -7 lines  
**Changes:**
- Renamed from "Production v1.0" to "Internal Pilot Release v1.0.0-RC2R"
- Added status: "NOT APPROVED for public production access"
- Added: "Stage RC2R Audit: PENDING — awaiting external audit by ChatGPT"
- Changed overview from "production-ready release" to "Release Candidate for internal pilot"
- Updated Security section: annotated RC2R fixes (Security Headers ✅, Rate Limiting ✅), marked TLS as ❌, HSTS as ❌, CORS as ⚠️
- Added scope note: "Internal pilot only. No SLA, no uptime guarantee, no public access."

### b) `aither-v2/services/ai-platform/app/main.py`
**Diff:** +22 / -1 lines  
**Changes:**
- `sqlite3.connect(DB_PATH)` → `sqlite3.connect(DB_PATH, timeout=10)` — added 10s busy timeout
- Added `PRAGMA busy_timeout=10000` after `PRAGMA journal_mode=WAL`
- Added `PRAGMA synchronous=NORMAL` after `PRAGMA foreign_keys=ON`
- Added `retry_on_lock` decorator function (max_retries=5, linear backoff 0.5s-2.5s)
- Decorator applied to 11 write-heavy endpoints: `create_user`, `update_user`, `delete_user`, `create_conversation`, `add_message`, `create_api_key`, `revoke_api_key`, `create_assistant`, `update_assistant`, `delete_model`, `create_model`

### c) `aither-v2/services/portal-frontend/nginx.conf`
**Diff:** +9 lines  
**Changes:**
- Added security headers inside `server` block:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `X-XSS-Protection: 0`
  - `Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()`
  - `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' http://aither-portal-backend:8000`

---

## 2. Untracked Files

### a) `aither-v2/docs/rc2r-corrections.md`
**Type:** Documentation  
**Content:** Lists corrections made to RC2 documentation — removes 5 contradictions (20/1000 claims, Stability NOT TESTED listed as PASS, contradictory GO recommendation, etc.)

### b) `aither-v2/evidence/rc2r/` (directory, ~55 files)
**Subdirectories:**
| Subdir | File Count | Contains |
|--------|-----------|----------|
| `backup-restore/` | 3 | Backup output, run log, restore test |
| `environment/` | 16 | Nodes, pods, services, PV/PVC, GPU, disk, RAM, deployments, ingress |
| `kubernetes/` | 3 | API server logs, 100-probe results, pods list |
| `load/` | 1 | Baseline benchmark |
| `network/` | 11 | conntrack analysis, ping, SSH probes, TCP 6443 probes |
| `sqlite/` | 11 | Auth token, API key, concurrency test results, db baseline, pod code check |

### c) `aither-v2/reports/rc2r/` (directory, 8 files)
| File | Content |
|------|---------|
| `environment-baseline.md` | Full cluster state snapshot |
| `kubernetes-stability.md` | K8s API stability report |
| `sqlite-concurrency.md` | SQLite fix + test report |
| `security-hardening.md` | Security headers + rate limiting report |
| `monitoring-alerting.md` | Monitoring base report |
| `production-readiness.md` | Production readiness assessment |
| `pass-fail-matrix.md` | PASS/FAIL matrix for all criteria |

### d) `aither-v2/scripts/rc2r/` (directory, 4 files)
| File | Content |
|------|---------|
| `k8s-stability-test.sh` | Shell script for K8s API probe test |
| `sequential-1000-test.py` | Python script for 1000 sequential requests |
| `sequential-1000-test.sh` | Shell variant of 1000-request test |
| `sqlite-concurrency-test.py` | Python script for SQLite concurrency test |

---

## Summary

| Category | Count | Description |
|----------|-------|-------------|
| Modified (staged) | 0 | — |
| Modified (unstaged) | 3 | `v1.0.md`, `main.py`, `nginx.conf` |
| Deleted | 0 | — |
| Untracked directories | 4 | `evidence/rc2r/`, `reports/rc2r/`, `scripts/rc2r/`, `docs/rc2r-corrections.md` |
| Untracked files total | ~68 | Evidence (55), reports (8), scripts (4), corrections doc (1) |
