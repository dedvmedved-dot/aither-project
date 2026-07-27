"""Billing integration tests — real PostgreSQL."""
import os, sys, uuid, time, threading
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import psycopg2
import psycopg2.pool

TEST_ORG = f"test-billing-{uuid.uuid4().hex[:8]}"
PG_URL = os.environ.get("PG_URL", "postgresql://postgres@localhost:5432/aither")

@pytest.fixture(scope="module")
def db_pool():
    """Create a test DB pool."""
    pool = psycopg2.pool.SimpleConnectionPool(1, 3, PG_URL)
    # Create test org with balance
    conn = pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO billing_accounts (org_id, balance, reserved, tier) VALUES (%s, 10000, 0, 'free') "
            "ON CONFLICT (org_id) DO UPDATE SET balance=10000, reserved=0",
            (TEST_ORG,)
        )
        conn.commit()
    finally:
        pool.putconn(conn)
    yield pool
    # Cleanup
    conn = pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM billing_reservations WHERE org_id = %s", (TEST_ORG,))
        cur.execute("DELETE FROM billing_ledger WHERE org_id = %s", (TEST_ORG,))
        cur.execute("DELETE FROM gateway_idempotency WHERE org_id = %s", (TEST_ORG,))
        cur.execute("DELETE FROM billing_accounts WHERE org_id = %s", (TEST_ORG,))
        conn.commit()
    finally:
        pool.putconn(conn)
    pool.closeall()

def test_reserve_success(db_pool):
    from billing import reserve, BillingResult
    result, ref = reserve(TEST_ORG, 100, db_pool, f"idem-{uuid.uuid4().hex[:8]}")
    assert result == BillingResult.SUCCESS
    assert ref is not None
    assert len(ref) == 12

def test_reserve_insufficient_balance(db_pool):
    from billing import reserve, BillingResult
    # Reserve more than available
    result, ref = reserve(TEST_ORG, 99999, db_pool, f"idem-big-{uuid.uuid4().hex[:8]}")
    assert result == BillingResult.INSUFFICIENT_BALANCE
    assert ref is None

def test_reserve_duplicate_idempotency(db_pool):
    from billing import reserve, BillingResult
    ikey = f"dup-{uuid.uuid4().hex[:8]}"
    r1, ref1 = reserve(TEST_ORG, 100, db_pool, ikey)
    assert r1 == BillingResult.SUCCESS
    r2, ref2 = reserve(TEST_ORG, 100, db_pool, ikey)
    assert r2 == BillingResult.ALREADY_COMPLETED
    assert ref2 == ref1

def test_settle_success(db_pool):
    from billing import reserve, settle, BillingResult
    ikey = f"settle-{uuid.uuid4().hex[:8]}"
    result, ref = reserve(TEST_ORG, 100, db_pool, ikey)
    assert result == BillingResult.SUCCESS
    sr = settle(TEST_ORG, ref, 50, db_pool)
    assert sr == BillingResult.SUCCESS

def test_settle_double_denied(db_pool):
    from billing import reserve, settle, BillingResult
    ikey = f"dsettle-{uuid.uuid4().hex[:8]}"
    _, ref = reserve(TEST_ORG, 100, db_pool, ikey)
    sr1 = settle(TEST_ORG, ref, 50, db_pool)
    assert sr1 == BillingResult.SUCCESS
    sr2 = settle(TEST_ORG, ref, 50, db_pool)
    assert sr2 == BillingResult.ALREADY_COMPLETED

def test_refund_success(db_pool):
    from billing import reserve, refund, BillingResult
    ikey = f"refund-{uuid.uuid4().hex[:8]}"
    _, ref = reserve(TEST_ORG, 100, db_pool, ikey)
    rr = refund(TEST_ORG, ref, db_pool)
    assert rr == BillingResult.SUCCESS

def test_refund_double_denied(db_pool):
    from billing import reserve, refund, BillingResult
    ikey = f"drefund-{uuid.uuid4().hex[:8]}"
    _, ref = reserve(TEST_ORG, 100, db_pool, ikey)
    rr1 = refund(TEST_ORG, ref, db_pool)
    assert rr1 == BillingResult.SUCCESS
    rr2 = refund(TEST_ORG, ref, db_pool)
    assert rr2 == BillingResult.ALREADY_COMPLETED

def test_settle_after_refund_denied(db_pool):
    from billing import reserve, settle, refund, BillingResult
    ikey = f"sar-{uuid.uuid4().hex[:8]}"
    _, ref = reserve(TEST_ORG, 100, db_pool, ikey)
    refund(TEST_ORG, ref, db_pool)
    sr = settle(TEST_ORG, ref, 50, db_pool)
    assert sr == BillingResult.INVALID_STATE

def test_ledger_balance_consistency(db_pool):
    """Check that balance + reserved = original after series of ops."""
    from billing import reserve, settle, refund, BillingResult
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT balance, reserved FROM billing_accounts WHERE org_id = %s", (TEST_ORG,))
        bal_before, res_before = cur.fetchone()
        total_before = bal_before + res_before

        ikey = f"ledger-{uuid.uuid4().hex[:8]}"
        _, ref = reserve(TEST_ORG, 200, db_pool, ikey)
        settle(TEST_ORG, ref, 150, db_pool)

        cur.execute("SELECT balance, reserved FROM billing_accounts WHERE org_id = %s", (TEST_ORG,))
        bal_after, res_after = cur.fetchone()
        total_after = bal_after + res_after
        # After settle: balance should decrease by settle amount, reserved should return
        assert bal_after == bal_before - 150
        assert res_after == res_before
    finally:
        db_pool.putconn(conn)
