# Stage 10 — Reports, Evidence, Scripts Inventory

## Task 6 — Repository Content Audit

### Legend
- ✅ **IN GIT** — committed to branch `aither-v2`
- ⚠️ **LOCAL ONLY** — exists in working tree, not committed
- ❌ **NOT PRESENT** — neither in Git nor locally

---

## 1. `reports/` Directory

### In Git (committed)

| Path | Stage |
|------|-------|
| `aither-v2/reports/ba02r/` (11 files) | BA-02R |
| `aither-v2/reports/beta/` (15 files) | Beta |
| `aither-v2/reports/rc1/` (8 files) | RC1 |
| `aither-v2/reports/rc2/` (2 files) | RC2 |

### Local only (uncommitted)

| Path | File Count | Description |
|------|-----------|-------------|
| `aither-v2/reports/rc2r/` | 7 files | RC2R reports (environment, kubernetes, sqlite, security, monitoring, production-readiness, pass-fail-matrix) |
| `aither-v2/reports/stage10/` | 4 files (growing) | Current Stage 10 reports |

### Not present

| Path | Status |
|------|--------|
| `aither-v2/reports/stage18/` | ❌ NOT PRESENT |
| `aither-v2/reports/stage19/` | ❌ NOT PRESENT |

---

## 2. `evidence/` Directory

### In Git (committed)

| Path | Description |
|------|-------------|
| `aither-v2/evidence/ba02r/e2e-results.txt` | BA-02R end-to-end results |
| `aither-v2/evidence/beta/01-openai-chat-completions.txt` | Beta OpenAI test |
| `aither-v2/evidence/rc2/stability/results.txt` | RC2 stability test |
| `aither-v2/evidence/rc2/validation-log.txt` | RC2 validation log |

### Local only (uncommitted)

| Subdirectory | File Count | Description |
|-------------|-----------|-------------|
| `aither-v2/evidence/rc2r/backup-restore/` | 3 | Backup output, run log, restore test |
| `aither-v2/evidence/rc2r/environment/` | 16 | Nodes, pods, GPU, disk, services, PV/PVC |
| `aither-v2/evidence/rc2r/kubernetes/` | 3 | API server logs, 100-probe results |
| `aither-v2/evidence/rc2r/load/` | 1 | Baseline benchmark |
| `aither-v2/evidence/rc2r/network/` | 11 | conntrack analysis, ping, SSH/TCP probes |
| `aither-v2/evidence/rc2r/sqlite/` | 11 | Auth token, API key, concurrency test iterations |
| **Total** | **45 files** | Full RC2R evidence collection |

---

## 3. `scripts/` Directory

### In Git (committed) — `aither-v2/scripts/`

| File | Purpose |
|------|---------|
| `backup.sh` | SQLite database backup |
| `bootstrap-admin.sh` | Admin user creation |
| `check-gateway-32b.sh` | Gateway health check |
| `restore.sh` | SQLite database restore |
| `scan-secrets.sh` | Secret scanning |
| `stage18a-build-images.sh` | Docker images build |
| `stage18a-deploy-services.sh` | Services deployment |
| `stage18a-push-images.sh` | Images push to registry |
| `stage18a-transfer-artifact.sh` | Artifact transfer |
| `stage18a-verify-registry.sh` | Registry verification |
| `test-check-gateway-dns-policy.sh` | Gateway DNS test |
| `test-gateway-32b-e2e.sh` | Gateway E2E test |
| `test-stage15-acceptance.sh` | Stage 15 acceptance |
| `test-stage16-acceptance.sh` | Stage 16 acceptance |
| `test-stage17-observability.sh` | Stage 17 observability |

### Local only (uncommitted) — `aither-v2/scripts/rc2r/`

| File | Purpose |
|------|---------|
| `k8s-stability-test.sh` | K8s API probe stability test |
| `sequential-1000-test.py` | 1000 sequential request test (Python) |
| `sequential-1000-test.sh` | 1000 sequential request test (Shell) |
| `sqlite-concurrency-test.py` | SQLite concurrent write test |

---

## Summary

| Category | In Git (committed) | Local Only (uncommitted) |
|----------|-------------------|------------------------|
| Reports | 36 files (ba02r, beta, rc1, rc2) | 11 files (rc2r: 7, stage10: 4 growing) |
| Evidence | 4 files (ba02r, beta, rc2) | 45 files (rc2r evidence collection) |
| Scripts | 16 files (production scripts) | 4 files (rc2r test scripts) |

### Missing from Git
All RC2R deliverables — reports, evidence, and test scripts — are **absent from the committed repository**. They exist only as local uncommitted changes.
