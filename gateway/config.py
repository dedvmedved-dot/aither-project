"""Gateway configuration from environment. CHANGE-0022."""
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Redis
    REDIS_HOST: str = "aither-redis-rate-limit.aither-inference.svc"
    REDIS_PORT: int = 6379

    # PostgreSQL
    PG_HOST: str = "postgres"
    PG_PORT: str = "5432"
    PG_USER: str = "aither"
    PG_DB: str = "aither"
    PGPASSWORD: str = ""

    @property
    def PG_URL(self) -> str:
        return f"postgresql://{self.PG_USER}:{self.PGPASSWORD}@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DB}"

    # vLLM upstream auth
    VLLM_API_KEY: str = ""

    # JWT delegation
    JWT_PUBLIC_KEY: str = ""

    # Rate limits (defaults)
    RATE_LIMIT_RPM: int = 300
    RATE_LIMIT_TPM: int = 100_000

    # Catalog
    CATALOG_PATH: str = "catalog.yaml"

    # Feature flags
    BILLING_ENABLED: bool = True
    SECURITY_ENABLED: bool = True
    RL_ENABLED: bool = True
    RAG_ENABLED: bool = True

    # Vault
    VAULT_ENABLED: bool = False
    VAULT_REQUIRED: bool = False

    # SIEM
    SIEM_ENABLED: bool = False

    # Admin
    ADMIN_API_KEY: str = ""

    # Upstream
    UPSTREAM_TIMEOUT: float = 300.0
    UPSTREAM_CONNECT_TIMEOUT: float = 10.0

    # Reaper
    REAPER_INTERVAL: int = 60
    STUCK_THRESHOLD: int = 120

    model_config = {"env_prefix": "", "case_sensitive": True}

settings = Settings()
