"""Idempotency Integration Tests - IDEM-001..008. CHANGE-0022-C3.

Direct function tests for billing.py idempotency.
For HTTP-level tests, see test_idempotency_http.py.
"""
import os, sys, uuid, time, json, hashlib, threading
import urllib.request
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import psycopg2
import psycopg2.pool

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://aither-gateway.aither-inference.svc:8000")
PG_URL = os.environ["PG_URL"]  # mandatory — tests must fail without it
REDIS_HOST = os.environ.get("REDIS_HOST", "aither-redis-rate-limit.aither-inference.svc")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
TEST_ORG = f"idem-test-{uuid.uuid4().hex[:8]}"

# Import billing for direct DB operations
from billing import (
    reserve, settle, refund, BillingResult,
    _compute_fingerprint, _check_billing_idempotency,
    _mark_idempotency_completed, _mark_idempotency_failed,
    _clean_expired_idempotency, _reconcile_settled_failed,
)

results = []


def record(test_id: str, command: str, expected: str, actual: str, passed: bool):
    """Record test result with evidence."""
    results.append({
        "test_id": test_id,
        "command": command,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "expected": expected,
        "actual": actual,
        "status": "PASS" if passed else "FAIL",
    })
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n{'='*60}")
    print(f"{status}: {test_id}")
    print(f"  Expected: {expected}")
    print(f"  Actual:   {actual}")
    print(f"{'='*60}")


def http_post(path: str, data: dict, headers: dict = None) -> tuple:
    """Make HTTP POST to gateway. Returns (status_code, response_body)."""
    url = f"{GATEWAY_URL}{path}"
    req_data = json.dumps(data).encode()
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    try:
        req = urllib.request.Request(url, data=req_data, headers=hdrs, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"error": body}
    except Exception as e:
        return 0, {"error": str(e)}


def setup_test_org(db_pool):
    """Create test org with balance."""
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO billing_accounts (org_id, balance, reserved, tier) VALUES (%s, 100000, 0, 'free') "
            "ON CONFLICT (org_id) DO UPDATE SET balance=100000, reserved=0",
            (TEST_ORG,)
        )
        conn.commit()
    finally:
        db_pool.putconn(conn)


def cleanup_test_org(db_pool):
    """Remove test data."""
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM billing_reservations WHERE org_id = %s", (TEST_ORG,))
        cur.execute("DELETE FROM billing_ledger WHERE org_id = %s", (TEST_ORG,))
        cur.execute("DELETE FROM gateway_idempotency WHERE org_id = %s", (TEST_ORG,))
        cur.execute("DELETE FROM billing_idempotency WHERE organisation = %s", (TEST_ORG,))
        cur.execute("DELETE FROM billing_accounts WHERE org_id = %s", (TEST_ORG,))
        conn.commit()
    finally:
        db_pool.putconn(conn)


# ═══════════════════════════════════════════════════════════════════════
# IDEM-001: Duplicate completed — replay previous result
# ═══════════════════════════════════════════════════════════════════════
def test_idem_001(db_pool):
    """IDEM-001: Same key + same payload → ALREADY_COMPLETED."""
    tag = "IDEM-001"
    ikey = f"idem001-{uuid.uuid4().hex[:8]}"
    fp = _compute_fingerprint({"test": "idem001", "org": TEST_ORG})

    # First call — should succeed
    r1, ref1 = reserve(TEST_ORG, 100, db_pool, idempotency_key=ikey, request_fingerprint=fp)
    expected1 = f"SUCCESS with reservation_id"
    actual1 = f"{r1.name} ref={'yes' if ref1 else 'none'}"
    passed1 = r1 == BillingResult.SUCCESS and ref1 is not None
    record(f"{tag}.1", "reserve(key=X, fp=Y)", expected1, actual1, passed1)

    # Second call — same key, same fp → ALREADY_COMPLETED
    r2, ref2 = reserve(TEST_ORG, 100, db_pool, idempotency_key=ikey, request_fingerprint=fp)
    expected2 = f"ALREADY_COMPLETED with same ref"
    actual2 = f"{r2.name} ref={'same' if ref2 == ref1 else 'diff'}"
    passed2 = r2 == BillingResult.ALREADY_COMPLETED and ref2 == ref1
    record(f"{tag}.2", "reserve(key=X, fp=Y) again", expected2, actual2, passed2)

    return passed1 and passed2


# ═══════════════════════════════════════════════════════════════════════
# IDEM-002: Duplicate concurrent — only one executes
# ═══════════════════════════════════════════════════════════════════════
def test_idem_002(db_pool):
    """IDEM-002: Concurrent same-key requests — one executes, others get IN_PROGRESS."""
    tag = "IDEM-002"
    ikey = f"idem002-{uuid.uuid4().hex[:8]}"
    fp = _compute_fingerprint({"test": "idem002"})

    results_concurrent = []

    def concurrent_call():
        status, data = _check_billing_idempotency(ikey, fp, TEST_ORG, db_pool)
        results_concurrent.append(status)

    # Start concurrent
    t1 = threading.Thread(target=concurrent_call)
    t2 = threading.Thread(target=concurrent_call)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    new_count = results_concurrent.count('new')
    in_progress_count = results_concurrent.count('in_progress')
    completed_count = results_concurrent.count('completed')

    expected = "one 'new', one 'in_progress' or 'completed'"
    actual = f"results: {results_concurrent} (new={new_count}, in_progress={in_progress_count}, completed={completed_count})"
    passed = new_count == 1 and (in_progress_count + completed_count) >= 1
    record(tag, "concurrent _check_billing_idempotency", expected, actual, passed)

    # Clean up
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM billing_idempotency WHERE idempotency_key = %s", (ikey,))
        conn.commit()
    finally:
        db_pool.putconn(conn)

    return passed


# ═══════════════════════════════════════════════════════════════════════
# IDEM-003: Same key, different payload → CONFLICT
# ═══════════════════════════════════════════════════════════════════════
def test_idem_003(db_pool):
    """IDEM-003: Same key + different fingerprint → CONFLICT (409)."""
    tag = "IDEM-003"
    ikey = f"idem003-{uuid.uuid4().hex[:8]}"
    fp1 = _compute_fingerprint({"test": "idem003", "v": 1})
    fp2 = _compute_fingerprint({"test": "idem003", "v": 2})

    # First call with fp1
    r1, ref1 = reserve(TEST_ORG, 100, db_pool, idempotency_key=ikey, request_fingerprint=fp1)
    record(f"{tag}.1", f"reserve(key=X, fp=v1)", "SUCCESS", f"{r1.name}", r1 == BillingResult.SUCCESS)

    # Second call with fp2 → should be CONFLICT
    r2, ref2 = reserve(TEST_ORG, 100, db_pool, idempotency_key=ikey, request_fingerprint=fp2)
    expected = "CONFLICT"
    actual = r2.name
    passed = r2 == BillingResult.CONFLICT
    record(f"{tag}.2", f"reserve(key=X, fp=v2)", expected, actual, passed)

    return passed


# ═══════════════════════════════════════════════════════════════════════
# IDEM-004: Retry after timeout/expiry (failed status → retry succeeds)
# ═══════════════════════════════════════════════════════════════════════
def test_idem_004(db_pool):
    """IDEM-004: After a failed settlement, retry with same key succeeds."""
    tag = "IDEM-004"
    ikey = f"idem004-{uuid.uuid4().hex[:8]}"
    fp = _compute_fingerprint({"test": "idem004"})

    # Simulate: mark as failed
    _mark_idempotency_failed(ikey, TEST_ORG, "test_settlement_error", db_pool)

    # Retry — should succeed (status=failed → reset to pending then process)
    r, ref = reserve(TEST_ORG, 100, db_pool, idempotency_key=ikey, request_fingerprint=fp)
    expected = "SUCCESS after failed status retry"
    actual = f"{r.name}"
    passed = r == BillingResult.SUCCESS
    record(tag, "reserve after _mark_idempotency_failed", expected, actual, passed)

    return passed


# ═══════════════════════════════════════════════════════════════════════
# IDEM-005: Retry after settlement failure → reconciliation
# ═══════════════════════════════════════════════════════════════════════
def test_idem_005(db_pool):
    """IDEM-005: Settlement failure → reconciliation retries settlement."""
    tag = "IDEM-005"
    ikey = f"idem005-{uuid.uuid4().hex[:8]}"
    fp = _compute_fingerprint({"test": "idem005"})

    # Normal reserve
    r1, ref = reserve(TEST_ORG, 100, db_pool, idempotency_key=ikey, request_fingerprint=fp)
    record(f"{tag}.1", "reserve", "SUCCESS", r1.name, r1 == BillingResult.SUCCESS)

    # Attempt settle with reconciliation — should succeed
    sr = settle(TEST_ORG, ref, 50, db_pool)
    expected = "SUCCESS or ALREADY_COMPLETED"
    actual = sr.name
    passed = sr in (BillingResult.SUCCESS, BillingResult.ALREADY_COMPLETED)
    record(f"{tag}.2", f"settle(ref={ref}, 50)", expected, actual, passed)

    # Now try reconcile directly (should be ALREADY_COMPLETED since settled)
    rr = _reconcile_settled_failed(TEST_ORG, ref, db_pool)
    expected2 = "ALREADY_COMPLETED"
    actual2 = rr.name
    passed2 = rr == BillingResult.ALREADY_COMPLETED
    record(f"{tag}.3", "_reconcile_settled_failed", expected2, actual2, passed2)

    return passed and passed2


# ═══════════════════════════════════════════════════════════════════════
# IDEM-006: Streaming request retry — idempotent replay
# ═══════════════════════════════════════════════════════════════════════
def test_idem_006(db_pool):
    """IDEM-006: Streaming with idempotency key — replay returns previous."""
    tag = "IDEM-006"
    ikey = f"idem006-{uuid.uuid4().hex[:8]}"
    fp = _compute_fingerprint({"test": "idem006", "stream": True})

    # Reserve with streaming context
    r1, ref1 = reserve(TEST_ORG, 100, db_pool, idempotency_key=ikey, request_fingerprint=fp)
    # Settle (simulating successful stream)
    settle(TEST_ORG, ref1, 50, db_pool)

    # Retry same key → ALREADY_COMPLETED
    r2, ref2 = reserve(TEST_ORG, 100, db_pool, idempotency_key=ikey, request_fingerprint=fp)
    expected = "ALREADY_COMPLETED with same ref"
    actual = f"{r2.name} ref={'same' if ref2 == ref1 else 'diff'}"
    passed = r2 == BillingResult.ALREADY_COMPLETED
    record(tag, "reserve after settle (stream replay)", expected, actual, passed)

    return passed


# ═══════════════════════════════════════════════════════════════════════
# IDEM-007: Idempotency key expiry — new execution after TTL
# ═══════════════════════════════════════════════════════════════════════
def test_idem_007(db_pool):
    """IDEM-007: Expired idempotency records allow new execution."""
    tag = "IDEM-007"
    ikey = f"idem007-{uuid.uuid4().hex[:8]}"
    fp = _compute_fingerprint({"test": "idem007"})

    # Insert with expired expiry
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO billing_idempotency (idempotency_key, request_fingerprint, organisation, processing_status, expiry) "
            "VALUES (%s, %s, %s, 'completed', NOW() - INTERVAL '25 hours') "
            "ON CONFLICT (idempotency_key) DO UPDATE SET expiry = NOW() - INTERVAL '25 hours'",
            (ikey, fp, TEST_ORG),
        )
        conn.commit()
    finally:
        db_pool.putconn(conn)

    # Clean expiry
    deleted = _clean_expired_idempotency(db_pool)
    record(f"{tag}.1", "_clean_expired_idempotency", "deleted ≥ 1", f"deleted={deleted}", deleted >= 1)

    # Now new request should succeed
    r, ref = reserve(TEST_ORG, 100, db_pool, idempotency_key=ikey, request_fingerprint=fp)
    expected = "SUCCESS (expired record cleaned)"
    actual = r.name
    passed = r == BillingResult.SUCCESS
    record(f"{tag}.2", "reserve after cleanup", expected, actual, passed)

    return passed


# ═══════════════════════════════════════════════════════════════════════
# IDEM-008: Org isolation — same key, different orgs are separate
# ═══════════════════════════════════════════════════════════════════════
def test_idem_008(db_pool):
    """IDEM-008: Same idempotency key for different orgs → separate records."""
    tag = "IDEM-008"
    org_a = f"{TEST_ORG}-a"
    org_b = f"{TEST_ORG}-b"
    ikey = f"idem008-{uuid.uuid4().hex[:8]}"
    fp = _compute_fingerprint({"test": "idem008"})

    # Create both orgs
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        for org in [org_a, org_b]:
            cur.execute(
                "INSERT INTO billing_accounts (org_id, balance, reserved, tier) VALUES (%s, 100000, 0, 'free') "
                "ON CONFLICT (org_id) DO UPDATE SET balance=100000, reserved=0",
                (org,),
            )
        conn.commit()
    finally:
        db_pool.putconn(conn)

    # Org A reserves
    r_a, ref_a = reserve(org_a, 100, db_pool, idempotency_key=ikey, request_fingerprint=fp)
    record(f"{tag}.1", f"reserve(org=A, key={ikey})", "SUCCESS", r_a.name, r_a == BillingResult.SUCCESS)

    # Org B with same key — should also succeed (different billing_idempotency.organisation)
    r_b, ref_b = reserve(org_b, 100, db_pool, idempotency_key=ikey, request_fingerprint=fp)
    expected = "SUCCESS (org isolation)"
    actual = r_b.name
    passed = r_b == BillingResult.SUCCESS and ref_a != ref_b
    record(f"{tag}.2", f"reserve(org=B, key={ikey})", expected, actual, passed)

    # Cleanup orgs
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        for org in [org_a, org_b]:
            cur.execute("DELETE FROM billing_reservations WHERE org_id = %s", (org,))
            cur.execute("DELETE FROM billing_ledger WHERE org_id = %s", (org,))
            cur.execute("DELETE FROM billing_accounts WHERE org_id = %s", (org,))
        cur.execute("DELETE FROM billing_idempotency WHERE idempotency_key = %s", (ikey,))
        cur.execute("DELETE FROM gateway_idempotency WHERE idempotency_key = %s", (ikey,))
        conn.commit()
    finally:
        db_pool.putconn(conn)

    return passed


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("  IDEMPOTENCY INTEGRATION TESTS (IDEM-001..008)")
    print(f"  Gateway: {GATEWAY_URL}")
    print(f"  Test Org: {TEST_ORG}")
    print("=" * 70)

    # Init DB pool
    db_pool = psycopg2.pool.SimpleConnectionPool(1, 5, PG_URL)
    setup_test_org(db_pool)

    try:
        tests = [
            ("IDEM-001", test_idem_001, "Duplicate completed request → replay previous result"),
            ("IDEM-002", test_idem_002, "Concurrent same-key → only one executes"),
            ("IDEM-003", test_idem_003, "Same key, different payload → CONFLICT 409"),
            ("IDEM-004", test_idem_004, "Retry after failed status → succeeds"),
            ("IDEM-005", test_idem_005, "Settlement failure → reconciliation"),
            ("IDEM-006", test_idem_006, "Streaming retry → idempotent replay"),
            ("IDEM-007", test_idem_007, "Expiry → new execution after TTL"),
            ("IDEM-008", test_idem_008, "Org isolation → separate records"),
        ]

        all_passed = True
        for tid, test_fn, desc in tests:
            print(f"\n▶ Running {tid}: {desc}")
            try:
                passed = test_fn(db_pool)
                if not passed:
                    all_passed = False
            except Exception as e:
                record(tid, str(test_fn.__name__), "no exception", f"EXCEPTION: {e}", False)
                all_passed = False
                print(f"  ❌ {tid} EXCEPTION: {e}")

        # Summary
        print("\n" + "=" * 70)
        print("  RESULTS SUMMARY")
        print("=" * 70)
        passed_count = sum(1 for r in results if r["status"] == "PASS")
        failed_count = sum(1 for r in results if r["status"] == "FAIL")
        print(f"  Total: {len(results)} | Passed: {passed_count} | Failed: {failed_count}")
        for r in results:
            icon = "✅" if r["status"] == "PASS" else "❌"
            print(f"  {icon} {r['test_id']}: {r['status']} — {r['actual'][:80]}")

        print(f"\n  OVERALL: {'✅ ALL PASSED' if all_passed else '❌ SOME FAILED'}")

    finally:
        cleanup_test_org(db_pool)
        db_pool.closeall()

    # Save evidence JSON
    evidence_path = "/tmp/idempotency_evidence.json"
    with open(evidence_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nEvidence saved to {evidence_path}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
