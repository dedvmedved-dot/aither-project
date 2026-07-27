"""Model routing via catalog. PG-backed drain state. CHANGE-0022-C2."""
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("aither.gateway.routing")

@dataclass
class ModelEntry:
    id: str
    display_name: str
    upstream_url: str
    endpoint_type: str
    served_model_name: str
    status: str = "active"
    max_model_len: int = 4096
    tokens_per_ruble: int = 100
    tier_access: list = field(default_factory=lambda: ["free"])
    rag_support: bool = False
    stream_support: bool = True
    timeout_seconds: int = 300
    health_endpoint: str = "/health"
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "object": "model",
            "owned_by": "aither",
            "display_name": self.display_name,
            "max_model_len": self.max_model_len,
            "status": self.status,
        }


def is_model_drained(model_id: str, db_pool) -> bool:
    """Check if model is drained in PostgreSQL (authoritative cross-replica state).

    FAIL-CLOSED: when PG is unavailable, drained state is UNKNOWN → treat as drained.
    Never return False when the authoritative drain database is unreachable.
    """
    if not db_pool:
        logger.warning("is_model_drained: no PG pool — fail-closed (treated as drained)")
        return True  # fail-closed: without PG, can't verify drain state → block
    try:
        conn = db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT drained FROM model_drain_state WHERE model_id = %s",
                (model_id,),
            )
            row = cur.fetchone()
            return bool(row and row[0])
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.warning("is_model_drained PG error for %s: %s — fail-closed", model_id, e)
        return True  # fail-closed: PG error → can't verify → block


def route_model(model_id: str, catalog: list, tier: str, db_pool=None) -> tuple[Optional[ModelEntry], Optional[str], Optional[int]]:
    """Find model by ID, check tier access and drain state.

    Returns (model, error_reason, suggested_http_status).
    - (model, None, None) = success
    - (None, reason, 403) = access denied
    - (None, reason, 503) = dependency unavailable (PG down, drain unknown)
    """
    for m in catalog:
        if m.id == model_id or m.served_model_name == model_id:
            if m.status != "active":
                logger.warning("Model %s is %s", model_id, m.status)
                return None, f"model_{m.status}", 403
            # Check PG-backed drain state (cross-replica)
            try:
                drained = is_model_drained(m.id, db_pool)
            except Exception:
                logger.error("is_model_drained crashed for %s", model_id)
                return None, "drain_dependency_unavailable", 503
            if drained:
                logger.warning("Model %s is drained (PG)", model_id)
                return None, "model_drained", 403
            if tier not in m.tier_access:
                logger.warning("Model %s denied for tier %s", model_id, tier)
                return None, "tier_not_allowed", 403
            return m, None, None
    return None, "model_not_found", 403
