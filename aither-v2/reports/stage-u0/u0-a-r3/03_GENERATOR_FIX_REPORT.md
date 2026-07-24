# Generator Fix Report — Stage U0.A-R3

## Issue: Working tree fallback in sha256_from_git()

### Previous behavior (Stage U0.A-R2 generator)
```python
def sha256_from_git(repo_root, path, snapshot_sha):
    out, err, rc = git_run(repo_root, "show", f"{snapshot_sha}:{path}")
    if rc != 0:
        # File might not exist in snapshot (newly added in working tree)
        # Fall back to working tree content
        full = os.path.join(repo_root, path)
        if os.path.exists(full):
            return sha256_file(full)
        return "0" * 64  # Silent zero hash
```

**Problems:**
1. Silent fallback to working tree — hashes could be from modified files, not snapshot
2. `"0"*64` return is indistinguishable from a real zero-content hash
3. No error reporting — generator continues as if nothing happened
4. Size was also read from working tree (`os.path.getsize`)

### Fixed behavior (Stage U0.A-R3 generator)
```python
def get_blob_from_snapshot(repo_root, path, snapshot_sha):
    out, err, rc = git_run(repo_root, "show", f"{snapshot_sha}:{path}")
    if rc != 0:
        raise RuntimeError(
            f"Cannot read tracked path from snapshot {snapshot_sha}: {path}\n"
            f"  stderr: {err.decode('utf-8', errors='replace').strip()}"
        )
    return out
```

**Changes:**
1. `sha256_from_git()` removed entirely — replaced by `get_blob_from_snapshot()` + `sha256_from_blob()`
2. `get_blob_size()` added — reads file size from `git cat-file -s`, not from `os.path.getsize()`
3. `verify_snapshot_commit()` added — exits non-zero if snapshot SHA is not a valid commit
4. `verify_path_in_snapshot()` added — exits non-zero if any tracked path is not in snapshot
5. Generator now exits with code 1 on any snapshot read failure

### Verification
- `git cat-file -t <sha>^{commit}` — verifies snapshot is a valid commit
- `git cat-file -e <sha>:<path>` — verifies each tracked path exists in snapshot
- `git show <sha>:<path>` — reads blob content (Raises RuntimeError on failure)
- `git cat-file -s <sha>:<path>` — reads blob size

### Commit fix
Commit `bc3475b84a3d266f992046db125c65ed60506bd0`
