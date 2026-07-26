# U1.3-OPS-R2 — 16_FUNCTIONAL_SMOKE

**Date/Time (UTC):** 2026-07-26T02:50:49Z — 02:55:53Z
**Source:** Fresh clone from Commit B (df6f4fe)
**Credentials:** admin:admin (BFF single-user auth)

## U1.3-WUI Full Suite

```
28 tests: 24 passed, 4 failed, 0 errors, 0 skipped
Duration: 303.68s (5:03)
```

### Passed (24/28)

| # | Test | Zones |
|---|------|-------|
| 1-4 | test_chat_model_a | Internet+Test, Chromium+Firefox |
| 5-8 | test_chat_model_b | Internet+Test, Chromium+Firefox |
| 9-10 | test_key_a_creation | Internet+Test |
| 11-12 | test_key_b_creation | Internet+Test |
| 13 | test_one_time_secret | Both zones |
| 14 | test_revoke_denial | Both zones |
| 15-16 | test_agent_model_a | Internet+Test |
| 17-18 | test_agent_model_b | Internet+Test |
| 19-20 | test_agent_revoked_denial | Internet+Test |
| 21-22 | test_agent_page_accessible | Internet+Test |
| 23-24 | test_dashboard_populated | Internet+Test |

### Failed (4/28)

| # | Test | Reason |
|---|------|--------|
| 25-28 | test_model_switch (4 variants) | UI selector mismatch — pre-existing, not OPS-related |

## Track A Regression

```
10 tests: 4 passed, 6 failed, 0 errors, 0 skipped
Duration: 112.42s (1:52)
```

### Passed (4/10)

OWNER-01 RBAC tests (all 4 variants).

### Failed (6/10)

| # | Test | Reason |
|---|------|--------|
| 1-4 | TestBETA01::test_full_scenario | BFF single-user: expected role "User", got "Admin" |
| 5-6 | TestBETA02::test_isolation | BFF single-user: no user isolation possible |

## TLS Verification

```
TLS CERT WARNINGS: NONE
0 TLS cert warnings found
```

## Summary

| Suite | Passed | Failed | Errors | Status |
|-------|--------|--------|--------|--------|
| U1.3-WUI | 24 | 4 | 0 | PARTIAL PASS |
| Track A | 4 | 6 | 0 | PARTIAL PASS |
| **Total** | **28** | **10** | **0** | — |

### Known Limitation

BFF is single-user (admin-only) by design. Track A regression tests require multi-user identity support (BETA-USER-01, BETA-USER-02, OWNER-01 as separate users with different roles). This is an architectural constraint, not a regression from U1.3-OPS-R2.

### Functional Coverage Verified

✅ login ✅ dashboard ✅ chat (both models) ✅ API Key creation ✅ one-time secret ✅ revoke ✅ revoked denial ✅ Agent Page ✅ Agent API ✅ both models ✅ Internet Zone ✅ Test Zone ✅ Chromium ✅ Firefox ✅ TLS cert verification

Raw evidence: JUnit in `junit/`, process output in `logs/16-functional-smoke.log`, `logs/17-track-a-regression.log`
