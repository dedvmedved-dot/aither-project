# Stage U0.A Findings — Repository Inventory & Documentation Index

## Finding Register

| ID | Severity | Area | Description | Status |
|----|----------|------|-------------|--------|
| U0A-FIND-01 | INFO | Repository | 855 tracked files across 2 branches (~100 directories) | OPEN |
| U0A-FIND-02 | INFO | Inventory | 563 files in aither-v2/ (active), 292 at root (historical) | OPEN |
| U0A-FIND-03 | LOW | Duplicates | 41 empty .gitkeep files (all zero-size, same hash) | OPEN |
| U0A-FIND-04 | LOW | Duplicates | aither-send/ and aither-send (2)/ are duplicates of aither-article/ (12 SVG files + 3 article.md) | OPEN |
| U0A-FIND-05 | MEDIUM | Isolation | Root-level gateway/ and portal/ are superseded by aither-v2/services/ | OPEN |
| U0A-FIND-06 | MEDIUM | Isolation | Root-level manifests/ and docs/ overlap with aither-v2/ equivalents | OPEN |
| U0A-FIND-07 | INFO | Branches | main branch (73 commits) contains historical content not merged into aither-v2 | OPEN |
| U0A-FIND-08 | LOW | Placeholders | 7 placeholder directories (01- through 07-) in aither-v2/ contain only .gitkeep | OPEN |
| U0A-FIND-09 | LOW | Placeholders | release/mvp-rc1/ contains only empty .gitkeep files | OPEN |
| U0A-FIND-10 | INFO | Config | offline-deploy/ has full K8s manifests parallel to aither-v2/manifests/ | OPEN |
| U0A-FIND-11 | LOW | Security | PEM public keys committed in delegation/ and portal/ — public only, non-sensitive | OPEN |
| U0A-FIND-12 | INFO | Pre-existing | 5 modified files in working tree (3 fix findings, 2 code changes) | PRE-EXISTING |
| U0A-FIND-13 | INFO | Pre-existing | RC2R evidence/reports/scripts are untracked, not committed | PRE-EXISTING |
| U0A-FIND-14 | LOW | Orphans | 0-byte .gitkeep files scattered across empty directories | OPEN |
| U0A-FIND-15 | INFO | Secret scan | No real secrets detected in committed tracked files | PASSED |
| U0A-FIND-16 | LOW | Markdown | Several .md files have unmatched triple-backtick fences (historical) | OPEN |

## Findings Corrected (pre-existing)

| ID | File | Correction | Status |
|----|------|------------|--------|
| GOV-U1-01 | PROJECT_MASTER.md | `|| Stage 10G` → `| Stage 10G` | CORRECTED |
| GOV-U1-02 | 11_FINAL_STATUS.md | SHA placeholder → actual SHA | CORRECTED |
| ROADMAP-U0A-01 | STAGE_U1_ROADMAP.md | Updated statuses, added U0.A stage | CORRECTED |

## Verdicts

| Check | Result |
|-------|--------|
| Baseline verified | ✅ HEAD = origin/aither-v2 |
| Branch consistency | ✅ No divergence between local/remote |
| File inventory | ✅ 855 files catalogued |
| Duplicate analysis | ✅ 41 .gitkeep + 15 content duplicates |
| Orphan analysis | ✅ 292 root-level files identified |
| Secret scan (committed) | ✅ No real secrets found |
| Finding corrections | ✅ 3 findings corrected |
