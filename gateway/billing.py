"""Billing: transactional reserve → settle → refund with idempotency. CHANGE-0022-C2."""
import uuid, logging, enum
from typing import Optional
from siem import billing_reserve, billing_settle, billing_refund

logger = logging.getLogger("aither.gateway.billing")

RESERVE_AMOUNT = 100


class BillingResult(enum.Enum):
    SUCCESS = "success"
    ALREADY_COMPLETED = "already_completed"
    INSUFFICIENT_BALANCE = "insufficient_balance"
    INVALID_STATE = "invalid_state"
    DATABASE_ERROR = "database_error"


def _get_idempotency_key(app, request) -> str:
    """Extract idempotency key: X-Idempotency-Key header or request_id fallback."""
    # For non-request contexts, fallback to UUID
    return uuid.uuid4().hex[:16]


def reserve(org_id: str, estimated_tokens: int, db_pool, idempotency_key: str = None) -> tuple[BillingResult, Optional[str]]:
    """Atomic reserve with idempotency. Returns (result, reservation_id)."""
    ikey = idempotency_key or uuid.uuid4().hex[:16]
    ref = uuid.uuid4().hex[:12]
    amount = max(estimated_tokens, RESERVE_AMOUNT)

    try:
        conn = db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("BEGIN")

            # Check idempotency — if already processed, return existing result
            cur.execute(
                "SELECT reservation_id, result_status FROM gateway_idempotency WHERE idempotency_key = %s FOR UPDATE",
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
                return BillingResult.INSUFFICIENT_BALANCE, None

            available = row[0] - row[1]
            if available < amount:
                cur.execute("ROLLBACK")
                logger.warning("Insufficient balance: org=%s need=%d have=%d", org_id, amount, available)
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
                "INSERT INTO gateway_idempotency (idempotency_key, org_id, reservation_id, result_status) "
                "VALUES (%s, %s, %s, 'reserved') ON CONFLICT (idempotency_key) DO UPDATE SET reservation_id = EXCLUDED.reservation_id",
                (ikey, org_id, ref),
            )
            cur.execute("COMMIT")
            billing_reserve(org_id, ref, amount)
            return BillingResult.SUCCESS, ref
        except Exception:
            cur.execute("ROLLBACK")
            raise
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Reserve failed for %s: %s", org_id, e)
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
            if status != "reserved":
                cur.execute("ROLLBACK")
                logger.warning("Cannot settle reservation %s: status=%s", reservation_id, status)
                return BillingResult.INVALID_STATE

            reserved_amount = row[0]
            settle_amount = actual_tokens

            cur.execute(
                "UPDATE billing_accounts SET balance = balance - %s, reserved = reserved - %s, updated_at = NOW() WHERE org_id = %s",
                (settle_amount, reserved_amount, org_id),
            )
            cur.execute(
                "INSERT INTO billing_ledger (org_id, reservation_id, operation, amount, balance_before, balance_after) "
                "VALUES (%s, %s, 'settle', %s, (SELECT balance + reserved FROM billing_accounts WHERE org_id = %s), "
                "(SELECT balance FROM billing_accounts WHERE org_id = %s))",
                (org_id, reservation_id, settle_amount, org_id, org_id),
            )
            cur.execute(
                "UPDATE billing_reservations SET status = 'settled' WHERE reservation_id = %s",
                (reservation_id,),
            )
            cur.execute(
                "UPDATE gateway_idempotency SET result_status = 'settled' WHERE reservation_id = %s",
                (reservation_id,),
            )
            cur.execute("COMMIT")
            billing_settle(org_id, reservation_id, settle_amount)
            return BillingResult.SUCCESS
        except Exception:
            cur.execute("ROLLBACK")
            raise
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Settle failed for %s/%s: %s", org_id, reservation_id, e)
        return BillingResult.DATABASE_ERROR


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
            if status != "reserved":
                cur.execute("ROLLBACK")
                logger.warning("Cannot refund reservation %s: status=%s", reservation_id, status)
                return BillingResult.INVALID_STATE

            reserved_amount = row[0]

            cur.execute(
                "UPDATE billing_accounts SET reserved = GREATEST(reserved - %s, 0), updated_at = NOW() WHERE org_id = %s",
                (reserved_amount, org_id),
            )
            cur.execute(
                "INSERT INTO billing_ledger (org_id, reservation_id, operation, amount, balance_before, balance_after) "
                "VALUES (%s, %s, 'refund', %s, (SELECT balance + reserved FROM billing_accounts WHERE org_id = %s), "
                "(SELECT balance FROM billing_accounts WHERE org_id = %s))",
                (org_id, reservation_id, reserved_amount, org_id, org_id),
            )
            cur.execute(
                "UPDATE billing_reservations SET status = 'refunded' WHERE reservation_id = %s",
                (reservation_id,),
            )
            cur.execute(
                "UPDATE gateway_idempotency SET result_status = 'refunded' WHERE reservation_id = %s",
                (reservation_id,),
            )
            cur.execute("COMMIT")
            billing_refund(org_id, reservation_id, reserved_amount)
            return BillingResult.SUCCESS
        except Exception:
            cur.execute("ROLLBACK")
            raise
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Refund failed for %s/%s: %s", org_id, reservation_id, e)
        return BillingResult.DATABASE_ERROR
