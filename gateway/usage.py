"""Usage collector: records token usage. CHANGE-0022."""
import logging

logger = logging.getLogger("aither.gateway.usage")

def record_usage(org_id: str, request_id: str, model: str, prompt_tokens: int,
                 completion_tokens: int, status: int, operation: str, db_pool):
    """Record usage to PostgreSQL."""
    if not prompt_tokens and not completion_tokens:
        return
    total = prompt_tokens + completion_tokens
    try:
        conn = db_pool.getconn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO usage_records (org_id, request_id, model, prompt_tokens, "
                        "completion_tokens, total_tokens, status_code, operation, created_at) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())",
                        (org_id, request_id, model, prompt_tokens, completion_tokens, total, status, operation),
                    )
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("Usage record failed: %s", e)
