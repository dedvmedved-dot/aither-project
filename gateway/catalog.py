"""Model Catalog — loads model registry from YAML. CHANGE-0022."""
import os, time, logging
import yaml
from dataclasses import dataclass, field
from typing import Optional
from urllib.request import Request, urlopen

logger = logging.getLogger("aither.gateway.catalog")

CATALOG_PATH = os.environ.get("CATALOG_PATH", "/app/catalog.yaml")
HEALTH_TTL = int(os.environ.get("HEALTH_TTL", "30"))

_models: list = []
_health: dict = {}
_last_load = 0

@dataclass
class ModelEntry:
    id: str
    display_name: str = ""
    description: str = ""
    upstream_url: str = ""
    endpoint_type: str = "chat_completions"
    served_model_name: str = ""
    status: str = "active"
    max_model_len: int = 4096
    tokens_per_ruble: int = 100
    tier_access: list = field(default_factory=lambda: ["free"])
    rag_support: bool = False
    stream_support: bool = True
    timeout_seconds: int = 300
    health_endpoint: str = "/health"

    def to_dict(self) -> dict:
        return {
            "id": self.id, "object": "model", "owned_by": "aither",
            "display_name": self.display_name, "max_model_len": self.max_model_len,
            "status": self.status,
        }

def load_catalog(path: str = "") -> list:
    """Load model catalog from YAML. Returns list of ModelEntry."""
    global _models, _last_load
    path = path or CATALOG_PATH
    if not os.path.exists(path):
        logger.warning("Catalog not found: %s", path)
        _models = []
        return _models
    with open(path) as f:
        data = yaml.safe_load(f)
    models_raw = data.get("models", [])
    _models = [ModelEntry(
        id=m.get("id", m.get("name", "")),
        display_name=m.get("display_name", ""),
        description=m.get("description", ""),
        upstream_url=m.get("upstream_url", m.get("backend", "")),
        endpoint_type=m.get("endpoint_type", "chat_completions"),
        served_model_name=m.get("served_model_name", ""),
        status=m.get("status", "active"),
        max_model_len=m.get("max_model_len", m.get("max_tokens", 4096)),
        tokens_per_ruble=m.get("tokens_per_ruble", 100),
        tier_access=m.get("tier_access", ["free"]),
        rag_support=m.get("rag_support", False),
        stream_support=m.get("stream_support", True),
        timeout_seconds=m.get("timeout_seconds", 300),
        health_endpoint=m.get("health_endpoint", "/health"),
    ) for m in models_raw if m.get("status") != "inactive"]
    _last_load = time.time()
    logger.info("Catalog loaded: %d models from %s", len(_models), path)
    return _models

def model_list() -> list:
    """Return public model list."""
    return _models

def resolve(model_name: str) -> Optional[ModelEntry]:
    """Find model by ID or served name."""
    for m in _models:
        if m.id == model_name or m.served_model_name == model_name:
            return m
    return None

def health_check(backend_url: str, timeout: int = 5) -> bool:
    """Check vLLM backend health."""
    global _health
    if backend_url in _health and time.time() - _health[backend_url]["last_check"] < HEALTH_TTL:
        return _health[backend_url]["alive"]
    try:
        req = Request(f"{backend_url}/health")
        resp = urlopen(req, timeout=timeout)
        alive = resp.status == 200
    except Exception:
        alive = False
    _health[backend_url] = {"last_check": time.time(), "alive": alive}
    return alive

load_catalog()
