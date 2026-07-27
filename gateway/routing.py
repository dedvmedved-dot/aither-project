"""Model routing via catalog.yaml. CHANGE-0022."""
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("aither.gateway.routing")

@dataclass
class ModelEntry:
    id: str
    display_name: str
    upstream_url: str
    endpoint_type: str  # "chat_completions" | "completions"
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

def route_model(model_id: str, catalog: list, tier: str) -> Optional[ModelEntry]:
    """Find model by ID, check tier access."""
    for m in catalog:
        if m.id == model_id or m.served_model_name == model_id:
            if m.status != "active":
                logger.warning("Model %s is %s", model_id, m.status)
                return None
            if tier not in m.tier_access:
                logger.warning("Model %s denied for tier %s", model_id, tier)
                return None
            return m
    return None
