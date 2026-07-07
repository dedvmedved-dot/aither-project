"""Model Catalog — loads model registry and resolves model→backend mappings."""
import os
import yaml
import json
import time
from urllib.request import Request, urlopen
from urllib.error import URLError

CATALOG_PATH = os.environ.get("CATALOG_PATH", "/app/catalog.yaml")
HEALTH_TTL = int(os.environ.get("HEALTH_TTL", "30"))  # seconds

# In-memory state
_registry: dict = {}          # name → model entry
_health: dict = {}            # backend → {last_check, alive}
_last_load = 0


def load_catalog(path: str = ""):
    """Load model catalog from YAML file. Returns {name: entry, ...}."""
    global _registry, _last_load
    path = path or CATALOG_PATH

    if not os.path.exists(path):
        print(f"[Catalog] WARNING: {path} not found, using empty catalog", flush=True)
        _registry = {}
        return _registry

    with open(path) as f:
        data = yaml.safe_load(f)

    models = data.get("models", [])
    _registry = {m["name"]: m for m in models if m.get("status") != "inactive"}
    _last_load = time.time()
    print(f"[Catalog] Loaded {len(_registry)} models from {path}", flush=True)
    return _registry


def list_models() -> list:
    """Return public model list (no backend/internal fields)."""
    if not _registry:
        load_catalog()
    return [
        {
            "id": m["name"],
            "object": "model",
            "created": int(_last_load),
            "owned_by": "aither",
            "display_name": m.get("display_name", m["name"]),
            "description": m.get("description", ""),
            "max_tokens": m.get("max_tokens", 4096),
            "tokens_per_ruble": m.get("tokens_per_ruble", 100),
            "tags": m.get("tags", []),
        }
        for m in _registry.values()
    ]


def resolve(model_name: str) -> tuple:
    """Resolve model name → (backend_url, model_path, error).
    Returns (url, path, None) on success, or (None, None, error_str) on failure.
    """
    if not _registry:
        load_catalog()

    # Exact match
    if model_name in _registry:
        m = _registry[model_name]
        return m["backend"], m["model_path"], None

    # Fuzzy match: check if model_name contains any known name
    for name, entry in _registry.items():
        if name.lower() in model_name.lower():
            return entry["backend"], entry["model_path"], None

    # Default: first active model
    if _registry:
        first = list(_registry.values())[0]
        return first["backend"], first["model_path"], None

    return None, None, f"model '{model_name}' not found in catalog"


def health_check(backend_url: str, timeout: int = 5) -> bool:
    """Check if a vLLM backend is healthy via /health endpoint."""
    global _health
    now = time.time()

    # Use cache if recent enough
    if backend_url in _health:
        entry = _health[backend_url]
        if now - entry["last_check"] < HEALTH_TTL:
            return entry["alive"]

    try:
        url = f"{backend_url}/health"
        req = Request(url)
        resp = urlopen(req, timeout=timeout)
        alive = resp.status == 200
    except Exception:
        alive = False

    _health[backend_url] = {"last_check": now, "alive": alive}
    return alive


def health_summary() -> dict:
    """Return health status of all known backends."""
    result = {}
    if not _registry:
        load_catalog()
    for name, entry in _registry.items():
        backend = entry["backend"]
        alive = health_check(backend)
        result[name] = {"backend": backend, "alive": alive}
    return result


# Auto-load on import
load_catalog()
