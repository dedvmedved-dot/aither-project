# R7-R5-REPOSITORY-CLEANUP-01 — Change Summary

## Repository Baseline

| Field | Value |
|-------|-------|
| Repository | `dedvmedved-dot/aither-project` |
| Branch | `aither-v2` |
| Starting SHA | `39a8946143e7a38ceff9faabad024225acbf202e` |
| Final documentation SHA | (to be filled after commit) |
| Working tree | Clean |

## Commit Chronology Documented

| Commit | Files | Classification |
|--------|-------|----------------|
| `407cbe7` | `vllm-32b-instruct-awq.yaml`, `portal-backend/main.py` | Qwen2.5-32B native chat |
| `8ba71ac` | `vllm-qwen3-32b-awq.yaml`, `portal-backend/main.py` | Qwen3-32B + thinking off |
| `27c897a` | `identity/main.py`, `portal-backend/main.py`, `requirements.*` | Feedback attachments |
| `95723c6` | `identity/main.py` | Default scopes fix |
| `39a8946` | `portal-frontend/app.js`, `portal-frontend/index.html` | WUI refresh |

## Files Created/Modified

### Created

| File | Purpose |
|------|---------|
| `docs/current-state/CHANGE_HISTORY_2026-08-06_07.md` | 5-commit analysis with Git/Runtime classification |
| `docs/current-state/CURRENT_STATE_2026-08-07.md` | Full current state document (20 sections) |
| `docs/current-state/REPOSITORY_STATE_MATRIX.md` | 31-claim state matrix |
| `docs/current-state/REPOSITORY_KNOWN_DEFECTS.md` | 7 known defects (2 fixed, 5 open) |
| `docs/models/MODEL_CATALOG.md` | Model catalog with specs, context, performance |
| `reports/R7-R5-REPOSITORY-CLEANUP-01/CHANGE_SUMMARY.md` | This file |
| `docs/users/` | Directory for user docs (created) |

### Modified

| File | Changes |
|------|---------|
| `README.md` | Models section: Qwen2.5/Qwen3, historical section, scopes updated |
| `docs/hermes-aither-connection.md` | Rewritten: current models, 2 methods, historical section |

## Claims Corrected

- README: removed `qwen-14b`, `qwen-32b-base`, `model:32b:chat-adapter` from current state → moved to historical
- Hermes guide: removed completion adapter requirement, added current model IDs
- Commit `39a8946`: documented that it claims tokenizer/DB/Identity changes but diff shows only WUI files

## Runtime-Only Claims Identified

1. 45 users DB migration — not in Git
2. tokenizer_config.json patch — not in Git
3. 7 portal docs updated — not in Git
4. YaRN 64K — not in tracked files
5. Hermes operational status — not in Git

## Known Defects Registered

| ID | Status |
|----|--------|
| REPO-DEFECT-APIKEY-WUI-001 | OPEN |
| REPO-DEFECT-FEEDBACK-DB-SCHEMA-001 | OPEN |
| REPO-DEFECT-FEEDBACK-AUTH-001 | OPEN |
| REPO-DEFECT-FEEDBACK-SIZE-001 | OPEN |
| REPO-DEFECT-TOKENIZER-CONFIG-001 | OPEN |
| REPO-DEFECT-README-OBSOLETE-001 | FIXED |
| REPO-DEFECT-HERMES-DOC-001 | FIXED |

## Secrets Scan

- Scanned: all new and modified docs
- Result: PASSED — only placeholders (`<VLLM_API_KEY>`, `athr_...`)
- No real credentials in new documentation

## Broken Links

- Checked: all relative links in new docs
- Result: 0 broken links

## Final Checklist

- [x] 5 commits analyzed and documented
- [x] Current state documented
- [x] State matrix created (31 claims)
- [x] Known defects registered (7)
- [x] Model catalog created
- [x] README updated
- [x] Hermes guide updated
- [x] Secret scan passed
- [x] Broken links fixed
- [x] No application code modified
- [x] No system access
- [x] No runtime changes
- [x] Documentation-only commit
