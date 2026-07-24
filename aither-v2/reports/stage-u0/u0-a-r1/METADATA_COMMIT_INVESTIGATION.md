# Metadata Commit Investigation

## Finding U0A-GIT-002

### Reported SHA

```
704bb2d253a3dfb5ac4e9e0a8c72e0e7de41c13b
```

### Actual committed SHA

```
704bb2dcc658b8aeab698e08819c53c28f26e0a2
```

### Short SHA

```
704bb2d
```

### Cause

The commit SHA `704bb2d253a3dfb5ac4e9e0a8c72e0e7de41c13b` was **never generated** by the repository.

The actual commit SHA is `704bb2dcc658b8aeab698e08819c53c28f26e0a2`. The erroneous SHA appears to be a typo or prediction error in the Stage U0.A final report.

Both SHAs share the same 7-character prefix `704bb2d`, which is sufficient for Git disambiguation. The full 40-character SHA provided in the report is **incorrect**.

### Verification

| Check | Result |
|-------|--------|
| `git cat-file -t 704bb2d253a3dfb5ac4e9e0a8c72e0e7de41c13b` | ❌ `fatal: could not get object info` |
| `git cat-file -t 704bb2dcc658b8aeab698e08819c53c28f26e0a2` | ✅ commit |
| `git rev-parse 704bb2d` | ✅ `704bb2dcc658b8aeab698e08819c53c28f26e0a2` |
| `git log --oneline 704bb2d -1` | ✅ `704bb2d docs(stage-u0.a): record final evidence commit metadata` |
| `git rev-parse origin/aither-v2` | ✅ `704bb2dcc658b8aeab698e08819c53c28f26e0a2` |

### Was the commit pushed?

**YES.** The commit `704bb2dcc658b8aeab698e08819c53c28f26e0a2` exists both locally and in `origin/aither-v2`.

### Conclusion

| Question | Answer |
|----------|--------|
| Commit not pushed? | ❌ — Commit was pushed successfully. |
| SHA specified incorrectly? | ✅ — Yes, the 40-char SHA in the report is wrong. |
| Commit rewritten? | ❌ — No. Only one commit with that prefix exists. |
| HEAD changed? | ❌ — HEAD still points to this commit. |
| Local-only commit? | ❌ — Present in origin/aither-v2. |
| Commit absent? | ❌ — The commit exists, but the reported full SHA is erroneous. |

**Recommendation:** Correct the SHA in `reports/stage-u0/u0-a/16_FINAL_STATUS.md` from `704bb2d253a3dfb5ac4e9e0a8c72e0e7de41c13b` to `704bb2dcc658b8aeab698e08819c53c28f26e0a2`.

### Evidence

```
$ git rev-parse HEAD
704bb2dcc658b8aeab698e08819c53c28f26e0a2

$ git log --oneline 704bb2d -1
704bb2d docs(stage-u0.a): record final evidence commit metadata

$ git rev-parse origin/aither-v2
704bb2dcc658b8aeab698e08819c53c28f26e0a2
```
