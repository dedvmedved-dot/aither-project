"""
Aither Gateway — Usage Records Collector.

Records request usage to PostgreSQL (usage_records table).
Also tracks daily usage in Redis for dashboard display.
"""
import logging
import psycopg2.pool

logger = logging.getLogger("gateway.usage")


def ensure_usage_table(db_pool: psycopg2.pool.SimpleConnectionPool) -> None:
    """Create usage_records table and indexes if they don't exist."""
    conn = db_pool.getconn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS usage_records (
                        id SERIAL PRIMARY KEY,
                        org_id UUID NOT NULL,
                        request_id VARCHAR(16),
                        model VARCHAR(64),
                        input_tokens INTEGER NOT NULL DEFAULT 0,
                        output_tokens INTEGER NOT NULL DEFAULT 0,
                        total_tokens INTEGER NOT NULL DEFAULT 0,
                        status VARCHAR(32) NOT NULL DEFAULT 'success',
                        latency_ms INTEGER,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                """)
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_usage_org_time"
                    " ON usage_records (org_id, created_at DESC)"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_usage_model"
                    " ON usage_records (model)"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_usage_status"
                    " ON usage_records (status)"
                )
        logger.info("Usage records table ready")
    except Exception as e:
        logger.error("Failed to create usage_records table: %s", e)
        raise
    finally:
        db_pool.putconn(conn)


def record_usage(
    db_pool: psycopg2.pool.SimpleConnectionPool,
    org_id: str,
    request_id: str,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int = 0,
    status: str = "success",
    latency_ms: int | None = None,
) -> bool:
    """
    Record a usage event in PostgreSQL.

    Returns True on success, False on error (logged).
    Non-critical — errors are logged but not raised.
    """
    try:
        conn = db_pool.getconn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO usage_records"
                        " (org_id, request_id, model, input_tokens,"
                        "  output_tokens, total_tokens, status, latency_ms)"
                        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        (org_id, request_id, model,
                         input_tokens, output_tokens, total_tokens,
                         status, latency_ms),
                    )
        finally:
            db_pool.putconn(conn)
        return True
    except Exception as e:
        logger.warning("Usage record error (non-critical): %s", e)
        return False


def get_usage_summary(
    db_pool: psycopg2.pool.SimpleConnectionPool,
    org_id: str,
) -> dict:
    """Get usage summary for an organisation."""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            # Total settled tokens from billing ledger
            cur.execute(
                "SELECT count(*), coalesce(sum(amount), 0)"
                " FROM billing_ledger"
                " WHERE org_id = %s AND operation = 'settle'",
                (org_id,),
            )
            row = cur.fetchone()
            cnt = row[0] if row else 0
            total = row[1] if row else 0

            # Recent usage stats
            cur.execute(
                "SELECT count(*), coalesce(sum(total_tokens), 0)"
                " FROM usage_records"
                " WHERE org_id = %s AND created_at >= now() - interval '24 hours'",
                (org_id,),
            )
            row2 = cur.fetchone()
            recent_cnt = row2[0] if row2 else 0
            recent_tokens = row2[1] if row2 else 0

            return {
                "org_id": org_id,
                "total_requests": cnt,
                "total_tokens": int(total or 0),
                "requests_24h": recent_cnt or 0,
                "tokens_24h": int(recent_tokens or 0),
            }
    except Exception as e:
        logger.error("Usage summary error for org=%s: %s", org_id, e)
        return {"org_id": org_id, "error": str(e)}
    finally:
        db_pool.putconn(conn)


def get_usage_stats(
    db_pool: psycopg2.pool.SimpleConnectionPool,
    org_id: str,
    days: int = 7,
) -> dict:
    """Get per-day per-model usage statistics."""
    days = min(days, 90)  # cap at 90 days
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT date(created_at) as day, model,"
                " count(*) as requests,"
                " coalesce(sum(input_tokens), 0) as input_tk,"
                " coalesce(sum(output_tokens), 0) as output_tk,"
                " coalesce(sum(total_tokens), 0) as total_tk,"
                " count(*) FILTER (WHERE status NOT IN ('success', 'blocked_egress')) as errors"
                " FROM usage_records"
                " WHERE org_id = %s AND created_at >= now() - interval %s"
                " GROUP BY day, model ORDER BY day DESC, model",
                (org_id, f"{days} days"),
            )
            rows = cur.fetchall()
            return {
                "org_id": org_id,
                "days": days,
                "stats": [
                    {
                        "day": str(r[0]),
                        "model": r[1],
                        "requests": r[2],
                        "input_tokens": int(r[3]),
                        "output_tokens": int(r[4]),
                        "total_tokens": int(r[5]),
                        "errors": r[6],
                    }
                    for r in rows
                ],
            }
    except Exception as e:
        logger.error("Usage stats error for org=%s: %s", org_id, e)
        return {"org_id": org_id, "error": str(e)}
    finally:
        db_pool.putconn(conn)


def get_billing_history(
    db_pool: psycopg2.pool.SimpleConnectionPool,
    org_id: str,
    limit: int = 20,
) -> dict:
    """Get recent billing ledger entries for an org."""
    limit = min(limit, 100)
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT amount, operation, reference, balance_after, created_at"
                " FROM billing_ledger WHERE org_id = %s"
                " ORDER BY id DESC LIMIT %s",
                (org_id, limit),
            )
            rows = cur.fetchall()
            return {
                "org_id": org_id,
                "ledger": [
                    {
                        "amount": r[0],
                        "operation": r[1],
                        "reference": r[2],
                        "balance_after": r[3],
                        "created_at": r[4].isoformat() if r[4] else None,
                    }
                    for r in rows
                ],
            }
    except Exception as e:
        logger.error("Billing history error for org=%s: %s", org_id, e)
        return {"org_id": org_id, "error": str(e)}
    finally:
        db_pool.putconn(conn)
