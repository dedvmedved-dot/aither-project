# Gitleaks Scan Summary — R7-R5

**Generated:** 2026-07-26T23:09:00Z
**Baseline HEAD:** `170bf8f`
**Current HEAD:** `ffd712c`
**Gitleaks version:** 8.18.4

## Scan Matrix

| # | Scan Type | Scope | Findings | Exit Code | File |
|---|---|---|---|---|---|
| 1 | Staged | `git diff --cached` (pipe) | 0 | 0 | `gitleaks-staged.json` |
| 2 | Diff | `170bf8f..HEAD` (2 commits) | 102 | 1 | `gitleaks-diff.json` |
| 3 | Current | Full repo (421 commits) | 182 | 1 | `gitleaks-current.json` |
| 4 | Evidence | `--no-git` (working tree) | 92 | 1 | `gitleaks-evidence.json` |
| 5 | Final HEAD | Full repo at `ffd712c` | 182 | 1 | `gitleaks-final-head.json` |

## Sanitization

All findings have `Match` and `Secret` fields redacted to `[REDACTED]`. No plaintext credentials in any scan output.

## Diff Analysis (102 new findings in R7-R5 commits)

The diff scan covers 2 commits:
- `170bf8f` → `9ef356a` (Commit B — security containment)
- `9ef356a` → `ffd712c` (Commit C — Direction 14 fix)

These 102 findings are from files added/modified in R7-R5 and represent the incremental security surface.

## Verification

- All 5 scan types present: YES
- All outputs sanitized: YES
- No raw Match/Secret values: YES
- Scan summary generated: YES
