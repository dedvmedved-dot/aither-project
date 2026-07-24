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

## Stage U0.A-R1 Findings

### U0A-GOV-001 — Baseline STOP Gate Procedural Finding
**Severity**: LOW
**Category**: Procedure
**Description**: The Stage U0.A task required STOP on unexpected dirty working tree. Five pre-existing RC2R dirty paths (2 modified, 3 untracked) existed before Stage U0.A. These were documented, expected, and unchanged. No new dirty paths appeared during the stage. The STOP gate was acknowledged but not invoked because the paths were not "unexpected."
**Status**: CLOSED WITH FINDING — documented in BASELINE_PROVENANCE.md and BASELINE_INTEGRITY.md
**Evidence**: `docs/repository/BASELINE_PROVENANCE.md`, `docs/repository/BASELINE_INTEGRITY.md`

### U0A-CAT-001 — File Catalog Incompleteness
**Severity**: HIGH
**Category**: Inventory
**Description**: The previous FILE_CATALOG.md contained aggregated entries ("plus 33 others", "..."). This violated the requirement for 100% complete inventory.
**Status**: CORRECTED — new FILE_CATALOG.md generated with 887 individual file entries, no aggregation
**Evidence**: `docs/repository/FILE_CATALOG.md` (887 rows, 0 aggregations)

### U0A-VAL-001 — Validation and Reconciliation
**Severity**: HIGH
**Category**: Quality
**Description**: File count reconciliation across git ls-files (887), FILE_CATALOG.md (887), FILE_METADATA.csv (887 + header), and FILE_HASHES.txt (887) confirmed all sources match.
**Status**: CORRECTED — documented in FILE_RECONCILIATION.md and VALIDATION_REPORT.md
**Evidence**: `docs/repository/FILE_RECONCILIATION.md`, `docs/repository/VALIDATION_REPORT.md`

### U0A-GIT-001 — Baseline Integrity
**Severity**: MEDIUM
**Category**: Governance
**Description**: The baseline integrity was verified. All pre-existing dirty paths are documented RC2R changes. The committed state (HEAD 11b0d64) is reproducible from GitHub. No procedural violations beyond the documented GOV-001.
**Status**: CORRECTED — documented in BASELINE_INTEGRITY.md
**Evidence**: `docs/repository/BASELINE_INTEGRITY.md`

### U0A-GIT-002 — Metadata Commit SHA Error
**Severity**: LOW
**Category**: Documentation
**Description**: The Stage U0.A final report contained an erroneous full SHA `704bb2d253a3dfb5ac4e9e0a8c72e0e7de41c13b` for the metadata commit. The correct SHA is `704bb2dcc658b8aeab698e08819c53c28f26e0a2`. Both share the same 7-char prefix `704bb2d`. The commit exists and was pushed.
**Status**: CORRECTED — documented in METADATA_COMMIT_INVESTIGATION.md
**Evidence**: `reports/stage-u0/u0-a-r1/METADATA_COMMIT_INVESTIGATION.md`

### U0A-DEP-001 — Dependency Map Expansion
**Severity**: LOW
**Category**: Documentation
**Description**: The DEPENDENCY_MAP.md was expanded with service dependency tables, storage dependencies, network dependencies, and detailed protocol/port/auth mappings. Mermaid diagram retained for visual reference.
**Status**: CORRECTED
**Evidence**: `docs/repository/DEPENDENCY_MAP.md`

### U0A-CLN-001 — Cleanup Plan Risk Completeness
**Severity**: LOW
**Category**: Documentation
**Description**: The CLEANUP_PLAN.md contained "Risk: None" for P1.1. Replaced with "Risk: Low" including approval, rollback, and reference validation requirements.
**Status**: CORRECTED
**Evidence**: `docs/repository/CLEANUP_PLAN.md`

|---

## Stage U0.A-R2 Findings

### U0AR2-GIT-001 — Generated Commit SHA Error in Report
**Severity**: MEDIUM
**Category**: Documentation
**Description**: The Stage U0.A-R2 final report claimed SHA `e3c543a7f8390b8aad3c3fe1dce840ba7e88b2bb` which is invalid (47 chars, non-existent object). The actual generated commit SHA is `e3c543ac55c364f2abe968b4f8e5fc2a98645561`. The commit exists both locally and on remote with valid chain.
**Status**: CORRECTED / AWAITING EXTERNAL VERIFICATION
**Corrective action**: Investigation documented; actual SHA confirmed
**Corrective commit**: `bc3475b84a3d266f992046db125c65ed60506bd0`
**Evidence**: `reports/stage-u0/u0-a-r3/01_GENERATED_COMMIT_INVESTIGATION.md`
**Self-audit**: PASSED

### U0AR2-MAN-001 — Snapshot Manifest Incomplete
**Severity**: MEDIUM
**Category**: Documentation
**Description**: The Snapshot Manifest (09_SNAPSHOT_MANIFEST.txt) was incomplete with minimal fields in Stage U0.A-R2.
**Status**: CORRECTED / AWAITING EXTERNAL VERIFICATION
**Corrective action**: Full 24-field manifest created with all required values
**Corrective commit**: `13aa44d374269e27cfa00f7f1f53c2263a57945c`
**Evidence**: `reports/stage-u0/u0-a-r3/09_SNAPSHOT_MANIFEST.txt`
**Self-audit**: PASSED

### U0AR2-VAL-001 — False Positive in Validation
**Severity**: LOW
**Category**: Quality
**Description**: The `...` pattern incorrectly flagged 909 instances of common punctuation as aggregation placeholders.
**Status**: CORRECTED / AWAITING EXTERNAL VERIFICATION
**Corrective action**: Pattern `...` now only flags aggregation contexts ("plus others...")
**Corrective commit**: `13aa44d374269e27cfa00f7f1f53c2263a57945c`
**Evidence**: `reports/stage-u0/u0-a-r3/07_VALIDATION_RAW.txt`
**Self-audit**: PASSED

### U0AR2-GEN-001 — Working Tree Fallback in Generator
**Severity**: HIGH
**Category**: Integrity
**Description**: Generator had silent fallback to working tree content when `git show` failed for a path. Hashes could be computed from modified files, not snapshot.
**Status**: CORRECTED / AWAITING EXTERNAL VERIFICATION
**Corrective action**: Removed `sha256_file()` fallback; generator now raises RuntimeError on any snapshot read failure
**Corrective commit**: `bc3475b84a3d266f992046db125c65ed60506bd0`
**Evidence**: `reports/stage-u0/u0-a-r3/03_GENERATOR_FIX_REPORT.md`
**Self-audit**: PASSED

### U0AR2-TRACE-001 — Commit Traceability Gap
**Severity**: HIGH
**Category**: Governance
**Description**: Report SHA did not match actual commits. Generated commit SHA in R2 report was incorrect.
**Status**: CORRECTED / AWAITING EXTERNAL VERIFICATION
**Corrective action**: Full commit chain documented, all SHAs verified locally and remotely
**Corrective commit**: `13aa44d374269e27cfa00f7f1f53c2263a57945c`
**Evidence**: `reports/stage-u0/u0-a-r3/08_COMMIT_CHAIN.txt`, `reports/stage-u0/u0-a-r3/12_COMMIT_EXISTENCE_CHECKS.txt`
**Self-audit**: PASSED

---

## Pre-Audit Summary (Stage U0.A-R3)

### U0A-CAT-001 — File Catalog Incompleteness
**Previous status**: CORRECTED (R1)
**Current status**: CORRECTED / AWAITING EXTERNAL VERIFICATION
**Self-audit**: PASSED — 906 individual entries, 0 aggregations, all 10 fields populated

### U0A-VAL-001 — Validation and Reconciliation
**Previous status**: CORRECTED (R1)
**Current status**: CORRECTED / AWAITING EXTERNAL VERIFICATION
**Self-audit**: PASSED — all 6 reconciliation checks pass, set equality verified, validation patterns clean

### U0AR1-VAL-001 — R1 Validation Completeness
**Previous status**: CORRECTED (R1)
**Current status**: CORRECTED / AWAITING EXTERNAL VERIFICATION
**Self-audit**: PASSED — check-only exit 0, deterministic regeneration confirmed

### U0AR1-CAT-001 — R1 Catalog Field Completeness
**Previous status**: CORRECTED (R1)
**Current status**: CORRECTED / AWAITING EXTERNAL VERIFICATION
**Self-audit**: PASSED — 10-field catalog with Purpose, Last Commit, Recommendation

### U0AR1-CAT-002 — R1 CSV Completeness
**Previous status**: CORRECTED (R1)
**Current status**: CORRECTED / AWAITING EXTERNAL VERIFICATION
**Self-audit**: PASSED — 13 columns, sha256 + snapshot_sha present

### U0AR1-CAT-003 — R1 Hash Integrity
**Previous status**: CORRECTED (R1)
**Current status**: CORRECTED / AWAITING EXTERNAL VERIFICATION
**Self-audit**: PASSED — all hashes from snapshot blob, independent sample verified

### U0AR1-VAL-002 — R1 Placeholder Validation
**Previous status**: CORRECTED (R1)
**Current status**: CORRECTED / AWAITING EXTERNAL VERIFICATION
**Self-audit**: PASSED — TBD replaced, placeholder scan clean

---

## Summary (Updated — Stage U0.A-R3)

| Severity | Count | Key Items |
|----------|-------|-----------|
| 🔴 CRITICAL | 0 | — |
| 🟡 HIGH | 4 | U0A-CAT-001, U0A-VAL-001, U0AR2-GEN-001, U0AR2-TRACE-001 |
| 🟢 MEDIUM | 6 | U0A-FIND-03, U0A-FIND-04, U0A-FIND-05, U0A-FIND-07, U0AR2-GIT-001, U0AR2-MAN-001 |
| ℹ️ LOW | 5 | U0A-GOV-001 (CLOSED WITH FINDING), U0A-GIT-002, U0A-DEP-001, U0A-CLN-001, U0AR2-VAL-001 |
| ℹ️ INFO | 4 | U0A-FIND-01, U0A-FIND-08, U0A-FIND-09, U0A-FIND-10 |

| **Stage U0.A-R3 findings**: 5 new R2 findings + 7 legacy findings verified — all CORRECTED / AWAITING EXTERNAL VERIFICATION
|----------------------------------|-------|-----------|
|
|---

## Stage U0.A-R3.1 Findings

### U0AR3-MAN-001 — Manifest References Incorrect Metadata SHA
**Severity**: MEDIUM
**Category**: Documentation
**Description**: The R3 Snapshot Manifest listed `metadata_commit_sha` as `13aa44d` (generated inventory commit) instead of `1db3410` (actual R3 metadata commit). Manifest also lacked fields for R3.1 commits.
**Root cause**: Manifest was created during Commit 2 but not updated after Commit 3 (the actual metadata commit).
**Status**: CORRECTED / AWAITING EXTERNAL VERIFICATION
**Corrective action**: Manifest rewritten with full chain: r3_metadata_commit_sha = 1db3410 + R3.1 fields
**Corrective commit**: `e91ceb5109939962c75374b86b5e941cadf45d56`
**Evidence**: `reports/stage-u0/u0-a-r3/09_SNAPSHOT_MANIFEST.txt`
**Final pre-audit target SHA**: `e91ceb5109939962c75374b86b5e941cadf45d56`
**Residual risk**: LOW — cosmetic only, no functional impact

### U0AR3-AUD-001 — Pre-Audit Verification Referenced Wrong HEAD
**Severity**: HIGH
**Category**: Governance
**Description**: Pre-Audit Self Verification (10_PRE_AUDIT_SELF_VERIFICATION.md) stated "After final commit (Commit 2: 13aa44d)" when the actual final commit was `1db3410`. Pre-audit was executed against commit 13aa44d, not 1db3410.
**Root cause**: Pre-audit created mid-Stage before metadata commit, then never re-executed.
**Status**: CORRECTED / AWAITING EXTERNAL VERIFICATION
**Corrective action**: Pre-audit rewritten with FINAL_HEAD as target, executed AFTER push of final commit
**Corrective commit**: `e91ceb5109939962c75374b86b5e941cadf45d56`
**Evidence**: `reports/stage-u0/u0-a-r3/10_PRE_AUDIT_SELF_VERIFICATION.md`, `reports/stage-u0/u0-a-r3/11_PRE_AUDIT_RAW.txt`
**Final pre-audit target SHA**: `e91ceb5109939962c75374b86b5e941cadf45d56`
**Residual risk**: LOW — corrected, verification now targets final HEAD

### U0AR3-TRACE-001 — Commit Existence Evidence Missing Final HEAD
**Severity**: MEDIUM
**Category**: Documentation
**Description**: Commit Existence Checks (12_COMMIT_EXISTENCE_CHECKS.txt) listed only 4 SHAs (baseline, R3 tooling, R2 metadata, R3 generated). Missing: R3 metadata (1db3410), R3.1 preparation, R3.1 final HEAD.
**Root cause**: Evidence created before full commit chain complete.
**Status**: CORRECTED / AWAITING EXTERNAL VERIFICATION
**Corrective action**: All 7 SHAs now included with local/remote/parent verification
**Corrective commit**: `e91ceb5109939962c75374b86b5e941cadf45d56`
**Evidence**: `reports/stage-u0/u0-a-r3/12_COMMIT_EXISTENCE_CHECKS.txt`, `reports/stage-u0/u0-a-r3/08_COMMIT_CHAIN.txt`
**Final pre-audit target SHA**: `e91ceb5109939962c75374b86b5e941cadf45d56`
**Residual risk**: LOW

### U0AR3-STATUS-001 — Final Status Contains Duplicated SHA
**Severity**: MEDIUM
**Category**: Documentation
**Description**: Final Status listed Metadata (C3) with same SHA as Generated (C2): `13aa44d`. Actual C3 commit is `1db3410`.
**Root cause**: Generated and metadata commits were conflated in chain table.
**Status**: CORRECTED / AWAITING EXTERNAL VERIFICATION
**Corrective action**: Final Status rewritten with complete 7-commit chain, metadata SHA corrected
**Corrective commit**: `e91ceb5109939962c75374b86b5e941cadf45d56`
**Evidence**: `reports/stage-u0/u0-a-r3/06_FINAL_STATUS.md`
**Final pre-audit target SHA**: `e91ceb5109939962c75374b86b5e941cadf45d56`
**Residual risk**: LOW

### U0AR3-DET-001 — Determinism Mode Not Specified
**Severity**: LOW
**Category**: Quality
**Description**: Determinism statement used "modulo timestamps" without specifying mode (byte-identical vs canonical).
**Root cause**: Generator uses datetime.now() creating volatile timestamps.
**Status**: CORRECTED / AWAITING EXTERNAL VERIFICATION
**Corrective action**: Mode explicitly documented: byte-identical NOT YET, canonical YES. Generator modification deferred to avoid unnecessary regeneration. Byte-identical achievable by passing --generated-at parameter with commit timestamp.
**Corrective commit**: `e91ceb5109939962c75374b86b5e941cadf45d56`
**Evidence**: `reports/stage-u0/u0-a-r3/15_DETERMINISM_CHECK.txt`
**Final pre-audit target SHA**: `e91ceb5109939962c75374b86b5e941cadf45d56`
**Residual risk**: LOW — canonical determinism verified. Strict byte-identical requires generator CLI option.

---

## Summary (Updated — Stage U0.A-R3.1)
## Stage U0.A-R3.2 Findings

### U0AR31-MAN-001 — Manifest References Incorrect Metadata SHA (R3.1 correction)
**Severity**: MEDIUM
**Category**: Documentation
**Description**: Stage R3.1 Manifest assigned `final_head_sha = e91ceb5` (preparation commit) instead of the actual final commit. Violated rule that no committed file should claim parent commit as final HEAD.
**Root cause**: Manifest attempted to embed SHA of not-yet-created commit — fundamental self-reference problem.
**Current status**: CORRECTED / AWAITING EXTERNAL VERIFICATION
**Corrective action**: Evidence identity model redefined: `evidence_commit_identity: SELF` + `post_push_remote_sha: NOT STORED BY DESIGN`. Parent commit SHA stored as `evidence_commit_parent_sha`. Actual evidence commit SHA resolved after push.
**Corrective commit**: SELF — Stage U0.A-R3.2 evidence commit
**Evidence**: `reports/stage-u0/u0-a-r3/09_SNAPSHOT_MANIFEST.txt`
**Residual risk**: NONE — model is honest and verifiable

### U0AR31-STATUS-001 — Final Status Contradicts SHA Evidence (R3.1 correction)
**Severity**: MEDIUM
**Category**: Documentation
**Description**: R3.1 Final Status claimed `final_head_sha = e91ceb5` (parent) while actual remote HEAD was `4be97e2`.
**Root cause**: Same self-reference issue as U0AR31-MAN-001.
**Current status**: CORRECTED / AWAITING EXTERNAL VERIFICATION
**Corrective action**: Final Status now has two sections: Committed Evidence Identity (with SELF) + Post-Push Verification (resolved after push, not stored).
**Corrective commit**: SELF — Stage U0.A-R3.2 evidence commit
**Evidence**: `reports/stage-u0/u0-a-r3/06_FINAL_STATUS.md`
**Residual risk**: NONE

### U0AR31-TRACE-001 — Commit Chain Contains Self-Parent Record (R3.1 correction)
**Severity**: MEDIUM
**Category**: Documentation
**Description**: R3.1 Commit Chain showed `<SHA> <same SHA> <message>` — commit listed as its own parent.
**Root cause**: Attempt to fill final SHA before commit was created.
**Current status**: CORRECTED / AWAITING EXTERNAL VERIFICATION
**Corrective action**: Chain now shows real commits up to `4be97e2` + `SELF` for R3.2. Parent verified (`4be97e2`). Actual SHA resolved after push.
**Corrective commit**: SELF — Stage U0.A-R3.2 evidence commit
**Evidence**: `reports/stage-u0/u0-a-r3/08_COMMIT_CHAIN.txt`
**Residual risk**: NONE

### U0AR31-AUD-001 — Pre-Audit Committed Instead of Post-Push (R3.1 correction)
**Severity**: HIGH
**Category**: Governance
**Description**: R3.1 committed pre-audit claimed to have verified final HEAD, but was itself included in a commit that was not the final HEAD.
**Root cause**: Pre-audit executed mid-stage; verification committed.
**Current status**: CORRECTED / AWAITING EXTERNAL VERIFICATION
**Corrective action**: Renamed to PRE-COMMIT VALIDATION. Post-push verification performed separately and NOT committed. Final report (outside Git) contains post-push results.
**Corrective commit**: SELF — Stage U0.A-R3.2 evidence commit
**Evidence**: `reports/stage-u0/u0-a-r3/10_PRE_AUDIT_SELF_VERIFICATION.md`
**Residual risk**: NONE

### U0AR31-DET-001 — Determinism Mode Ambiguity (R3.1 correction)
**Severity**: LOW
**Category**: Quality
**Description**: R3.1 determinism check used "modulo timestamps" without mode specification. Generator used `datetime.now()` causing volatile timestamps.
**Root cause**: Generator implementation choice.
**Current status**: CORRECTED / AWAITING EXTERNAL VERIFICATION
**Corrective action**: Generator now uses snapshot commit timestamp. Byte-identical determinism verified via two-run diff (exit 0). `--generated-at` CLI option available for manual override.
**Corrective commit**: SELF — Stage U0.A-R3.2 evidence commit
**Evidence**: `reports/stage-u0/u0-a-r3/15_DETERMINISM_CHECK.txt`, `scripts/repository_inventory.py`
**Residual risk**: NONE — byte-identical determinism PASSED

---

## Summary (Updated — Stage U0.A-R3.2)

| Severity | Count | Key Items |
|----------|-------|-----------|
| 🔴 CRITICAL | 0 | — |
| 🟡 HIGH | 5 | U0A-CAT-001, U0A-VAL-001, U0AR2-GEN-001, U0AR2-TRACE-001, U0AR31-AUD-001 |
| 🟢 MEDIUM | 9 | U0A-FIND-03, U0A-FIND-04, U0A-FIND-05, U0A-FIND-07, U0AR2-GIT-001, U0AR2-MAN-001, U0AR31-MAN-001, U0AR31-STATUS-001, U0AR31-TRACE-001 |
| ℹ️ LOW | 6 | U0A-GOV-001 (CLOSED WITH FINDING), U0A-GIT-002, U0A-DEP-001, U0A-CLN-001, U0AR2-VAL-001, U0AR31-DET-001 |
| ℹ️ INFO | 4 | U0A-FIND-01, U0A-FIND-08, U0A-FIND-09, U0A-FIND-10 |

**Stage U0.A-R3.2 findings**: 5 new R3.1 findings — all CORRECTED / AWAITING EXTERNAL VERIFICATION
