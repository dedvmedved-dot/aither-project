# Cleanup Plan

> Proposed cleanup actions for the Aither Project repository. 
> **Note**: All cleanup actions are PROPOSALS only — no destructive operations are executed in this stage.

---

## Priority 1 — High Impact (Duplicates)

### P1.1 Remove duplicate article directories
- **Files**: 12 redundant files
- **Action**: `git rm -r aither-send/ aither-send\ 2/`
- **Risk**: None — exact duplicates of `aither-article/`
- **Estimated savings**: 12 files

### P1.2 Remove empty placeholder directories
- **Files**: 4 .gitkeep files
- **Action**: `git rm` each .gitkeep in directories `04-tensor-parallelism/` through `07-oauth/`
- **Risk**: Low — directories are intentionally empty
- **Note**: These may be waiting for future stage content

---

## Priority 2 — Medium Impact (Legacy/Stale)

### P2.1 Archive `03-vllm-14b-deploy/`
- **Files**: 40 files
- **Action**: Move to `archive/` at root level or document as legacy frozen content
- **Risk**: Low — vLLM 14B deployment is superseded by current manifests
- **Dependency**: Verify that no active document links to these files

### P2.2 Migrate or link root-level documentation
- **Files**: 28 files in `docs/` (root)
- **Action**: Review each file; integrate key content into `aither-v2/docs/` where relevant; archive rest
- **Risk**: Medium — some root docs may still be referenced

### P2.3 Archive historical infrastructure code
- **Files**: 12 in `gateway/`, 35 in `portal/`, 22 in `manifests/` (root)
- **Action**: These are superseded by `aither-v2/services/` and `aither-v2/manifests/`
- **Option A**: Remove from branch (git rm)
- **Option B**: Keep for reference (documented as historical)
- **Recommendation**: Option B for auditability; tag a "pre-cleanup" commit

---

## Priority 3 — Low Impact (Housekeeping)

### P3.1 Review .gitkeep files
- **Files**: 41 .gitkeep files
- **Action**: Remove unnecessary .gitkeep from directories that already have tracked content
- **Note**: Some .gitkeep files are needed for preserving empty directories

### P3.2 Consolidate lab journals
- **Files**: `bortovoy-zhurnal.md`, `lab-journal.md`
- **Action**: Keep current, archive outdated entries

### P3.3 Review duplicate template/config files
- **Files**: ~10 small files with identical SHA-256 hashes
- **Action**: Investigate source; remove duplicates

---

## Implementation Order

```
Phase 1: P1.1 + P1.2 (safe removals, no reference impact)
Phase 2: P2.1 + P2.3 (legacy archive, no runtime impact)
Phase 3: P2.2 (root docs review — requires manual verification)
Phase 4: P3.1 + P3.2 + P3.3 (housekeeping)
```

## Estimated Impact

| Phase | Files to Remove | Files to Archive |
|-------|----------------|-----------------|
| Phase 1 | 16 | 0 |
| Phase 2 | 0 | ~117 |
| Phase 3 | ~10 | 0 |
| **Total** | **~26** | **~117** |

**Savings**: ~143 files (17% of 855 tracked files) would be either removed or clearly labelled as archived.

## Blockers

1. **External audit required** — cleanup must be authorized by ChatGPT architect
2. **Cross-reference check** — verify no active docs link to files targeted for removal
3. **Commit discipline** — each phase must be a separate commit with documented scope
