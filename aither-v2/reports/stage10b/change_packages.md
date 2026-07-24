# Stage 10B — Change Package Classification

## Task 7 — Independent Package Decomposition of RC2R Local Changes

---

## Package A — SQLite Remediation

| Field | Value |
|-------|-------|
| **Files** | `services/ai-platform/app/main.py` (modified), `scripts/rc2r/sqlite-concurrency-test.py`, SQLite evidence files |
| **Dependencies** | None on other packages |
| **Secrets** | None found |
| **Evidence quality** | ⚠️ Mixed: `pod-code-check.txt` confirms fix deployed, but concurrency test results show infrastructure failures (K8s API timeouts), not SQLite errors |
| **Required review** | Verify SQLite fix doesn't affect read-only paths; confirm busy_timeout interacts correctly with WAL mode |
| **Future commit allowed** | ✅ YES — independent package |
| **Runtime test required** | ✅ YES — concurrency test must be re-run in stable conditions |
| **Recommended order** | **1st** — lowest risk, highest value |

**Notes:**
- Fix is already deployed to runtime (image `rc2r-sqlite-fix`)
- Code change is minimal: +22 lines, additive only
- Evidence of deployment exists but evidence of successful concurrency test does NOT
- Re-running `sqlite-concurrency-test.py` via `kubectl run` Job is recommended before commit

---

## Package B — Portal Security Headers

| Field | Value |
|-------|-------|
| **Files** | `services/portal-frontend/nginx.conf` (modified) |
| **Dependencies** | None on other packages |
| **Secrets** | None (no tokens/keys in nginx.conf) |
| **Evidence quality** | N/A — not deployed; local file only |
| **Required review** | Verify CSP does not break SPA assets or API connectivity; functional test required |
| **Future commit allowed** | ✅ YES — independent package |
| **Runtime test required** | ✅ YES — must deploy and verify portal still loads correctly |
| **Recommended order** | **2nd** — after SQLite, before infrastructure changes |

**Notes:**
- Not deployed to runtime
- CSP policy may block inline scripts if not configured correctly for the SPA
- Security headers are additive and safe if CSP is properly scoped
- Functional testing (portal page load, API calls) is required before acceptance

---

## Package C — Release and Governance Corrections

| Field | Value |
|-------|-------|
| **Files** | `docs/releases/v1.0.md` (modified), `docs/rc2r-corrections.md` (untracked) |
| **Dependencies** | None |
| **Secrets** | None (documentation only) |
| **Evidence quality** | N/A — documentation |
| **Required review** | Verify all 5 RC2 contradictions are correctly identified; verify updated status reflects current project state |
| **Future commit allowed** | ✅ YES — independent package |
| **Runtime test required** | ❌ NO — documentation only |
| **Recommended order** | **3rd** — no runtime risk, can be committed anytime |

**Notes:**
- Corrects false claims from RC2 reports (20/1000, GO recommendation, etc.)
- Aligns release notes with governance status (PROD-READY-01: OPEN)
- Pure documentation — no code changes

---

## Package D — Infrastructure Evidence

| Field | Value |
|-------|-------|
| **Files** | `evidence/rc2r/environment/` (16 files), `evidence/rc2r/network/` (11 files), `evidence/rc2r/kubernetes/` (3 files), `evidence/rc2r/backup-restore/` (3 files), `evidence/rc2r/sqlite/` (15 files), `scripts/rc2r/k8s-stability-test.sh`, `reports/rc2r/environment-baseline.md`, `reports/rc2r/kubernetes-stability.md`, `reports/rc2r/sqlite-concurrency.md`, `reports/rc2r/security-hardening.md` |
| **Dependencies** | Package A (SQLite report references the fix) |
| **Secrets** | None (admin/admin in scripts is placeholder, not production) |
| **Evidence quality** | ✅ Generally good — most files are RAW COMMAND OUTPUT with timestamps. 6 empty files, 1 duplicate |
| **Required review** | Resolve contradictions (backup-run vs backup-output, 100/100 vs 99/100), remove empty/duplicate files |
| **Future commit allowed** | ✅ YES — but with cleanup |
| **Runtime test required** | ❌ NO — evidence is retrospective |
| **Recommended order** | **4th** — after SQLite and security, before incomplete tests |

**Notes:**
- Largest package (48 evidence files + reports + scripts)
- Evidence integrity review identified:
  - 6 empty files (failed/abandoned tests)
  - 1 duplicate file
  - 2 sets of contradictory evidence
  - 1 misleading filename (`apiserver-logs.txt` contains conntrack data)
- Package should be cleaned before commit (remove empties, deduplicate, rename)

---

## Package E — Incomplete Acceptance Tests

| Field | Value |
|-------|-------|
| **Files** | `evidence/rc2r/long-run/` (empty dir), `evidence/rc2r/alerts/` (empty dir), `evidence/rc2r/metrics/` (empty dir), `evidence/rc2r/screenshots/` (empty dir), `evidence/rc2r/load/baseline-benchmark.txt` (empty), `scripts/rc2r/sequential-1000-test.py`, `scripts/rc2r/sequential-1000-test.sh`, `reports/rc2r/monitoring-alerting.md`, `reports/rc2r/production-readiness.md`, `reports/rc2r/pass-fail-matrix.md` |
| **Dependencies** | Infrastructure stability (K8s API, SSH, conntrack) — ALL BLOCKED |
| **Secrets** | admin/admin in scripts (placeholder) |
| **Evidence quality** | ❌ Poor — 4 empty directories, 1 empty file, reports written without completed tests |
| **Required review** | Test infrastructure must be stabilized first |
| **Future commit allowed** | ⚠️ Reports only — evidence directories are empty (commit nothing or commit as "not tested") |
| **Runtime test required** | ✅ YES — all tests must be re-executed |
| **Recommended order** | **Last** — blocked by infrastructure stability |

**Notes:**
- The following tests were NOT completed:
  - 1000 sequential requests (attempted, failed: K8s API timeout)
  - 24-hour Long Run (never attempted)
  - Monitoring/Alerting setup (never deployed)
  - TLS (never implemented)
- Reports in `reports/rc2r/` reference these tests but they were never executed
- **These packages cannot be committed as "passed"** — at best they document what was NOT tested

---

## Dependency Graph

```
Package A (SQLite) ──────┐
                           ├──> Package D (Evidence) ──> Package E (Reports)
Package B (Security) ─────┘
                               
Package C (Docs) ──────── (independent, can merge anytime)

Package E (Tests) ──── BLOCKED by:
    ├── K8s API stability (conntrack fix on n8)
    ├── SSH reliability
    └── Available test infrastructure (kubectl run Job, not kubectl exec)
```

---

## Commit Strategy Recommendation

| Step | Package | Action |
|------|---------|--------|
| 1 | Package C | Commit documentation fixes (v1.0.md + rc2r-corrections.md) — zero risk |
| 2 | Package A | Re-run concurrency test via K8s Job, then commit code + test script + evidence |
| 3 | Package B | Deploy nginx config to test namespace, verify portal, then commit |
| 4 | Package D | Clean evidence (remove empties, deduplicate), then commit |
| 5 | Package E | Resolve infrastructure blockers, re-run tests, then commit reports or "NOT TESTED" declarations |

**No single commit should mix packages.** Each package must be independently reviewable by ChatGPT via GitHub Connector.
