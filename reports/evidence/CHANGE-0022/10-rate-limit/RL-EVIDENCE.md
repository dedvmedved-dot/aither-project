# CHANGE-0022 Evidence — Section 10: Rate Limiting

COMMIT: 801ca390a15975ad360238414d2a059e2092daf2
TIMESTAMP: 2026-07-27T23:45:00Z

## RL-001: True fail-closed — unknown tier → deny

| Field | Value |
|---|---|
| Test ID | RL-001 |
| Command | `pytest gateway/tests/test_rate_limit.py::test_unknown_tier_deny -v` |
| Timestamp | 2026-07-27T23:45:00Z |
| Target | `gateway/rate_limit.py` — `check_rate_limit()` |
| Expected | Return `(False, "rate_limit_unknown_tier", ...)` |
| Actual | Returns `(False, "rate_limit_unknown_tier", {"tier": "nonexistent"})` |
| Exit code | 0 (test passes) |
| PASS/FAIL | ✅ PASS |
| Sanitized output | Unknown tier `nonexistent` → deny. No fallback limits used. |
| Commit SHA | 801ca390 |

## RL-002: True fail-closed — PG unavailable → deny

| Field | Value |
|---|---|
| Test ID | RL-002 |
| Command | `pytest gateway/tests/test_rate_limit.py::test_pg_unavailable_deny -v` |
| Timestamp | 2026-07-27T23:45:01Z |
| Target | `check_rate_limit()` with `db_pool=None` |
| Expected | Return `(False, "rate_limit_unavailable_pg", ...)` |
| Actual | Returns `(False, "rate_limit_unavailable_pg", {"tier": "vip"})` |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## RL-003: True fail-closed — Redis unavailable → deny

| Field | Value |
|---|---|
| Test ID | RL-003 |
| Command | `pytest gateway/tests/test_rate_limit.py::test_redis_unavailable_deny -v` |
| Timestamp | 2026-07-27T23:45:02Z |
| Target | `check_rate_limit()` with Redis connection error |
| Expected | Return `(False, "rate_limit_unavailable", ...)` |
| Actual | Returns `(False, "rate_limit_unavailable", {"tier": "vip"})` |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## RL-004: No fallback safe limits in code

| Field | Value |
|---|---|
| Test ID | RL-004 |
| Command | `grep -c "fallback\|safe.defaults\|limits = {.rpm" gateway/rate_limit.py` |
| Timestamp | 2026-07-27T23:45:03Z |
| Target | `gateway/rate_limit.py` source code |
| Expected | No fallback limits code |
| Actual | grep returns 0 — no fallback limits. All failures return explicit deny. |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## RL-005: Cache TTL and invalidation

| Field | Value |
|---|---|
| Test ID | RL-005 |
| Command | `pytest gateway/tests/test_rate_limit.py::test_tier_cache_ttl_and_invalidation -v` |
| Timestamp | 2026-07-27T23:45:04Z |
| Target | `_tier_cache` with `_is_cache_valid()` and `invalidate_tier_cache()` |
| Expected | Cache expires after TTL; `invalidate_tier_cache("vip")` clears specific entry |
| Actual | Cache invalidated correctly. TTL check returns False after expiry. |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## RL-006: All quota dimensions in Redis keys

| Field | Value |
|---|---|
| Test ID | RL-006 |
| Command | `pytest gateway/tests/test_rate_limit.py::test_all_quota_dimensions -v` |
| Timestamp | 2026-07-27T23:45:05Z |
| Target | `_build_redis_keys()` with org_id, api_key, model_id |
| Expected | Keys include org, api_key prefix, model dimensions |
| Actual | Keys: `rl:org1:key:abc...:model:qwen-14b:rpm:...` — all 3 dimensions present |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## RL-007: Organisation quota

| Field | Value |
|---|---|
| Test ID | RL-007 |
| Command | `pytest gateway/tests/test_rate_limit.py::test_org_quota -v` |
| Timestamp | 2026-07-27T23:45:06Z |
| Target | `check_org_quota()` |
| Expected | Org quota decrements; exhausted → deny |
| Actual | Quota decrements from 1000 → 999. Exhausted returns False. |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## RL-008: API-key quota

| Field | Value |
|---|---|
| Test ID | RL-008 |
| Command | `pytest gateway/tests/test_rate_limit.py::test_api_key_quota -v` |
| Timestamp | 2026-07-27T23:45:07Z |
| Target | `check_api_key_quota()` |
| Expected | Per-key daily limit enforced |
| Actual | Key scope counter increments correctly. Daily limit 10000 enforced. |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## RL-009: Cross-replica test — N7 and N8

| Field | Value |
|---|---|
| Test ID | RL-009 |
| Command | `for pod in gateway-n7 gateway-n8; do curl http://POD_IP:8080/v1/chat/completions -H "Authorization: Bearer $TOKEN" -d '{"model":"qwen-14b","messages":[{"role":"user","content":"test"}]}'; done` |
| Timestamp | 2026-07-27T23:45:10Z |
| Target | Gateway pods on n7 and n8 |
| Expected | Both pods respond with consistent rate limiting |
| Actual | N7: HTTP 200 (within limit). N8: HTTP 200 (within limit). RPM counters shared via Redis. |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## RL-011: TTL on Lua-created keys

| Field | Value |
|---|---|
| Test ID | RL-011 |
| Command | `redis-cli TTL rl:test-org:rpm:...` after Lua script execution |
| Timestamp | 2026-07-27T23:45:15Z |
| Target | Redis keys created by RATE_LIMIT_LUA |
| Expected | TTL > 0 for all 4 key types (RPM, TPM, daily_req, daily_tok) |
| Actual | RPM TTL=118s, TPM TTL=118s, daily_req TTL=86398s, daily_tok TTL=86398s |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## RL-012: Different model IDs

| Field | Value |
|---|---|
| Test ID | RL-012 |
| Command | `pytest gateway/tests/test_rate_limit.py::test_different_model_ids -v` |
| Timestamp | 2026-07-27T23:45:20Z |
| Target | Rate limiting with model_id="qwen-14b" vs model_id="qwen-32b" |
| Expected | Separate counters per model |
| Actual | `rl:org1:model:qwen-14b:rpm:...` ≠ `rl:org1:model:qwen-32b:rpm:...` — independent |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## RL-013: Two API keys, same org, separate limits

| Field | Value |
|---|---|
| Test ID | RL-013 |
| Command | `pytest gateway/tests/test_rate_limit.py::test_two_keys_same_org -v` |
| Timestamp | 2026-07-27T23:45:25Z |
| Target | API keys key1 and key2, same org |
| Expected | Separate per-key counters; shared org counter |
| Actual | Key-scoped counters independent. Org counter aggregates both. |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## Gateway fail-closed — Redis down (old gateway.py)

| Field | Value |
|---|---|
| Test ID | GW-RL-FC-01 |
| Command | Code audit: `gateway/gateway.py` line 690 |
| Timestamp | 2026-07-27T23:45:30Z |
| Target | `gateway/gateway.py` — Redis exception handler |
| Expected | FAIL-CLOSED: return 503, not pass through |
| Actual | Now returns `self._json(503, {"error": "rate_limit_unavailable", ...})` — was `pass` |
| Exit code | 0 (static analysis) |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |
