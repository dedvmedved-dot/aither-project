"""Billing: reserve → settle → refund. CHANGE-0022."""
import uuid, logging
from typing import Optional

logger = logging.getLogger("aither.gateway.billing")

def reserve(org_id: str, estimated_tokens: int, db_pool) -> Optional[str]:
    """Reserve tokens before inference. Returns reference ID or None."""
    ref = str(uuid.uuid4())[:12]
    try:
        conn = db_pool.getconn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE billing_accounts SET reserved = reserved + %s, updated_at = NOW() "
                        "WHERE org_id = %s AND balance - reserved >= %s RETURNING org_id",
                        (estimated_tokens, org_id, estimated_tokens),
                    )
                    if cur.fetchone():
                        cur.execute(
                            "INSERT INTO billing_ledger (org_id, amount, operation, reference, balance_after, created_at) "
                            "VALUES (%s, %s, 'reserve', %s, (SELECT balance FROM billing_accounts WHERE org_id = %s), NOW())",
                            (org_id, estimated_tokens, ref, org_id),
                        )
                        return ref
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Reserve failed: %s", e)
    return None

def settle(org_id: str, ref: str, actual_tokens: int, db_pool):
    """Settle after successful inference. Deduct from balance and reserved."""
    try:
        conn = db_pool.getconn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE billing_accounts SET balance = balance - %s, reserved = reserved - %s, updated_at = NOW() "
                        "WHERE org_id = %s",
                        (actual_tokens, actual_tokens, org_id),
                    )
                    cur.execute(
                        "INSERT INTO billing_ledger (org_id, amount, operation, reference, balance_after, created_at) "
                        "VALUES (%s, %s, 'settle', %s, (SELECT balance FROM billing_accounts WHERE org_id = %s), NOW())",
                        (org_id, actual_tokens, ref, org_id),
                    )
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Settle failed: %s", e)

def refund(org_id: str, ref: str, db_pool):
    """Refund reserved tokens after error."""
    try:
        conn = db_pool.getconn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE billing_accounts SET reserved = GREATEST(reserved - 100, 0), updated_at = NOW() "
                        "WHERE org_id = %s",
                        (org_id,),
                    )
                    cur.execute(
                        "INSERT INTO billing_ledger (org_id, amount, operation, reference, balance_after, created_at) "
                        "VALUES (%s, 100, 'refund', %s, (SELECT balance FROM billing_accounts WHERE org_id = %s), NOW())",
                        (org_id, ref, org_id),
                    )
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Refund failed: %s", e)
