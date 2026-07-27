"""
Aither Gateway — Configuration (environment-based).

All configuration is sourced from environment variables with sensible defaults.
No credentials or secrets are hardcoded.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
CATALOG_PATH = os.environ.get("CATALOG_PATH", str(BASE_DIR / "catalog.yaml"))
PUBLIC_KEY_PATH = os.environ.get("PUBLIC_KEY_PATH", "")
WIKI_ROOT = os.environ.get("WIKI_ROOT", str(Path("/app/wiki")))
SECURITY_LOG_DIR = os.environ.get("SECURITY_LOG_DIR", "/var/log/aither")

# ── Networking ───────────────────────────────────────────────────────────
HOST = os.environ.get("GATEWAY_HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))

# ── Redis ────────────────────────────────────────────────────────────────
REDIS_HOST = os.environ.get("REDIS_HOST", "aither-redis-rate-limit.aither-inference.svc")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "") or None
REDIS_CONNECT_TIMEOUT = float(os.environ.get("REDIS_CONNECT_TIMEOUT", "2.0"))
REDIS_SOCKET_TIMEOUT = float(os.environ.get("REDIS_SOCKET_TIMEOUT", "5.0"))

# ── PostgreSQL ───────────────────────────────────────────────────────────
# Accept PG_URL directly (preferred) or build from PG_HOST/PG_PORT/PG_USER/PG_DB/PGPASSWORD
PG_URL = os.environ.get("PG_URL", "")
if not PG_URL:
    _pg_host = os.environ.get("PG_HOST", "aither-postgres")
    _pg_port = os.environ.get("PG_PORT", "5432")
    _pg_user = os.environ.get("PG_USER", "aither")
    _pg_pass = os.environ.get("PGPASSWORD", "")
    _pg_db = os.environ.get("PG_DB", "aither")
    if _pg_pass:
        PG_URL = f"postgresql://{_pg_user}:{_pg_pass}@{_pg_host}:{_pg_port}/{_pg_db}"
    else:
        PG_URL = f"postgresql://{_pg_user}@{_pg_host}:{_pg_port}/{_pg_db}"

PG_MIN_CONNECTIONS = int(os.environ.get("PG_MIN_CONN", "1"))
PG_MAX_CONNECTIONS = int(os.environ.get("PG_MAX_CONN", "10"))

# ── JWT / Auth ───────────────────────────────────────────────────────────
JWT_PUBLIC_KEY = os.environ.get("JWT_PUBLIC_KEY", "")
JWT_ALGORITHMS = os.environ.get("JWT_ALGORITHMS", "RS256").split(",")
JWT_ISSUER = os.environ.get("JWT_ISSUER", "")

# If JWT_PUBLIC_KEY not set via env, try file
if not JWT_PUBLIC_KEY:
    for p in [PUBLIC_KEY_PATH, str(BASE_DIR / "delegation" / "public.pem"), "/app/delegation/public.pem"]:
        try:
            with open(p) as f:
                JWT_PUBLIC_KEY = f.read()
            break
        except (FileNotFoundError, PermissionError):
            pass

ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")
if not ADMIN_API_KEY:
    admin_key_file = os.environ.get("ADMIN_KEY_FILE", "")
    if admin_key_file:
        try:
            with open(admin_key_file) as f:
                ADMIN_API_KEY = f.read().strip()
        except (FileNotFoundError, PermissionError):
            pass

# ── vLLM upstream ───────────────────────────────────────────────────────
VLLM_API_KEY = os.environ.get("VLLM_API_KEY", "")

# ── Feature flags ────────────────────────────────────────────────────────
AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "true").lower() == "true"
RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"
BILLING_ENABLED = os.environ.get("BILLING_ENABLED", "false").lower() == "true"  # default false until PG ready
SECURITY_ENABLED = os.environ.get("SECURITY_ENABLED", "true").lower() == "true"
SECURITY_EGRESS_ENABLED = os.environ.get("SECURITY_EGRESS_ENABLED", "true").lower() == "true"
USAGE_ENABLED = os.environ.get("USAGE_ENABLED", "true").lower() == "true"
METRICS_ENABLED = os.environ.get("METRICS_ENABLED", "true").lower() == "true"

# ── Rate Limiting ────────────────────────────────────────────────────────
RATE_LIMIT_RPM_DEFAULT = int(os.environ.get("RATE_LIMIT_RPM", "300"))
RATE_LIMIT_TPM_DEFAULT = int(os.environ.get("RATE_LIMIT_TPM", "100000"))
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("RATE_LIMIT_WINDOW", "60"))
RATE_LIMIT_TIER_CACHE_TTL = int(os.environ.get("RATE_LIMIT_TIER_CACHE_TTL", "60"))

# ── Billing ──────────────────────────────────────────────────────────────
TOKEN_COST_MULTIPLIER = int(os.environ.get("TOKEN_COST", "1"))
BILLING_DEFAULT_BALANCE = int(os.environ.get("BILLING_DEFAULT_BALANCE", "1000000"))

# ── Timeouts ─────────────────────────────────────────────────────────────
UPSTREAM_TIMEOUT_SECONDS = float(os.environ.get("UPSTREAM_TIMEOUT", "300.0"))
UPSTREAM_CONNECT_TIMEOUT = float(os.environ.get("UPSTREAM_CONNECT_TIMEOUT", "10.0"))
HEALTH_CHECK_TIMEOUT = float(os.environ.get("HEALTH_CHECK_TIMEOUT", "5.0"))

# ── Reaper ───────────────────────────────────────────────────────────────
REAP_INTERVAL_SECONDS = int(os.environ.get("REAP_INTERVAL", "60"))
STUCK_THRESHOLD_SECONDS = int(os.environ.get("STUCK_THRESHOLD", "300"))

# ── Vault ────────────────────────────────────────────────────────────────
VAULT_ENABLED = os.environ.get("VAULT_ENABLED", "false").lower() == "true"
VAULT_REQUIRED = os.environ.get("VAULT_REQUIRED", "false").lower() == "true"

# ── SIEM ─────────────────────────────────────────────────────────────────
SIEM_ENABLED = os.environ.get("SIEM_ENABLED", "false").lower() == "true"

# ── RAG ──────────────────────────────────────────────────────────────────
RAG_ENABLED = os.environ.get("RAG_ENABLED", "false").lower() == "true"
CHROMA_URL = os.environ.get("CHROMA_URL", "http://chromadb:8000")

# ── Logging ──────────────────────────────────────────────────────────────
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.environ.get("LOG_FORMAT", "json")

# ── Tier cache ───────────────────────────────────────────────────────────
TIER_CACHE_TTL = int(os.environ.get("TIER_CACHE_TTL", "60"))


@dataclass
class Settings:
    """Aggregated settings for dependency injection."""
    redis_host: str = REDIS_HOST
    redis_port: int = REDIS_PORT
    redis_db: int = REDIS_DB
    redis_password: str | None = REDIS_PASSWORD
    redis_connect_timeout: float = REDIS_CONNECT_TIMEOUT
    redis_socket_timeout: float = REDIS_SOCKET_TIMEOUT

    pg_url: str = PG_URL
    pg_min_conn: int = PG_MIN_CONNECTIONS
    pg_max_conn: int = PG_MAX_CONNECTIONS

    jwt_public_key: str = JWT_PUBLIC_KEY
    jwt_algorithms: list[str] = field(default_factory=lambda: JWT_ALGORITHMS)
    jwt_issuer: str = JWT_ISSUER

    admin_api_key: str = ADMIN_API_KEY

    vllm_api_key: str = VLLM_API_KEY

    # Feature flags
    auth_enabled: bool = AUTH_ENABLED
    rate_limit_enabled: bool = RATE_LIMIT_ENABLED
    billing_enabled: bool = BILLING_ENABLED
    security_enabled: bool = SECURITY_ENABLED
    security_egress_enabled: bool = SECURITY_EGRESS_ENABLED
    usage_enabled: bool = USAGE_ENABLED
    metrics_enabled: bool = METRICS_ENABLED
    vault_enabled: bool = VAULT_ENABLED
    vault_required: bool = VAULT_REQUIRED
    siem_enabled: bool = SIEM_ENABLED
    rag_enabled: bool = RAG_ENABLED
    chroma_url: str = CHROMA_URL

    rate_limit_rpm_default: int = RATE_LIMIT_RPM_DEFAULT
    rate_limit_tpm_default: int = RATE_LIMIT_TPM_DEFAULT
    rate_limit_window_seconds: int = RATE_LIMIT_WINDOW_SECONDS
    rate_limit_tier_cache_ttl: int = RATE_LIMIT_TIER_CACHE_TTL

    token_cost_multiplier: int = TOKEN_COST_MULTIPLIER
    billing_default_balance: int = BILLING_DEFAULT_BALANCE

    upstream_timeout_seconds: float = UPSTREAM_TIMEOUT_SECONDS
    upstream_connect_timeout: float = UPSTREAM_CONNECT_TIMEOUT
    health_check_timeout: float = HEALTH_CHECK_TIMEOUT

    catalog_path: str = CATALOG_PATH

    log_level: str = LOG_LEVEL
    log_format: str = LOG_FORMAT

    tier_cache_ttl: int = TIER_CACHE_TTL

    wiki_root: str = WIKI_ROOT

    # Reaper
    reaper_interval_seconds: int = REAP_INTERVAL_SECONDS
    stuck_threshold_seconds: int = STUCK_THRESHOLD_SECONDS

    # Server
    host: str = HOST
    port: int = PORT


settings = Settings()
