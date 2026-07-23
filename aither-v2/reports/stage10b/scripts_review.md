# Stage 10B — Scripts Static Review

## Task 6 — RC2R Test Scripts Analysis (no execution)

---

## 1. `scripts/rc2r/k8s-stability-test.sh`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Run 100 sequential probes to K8s API (`kubectl get nodes`) and SSH port on n8 |
| **Language** | Bash |
| **Lines** | ~120 |
| **Input parameters** | None (hardcoded paths: `/root/aither-v2/aither-v2/evidence/rc2r/`) |
| **Hardcoded addresses** | `10.129.13.78` (n8 IP) for SSH test |
| **Hardcoded credentials** | None |
| **Timeout** | `timeout 10` per kubectl call |
| **Expected runtime** | ~17 minutes (100 probes × ~10s) |
| **Error handling** | Basic: captures exit code, records SUCCESS/FAILURE/TIMEOUT per probe |
| **Exit code preserved** | ✅ Yes, per probe level |
| **Resumable** | ❌ No — always starts from #1 |
| **Output format** | Structured log: `[timestamp] #N STATUS latency=Xms` |
| **Reproducibility** | ✅ High — self-contained, no external dependencies |
| **Risk of hanging** | LOW — each probe has 10s timeout |
| **Dependency on long-lived `kubectl exec`** | ⚠️ Sequential `kubectl` calls, each is a new connection — independent sessions |
| **Assessment** | ✅ Clean design. Each probe is a separate `kubectl` call with timeout. Does not depend on a single long-lived session. |

---

## 2. `scripts/rc2r/sqlite-concurrency-test.py`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Test 10 concurrent clients × 100 write operations = 1000 total operations against AI Platform API |
| **Language** | Python 3 |
| **Lines** | ~270 |
| **Input parameters** | CLI args: `--url`, `--clients`, `--operations`, `--delay` |
| **Hardcoded addresses** | None (configurable via `--url`) |
| **Hardcoded credentials** | None (uses API key, obtained via auth endpoint) |
| **Timeout** | `timeout=10` for HTTP requests |
| **Expected runtime** | ~2-5 minutes depending on concurrency |
| **Error handling** | Comprehensive: separates `database is locked` errors from HTTP errors, network errors, timeouts |
| **Exit code preserved** | ✅ Exit code reflects test result |
| **Resumable** | ❌ No — idempotent test |
| **Output format** | Human-readable summary + JSON-structured evidence file |
| **Reproducibility** | ✅ High — self-contained Python, no external tools beyond `urllib` |
| **Risk of hanging** | LOW — 10s HTTP timeout for each request |
| **Dependency on long-lived `kubectl exec`** | ❌ N/A — runs via HTTP to AI Platform, not kubectl exec |
| **Assessment** | ✅ Well-designed. Configurable, concurrent, proper error classification. The ideal pattern for RC2R tests — HTTP-level, not kubectl-exec level. |

---

## 3. `scripts/rc2r/sequential-1000-test.py`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Send 1000 sequential inference requests to Gateway, record latency and errors |
| **Language** | Python 3 |
| **Lines** | ~110 |
| **Input parameters** | None (hardcoded) |
| **Hardcoded addresses** | `http://aither-identity:8000` (internal K8s service DNS), `http://nginx-gateway-32b:8000` |
| **Hardcoded credentials** | `admin`/`admin` (test/default credentials — documented) |
| **Timeout** | 120s per HTTP request |
| **Expected runtime** | ~35 minutes (1000 requests × 2.1s) |
| **Error handling** | Basic: catches all exceptions, records SUCCESS/FAILED/TIMEOUTS |
| **Exit code preserved** | ✅ Summary written at end |
| **Resumable** | ❌ No |
| **Output format** | JSONL per-request log + summary with totals |
| **Reproducibility** | ⚠️ Requires running inside cluster (service DNS names) |
| **Risk of hanging** | ⚠️ MEDIUM — 120s timeout per request, 1000 sequential = up to 33h if every request hangs |
| **Dependency on long-lived `kubectl exec`** | ✅ NOT used — script must be deployed to pod or run via `kubectl run` as Job |
| **Assessment** | ⚠️ Has a risk: 120s timeout is generous. If the Gateway hangs (no response, no timeout), the script could take 33 hours. Should use `kubectl run --restart=Never` as a Job, not `kubectl exec`. |

---

## 4. `scripts/rc2r/sequential-1000-test.sh`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Same as Python variant — 1000 sequential inference requests |
| **Language** | Bash |
| **Lines** | ~110 |
| **Input parameters** | None (hardcoded) |
| **Hardcoded addresses** | `http://aither-identity:8000`, `http://nginx-gateway-32b:8000` |
| **Hardcoded credentials** | `admin`/`admin` (test/default credentials — documented) |
| **Timeout** | Implicit (curl default), ~1s sleep between requests |
| **Expected runtime** | ~35-40 minutes |
| **Error handling** | Basic: shell-level exit code checking |
| **Exit code preserved** | ✅ Summary written to file |
| **Resumable** | ❌ No |
| **Output format** | JSONL request log + summary |
| **Reproducibility** | ⚠️ Requires cluster-internal execution |
| **Risk of hanging** | ⚠️ MEDIUM — similar to Python variant |
| **Dependency on long-lived `kubectl exec`** | ⚠️ Was intended for `kubectl exec` — this is the one that failed with exit 127 (curl not in image) |
| **Assessment** | ❌ Incompatible with portal-backend image (no curl). Should be refactored as Python script or deployed as K8s Job. |

---

## Comparative Assessment

| Criterion | k8s-stability-test.sh | sqlite-concurrency-test.py | sequential-1000-test.py | sequential-1000-test.sh |
|-----------|----------------------|---------------------------|------------------------|------------------------|
| Language | Bash | Python | Python | Bash |
| Hardcoded secrets | ✅ None | ✅ None | ⚠️ admin/admin | ⚠️ admin/admin |
| Configurable | ❌ No | ✅ Yes (CLI args) | ❌ No | ❌ No |
| Timeout per unit | 10s | 10s | 120s | curl default |
| Risk of hanging | LOW | LOW | MEDIUM | MEDIUM |
| Resumable | ❌ | ❌ | ❌ | ❌ |
| Lives independent of kubectl exec | ✅ | ✅ | ✅ | ❌ (needs curl in pod) |
| Test lifecycle separation | ✅ Separate calls | ✅ HTTP calls | ✅ HTTP calls | ❌ kubectl exec |

## Recommendations

1. **`k8s-stability-test.sh`** — ✅ Ready for use. Perfectly designed with independent sessions.
2. **`sqlite-concurrency-test.py`** — ✅ Ready for use. Best-designed script in the set.
3. **`sequential-1000-test.py`** — ⚠️ Reduce timeout from 120s to 30s. Run as `kubectl run` Job, not `kubectl exec`.
4. **`sequential-1000-test.sh`** — ❌ Deprecate in favor of the Python variant. Bash adds no value and requires curl in the pod image.
