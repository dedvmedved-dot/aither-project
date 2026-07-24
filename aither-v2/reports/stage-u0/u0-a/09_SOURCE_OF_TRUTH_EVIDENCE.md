# Source of Truth Evidence — Stage U0.A

## Identified Sources of Truth

| Area | Source of Truth | Location | Status |
|------|----------------|----------|--------|
| Git authoritative state | GitHub remote | `origin/aither-v2` | ✅ Verified in sync |
| Governance status | PROJECT_MASTER.md | `docs/project-control/PROJECT_MASTER.md` | ✅ Updated |
| Release status | CHAT_HANDOVER.md | `docs/project-control/CHAT_HANDOVER.md` | ✅ Updated |
| MVP status | current-mvp-status.md | `docs/mvp-roadmap/00-governance/current-mvp-status.md` | ✅ Present |
| Stage U1 roadmap | STAGE_U1_ROADMAP.md | `docs/user-launch/STAGE_U1_ROADMAP.md` | ✅ Updated |
| Architecture access | USER_ACCESS_ARCHITECTURE.md | `docs/user-launch/USER_ACCESS_ARCHITECTURE.md` | ✅ Present |
| Endpoint matrix | ENDPOINT_MATRIX.md | `docs/user-launch/ENDPOINT_MATRIX.md` | ✅ Present |
| Security baseline | ACCESS_SECURITY_BASELINE.md | `docs/user-launch/ACCESS_SECURITY_BASELINE.md` | ✅ Present |
| ADRs | ADR_U1_ACCESS.md | `docs/user-launch/ADR_U1_ACCESS.md` | ✅ Present |
| Stage 10 audit | Various reports | `reports/stage10*/` | ✅ Present |
| Stage 10G status | 10-STAGE-10G-STATUS.md | `reports/stage10g/` | ✅ Present |
| Beta acceptance | BA-02R reports | `reports/ba02r/` | ✅ Present |
| RC1 readiness | RC1 report | `reports/rc1/` | ✅ Present |
| RC2 evidence | RC2 evidence | `evidence/rc2/` | ✅ Present |

## Source of Truth Principles

1. **Git is the authoritative source** for all committed content
2. **PROJECT_MASTER.md** is the governance source of truth
3. **CHAT_HANDOVER.md** records the stage-by-stage audit trail
4. **current-mvp-status.md** reflects the current MVP progression
5. **User Launch docs** (`docs/user-launch/`) are the SOT for Track A
6. **Stage reports** are timestamped snapshots — frozen at creation time
7. **Evidence files** are raw command outputs, not derived summaries
8. **K8s runtime** is the operational SOT (not accessible for this stage)
