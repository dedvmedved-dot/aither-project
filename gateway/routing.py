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
    """Check if model is drained in PostgreSQL (authoritative cross-replica state)."""
    if not db_pool:
        return False
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
        logger.warning("is_model_drained PG error for %s: %s", model_id, e)
        return False


def route_model(model_id: str, catalog: list, tier: str, db_pool=None) -> Optional[ModelEntry]:
    """Find model by ID, check tier access and drain state."""
    for m in catalog:
        if m.id == model_id or m.served_model_name == model_id:
            if m.status != "active":
                logger.warning("Model %s is %s", model_id, m.status)
                return None
            # Check PG-backed drain state (cross-replica)
            if is_model_drained(m.id, db_pool):
                logger.warning("Model %s is drained (PG)", model_id)
                return None
            if tier not in m.tier_access:
                logger.warning("Model %s denied for tier %s", model_id, tier)
                return None
            return m
    return None
