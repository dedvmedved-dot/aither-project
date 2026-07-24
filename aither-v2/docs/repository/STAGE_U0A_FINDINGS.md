# Stage U0.A Findings — Repository Inventory & Documentation Index

> Registry of findings from the Stage U0.A inventory and documentation index.

---

## Finding Register

### U0A-FIND-01 — Repository Size
**Severity**: INFO
**Category**: Inventory
**Description**: The repository has 855 tracked files across ~100 directories and 2 branches (aither-v2, main). 563 files are in aither-v2/ (active workspace), 292 at root level (historical/reference).
**Evidence**: git ls-files count, directory tree scan

### U0A-FIND-02 — 41 Empty .gitkeep Files
**Severity**: LOW
**Category**: Housekeeping
**Description**: 41 .gitkeep files are all zero-byte empty files with identical SHA-256 hash `e3b0c44...`. These are standard placeholder files but excessive in number.
**Evidence**: SHA-256 hash analysis

### U0A-FIND-03 — aither-send Duplicate Cluster
**Severity**: MEDIUM
**Category**: Duplicates
**Description**: `aither-send/` and `aither-send (2)/` are exact copies of `aither-article/`. 12 redundant files (6 files × 2 copies) with identical content.
**Evidence**: SHA-256 hash match, manual inspection
**Recommendation**: Remove `aither-send/` and `aither-send (2)/`

### U0A-FIND-04 — Legacy 03-vllm-14b-deploy Directory
**Severity**: MEDIUM
**Category**: Stale content
**Description**: `aither-v2/03-vllm-14b-deploy/` contains 40 legacy files (docs + manifests) for vLLM 14B deployment. Superseded by current manifests.
**Evidence**: Directory inventory
**Recommendation**: Archive or remove

### U0A-FIND-05 — Superseded Root-Level Infrastructure
**Severity**: MEDIUM
**Category**: Stale content
**Description**: Root-level `gateway/` (12 files), `portal/` (35 files), and `manifests/` (22 files) are superseded by `aither-v2/services/` and `aither-v2/manifests/`. Approximately 69 files in stale components.
**Evidence**: Cross-directory comparison
**Recommendation**: Archive as historical reference; prevent new additions

### U0A-FIND-06 — 7 Placeholder Directories
**Severity**: LOW
**Category**: Housekeeping
**Description**: `04-tensor-parallelism/` through `07-oauth/` each contain only a `.gitkeep` file. `release/mvp-rc1/` has 4 empty `.gitkeep` files.
**Evidence**: Directory listing
**Recommendation**: Populate with content or clean up

### U0A-FIND-07 — Root-Level Documentation Split
**Severity**: MEDIUM
**Category**: Organization
**Description**: 28 documentation files exist at root-level `docs/` while 364 exist in `aither-v2/docs/`. Content is split between two locations with no cross-reference.
**Evidence**: git ls-files, inventory
**Recommendation**: Consolidate documentation into aither-v2/docs/ or clearly mark root docs as historical

### U0A-FIND-08 — main Branch Historical Content
**Severity**: INFO
**Category**: Branch management
**Description**: `main` branch has 73 commits with training manual content, K8s recovery reports, and historical feature work not present on `aither-v2`.
**Evidence**: git log analysis, branch comparison

### U0A-FIND-09 — Uncommitted Code Changes
**Severity**: INFO
**Category**: Working tree
**Description**: Two service files are modified but not committed: `services/ai-platform/app/main.py` (22 insertions, gateway API key) and `services/portal-frontend/nginx.conf` (9 insertions, security headers). These are pre-existing RC2R changes.
**Evidence**: git diff --stat
**Recommendation**: Document and commit as separate RC2R package (Package B/C pattern from Stage 10B)

### U0A-FIND-10 — Pre-existing Finding Corrections Verified
**Severity**: INFO
**Category**: Compliance
**Description**: Three governance findings (GOV-U1-01, GOV-U1-02, ROADMAP-U0A-01) have been corrected in the working tree. The `|| Stage 10G` double-pipe is fixed, the SHA placeholder is replaced, and the roadmap statuses are updated.
**Evidence**: git diff for each file

---

## Summary

| Severity | Count | Key Items |
|----------|-------|-----------|
| 🔴 CRITICAL | 0 | — |
| 🟡 MEDIUM | 4 | U0A-FIND-03 (duplicates), U0A-FIND-04 (legacy), U0A-FIND-05 (superseded), U0A-FIND-07 (split docs) |
| 🟢 LOW | 3 | U0A-FIND-02 (.gitkeep), U0A-FIND-06 (placeholders), others |
| ℹ️ INFO | 3 | U0A-FIND-01 (size), U0A-FIND-08 (branches), U0A-FIND-09 (code changes), U0A-FIND-10 (corrections) |

**Status**: Stage U0.A deliverables complete. All findings documented — no destructive actions taken.
