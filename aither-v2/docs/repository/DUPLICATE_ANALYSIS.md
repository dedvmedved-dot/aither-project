# Duplicate Analysis

> Analysis of duplicate files in the repository, identified by SHA-256 hash and by filename.

---

## 1. Empty Files (.gitkeep) — All Identical Hash

| Count | SHA-256 | File Pattern |
|-------|---------|--------------|
| **41** | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | Various `.gitkeep` files |

These are all zero-byte placeholder files. They are legitimate gitkeep markers.

**Verdict**: 🟢 Low — standard practice for preserving empty directories.

## 2. Duplicate Content Clusters (non-empty)

### Cluster A: aither-send/ = aither-article/

| SHA-256 | Files |
|---------|-------|
| `8a2a7c50aef14d0255926cb80d337a5313edd987a055d14b1d5ea22afa05e47c` | 4 files: `aither-send/article.md`, `aither-send (2)/article.md`, `aither-article/article.md` + 1 more |

The `aither-send/` and `aither-send (2)/` directories are direct copies of `aither-article/`:

| File | Count | Locations |
|------|-------|-----------|
| `article.md` | 3 | aither-article/, aither-send/, aither-send (2)/ |
| `architecture.svg` | 3 | Same 3 directories |
| `deployment.svg` | 3 | Same 3 directories |
| `gpu-stack.svg` | 3 | Same 3 directories |
| `request-flow.svg` | 3 | Same 3 directories |
| `tensor-parallelism.svg` | 3 | Same 3 directories |

**Total duplicate files in this cluster**: 18 files across 3 directories (but only 6 unique files)

**Verdict**: 🟡 Medium — 12 of 18 files are pure duplicates; remove 2 of the 3 copies.

### Cluster B: README.md variants

| COUNT | Filename |
|-------|----------|
| 6 | `README.md` (in different directories — different content, same name) |

These are legitimate — each README.md is specific to its directory context.

**Verdict**: 🟢 Low — standard practice.

### Cluster C: INSTRUCTIONS.md

| COUNT | Filename |
|-------|----------|
| 8 | `INSTRUCTIONS.md` (in legacy stage directories) |

Different content per directory. Legitimate.

**Verdict**: 🟢 Low

### Cluster D: Duplicate by hash (miscellaneous)

| Hash | Count | Files |
|------|-------|-------|
| `73f016e74f5105ec1043359afc9bc87fed28fcb3b9b0bf607f3cb683f553c393` | 4 | Various template files |
| `220a7db5abef6abf18c542dc922e8e920cc7db2c6808b57200bd494f02260352` | 4 | Various config files |
| `e4a344dc955c738f4ae0b6222cd178daa2a2264c27e47b68405002f034371d86` | 3 | Template/example files |
| `398621fe2e9c04a4af95115508ea1ed28d6660e9a24c8f37f89f3e060f04378f` | 3 | Other template files |
| Various (2 each) | 8 pairs | Various small config/snippet files |

**Verdict**: 🟢 Low — these are likely template files or auto-generated content.

---

## 3. Duplicate Names Analysis

| Filename | Count | Locations | Duplicate Content? |
|----------|-------|-----------|-------------------|
| `.gitkeep` | 41 | Various directories | ✅ Yes (all empty) |
| `README.md` | 6 | Various directories | ❌ No (different content) |
| `INSTRUCTIONS.md` | 8 | Legacy stage dirs | ❌ No (different content) |
| `DEPLOYMENT.md` | 5 | Various directories | ❌ No |
| `Dockerfile` | 5 | services/ subdirectories | ❌ No |
| `requirements.txt` | 4 | services/ subdirectories | ❌ No |
| `summary.md` | 3 | Various | ❌ No |
| `main.py` | 3 | services/ subdirectories | ❌ No |
| `nginx.conf` | 2 | services/portal-frontend/ | ❌ No |
| `styles.css` | 2 | Various | ❌ No |

---

## Summary

| Category | Count | Severity |
|----------|-------|----------|
| Empty .gitkeep (all identical) | 41 files | 🟢 Low |
| aither-send duplicates | 12 redundant files | 🟡 Medium |
| Template/example duplicates | ~10 files | 🟢 Low |
| Same-name different-content | ~25 files (legitimate) | 🟢 Low |

**Total redundant files**: ~12 (from aither-send duplication cluster)

**Recommendation**: Remove `aither-send/` and `aither-send (2)/` directories to eliminate 12 redundant files. Keep `.gitkeep` files and same-name-different-content files as-is.
