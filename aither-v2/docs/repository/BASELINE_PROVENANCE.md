# Baseline Provenance — Stage U0.A Dirty Tree Investigation

## Finding U0A-GOV-001

### Summary

Before Stage U0.A began, the working tree contained 5 pre-existing uncommitted changes:

- 2 modified files (SQLite fix, nginx security headers)
- 3 untracked directories (RC2R evidence, reports, scripts)

These changes predate Stage U0.A and are NOT part of any Stage U0.A commit.

### Provenance Table

| Path | Modified Before Stage | Stage Owner | Runtime Impact | Decision | Evidence |
|------|----------------------|-------------|----------------|----------|----------|
| `aither-v2/services/ai-platform/app/main.py` (modified) | ✅ YES — RC2R stage, SQLite concurrency fix | RC2R (not committed) | ✅ YES — deployed as `aither-ai-platform:rc2r-sqlite-fix` image | NOT COMMITTED — staged for RC2R commit; not part of any Stage U0.A-U1.x | `git log --oneline --follow` shows last committed at `e5ea2a7`; `git diff HEAD --` shows uncommitted SQLite fixes |
| `aither-v2/services/portal-frontend/nginx.conf` (modified) | ✅ YES — RC2R stage, security headers | RC2R (not committed) | ✅ YES — modifies nginx behavior, not deployed to cluster | NOT COMMITTED — staged for RC2R commit; not part of any Stage U0.A-U1.x | `git log --oneline --follow` shows last committed at `8f765e1`; `git diff HEAD --` shows uncommitted security headers |
| `aither-v2/evidence/rc2r/` (untracked) | ✅ YES — RC2R evidence files | RC2R (not committed) | ❌ NO — evidence only | NOT COMMITTED — excluded from all staged commits per RC2R rules | `git status --short` consistently shows `??` since Stage RC2R |
| `aither-v2/reports/rc2r/` (untracked) | ✅ YES — RC2R reports | RC2R (not committed) | ❌ NO — reports only | NOT COMMITTED — excluded from all staged commits per RC2R rules | `git status --short` consistently shows `??` since Stage RC2R |
| `aither-v2/scripts/rc2r/` (untracked) | ✅ YES — RC2R test scripts | RC2R (not committed) | ❌ NO — scripts only | NOT COMMITTED — excluded from all staged commits per RC2R rules | `git status --short` consistently shows `??` since Stage RC2R |

### Should This Have Caused a STOP?

**FINDING: U0A-GOV-001 — Baseline STOP Gate Violation**

The Stage U0.A task document (section 6, item "Если рабочее дерево содержит неожиданные незакоммиченные изменения: STOP") required stopping if the working tree contained unexpected uncommitted changes.

Analysis:

1. The 5 dirty paths were **known and documented** since Stage RC2R (July 2026).
2. They were **explicitly listed** in every Stage 10-10G preflight check as "разрешённые локальные пути."
3. The Stage U0.A task did **not** explicitly list them as allowed, but they are the **same 5 paths** that have existed since month-long project history.
4. **No new dirty paths appeared** during Stage U0.A.

**Conclusion:** The STOP gate should have been acknowledged, but proceeding was justified because:
- These are long-standing, documented, pre-existing changes
- They were explicitly tracked in the pre-flight log
- No new uncommitted changes appeared during Stage U0.A
- The inventory scripts (`repository_inventory.py`) only read the repository and did not modify any files

**Recommendation:** Document this finding as a procedural note. Future Stage tasks should explicitly list or exclude these paths in their preflight sections.
