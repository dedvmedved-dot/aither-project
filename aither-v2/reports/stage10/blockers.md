# Stage 10 — Infrastructure Blockers in Git

## Task 7 — Known Blockers from Repository Content

### Methodology
Only committed content at HEAD (`519970f`) is examined. No runtime inspection performed.

---

## 1. Conntrack / Connection Tracking

| Aspect | In Git? | Details |
|--------|---------|---------|
| Conntrack mentioned as root cause | ✅ | `iteration-12-summary.md`: "The API timeout issue is in the bastion (nginx/conntrack configuration), NOT in the Kubernetes API server or etcd." |
| conntrack-tools installed | ✅ | Listed in `ks-node01.cfg` and `ks-node02.cfg` Kickstart configs |
| conntrack fix/tuning | ❌ | No sysctl tuning, no `nf_conntrack_buckets` increase, no conntrack-specific remediation in any committed file |
| Formal conntrack analysis | ❌ | No dedicated conntrack analysis report committed |

**Finding:** Conntrack is identified as the root cause of API timeouts in earlier stage documentation, but **no fix or tuning has been committed** to the repository.

---

## 2. K8s API Timeouts

| Aspect | In Git? | Details |
|--------|---------|---------|
| API timeout documented | ✅ | Multiple files across stages 11-13, RC2 validation log |
| Stability probe results | ⚠️ | `evidence/rc2/stability/results.txt` exists but references only 20 Hermes requests (not K8s API probes) |
| 100-probe results | ❌ | No 100-probe K8s API test results in Git |
| 99/100 metric | ❌ | Not recorded in any committed file |
| Root cause documented | ✅ | `iteration-12-summary.md`, `iteration-13-summary.md` — bastion/conntrack identified |

**Finding:** K8s API timeouts are well-documented as a known infrastructure limitation across multiple iteration summaries. The root cause (bastion nginx/conntrack configuration) is identified but **never remediated**.

---

## 3. SSH Intermittency

| Aspect | In Git? | Details |
|--------|---------|---------|
| SSH timeout documented | ✅ | `stage18/RUNTIME-VALIDATION.md`: "SSH connection timeout on large data streams" |
| SSH timeout in RC2 evidence | ✅ | `evidence/rc2/validation-log.txt`: multiple "❌ SSH timeout" entries |
| SSH in deploy scripts | ✅ | `stage18a-*.sh` scripts use `ConnectTimeout=30` as workaround |
| SSH root cause | ❌ | No SSH-specific root cause analysis committed (appears linked to conntrack) |

---

## 4. Long-Running Test Limitations

| Aspect | In Git? | Details |
|--------|---------|---------|
| 24h Long Run mentioned | ❌ | Not mentioned in any committed file |
| Load test "Not completed" | ✅ | `load-test-results.md`: "Not completed. Kubernetes API was intermittently unavailable (i/o timeout)." |
| Endurance benchmark manifest | ✅ | `benchmark-endurance-60min.yaml` exists but test never ran |

**Finding:** Long-running tests are known to be **not feasible** due to infrastructure instability. The load test result explicitly states "Not completed." No 24h Long Run has ever been committed to evidence.

---

## 5. SQLite "database is locked"

| Aspect | In Git? | Details |
|--------|---------|---------|
| "database is locked" in RC2 evidence | ✅ | `evidence/rc2/validation-log.txt`: "CREATE ASSISTANT: 500 (database locked - transient)" |
| Root cause in RC2 evidence | ✅ | Same file: "Root cause of 500: SQLite `database is locked` — transient concurrent write issue. WAL mode confirmed enabled. Retry would succeed." |
| SQLite fix | ❌ | **NOT committed** — only exists locally (see Task 5) |

**Finding:** The `database is locked` issue is documented in RC2 evidence but **never resolved** in committed code.

---

## Summary of Infrastructure Blockers in Git

| Blocker | Documented in Git? | Fix in Git? |
|---------|-------------------|-------------|
| Conntrack hash collisions | ✅ (iteration-12) | ❌ |
| K8s API timeout (1%) | ✅ (multiple docs) | ❌ |
| SSH intermittent | ✅ (stage18 docs, RC2 log) | ❌ (workaround only) |
| Long-running test blocked | ✅ (load-test-results.md) | ❌ |
| SQLite "database is locked" | ✅ (RC2 evidence) | ❌ |
| No TLS | ✅ (v1.0.md) | ❌ |

All five infrastructure blockers are **documented** in the committed repository. None of them have a committed fix.
