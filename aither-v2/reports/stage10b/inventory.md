# Stage 10B — Immutable File Inventory

## RC2R Local Changes — Complete File Manifest

### Date: 2026-07-23
### All dates: 2026-07-23
### Git status: untracked or modified (not committed)

---

## File Inventory

### Documentation

| Path | Size (bytes) | Type | Empty? | Sensitive? |
|------|-------------|------|--------|-----------|
| `aither-v2/docs/rc2r-corrections.md` | 3052 | TEXT | NO | NO |

### Reports

| Path | Size (bytes) | Type | Empty? | Sensitive? |
|------|-------------|------|--------|-----------|
| `aither-v2/reports/rc2r/environment-baseline.md` | 6161 | TEXT | NO | NO |
| `aither-v2/reports/rc2r/kubernetes-stability.md` | 5534 | TEXT | NO | NO |
| `aither-v2/reports/rc2r/monitoring-alerting.md` | 5063 | TEXT | NO | NO |
| `aither-v2/reports/rc2r/pass-fail-matrix.md` | 2757 | TEXT | NO | NO |
| `aither-v2/reports/rc2r/production-readiness.md` | 8117 | TEXT | NO | NO |
| `aither-v2/reports/rc2r/security-hardening.md` | 4190 | TEXT | NO | NO |
| `aither-v2/reports/rc2r/sqlite-concurrency.md` | 7075 | TEXT | NO | NO |

### Scripts

| Path | Size (bytes) | Type | Empty? | Sensitive? |
|------|-------------|------|--------|-----------|
| `aither-v2/scripts/rc2r/k8s-stability-test.sh` | 3886 | TEXT | NO | NO |
| `aither-v2/scripts/rc2r/sequential-1000-test.py` | 4080 | TEXT | NO | NO |
| `aither-v2/scripts/rc2r/sequential-1000-test.sh` | 3805 | TEXT | NO | NO |
| `aither-v2/scripts/rc2r/sqlite-concurrency-test.py` | 8992 | TEXT | NO | NO |

### Evidence

| Path | Size (bytes) | Type | Empty? | Sensitive? |
|------|-------------|------|--------|-----------|
| `aither-v2/evidence/rc2r/backup-restore/backup-output.txt` | 192 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/backup-restore/backup-run.txt` | 51 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/backup-restore/restore-test.txt` | 65 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/environment/deployments.txt` | 2225 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/environment/describe-n8-tail.txt` | 7656 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/environment/describe-nodes-head.txt` | 20678 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/environment/disk-usage.txt` | 821 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/environment/ingress.txt` | 19 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/environment/kubectl-version.txt` | 75 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/environment/n7-nvidia-smi.txt` | 2149 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/environment/n8-system.txt` | 2372 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/environment/nodes-short.txt` | 204 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/environment/nodes.txt` | 0 | TEXT | YES | NO |
| `aither-v2/evidence/rc2r/environment/nvidia-smi.txt` | 53 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/environment/pods.txt` | 9127 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/environment/pv.txt` | 528 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/environment/pvc.txt` | 456 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/environment/ram-usage.txt` | 207 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/environment/services.txt` | 2807 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/environment/statefulsets.txt` | 63 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/environment/top-nodes.txt` | 240 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/environment/top-pods.txt` | 4950 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/kubernetes/apiserver-logs.txt` | 14844 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/kubernetes/k8s-api-100.log` | 4894 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/kubernetes/n8-kubectl-pods.txt` | 2029 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/load/baseline-benchmark.txt` | 0 | TEXT | YES | NO |
| `aither-v2/evidence/rc2r/network/apiserver-livez.txt` | 319 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/network/apiserver-readyz.txt` | 319 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/network/conntrack-analysis.txt` | 99 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/network/ping-n7.txt` | 504 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/network/ping-n8.txt` | 504 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/network/ssh-tcp-100-n8.log` | 4792 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/network/tcp-22-n7.txt` | 56 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/network/tcp-22-n8.txt` | 236 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/network/tcp-6443-100.log` | 4795 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/network/tcp-6443-retry.txt` | 180 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/network/tcp-6443.txt` | 0 | TEXT | YES | NO |
| `aither-v2/evidence/rc2r/sqlite/api-key.txt` | 25 | TEXT | NO | POTENTIALLY |
| `aither-v2/evidence/rc2r/sqlite/auth-token.txt` | 65 | TEXT | NO | POTENTIALLY |
| `aither-v2/evidence/rc2r/sqlite/concurrency-test-result.txt` | 76 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/sqlite/concurrency-test-run.txt` | 56 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/sqlite/concurrency-test-v2.txt` | 75 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/sqlite/concurrency-test-v3.txt` | 46 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/sqlite/concurrency-test-v4.txt` | 395 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/sqlite/concurrency-test-v5.txt` | 0 | TEXT | YES | NO |
| `aither-v2/evidence/rc2r/sqlite/concurrency-test-v6.txt` | 46 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/sqlite/concurrency-test-v7.txt` | 0 | TEXT | YES | NO |
| `aither-v2/evidence/rc2r/sqlite/concurrency-test-v8.txt` | 0 | TEXT | YES | NO |
| `aither-v2/evidence/rc2r/sqlite/db-baseline.txt` | 283 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/sqlite/db-tables.txt` | 65 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/sqlite/deploy-image.txt` | 59 | TEXT | NO | NO |
| `aither-v2/evidence/rc2r/sqlite/pod-code-check.txt` | 1505 | TEXT | NO | NO |


---

## Summary Statistics

| Category | Files | Total Size | Empty Files | Potentially Sensitive |
|----------|-------|-----------|-------------|----------------------|
| Documentation | 1 | 3052 | 0 | 0 |
| Reports | 7 | 38897 | 0 | 0 |
| Scripts | 4 | 20763 | 0 | 0 |
| Evidence | 52 | 91205 | 6 | 2 |

| **Total** | **64** | **153917** | | |


---

## Empty Files

| Path | Size |
|------|------|
| `aither-v2/evidence/rc2r/sqlite/concurrency-test-v5.txt` | 0 |
| `aither-v2/evidence/rc2r/sqlite/concurrency-test-v7.txt` | 0 |
| `aither-v2/evidence/rc2r/sqlite/concurrency-test-v8.txt` | 0 |
| `aither-v2/evidence/rc2r/environment/nodes.txt` | 0 |
| `aither-v2/evidence/rc2r/network/tcp-6443.txt` | 0 |
| `aither-v2/evidence/rc2r/load/baseline-benchmark.txt` | 0 |

## Empty Evidence Directories

| Path |
|------|
| `aither-v2/evidence/rc2r/alerts/` |
| `aither-v2/evidence/rc2r/long-run/` |
| `aither-v2/evidence/rc2r/metrics/` |
| `aither-v2/evidence/rc2r/screenshots/` |

---

## Potentially Sensitive Files (by filename)

These files may contain authentication tokens, API keys or credentials.
Full secret scan required before commit eligibility can be determined.

| Path | Reason |
|------|--------|
| `aither-v2/evidence/rc2r/sqlite/auth-token.txt` | "auth-token" in name |
| `aither-v2/evidence/rc2r/sqlite/api-key.txt` | "api-key" in name |

---

*Inventory generated by SHA-256 verification across all RC2R local files.*
