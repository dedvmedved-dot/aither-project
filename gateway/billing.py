"""Billing: transactional reserve → settle → refund with org-scoped idempotency. CHANGE-0022-C3.

Key changes from C2:
  - Identity scope: (org_id, idempotency_key) — NOT global key alone
  - UNIQUE (organisation, idempotency_key) in billing_idempotency table
  - State machine: pending → inference_started → settlement_pending → completed | failed | expired
  - completed ONLY after: inference done + egress security passed + settle SUCCESS + replay result saved
  - NEVER set completed during reserve()
  - Replay: same org+key+fingerprint → return original HTTP status + original response
  - Settlement: check settle_result and refund_result. DATABASE_ERROR must NOT return normal success.
"""
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
    CONFLICT = "conflict"               # same org+key, different fingerprint
    IN_PROGRESS = "in_progress"         # concurrent request with same org+key
    SETTLE_FAILED = "settle_failed"


def _compute_fingerprint(request_data: dict) -> str:
    """Compute a deterministic fingerprint of the request payload."""
    canonical = json.dumps(request_data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


# ── State machine ────────────────────────────────────────────────────────

# Valid state transitions for billing_idempotency.processing_status
# pending → inference_started → settlement_pending → completed | failed | expired
VALID_TRANSITIONS = {
    'pending': {'inference_started', 'failed', 'expired'},
    'inference_started': {'settlement_pending', 'failed', 'expired'},
    'settlement_pending': {'completed', 'failed', 'expired'},
    'completed': set(),        # terminal
    'failed': {'pending'},     # retry resets to pending
    'expired': set(),          # terminal
}


def _transition_status(cur, ikey: str, org_id: str, new_status: str) -> bool:
    """Transition processing_status with validation. Returns True if transition was made."""
    cur.execute(
        "SELECT processing_status FROM billing_idempotency "
        "WHERE idempotency_key = %s AND organisation = %s FOR UPDATE",
        (ikey, org_id),
    )
    row = cur.fetchone()
    if not row:
        return False
    current = row[0]
    allowed = VALID_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        logger.warning(
            "Invalid state transition: %s → %s for key=%s org=%s",
            current, new_status, ikey, org_id,
        )
        return False
    cur.execute(
        "UPDATE billing_idempotency SET processing_status = %s "
        "WHERE idempotency_key = %s AND organisation = %s",
        (new_status, ikey, org_id),
    )
    return True


# ── Core idempotency check (org-scoped) ──────────────────────────────────

def _check_billing_idempotency(ikey: str, fingerprint: str, org_id: str, db_pool) -> tuple:
    """
    Check billing_idempotency by (organisation, idempotency_key) — org-scoped.

    Returns (status, result_tuple) where status is:
      - 'new': no existing record → caller should create one and proceed
      - 'completed': previous result available → replay
      - 'conflict': same org+key, different fingerprint → 409
      - 'in_progress': same org+key+fingerprint, still processing → wait/retry
      - 'failed': same org+key+fingerprint, previous failure → allow retry
      - 'error': database error
    """
    try:
        conn = db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("BEGIN")

            # Org-scoped lookup: (organisation, idempotency_key)
            cur.execute(
                "SELECT request_fingerprint, processing_status, reservation_id, "
                "http_status, sanitized_response_ref, settle_result, refund_result "
                "FROM billing_idempotency "
                "WHERE organisation = %s AND idempotency_key = %s FOR UPDATE",
                (org_id, ikey),
            )
            row = cur.fetchone()

            if row is None:
                # No existing record — caller will INSERT 'pending'
                cur.execute("ROLLBACK")
                return 'new', None

            existing_fingerprint = row[0]
            status = row[1]
            reservation_id = row[2]
            http_status = row[3]
            response_ref = row[4]
            settle_result = row[5]
            refund_result = row[6]

            if existing_fingerprint != fingerprint:
                cur.execute("ROLLBACK")
                return 'conflict', None

            if status == 'completed':
                cur.execute("ROLLBACK")
                return 'completed', (reservation_id, http_status, response_ref, settle_result, refund_result)

            if status in ('pending', 'inference_started', 'settlement_pending'):
                cur.execute("ROLLBACK")
                return 'in_progress', None

            if status == 'failed':
                # Retry allowed for failed — reset to pending
                cur.execute(
                    "UPDATE billing_idempotency SET processing_status = 'pending', "
                    "created_at = NOW(), reservation_id = NULL, http_status = NULL, "
                    "sanitized_response_ref = NULL, settle_result = NULL, refund_result = NULL "
                    "WHERE organisation = %s AND idempotency_key = %s",
                    (org_id, ikey),
                )
                cur.execute("COMMIT")
                return 'new', None

            if status == 'expired':
                cur.execute(
                    "DELETE FROM billing_idempotency WHERE organisation = %s AND idempotency_key = %s",
                    (org_id, ikey),
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
        logger.error("Idempotency check failed for org=%s key=%s: %s", org_id, ikey, e)
        return 'error', None


# ── Idempotency lifecycle helpers ────────────────────────────────────────

def _insert_idempotency_pending(ikey: str, fingerprint: str, org_id: str,
                                 model: str, db_pool) -> bool:
    """Insert a new 'pending' billing_idempotency record. Returns True on success."""
    try:
        conn = db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO billing_idempotency "
                "(idempotency_key, request_fingerprint, organisation, model, processing_status) "
                "VALUES (%s, %s, %s, %s, 'pending') "
                "ON CONFLICT (organisation, idempotency_key) DO NOTHING",
                (ikey, fingerprint, org_id, model),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Failed to insert idempotency pending for org=%s key=%s: %s", org_id, ikey, e)
        return False


def _mark_idempotency_inference_started(ikey: str, org_id: str, db_pool) -> None:
    """Transition: pending → inference_started."""
    try:
        conn = db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("BEGIN")
            _transition_status(cur, ikey, org_id, 'inference_started')
            conn.commit()
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Failed to mark inference_started for org=%s key=%s: %s", org_id, ikey, e)


def _mark_idempotency_settlement_pending(ikey: str, org_id: str, db_pool) -> None:
    """Transition: inference_started → settlement_pending."""
    try:
        conn = db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("BEGIN")
            _transition_status(cur, ikey, org_id, 'settlement_pending')
            conn.commit()
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Failed to mark settlement_pending for org=%s key=%s: %s", org_id, ikey, e)


def _mark_idempotency_completed(ikey: str, org_id: str, reservation_id: str,
                                 http_status: int, response_ref: str,
                                 settle_result: str, db_pool) -> None:
    """
    Mark billing_idempotency as completed.
    ONLY called after: inference done + egress security passed + settle SUCCESS + replay result saved.
    """
    try:
        conn = db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("BEGIN")
            cur.execute(
                "UPDATE billing_idempotency SET processing_status = 'completed', "
                "reservation_id = %s, http_status = %s, sanitized_response_ref = %s, "
                "settle_result = %s, completed_at = NOW() "
                "WHERE organisation = %s AND idempotency_key = %s",
                (reservation_id, http_status, response_ref, settle_result,
                 org_id, ikey),
            )
            conn.commit()
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Failed to mark idempotency complete for org=%s key=%s: %s", org_id, ikey, e)


def _mark_idempotency_failed(ikey: str, org_id: str, reason: str, db_pool) -> None:
    """Mark a billing_idempotency record as failed (allows retry)."""
    try:
        conn = db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE billing_idempotency SET processing_status = 'failed', "
                "sanitized_response_ref = %s WHERE organisation = %s AND idempotency_key = %s",
                (reason, org_id, ikey),
            )
            conn.commit()
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Failed to mark idempotency failed for org=%s key=%s: %s", org_id, ikey, e)


def _save_replay_result(ikey: str, org_id: str, reservation_id: str,
                         http_status: int, response_ref: str,
                         settle_result: str, db_pool) -> None:
    """Save replay result for completed idempotency record (for later replay)."""
    try:
        conn = db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE billing_idempotency SET reservation_id = %s, "
                "http_status = %s, sanitized_response_ref = %s, settle_result = %s "
                "WHERE organisation = %s AND idempotency_key = %s",
                (reservation_id, http_status, response_ref, settle_result,
                 org_id, ikey),
            )
            conn.commit()
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Failed to save replay for org=%s key=%s: %s", org_id, ikey, e)


def get_replay_response(ikey: str, org_id: str, db_pool) -> tuple:
    """Get original HTTP response for idempotent replay.

    Returns (http_status, content_type, body, settle_result) or None.
    Caller MUST verify settle_result != DATABASE_ERROR before returning.
    """
    try:
        conn = db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT http_status, sanitized_response_ref, settle_result "
                "FROM billing_idempotency "
                "WHERE organisation = %s AND idempotency_key = %s",
                (org_id, ikey),
            )
            row = cur.fetchone()
            if row:
                http_status = row[0]
                response_ref = row[1]
                settle_result = row[2]
                if settle_result == "DATABASE_ERROR":
                    return http_status, "application/json", "", "DATABASE_ERROR"
                if response_ref:
                    try:
                        body = json.loads(response_ref) if isinstance(response_ref, str) else response_ref
                        return http_status, "application/json", body, settle_result
                    except (json.JSONDecodeError, TypeError):
                        return http_status, "text/plain", str(response_ref), settle_result
                return http_status, "application/json", {}, settle_result
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Replay response fetch failed: %s", e)
        return None


# ── Expiry cleanup ───────────────────────────────────────────────────────

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


# ── Reconciliation ───────────────────────────────────────────────────────

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


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC API: reserve / settle / refund
# ═══════════════════════════════════════════════════════════════════════════

def reserve(org_id: str, estimated_tokens: int, db_pool,
            idempotency_key: str = None,
            request_fingerprint: str = None,
            model: str = "unknown") -> tuple:
    """
    Atomic reserve with org-scoped idempotency.

    Returns (BillingResult, reservation_id, extra_info).

    Idempotency (org-scoped):
      - same org + same key + same fingerprint → returns previous result
      - same org + same key + different fingerprint → CONFLICT (409)
      - different org + same key → independent request
      - DATABASE_ERROR must NOT return normal success

    State machine:
      pending → reserve() succeeds → transitions to inference_started outside
    """
    ikey = idempotency_key or uuid.uuid4().hex[:16]
    ref = uuid.uuid4().hex[:12]
    amount = max(estimated_tokens, RESERVE_AMOUNT)

    # Compute fingerprint
    fingerprint = request_fingerprint or _compute_fingerprint({
        'org_id': org_id, 'estimated_tokens': estimated_tokens, 'model': model
    })

    # 1. Check billing_idempotency (org-scoped)
    status, result_data = _check_billing_idempotency(ikey, fingerprint, org_id, db_pool)

    if status == 'completed':
        # Replay: return original HTTP status + original response
        reservation_id = result_data[0]
        http_status = result_data[1]
        response_ref = result_data[2]
        settle_result = result_data[3]
        refund_result = result_data[4]
        # DATABASE_ERROR settle_result must NOT return normal success
        if settle_result == 'DATABASE_ERROR':
            return BillingResult.DATABASE_ERROR, None
        return BillingResult.ALREADY_COMPLETED, reservation_id

    elif status == 'conflict':
        return BillingResult.CONFLICT, None

    elif status == 'in_progress':
        # Wait briefly and check again
        time.sleep(0.5)
        status2, result_data2 = _check_billing_idempotency(ikey, fingerprint, org_id, db_pool)
        if status2 == 'completed':
            reservation_id = result_data2[0]
            settle_result = result_data2[3]
            if settle_result == 'DATABASE_ERROR':
                return BillingResult.DATABASE_ERROR, None
            return BillingResult.ALREADY_COMPLETED, reservation_id
        elif status2 == 'in_progress':
            return BillingResult.IN_PROGRESS, None
        # Fall through to new attempt

    elif status == 'error':
        return BillingResult.DATABASE_ERROR, None

    # status == 'new' — proceed

    # 2. Insert pending record (will be transitioned later)
    if not _insert_idempotency_pending(ikey, fingerprint, org_id, model, db_pool):
        # Already exists (race) — check again
        status2, result_data2 = _check_billing_idempotency(ikey, fingerprint, org_id, db_pool)
        if status2 == 'completed':
            return BillingResult.ALREADY_COMPLETED, result_data2[0]
        elif status2 == 'conflict':
            return BillingResult.CONFLICT, None
        elif status2 == 'in_progress':
            return BillingResult.IN_PROGRESS, None
        return BillingResult.DATABASE_ERROR, None

    try:
        conn = db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("BEGIN")

            # Check gateway_idempotency (org-scoped) — if already processed, return existing result
            cur.execute(
                "SELECT reservation_id, result_status FROM gateway_idempotency "
                "WHERE org_id = %s AND idempotency_key = %s FOR UPDATE",
                (org_id, ikey),
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
                _mark_idempotency_failed(ikey, org_id, "no_account", db_pool)
                return BillingResult.INSUFFICIENT_BALANCE, None

            available = row[0] - row[1]
            if available < amount:
                cur.execute("ROLLBACK")
                logger.warning("Insufficient balance: org=%s need=%d have=%d", org_id, amount, available)
                _mark_idempotency_failed(ikey, org_id, "insufficient_balance", db_pool)
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

            # Transition: pending → inference_started (NOT completed!)
            cur.execute(
                "UPDATE billing_idempotency SET processing_status = 'inference_started', "
                "reservation_id = %s, model = %s "
                "WHERE organisation = %s AND idempotency_key = %s",
                (ref, model, org_id, ikey),
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
        _mark_idempotency_failed(ikey, org_id, str(e)[:200], db_pool)
        return BillingResult.DATABASE_ERROR, None


def settle(org_id: str, reservation_id: str, actual_tokens: int, db_pool,
           idempotency_key: Optional[str] = None) -> BillingResult:
    """
    Atomic settle: deduct from balance and reserved. Idempotent.

    Returns BillingResult — check settle_result for DATABASE_ERROR.
    DATABASE_ERROR must NOT be treated as normal success.
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


# ── Settlement result helpers for Gateway ────────────────────────────────

def settle_and_complete(org_id: str, reservation_id: str, actual_tokens: int,
                         db_pool, ikey: Optional[str] = None,
                         response_data: Optional[dict] = None) -> tuple:
    """
    Settle + mark idempotency as completed (for non-streaming path).

    Returns (BillingResult, settle_result_str).
    Caller MUST check for DATABASE_ERROR — do NOT return normal success on DB error.
    """
    # Transition to settlement_pending
    if ikey:
        _mark_idempotency_settlement_pending(ikey, org_id, db_pool)

    result = settle(org_id, reservation_id, actual_tokens, db_pool)

    if result == BillingResult.SUCCESS:
        # Save replay result, then mark completed
        if ikey and response_data:
            response_ref = json.dumps(response_data, ensure_ascii=False, default=str)
            _save_replay_result(ikey, org_id, reservation_id, 200, response_ref,
                                'SUCCESS', db_pool)
        if ikey:
            response_ref_str = json.dumps(response_data, ensure_ascii=False, default=str) if response_data else ''
            _mark_idempotency_completed(ikey, org_id, reservation_id, 200,
                                         response_ref_str, 'SUCCESS', db_pool)
        return result, 'SUCCESS'

    elif result == BillingResult.ALREADY_COMPLETED:
        if ikey:
            _mark_idempotency_completed(ikey, org_id, reservation_id, 200,
                                         '', 'ALREADY_COMPLETED', db_pool)
        return result, 'ALREADY_COMPLETED'

    elif result == BillingResult.DATABASE_ERROR:
        if ikey:
            _mark_idempotency_failed(ikey, org_id, 'DATABASE_ERROR', db_pool)
        return result, 'DATABASE_ERROR'

    else:
        if ikey:
            _mark_idempotency_failed(ikey, org_id, result.name, db_pool)
        return result, result.name


def settle_and_complete_stream(org_id: str, reservation_id: str, actual_tokens: int,
                                db_pool, ikey: Optional[str] = None) -> tuple:
    """
    Settle + mark idempotency as completed (for streaming path).
    Returns (BillingResult, settle_result_str).
    """
    # Transition to settlement_pending
    if ikey:
        _mark_idempotency_settlement_pending(ikey, org_id, db_pool)

    result = settle(org_id, reservation_id, actual_tokens, db_pool)

    if result == BillingResult.SUCCESS:
        if ikey:
            _mark_idempotency_completed(ikey, org_id, reservation_id, 200,
                                         '', 'SUCCESS', db_pool)
        return result, 'SUCCESS'

    elif result == BillingResult.ALREADY_COMPLETED:
        if ikey:
            _mark_idempotency_completed(ikey, org_id, reservation_id, 200,
                                         '', 'ALREADY_COMPLETED', db_pool)
        return result, 'ALREADY_COMPLETED'

    elif result == BillingResult.DATABASE_ERROR:
        if ikey:
            _mark_idempotency_failed(ikey, org_id, 'DATABASE_ERROR', db_pool)
        return result, 'DATABASE_ERROR'

    else:
        if ikey:
            _mark_idempotency_failed(ikey, org_id, result.name, db_pool)
        return result, result.name
