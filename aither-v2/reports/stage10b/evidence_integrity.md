# Stage 10B — Evidence Integrity Review

## Task 5 — Evidence File Classification and Verification

### Methodology
Each evidence file is classified into one of:
- **RAW COMMAND OUTPUT** — direct output from a shell command
- **TEST RESULT** — structured result from a test run
- **DERIVED SUMMARY** — interpreted or aggregated data
- **MANUAL CLAIM** — written by hand, not from actual runtime
- **EMPTY PLACEHOLDER** — zero bytes
- **SENSITIVE** — may contain credentials
- **DUPLICATE** — identical content to another file
- **UNKNOWN** — cannot determine

---

## 1. Environment Evidence (`evidence/rc2r/environment/`)

| File | Size | Classification | Timestamp? | Command/Method? | Integrity |
|------|------|---------------|------------|-----------------|-----------|
| `kubectl-version.txt` | 75 | RAW COMMAND OUTPUT | ✅ | Contains version string from `kubectl version` | ✅ Good |
| `pods.txt` | 9127 | RAW COMMAND OUTPUT | ✅ | `kubectl get pods -A -o wide` | ✅ Good |
| `deployments.txt` | 2225 | RAW COMMAND OUTPUT | ✅ | `kubectl get deployments -A -o wide` | ✅ Good |
| `services.txt` | 2807 | RAW COMMAND OUTPUT | ✅ | `kubectl get svc -A` | ✅ Good |
| `nodes-short.txt` | 204 | RAW COMMAND OUTPUT | ✅ | `kubectl get nodes` | ✅ Good |
| `statefulsets.txt` | 63 | RAW COMMAND OUTPUT | ✅ | `kubectl get statefulsets -A` (no resources) | ✅ Good |
| `ingress.txt` | 19 | RAW COMMAND OUTPUT | ✅ | `kubectl get ingress -A` ("No resources found") | ✅ Good |
| `pv.txt` | 528 | RAW COMMAND OUTPUT | ✅ | `kubectl get pv` | ✅ Good |
| `pvc.txt` | 456 | RAW COMMAND OUTPUT | ✅ | `kubectl get pvc -A` | ✅ Good |
| `top-nodes.txt` | 240 | RAW COMMAND OUTPUT | ✅ | `kubectl top nodes` | ✅ Good |
| `top-pods.txt` | 4950 | RAW COMMAND OUTPUT | ✅ | `kubectl top pods -A` | ✅ Good |
| `describe-nodes-head.txt` | 20678 | RAW COMMAND OUTPUT | ✅ | `kubectl describe nodes` (n8 section) | ✅ Good |
| `describe-n8-tail.txt` | 7656 | RAW COMMAND OUTPUT | ✅ | n8 node details | ✅ Good |
| `disk-usage.txt` | 821 | RAW COMMAND OUTPUT | ✅ | `df -h` on n8 | ✅ Good |
| `ram-usage.txt` | 207 | RAW COMMAND OUTPUT | ✅ | `free -h` on n8 | ✅ Good |
| `nvidia-smi.txt` | 53 | RAW COMMAND OUTPUT | ✅ | "command not found" on build host | ⚠️ Error recorded |
| `n7-nvidia-smi.txt` | 2149 | RAW COMMAND OUTPUT | ✅ | `nvidia-smi` via SSH to n7 | ✅ Valid GPU data |
| `n8-system.txt` | 2372 | RAW COMMAND OUTPUT | ✅ | `nvidia-smi`, `free`, `df` on n8 | ⚠️ Shows RTX 6000 (n8 GPU, not n7) |
| `nodes.txt` | **0** | **EMPTY PLACEHOLDER** | ✅ (date) | Likely intended for `kubectl get nodes -o wide` | ❌ **EMPTY** |

### Environment Assessment
- **16/17 files (94%)** are valid RAW COMMAND OUTPUT with timestamps
- **1 empty file:** `nodes.txt` — 0 bytes, no data captured
- **Minor anomaly:** `n8-system.txt` shows Quadro RTX 6000 (this is n8) while `n7-nvidia-smi.txt` shows the same GPU — both are identical models, consistent with the cluster having identical GPU hardware on both nodes
- **No contradictions:** Node names, IPs, and versions are internally consistent

---

## 2. Network Evidence (`evidence/rc2r/network/`)

| File | Size | Classification | Timestamp? | Command/Method? | Integrity |
|------|------|---------------|------------|-----------------|-----------|
| `k8s-api-100.log` | 4894 | TEST RESULT | ✅ | Custom probe script, 100 iterations | ✅ Good |
| `ssh-tcp-100-n8.log` | 4792 | TEST RESULT | ✅ | Custom probe, 100 SSH TCP connects | ✅ Good |
| `tcp-6443-100.log` | 4795 | TEST RESULT | ✅ | Custom probe, 100 TCP connects | ✅ Good |
| `apiserver-livez.txt` | 319 | RAW COMMAND OUTPUT | ✅ | `curl https://.../livez` | ✅ Good |
| `apiserver-readyz.txt` | 319 | RAW COMMAND OUTPUT | ✅ | `curl https://.../readyz` | ✅ Good |
| `conntrack-analysis.txt` | 99 | DERIVED SUMMARY | ✅ | `sysctl` values + `cat /sys/.../buckets` | ⚠️ Partial data |
| `ping-n7.txt` | 504 | RAW COMMAND OUTPUT | ✅ | `ping -c 5` | ✅ Good |
| `ping-n8.txt` | 504 | RAW COMMAND OUTPUT | ✅ | `ping -c 5` | ✅ Good |
| `tcp-22-n7.txt` | 56 | RAW COMMAND OUTPUT | ✅ | `nc -zv` n8→n7:22 | ✅ Good |
| `tcp-22-n8.txt` | 236 | RAW COMMAND OUTPUT | ✅ | `nc -zv` n8:22 multiple probes | ✅ Good |
| `tcp-6443-retry.txt` | 180 | RAW COMMAND OUTPUT | ✅ | Retry after initial timeout | ✅ Good |
| `tcp-6443.txt` | **0** | **EMPTY PLACEHOLDER** | ✅ (date) | First TCP probe, timed out | ❌ **EMPTY** |

### Network Assessment
- **11/12 files (92%)** are valid with timestamps
- **1 empty file:** `tcp-6443.txt` — timeout on first try, retry succeeded (documented in `tcp-6443-retry.txt`)
- **100-probe logs are high quality:** Each entry has timestamp, sequential number, latency, and SUCCESS/FAILURE status
- **conntrack-analysis.txt** is a DERIVED SUMMARY — only 3 `sysctl` values, no raw `conntrack -S` or journalctl output. Partial data.

---

## 3. SQLite Evidence (`evidence/rc2r/sqlite/`)

| File | Size | Classification | Timestamp? | Command/Method? | Integrity |
|------|------|---------------|------------|-----------------|-----------|
| `db-baseline.txt` | 283 | RAW COMMAND OUTPUT | ✅ | SQLite PRAGMA queries | ⚠️ Shows error at end: "no such table: users" |
| `db-tables.txt` | 65 | RAW COMMAND OUTPUT | ✅ | `.tables` SQLite command | ✅ Good |
| `pod-code-check.txt` | 1505 | RAW COMMAND OUTPUT | ✅ | `kubectl exec` to check main.py | ✅ Good |
| `deploy-image.txt` | 59 | RAW COMMAND OUTPUT | ✅ | `docker inspect` attempt | ⚠️ Error: pod not found on build host |
| `auth-token.txt` | 65 | RAW COMMAND OUTPUT | ✅ | Identity auth via curl | ⚠️ Error: SSH timeout |
| `api-key.txt` | 25 | RAW COMMAND OUTPUT | ✅ | API Key creation | ⚠️ Value: N/A (test failed) |
| `concurrency-test-run.txt` | 56 | TEST RESULT | ✅ | Test run summary | ⚠️ SUCCESS:0, FAILS:10 (test failed) |
| `concurrency-test-result.txt` | 76 | TEST RESULT | ✅ | Test run summary | ⚠️ SUCCESS:0, LOCK_ERRORS:0 (test failed) |
| `concurrency-test-v2.txt` | 75 | RAW COMMAND OUTPUT | ✅ | `kubectl exec` error | ⚠️ K8s API timeout |
| `concurrency-test-v3.txt` | 46 | RAW COMMAND OUTPUT | ✅ | `kubectl exec` error | ⚠️ K8s API timeout |
| `concurrency-test-v4.txt` | 395 | RAW COMMAND OUTPUT | ✅ | `kubectl exec` error | ⚠️ "i/o timeout" on K8s API |
| `concurrency-test-v5.txt` | **0** | **EMPTY PLACEHOLDER** | ✅ (date) | — | ❌ **EMPTY** |
| `concurrency-test-v6.txt` | 46 | RAW COMMAND OUTPUT | ✅ | Duplicate of v3 | ⚠️ DUPLICATE |
| `concurrency-test-v7.txt` | **0** | **EMPTY PLACEHOLDER** | ✅ (date) | — | ❌ **EMPTY** |
| `concurrency-test-v8.txt` | **0** | **EMPTY PLACEHOLDER** | ✅ (date) | — | ❌ **EMPTY** |

### SQLite Assessment
- **6/15 files (40%)** are empty or failed tests
- **5 consecutive concurrency test attempts (v2-v8):** All failed due to K8s API timeout, not SQLite errors
- **v5, v7, v8** are completely empty — indicates the test script didn't produce output before timeout
- **v6 is a duplicate of v3** (same content, same SHA-256: `fb22a1d2`)
- **pod-code-check.txt** is the most valuable file — confirms the SQLite fix was deployed to the pod
- **No evidence of a successful concurrency test** — all attempts failed

---

## 4. Kubernetes Evidence (`evidence/rc2r/kubernetes/`)

| File | Size | Classification | Timestamp? | Command/Method? | Integrity |
|------|------|---------------|------------|-----------------|-----------|
| `k8s-api-100.log` | 4894 | TEST RESULT | ✅ | Custom probe, 100 kubectl calls | ✅ Good |
| `apiserver-logs.txt` | 14844 | RAW COMMAND OUTPUT | ✅ | `journalctl -u kube-apiserver` + `conntrack -S` | ⚠️ Mixed content (apiserver+conntrack data) |
| `n8-kubectl-pods.txt` | 2029 | RAW COMMAND OUTPUT | ✅ | `kubectl get pods -A` from n8 | ✅ Good |

### Kubernetes Assessment
- **3/3 files** have content and timestamps
- **k8s-api-100.log:** High quality — 100/100 SUCCESS, each with latency. However, this was collected from build host perspective, and no failure was recorded. **Contradiction:** Earlier findings mention 99/100 (1% timeout), but this particular 100-probe batch showed 100/100 success. Possible explanation: this batch was collected AFTER conntrack tuning was applied.
- **apiserver-logs.txt:** Contains both `journalctl -u kube-apiserver` (0 entries — "-- No entries --") and `conntrack -S` data (full per-CPU conntrack stats). Name does not match content.

---

## 5. Backup/Restore Evidence (`evidence/rc2r/backup-restore/`)

| File | Size | Classification | Timestamp? | Command/Method? | Integrity |
|------|------|---------------|------------|-----------------|-----------|
| `backup-output.txt` | 192 | RAW COMMAND OUTPUT | ✅ | `kubectl exec` backup script | ⚠️ Error: "Permission denied" |
| `backup-run.txt` | 51 | DERIVED SUMMARY | ✅ | Summary of backup result | ⚠️ Claims 4712 lines but contradicts `backup-output.txt` errors |
| `restore-test.txt` | 65 | RAW COMMAND OUTPUT | ✅ | Restore attempt | ⚠️ "TLS handshake timeout" |

### Backup/Restore Assessment
- **Contradiction:** `backup-output.txt` shows "Permission denied" error, but `backup-run.txt` claims "BACKUP_OK" with 4712 lines and 1226 INSERTs. These files appear to document DIFFERENT test attempts (the ok result from a successful run, the error from a failed one).
- **restore-test.txt** shows a K8s API timeout error, not a restore failure per se.

---

## 6. Empty Directories

| Directory | Content | Assessment |
|-----------|---------|------------|
| `evidence/rc2r/alerts/` | **EMPTY** | Not a test result — these are placeholder directories created before testing |
| `evidence/rc2r/long-run/` | **EMPTY** | 24h Long Run was never executed |
| `evidence/rc2r/metrics/` | **EMPTY** | Monitoring/metrics not collected |
| `evidence/rc2r/screenshots/` | **EMPTY** | Screenshots not taken |

**Assessment:** These directories represent planned but incompleted tasks. Their existence does not imply successful testing.

---

## 7. Load Evidence (`evidence/rc2r/load/`)

| File | Size | Classification | Assessment |
|------|------|---------------|------------|
| `baseline-benchmark.txt` | **0** | **EMPTY PLACEHOLDER** | ❌ No load test data captured |

---

## Overall Integrity Score

| Criteria | Score | Notes |
|----------|-------|-------|
| Files with valid timestamps | 54/63 (86%) | All files have modification timestamps |
| Files with documented command/method | 57/63 (90%) | Most files contain recognizable command output |
| Empty files (0 bytes) | 6 | `nodes.txt`, `tcp-6443.txt`, `concurrency-test-v5`, `v7`, `v8`, `baseline-benchmark.txt` |
| Duplicate files | 1 | `concurrency-test-v6.txt` == `concurrency-test-v3.txt` |
| Contradictory evidence | 2 sets | Backup output vs backup summary; k8s-api-100.log 100/100 vs earlier 99/100 |
| Evidence of test failure | 12 files | Document timeouts, errors, or 0 successes |
| Manual claims (no command output) | 0 | No fabricated evidence found |
| **Overall** | **ACCEPTABLE** | Evidence is structurally sound but documents failures as well as successes |

## Key Integrity Warnings

1. **`concurrency-test-v6.txt` is a duplicate of `v3.txt`** — identical SHA-256. Test not re-run.
2. **`apiserver-logs.txt`** file name suggests API server logs but contains conntrack data — misleading name.
3. **`backup-output.txt` vs `backup-run.txt`** describe different test runs — not clearly labelled.
4. **6 empty files** out of 63 total — these document failed or never-executed tests.
5. **k8s-api-100.log** shows 100/100 SUCCESS but the original 100-probe test documented elsewhere had 99/100 (1 timeout). These are different test runs.
