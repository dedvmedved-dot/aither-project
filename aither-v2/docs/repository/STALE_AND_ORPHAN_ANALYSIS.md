# Stale and Orphan Analysis

> Analysis of stale (frozen/superseded) and orphan (unreferenced) files in the repository.

---

## 1. Stale Files — Frozen Stage Reports

The following report sets are **frozen snapshots** — they were accurate at their creation time but do NOT reflect the current state. They should not be modified.

| Report Set | Location | Frozen At | Reason |
|------------|----------|-----------|--------|
| Stage 10 audit | `reports/stage10/` | Commit f020aba | Initial audit — FAILED, superseded by 10A-10G |
| Stage 10B | `reports/stage10b/` | Commit 0dd4aa7 | Evidence quarantine — complete |
| BA-02R | `reports/ba02r/` | Commit 6a77a7c | Beta acceptance — complete |
| RC1 | `reports/rc1/` | Commit 3e4fa65 | RC1 readiness — complete |
| RC2 | `reports/rc2/` | Commit 519970f | RC2 production — complete |

**Verdict**: 🟢 Low — these are intentionally frozen historical records.

## 2. Stale Files — Legacy Stage Directories

The following directories contain legacy documentation from earlier stages that were not migrated to the `docs/mvp-roadmap/` structure:

| Directory | Files | Content |
|-----------|-------|---------|
| `aither-v2/01-k8s-gpu-operator/` | 3 | K8s GPU operator setup (superseded) |
| `aither-v2/02-containerd-nvidia-runtime/` | 6 | Containerd/NVIDIA config (superseded) |
| `aither-v2/03-vllm-14b-deploy/` | 40 | vLLM 14B deployment (historical) |

**Verdict**: 🟡 Medium — these consume 49 files that may no longer be relevant.

## 3. Stale Infrastructure Components

Root-level components that have been superseded by `aither-v2/` equivalents:

| Component | Location | Files | Superseded By | Status |
|-----------|----------|-------|---------------|--------|
| Historical Gateway | `gateway/` | 12 | `services/ai-platform/` + manifests | 🟡 Stale |
| Historical Portal | `portal/` | 35 | `services/portal-*` | 🟡 Stale |
| Historical Manifests | `manifests/` (root) | 22 | `aither-v2/manifests/` | 🟡 Stale |
| Historical Docs | `docs/` (root) | 28 | `aither-v2/docs/` | 🟡 Stale |
| Historical Configs | `configs/` | 5 | `services/*/` configs | 🟢 Low |

**Verdict**: 🟡 Medium — 102 files in superseded root-level components.

## 4. Orphan Files (Unreferenced)

Files that are tracked but not referenced by any active documentation or process:

| File | Location | Notes |
|------|----------|-------|
| `bortovoy-zhurnal.md` | Root | Lab journal — independent document |
| `lab-journal.md` | Root | Lab journal — independent document |
| `brief.md` | Root | Project brief |
| `plan.md` | Root | Project plan |
| `status.md` | Root | Status (may be stale) |
| `tr-status.md` | Root | TR status |
| `roadmap.md` | Root | Alternative roadmap |
| `FEATURES.md` | Root | Feature list |
| `nvidia_drv.txt` | Root | NVIDIA driver info |
| `Usage-Collector/` files | Root | Usage documentation |
| `fine-tuning/` files | Root | Standalone scripts (not part of services/) |

**Verdict**: 🟢 Low — orphan status is expected for root-level independent files.

## 5. Placeholder Directories

| Directory | Content | Notes |
|-----------|---------|-------|
| `aither-v2/04-tensor-parallelism/` | `.gitkeep` only | Empty placeholder |
| `aither-v2/05-gateway-redis/` | `.gitkeep` only | Empty placeholder |
| `aither-v2/06-portal-spa-bff-sse/` | `.gitkeep` only | Empty placeholder |
| `aither-v2/07-oauth/` | `.gitkeep` only | Empty placeholder |
| `aither-v2/release/mvp-rc1/` | 4 × `.gitkeep` | Empty release artifacts |

**Verdict**: 🟢 Low — placeholders for future work.

---

## Summary

| Category | Files | Severity |
|----------|-------|----------|
| Frozen stage reports | ~37 files | 🟢 Low — intentional |
| Legacy stage directories | 49 files | 🟡 Medium — consider archiving |
| Superseded root components | ~102 files | 🟡 Medium — consider migrating/archiving |
| Orphan root files | ~12 files | 🟢 Low — independent content |
| Placeholder directories | 7 dirs (7 .gitkeep) | 🟢 Low — intentional |

**Total potentially stale/orphan**: ~200 files (23% of all tracked files)

**Priority candidates for cleanup**:
1. `aither-v2/03-vllm-14b-deploy/` (40 files — largest legacy set)
2. `portal/` (35 files — superseded by services/)
3. `gateway/` (12 files — superseded)
4. `aither-send/` + `aither-send (2)/` (12 files — duplicates)
