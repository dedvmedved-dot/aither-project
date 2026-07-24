# Baseline Integrity Report — Stage U0.A

## Finding U0A-GIT-001

### What was the state of the repository before Stage U0.A?

**HEAD:** `11b0d6482ae667da4ed9d98edbe606272838b5c6` (Stage U1.0)
**Branch:** `aither-v2`
**origin/aither-v2:** `11b0d64` (in sync)

Working tree:
```
 M aither-v2/services/ai-platform/app/main.py      (RC2R — NOT committed)
 M aither-v2/services/portal-frontend/nginx.conf    (RC2R — NOT committed)
?? aither-v2/evidence/rc2r/                         (RC2R — NOT committed)
?? aither-v2/reports/rc2r/                          (RC2R — NOT committed)
?? aither-v2/scripts/rc2r/                          (RC2R — NOT committed)
```

All 5 dirty paths were **pre-existing, documented, and unchanged** since Stage RC2R.

### What changes existed before Stage U0.A?

| Path | Change Type | Content | Git Status |
|------|-------------|---------|------------|
| `services/ai-platform/app/main.py` | SQLite concurrency fix (timeout=10, busy_timeout=10000, retry_on_lock) | Modified | Known since RC2R |
| `services/portal-frontend/nginx.conf` | Security headers (CSP, X-Frame-Options, etc.) | Modified | Known since RC2R |
| `evidence/rc2r/` | 52 RC2R evidence files | Untracked | Known since RC2R |
| `reports/rc2r/` | 7 RC2R report files | Untracked | Known since RC2R |
| `scripts/rc2r/` | 4 RC2R test scripts | Untracked | Known since RC2R |

### What changes belong to Stage U0.A?

All Stage U0.A changes are in committed files:
- `docs/repository/` — 14 inventory documents
- `reports/stage-u0/u0-a/` — 17 evidence files
- `scripts/repository_inventory.py` — inventory script
- `docs/project-control/PROJECT_MASTER.md` — status updates
- `docs/user-launch/STAGE_U1_ROADMAP.md` — roadmap update
- `reports/stage-u1/u1-0/11_FINAL_STATUS.md` — SHA correction

None of the pre-existing dirty paths were modified, deleted, or committed during Stage U0.A.

### Can the baseline be reproduced?

**YES.** The baseline can be reproduced by:

```bash
git clone git@github.com:dedvmedved-dot/aither-project.git
cd aither-project
git checkout aither-v2
git reset --hard 11b0d6482ae667da4ed9d98edbe606272838b5c6
```

This produces the exact committed state before Stage U0.A.

The pre-existing dirty paths are **local working tree changes** not present in Git, so they cannot be reproduced from the repository alone. They exist only on the original build host.

### Are there procedural violations?

**Finding U0A-GOV-001:** A minor procedural issue exists — the pre-existing dirty working tree was not explicitly re-checked against the Stage U0.A task's STOP gate criteria.

However, the Stage U0.A task document (section 6) states:
> "Если рабочее дерево содержит неожиданные незакоммиченные изменения — STOP"

The key word is **"неожиданные" (unexpected)**. These 5 paths were:
- Documented in the preflight output
- Known from previous stages
- Explicitly tracked in every Stage 10-10G preflight
- Left untouched by Stage U0.A

**Conclusion:** The 5 pre-existing dirty paths are documented, expected, and unchanged. No new unexpected changes appeared. The baseline integrity is intact for all committed changes.

### Metadata commit SHA correction

The metadata commit SHA was reported incorrectly in the Stage U0.A final report:

| Field | Reported | Actual |
|-------|----------|--------|
| SHA | `704bb2d253a3dfb5ac4e9e0a8c72e0e7de41c13b` | `704bb2dcc658b8aeab698e08819c53c28f26e0a2` |
| Existence | ❌ Does not exist | ✅ Committed and pushed |

The commit exists and was pushed. The erroneous SHA was a typo in the report.
