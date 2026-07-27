"""Billing: transactional reserve → settle → refund with idempotency. CHANGE-0022-C2."""
import uuid, logging
from typing import Optional
from siem import billing_reserve, billing_settle, billing_refund

logger = logging.getLogger("aither.gateway.billing")

RESERVE_AMOUNT = 100  # default estimated token cost for reserve


def reserve(org_id: str, estimated_tokens: int, db_pool) -> Optional[str]:
    """Atomic reserve. Returns reservation_id or None if insufficient balance."""
    ref = str(uuid.uuid4())[:12]
    amount = max(estimated_tokens, RESERVE_AMOUNT)
    try:
        conn = db_pool.getconn()
        try:
            cur = conn.cursor()
            # Transactional: lock + validate + reserve
            cur.execute("BEGIN")
            cur.execute(
                "SELECT balance, reserved FROM billing_accounts WHERE org_id = %s FOR UPDATE",
                (org_id,),
            )
            row = cur.fetchone()
            if not row:
                cur.execute(
                    "INSERT INTO billing_accounts (org_id, balance, reserved, tier) VALUES (%s, 1000000, 0, 'free')",
                    (org_id,),
                )
                available = 1000000
            else:
                available = row[0] - row[1]

            if available < amount:
                cur.execute("ROLLBACK")
                logger.warning("Insufficient balance for %s: need=%d have=%d", org_id, amount, available)
                return None

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
                "VALUES (%s, %s, %s, %s, 'reserved') ON CONFLICT DO NOTHING",
                (ref, org_id, ref, amount),
            )
            cur.execute("COMMIT")
            billing_reserve(org_id, ref, amount)
            return ref
        except Exception:
            cur.execute("ROLLBACK")
            raise
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Reserve failed for %s: %s", org_id, e)
        return None


def settle(org_id: str, reservation_id: str, actual_tokens: int, db_pool):
    """Atomic settle: deduct from balance and reserved."""
    try:
        conn = db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("BEGIN")
            # Lock reservation row
            cur.execute(
                "SELECT reserved_amount, status FROM billing_reservations "
                "WHERE reservation_id = %s FOR UPDATE",
                (reservation_id,),
            )
            row = cur.fetchone()
            if not row or row[1] != "reserved":
                cur.execute("ROLLBACK")
                logger.warning("Cannot settle reservation %s: status=%s", reservation_id, row[1] if row else "not_found")
                return

            reserved_amount = row[0]
            settle_amount = actual_tokens  # charge actual tokens used

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
            cur.execute("COMMIT")
            billing_settle(org_id, reservation_id, settle_amount)
        except Exception:
            cur.execute("ROLLBACK")
            raise
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Settle failed for %s/%s: %s", org_id, reservation_id, e)


def refund(org_id: str, reservation_id: str, db_pool):
    """Atomic refund: release reserved tokens back."""
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
            if not row or row[1] != "reserved":
                cur.execute("ROLLBACK")
                logger.warning("Cannot refund reservation %s: status=%s", reservation_id, row[1] if row else "not_found")
                return

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
            cur.execute("COMMIT")
            billing_refund(org_id, reservation_id, reserved_amount)
        except Exception:
            cur.execute("ROLLBACK")
            raise
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Refund failed for %s/%s: %s", org_id, reservation_id, e)
