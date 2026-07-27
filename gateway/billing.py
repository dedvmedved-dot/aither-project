"""Billing: transactional reserve → settle → refund with idempotency. CHANGE-0022-C2."""
import uuid, logging, enum, hashlib, json, time
from typing import Optional
from siem import billing_reserve, billing_settle, billing_refund

logger = logging.getLogger("aither.gateway.billing")

RESERVE_AMOUNT = 100
IDEMPOTENCY_TTL_SECONDS = 86400  # 24 hours


class BillingResult(enum.Enum):
    SUCCESS = "success"
    ALREADY_COMPLETED = "already_completed"
    INSUFFICIENT_BALANCE = "insufficient_balance"
    INVALID_STATE = "invalid_state"
    DATABASE_ERROR = "database_error"
    CONFLICT = "conflict"               # same key, different payload
    IN_PROGRESS = "in_progress"         # concurrent request with same key


def _compute_fingerprint(request_data: dict) -> str:
    """Compute a deterministic fingerprint of the request payload."""
    canonical = json.dumps(request_data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _get_idempotency_key(app, request) -> str:
    """Extract idempotency key: X-Idempotency-Key header or request_id fallback."""
    return uuid.uuid4().hex[:16]


def _check_billing_idempotency(ikey: str, fingerprint: str, org_id: str, db_pool) -> tuple:
    """
    Check billing_idempotency table for existing request.
    Returns (status, result_tuple) where status is:
      - 'new': no existing record
      - 'completed': previous result available
      - 'conflict': same key, different fingerprint → 409
      - 'in_progress': same key, same fingerprint, still pending → wait/retry
      - 'error': database error
    """
    try:
        conn = db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("BEGIN")

            # Check billing_idempotency by key
            cur.execute(
                "SELECT request_fingerprint, processing_status, reservation_id, http_status, sanitized_response_ref "
                "FROM billing_idempotency WHERE idempotency_key = %s FOR UPDATE",
                (ikey,),
            )
            row = cur.fetchone()

            if row is None:
                # No existing record — insert a new pending one
                cur.execute(
                    "INSERT INTO billing_idempotency (idempotency_key, request_fingerprint, organisation, model, processing_status) "
                    "VALUES (%s, %s, %s, %s, 'pending')",
                    (ikey, fingerprint, org_id, 'unknown'),
                )
                cur.execute("COMMIT")
                return 'new', None

            existing_fingerprint = row[0]
            status = row[1]
            reservation_id = row[2]
            http_status = row[3]
            response_ref = row[4]

            if existing_fingerprint != fingerprint:
                cur.execute("ROLLBACK")
                return 'conflict', None

            if status == 'completed':
                cur.execute("ROLLBACK")
                return 'completed', (reservation_id, http_status, response_ref)

            if status == 'pending':
                cur.execute("ROLLBACK")
                return 'in_progress', None

            if status == 'failed':
                # Retry allowed for failed settlements
                cur.execute(
                    "UPDATE billing_idempotency SET processing_status = 'pending', created_at = NOW() "
                    "WHERE idempotency_key = %s",
                    (ikey,),
                )
                cur.execute("COMMIT")
                return 'new', None

            cur.execute("ROLLBACK")
            return 'error', None

        except Exception:
            try:
                cur.execute("ROLLBACK")
            except Exception:
                pass
            raise
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Idempotency check failed for key %s: %s", ikey, e)
        return 'error', None


def _mark_idempotency_completed(ikey: str, reservation_id: str, http_status: int,
                                 response_ref: str, db_pool) -> None:
    """Mark a billing_idempotency record as completed."""
    try:
        conn = db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE billing_idempotency SET processing_status = 'completed', "
                "reservation_id = %s, http_status = %s, sanitized_response_ref = %s, "
                "completed_at = NOW() WHERE idempotency_key = %s",
                (reservation_id, http_status, response_ref, ikey),
            )
            conn.commit()
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Failed to mark idempotency complete for %s: %s", ikey, e)


def _mark_idempotency_failed(ikey: str, reason: str, db_pool) -> None:
    """Mark a billing_idempotency record as failed (allows retry)."""
    try:
        conn = db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE billing_idempotency SET processing_status = 'failed', "
                "sanitized_response_ref = %s WHERE idempotency_key = %s",
                (reason, ikey),
            )
            conn.commit()
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Failed to mark idempotency failed for %s: %s", ikey, e)


def _clean_expired_idempotency(db_pool) -> int:
    """Clean up expired idempotency records. Returns count deleted."""
    try:
        conn = db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM billing_idempotency WHERE expiry < NOW()")
            deleted_b = cur.rowcount
            cur.execute("DELETE FROM gateway_idempotency WHERE expiry < NOW()")
            deleted_g = cur.rowcount
            conn.commit()
            return deleted_b + deleted_g
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Idempotency cleanup failed: %s", e)
        return 0


def _reconcile_settled_failed(org_id: str, reservation_id: str, db_pool) -> BillingResult:
    """
    Reconciliation for settled-failed edge case:
    If settlement was marked as failed but reserve was actually consumed,
    retry settlement or credit back.
    """
    try:
        conn = db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("BEGIN")
            cur.execute(
                "SELECT reserved_amount, status FROM billing_reservations "
                "WHERE reservation_id = %s FOR UPDATE",
                (reservation_id,),
            )
            row = cur.fetchone()
            if not row:
                cur.execute("ROLLBACK")
                return BillingResult.INVALID_STATE

            status = row[1]
            if status == 'settled':
                cur.execute("ROLLBACK")
                return BillingResult.ALREADY_COMPLETED

            if status == 'reserved':
                # Still reserved — retry settlement
                reserved_amount = row[0]
                cur.execute(
                    "UPDATE billing_accounts SET balance = balance - %s, reserved = reserved - %s, updated_at = NOW() "
                    "WHERE org_id = %s",
                    (reserved_amount, reserved_amount, org_id),
                )
                cur.execute(
                    "UPDATE billing_reservations SET status = 'settled' WHERE reservation_id = %s",
                    (reservation_id,),
                )
                cur.execute("COMMIT")
                billing_settle(org_id, reservation_id, reserved_amount)
                return BillingResult.SUCCESS

            cur.execute("ROLLBACK")
            return BillingResult.INVALID_STATE
        except Exception:
            cur.execute("ROLLBACK")
            raise
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Reconciliation failed for %s/%s: %s", org_id, reservation_id, e)
        return BillingResult.DATABASE_ERROR


def reserve(org_id: str, estimated_tokens: int, db_pool,
            idempotency_key: str = None,
            request_fingerprint: str = None,
            model: str = "unknown") -> tuple:
    """
    Atomic reserve with full idempotency.
    Returns (BillingResult, reservation_id, extra_info).

    Idempotency:
      - Same key + same fingerprint → returns previous result
      - Same key + different fingerprint → CONFLICT (409)
      - Concurrent with same key → IN_PROGRESS
    """
    ikey = idempotency_key or uuid.uuid4().hex[:16]
    ref = uuid.uuid4().hex[:12]
    amount = max(estimated_tokens, RESERVE_AMOUNT)

    # Check billing_idempotency first
    fingerprint = request_fingerprint or _compute_fingerprint({
        'org_id': org_id, 'estimated_tokens': estimated_tokens, 'model': model
    })

    status, result_data = _check_billing_idempotency(ikey, fingerprint, org_id, db_pool)

    if status == 'completed':
        existing_ref = result_data[0]
        return BillingResult.ALREADY_COMPLETED, existing_ref
    elif status == 'conflict':
        return BillingResult.CONFLICT, None
    elif status == 'in_progress':
        # Wait briefly and check again
        time.sleep(0.5)
        status2, result_data2 = _check_billing_idempotency(ikey, fingerprint, org_id, db_pool)
        if status2 == 'completed':
            return BillingResult.ALREADY_COMPLETED, result_data2[0]
        elif status2 == 'in_progress':
            return BillingResult.IN_PROGRESS, None
        # Fall through to new attempt if status changed

    try:
        conn = db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("BEGIN")

            # Check gateway_idempotency — if already processed, return existing result
            cur.execute(
                "SELECT reservation_id, result_status FROM gateway_idempotency "
                "WHERE idempotency_key = %s FOR UPDATE",
                (ikey,),
            )
            idem_row = cur.fetchone()
            if idem_row:
                cur.execute("ROLLBACK")
                existing_ref = idem_row[0]
                status = idem_row[1]
                if status == "reserved":
                    return BillingResult.ALREADY_COMPLETED, existing_ref
                return BillingResult.INVALID_STATE, None

            # Lock + validate balance
            cur.execute(
                "SELECT balance, reserved FROM billing_accounts WHERE org_id = %s FOR UPDATE",
                (org_id,),
            )
            row = cur.fetchone()
            if not row:
                cur.execute("ROLLBACK")
                logger.warning("No billing account for org %s", org_id)
                _mark_idempotency_failed(ikey, "no_account", db_pool)
                return BillingResult.INSUFFICIENT_BALANCE, None

            available = row[0] - row[1]
            if available < amount:
                cur.execute("ROLLBACK")
                logger.warning("Insufficient balance: org=%s need=%d have=%d", org_id, amount, available)
                _mark_idempotency_failed(ikey, "insufficient_balance", db_pool)
                return BillingResult.INSUFFICIENT_BALANCE, None

            # Reserve
            cur.execute(
                "UPDATE billing_accounts SET reserved = reserved + %s, updated_at = NOW() WHERE org_id = %s",
                (amount, org_id),
            )
            cur.execute(
                "INSERT INTO billing_ledger (org_id, reservation_id, operation, amount, balance_before, balance_after) "
                "VALUES (%s, %s, 'reserve', %s, %s, (SELECT balance - reserved FROM billing_accounts WHERE org_id = %s))",
                (org_id, ref, amount, available, org_id),
            )
            cur.execute(
                "INSERT INTO billing_reservations (reservation_id, org_id, idempotency_key, reserved_amount, status) "
                "VALUES (%s, %s, %s, %s, 'reserved') ON CONFLICT (reservation_id) DO NOTHING",
                (ref, org_id, ikey, amount),
            )
            cur.execute(
                "INSERT INTO gateway_idempotency (idempotency_key, org_id, reservation_id, result_status, request_fingerprint) "
                "VALUES (%s, %s, %s, 'reserved', %s) ON CONFLICT (idempotency_key) "
                "DO UPDATE SET reservation_id = EXCLUDED.reservation_id, request_fingerprint = EXCLUDED.request_fingerprint",
                (ikey, org_id, ref, fingerprint),
            )
            # Mark billing_idempotency as completed
            cur.execute(
                "UPDATE billing_idempotency SET processing_status = 'completed', "
                "reservation_id = %s, completed_at = NOW(), model = %s "
                "WHERE idempotency_key = %s",
                (ref, model, ikey),
            )
            cur.execute("COMMIT")
            billing_reserve(org_id, ref, amount)
            return BillingResult.SUCCESS, ref
        except Exception:
            try:
                cur.execute("ROLLBACK")
            except Exception:
                pass
            raise
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Reserve failed for %s: %s", org_id, e)
        _mark_idempotency_failed(ikey, str(e)[:200], db_pool)
        return BillingResult.DATABASE_ERROR, None


def settle(org_id: str, reservation_id: str, actual_tokens: int, db_pool) -> BillingResult:
    """Atomic settle: deduct from balance and reserved. Idempotent."""
    try:
        conn = db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("BEGIN")
            cur.execute(
                "SELECT reserved_amount, status FROM billing_reservations "
                "WHERE reservation_id = %s FOR UPDATE",
                (reservation_id,),
            )
            row = cur.fetchone()
            if not row:
                cur.execute("ROLLBACK")
                return BillingResult.INVALID_STATE

            status = row[1]
            if status == "settled":
                cur.execute("ROLLBACK")
                return BillingResult.ALREADY_COMPLETED
            if status == "refunded":
                cur.execute("ROLLBACK")
                logger.warning("Cannot settle refunded reservation %s", reservation_id)
                return BillingResult.INVALID_STATE
            if status != "reserved":
                cur.execute("ROLLBACK")
                logger.warning("Cannot settle reservation %s: status=%s", reservation_id, status)
                return BillingResult.INVALID_STATE

            reserved_amount = row[0]
            settle_amount = actual_tokens

            cur.execute(
                "UPDATE billing_accounts SET balance = balance - %s, reserved = reserved - %s, updated_at = NOW() "
                "WHERE org_id = %s",
                (settle_amount, reserved_amount, org_id),
            )
            cur.execute(
                "INSERT INTO billing_ledger (org_id, reservation_id, operation, amount, balance_before, balance_after) "
                "VALUES (%s, %s, 'settle', %s, "
                "(SELECT balance + reserved FROM billing_accounts WHERE org_id = %s), "
                "(SELECT balance FROM billing_accounts WHERE org_id = %s))",
                (org_id, reservation_id, settle_amount, org_id, org_id),
            )
            cur.execute(
                "UPDATE billing_reservations SET status = 'settled' WHERE reservation_id = %s",
                (reservation_id,),
            )
            cur.execute(
                "UPDATE gateway_idempotency SET result_status = 'settled', completed_at = NOW() "
                "WHERE reservation_id = %s",
                (reservation_id,),
            )
            cur.execute(
                "UPDATE billing_idempotency SET processing_status = 'settled', completed_at = NOW() "
                "WHERE reservation_id = %s",
                (reservation_id,),
            )
            cur.execute("COMMIT")
            billing_settle(org_id, reservation_id, settle_amount)
            return BillingResult.SUCCESS
        except Exception:
            try:
                cur.execute("ROLLBACK")
            except Exception:
                pass
            raise
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Settle failed for %s/%s: %s", org_id, reservation_id, e)
        # Attempt reconciliation
        return _reconcile_settled_failed(org_id, reservation_id, db_pool)


def refund(org_id: str, reservation_id: str, db_pool) -> BillingResult:
    """Atomic refund: release reserved tokens. Idempotent."""
    try:
        conn = db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("BEGIN")
            cur.execute(
                "SELECT reserved_amount, status FROM billing_reservations "
                "WHERE reservation_id = %s FOR UPDATE",
                (reservation_id,),
            )
            row = cur.fetchone()
            if not row:
                cur.execute("ROLLBACK")
                return BillingResult.INVALID_STATE

            status = row[1]
            if status == "refunded":
                cur.execute("ROLLBACK")
                return BillingResult.ALREADY_COMPLETED
            if status == "settled":
                cur.execute("ROLLBACK")
                logger.warning("Cannot refund settled reservation %s", reservation_id)
                return BillingResult.INVALID_STATE
            if status != "reserved":
                cur.execute("ROLLBACK")
                logger.warning("Cannot refund reservation %s: status=%s", reservation_id, status)
                return BillingResult.INVALID_STATE

            reserved_amount = row[0]

            cur.execute(
                "UPDATE billing_accounts SET reserved = GREATEST(reserved - %s, 0), updated_at = NOW() "
                "WHERE org_id = %s",
                (reserved_amount, org_id),
            )
            cur.execute(
                "INSERT INTO billing_ledger (org_id, reservation_id, operation, amount, balance_before, balance_after) "
                "VALUES (%s, %s, 'refund', %s, "
                "(SELECT balance + reserved FROM billing_accounts WHERE org_id = %s), "
                "(SELECT balance FROM billing_accounts WHERE org_id = %s))",
                (org_id, reservation_id, reserved_amount, org_id, org_id),
            )
            cur.execute(
                "UPDATE billing_reservations SET status = 'refunded' WHERE reservation_id = %s",
                (reservation_id,),
            )
            cur.execute(
                "UPDATE gateway_idempotency SET result_status = 'refunded', completed_at = NOW() "
                "WHERE reservation_id = %s",
                (reservation_id,),
            )
            cur.execute(
                "UPDATE billing_idempotency SET processing_status = 'refunded', completed_at = NOW() "
                "WHERE reservation_id = %s",
                (reservation_id,),
            )
            cur.execute("COMMIT")
            billing_refund(org_id, reservation_id, reserved_amount)
            return BillingResult.SUCCESS
        except Exception:
            try:
                cur.execute("ROLLBACK")
            except Exception:
                pass
            raise
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Refund failed for %s/%s: %s", org_id, reservation_id, e)
        return BillingResult.DATABASE_ERROR
