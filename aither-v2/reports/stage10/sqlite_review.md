# Stage 10 — SQLite Review

## Task 5 — SQLite Fix Status in Git

### Git (HEAD `519970f`) — Current State

| Item | Status | Details |
|------|--------|---------|
| `busy_timeout` PRAGMA | ❌ **NOT PRESENT** | Git's `get_db()` has no `busy_timeout` setting |
| `timeout` on `sqlite3.connect()` | ❌ **NOT PRESENT** | Git has `conn = sqlite3.connect(DB_PATH)` — no timeout |
| `synchronous=NORMAL` PRAGMA | ❌ **NOT PRESENT** | Git has only `journal_mode=WAL` and `foreign_keys=ON` |
| `retry_on_lock` decorator | ❌ **NOT PRESENT** | No retry logic exists in Git's `main.py` |
| Endpoint retry wrapping | ❌ **NOT PRESENT** | All 11 write-heavy endpoints have no retry protection |
| WAL mode | ✅ **PRESENT** | `PRAGMA journal_mode=WAL` is set in Git's `get_db()` |

### Git commit history

No commits related to SQLite fix or concurrency exist in the Git history. The `database is locked` issue was never addressed in any committed change.

### Local Working Tree (uncommitted) — Current State

| Fix | Present Locally? |
|-----|-----------------|
| `timeout=10` on `sqlite3.connect()` | ✅ Added |
| `PRAGMA busy_timeout=10000` | ✅ Added |
| `PRAGMA synchronous=NORMAL` | ✅ Added |
| `retry_on_lock` decorator (max_retries=5) | ✅ Added |
| Applied to 11 endpoints | ✅ Present |

### Conclusion

The SQLite concurrency fix **does NOT exist in the Git repository**. It exists only as local uncommitted changes. The fix was deployed to runtime (image `rc2r-sqlite-fix`) but has **no corresponding commit** in the repository history.
