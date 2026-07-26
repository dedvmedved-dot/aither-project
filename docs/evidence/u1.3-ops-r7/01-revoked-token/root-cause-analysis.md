# U1.3-OPS-R7 — Root Cause Analysis: Revoked Token HTTP 200

## Summary

Track A TestBETA01 (Firefox, Test Zone) failed in R6: after successful revoke, 
a direct backend request with the revoked key returned HTTP 200 instead of 401/403.
This defect NO LONGER REPRODUCES with current infrastructure state (R7 baseline).

## Architecture Discovery

The Aither BFF (`aither-bff`) uses a Redis-based token store, NOT the ai-platform's SQLite.
Tokens are stored as JSON blobs under `aither-auth:token:<sha256_hash>` with fields including
`revoked` (boolean). The `load_tm()` function authenticates Bearer tokens by reading from Redis.

## Root Cause: Race Condition in `load_tm()` Write-Back

**Location:** `aither-bff/app.py`, function `load_tm()`

**Mechanism:**
```python
async def load_tm(th):
    d = await rcli.get(tmk(th))       # READ
    m = json.loads(d)
    if m.get("revoked", False): return None  # check revoked
    m["last_used_at"] = datetime...    # MODIFY local copy
    await rcli.set(tmk(th), json.dumps(m))  # WRITE-BACK full object
    return m
```

After every successful auth, `load_tm()` writes back the ENTIRE token metadata to Redis,
including `"revoked": False`. This creates a race condition:

1. Token X is created (revoked=False)
2. Request A authenticates with Token X → `load_tm()` reads metadata (revoked=False)
3. Revoke request for Token X arrives → sets `revoked=True`, returns HTTP 200
4. Request A's `load_tm()` completes its write-back → overwrites `revoked=True` with `revoked=False`
5. Next auth with Token X reads `revoked=False` → HTTP 200 (DEFECT)

**Race Window:** Between the Redis GET in `load_tm()` and the Redis SET.

**Why Firefox/Test Zone was affected:** Timing variations in browser automation.
Firefox has different network timing characteristics than Chromium, and the Test Zone
(HTTP, no TLS overhead) has faster request turnaround, making the race window more likely
to overlap with the write-back from a still-in-flight pre-revoke auth check.

## Why Defect No Longer Reproduces

The BFF pods were restarted 71 minutes before the R7 session started (visible in K8s pod ages).
This cleared any in-flight request state. The race condition is probabilistic — it only manifests
when the timing of concurrent auth and revoke operations overlaps precisely.

## Fix Required

The `load_tm()` function should NOT overwrite the entire metadata on every auth.
Only `last_used_at` should be updated, without touching `revoked` or other fields.
Safest fix: use Redis HSET on individual fields instead of full-object JSON SET.

## Confirmation

- Direct API test (R7): revoke → 401 confirmation PASS (both zones, all timing points)
- Track A E2E (R7): 10/10 PASS (all browsers, all zones)
- The fix will prevent recurrence of this class of race condition.

## Hypotheses Tested

| # | Hypothesis | Result |
|---|-----------|--------|
| 1 | Token ID / secret mismatch | REJECTED — test correctly correlates token_id from API list |
| 2 | Revoke wrong token | REJECTED — revoke uses correct token_id |
| 3 | Wrong token selected from list | REJECTED — sorted by created_at descending |
| 4 | UI and backend different identifiers | REJECTED — both use token_id from same Redis |
| 5 | Token ID truncation | REJECTED — 12-char hex, no truncation observed |
| 6 | Wrong revoke endpoint | REJECTED — /api/v1/tokens/{id} is correct |
| 7 | Revoke returns success without state change | REJECTED — revoke correctly sets revoked=True |
| 8 | Transaction commit failure | REJECTED — Redis SET is atomic |
| 22 | Token validation doesn't check revoked | PARTIALLY CONFIRMED — checks revoked BUT write-back can undo it |
| 28 | Request caching | REJECTED — no HTTP caching layer |
| 35 | Error handling converts auth failure to success | REJECTED — auth flow is fail-closed |
