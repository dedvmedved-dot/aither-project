# Branch Catalog

> Overview of Git branches in the Aither Project repository.

---

## Active Branch: `aither-v2`

| Property | Value |
|----------|-------|
| **HEAD** | `11b0d6482ae667da4ed9d98edbe606272838b5c6` |
| **Status** | Active (checked out, up to date with origin) |
| **Total files** | 855 (563 in aither-v2/, 292 at root) |
| **Recent commits** | Stage U1.0 (2026-07-24) |
| **Upstream** | `origin/aither-v2` |
| **Divergence from main** | 6 commits ahead, 73 commits behind |

### Recent Commit History
```
11b0d64 docs(stage-u1.0): define user access architecture and governance
4436ddb docs(stage10g): close stage10f audit and repair status table
0997db7 docs(stage10f): repair handover fence structure
fae8cee docs(stage10e): close stage10d audit and repair handover markdown
8dc7e01 docs(stage10d): align governance with stage10 audit status
f65c6ee docs(stage10c): correct release status and rc2 claims
```

### Working Tree Changes
- **Modified (4 files)**: PROJECT_MASTER.md, STAGE_U1_ROADMAP.md, 11_FINAL_STATUS.md, services/ai-platform/app/main.py, services/portal-frontend/nginx.conf
- **Untracked**: evidence/rc2r/, reports/rc2r/, scripts/rc2r/, scripts/repository_inventory.py

---

## Historical Branch: `main`

| Property | Value |
|----------|-------|
| **HEAD** | `89340ee55b476257fe1b197027b761b93fc63423` |
| **Status** | Historical (not checked out) |
| **Upstream** | `origin/main` |
| **Description** | Earlier development history with ~73 commits |

### Characteristic Content (not in aither-v2)
- Historical training manual chapters (24 chapters)
- K8s cluster recovery reports
- Fine-tuning work (LoRA, QLoRA)
- Portal development (#36, #39, #21)
- Lab journal entries
- Offline-deploy v1.x
- Physical architecture diagrams

---

## Remote Branches

| Remote Ref | SHA | Sync Status |
|------------|-----|-------------|
| `origin/HEAD` | → `origin/main` | Default |
| `origin/aither-v2` | `11b0d6482ae667da4ed9d98edbe606272838b5c6` | ✅ In sync |
| `origin/main` | `89340ee55b476257fe1b197027b761b93fc63423` | ✅ In sync |

---

## Tags

No tags exist in the repository.

---

## Branch Relationship Map

```
main (89340ee)  ---- 73 historical commits ----.
                                                  \
                                                   merge-base (35c8cdf)
                                                  /
aither-v2 (11b0d64)  -- 6 stage commits ---------'
```

- **Merge base**: `35c8cdffb04bfb6a1c09ccc36138019ff4b213cd`
- **Divergence**: aither-v2 has 6 stage/audit commits; main has training manual, K8s recovery, and earlier feature work
