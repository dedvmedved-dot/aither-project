"""
Vault Integration — external API key management with security policies.

Внешний корпоративный Vault (HashiCorp Vault) для генерации API-ключей
и применения политик безопасности от ИБ.

Architecture:
  BFF → Vault PKI (create key) → cache in local PostgreSQL
  Gateway → Vault (validate key) → Redis cache → apply policies

Policies from Vault:
  - max_rpm / max_tpm → rate limiting
  - allowed_models → model access control
  - ip_whitelist → IP restriction
  - expires_at → key expiry
  - org_id → organization binding
"""
import os
import json
import time
import urllib.request
import urllib.error

# ── Configuration ──────────────────────────────────────────────────────

VAULT_ENABLED = os.environ.get("VAULT_ENABLED", "true").lower() == "true"
VAULT_ADDR = os.environ.get("VAULT_ADDR", "http://vault:8200")
VAULT_TOKEN = os.environ.get("VAULT_TOKEN", "")
VAULT_PKI_PATH = os.environ.get("VAULT_PKI_PATH", "aither-pki")
VAULT_PKI_ROLE = os.environ.get("VAULT_PKI_ROLE", "api-key")
VAULT_REQUEST_TIMEOUT = int(os.environ.get("VAULT_TIMEOUT", "5"))

# Redis for caching (imported at use site to avoid circular imports)
_redis_client = None


def _get_redis(redis_module=None):
    """Lazy Redis client for cache."""
    global _redis_client
    if _redis_client is None and redis_module:
        try:
            redis_url = os.environ.get("REDIS_URL", "redis")
            _redis_client = redis_module.Redis(
                host=redis_url, port=6379, decode_responses=True,
                socket_connect_timeout=2)
        except Exception:
            pass
    return _redis_client


def _vault_api(method: str, path: str, body: dict = None) -> tuple:
    """
    Call Vault HTTP API.
    Returns (ok: bool, data: dict, error: str).
    """
    if not VAULT_ENABLED:
        return False, {}, "vault_disabled"

    url = f"{VAULT_ADDR}/v1/{path}"
    headers = {
        "X-Vault-Token": VAULT_TOKEN,
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body else None

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=VAULT_REQUEST_TIMEOUT) as resp:
            result = json.loads(resp.read())
            return True, result.get("data", result), ""
    except urllib.error.HTTPError as e:
        try:
            error_body = json.loads(e.read())
            errors = error_body.get("errors", [str(e)])
            return False, error_body, "; ".join(errors)
        except Exception:
            return False, {}, f"HTTP {e.code}"
    except Exception as e:
        return False, {}, f"vault_unreachable: {e}"


# ── Key Generation (called by BFF) ─────────────────────────────────────

def vault_create_api_key(org_id: str, key_name: str = "default",
                         ttl: str = "2160h", max_rpm: int = 60,
                         max_tpm: int = 100000, allowed_models: list = None,
                         ip_whitelist: list = None) -> dict:
    """
    Issue a new API key via Vault PKI secrets engine.

    Returns: { ok, api_key, fingerprint, expires_at, policies, error }
    """
    if not VAULT_ENABLED:
        return {"ok": False, "error": "vault_disabled"}

    # Build Vault PKI issue request with custom metadata
    payload = {
        "common_name": org_id,
        "ttl": ttl,
        "metadata": json.dumps({
            "org_id": org_id,
            "key_name": key_name,
            "max_rpm": str(max_rpm),
            "max_tpm": str(max_tpm),
            "allowed_models": ",".join(allowed_models) if allowed_models else "",
            "ip_whitelist": ",".join(ip_whitelist) if ip_whitelist else "",
        }),
    }

    ok, data, err = _vault_api(
        "POST",
        f"{VAULT_PKI_PATH}/issue/{VAULT_PKI_ROLE}",
        payload,
    )

    if not ok:
        return {"ok": False, "error": err}

    # Vault PKI returns certificate + private_key
    # We use the certificate serial as the API key
    # Format: ak-<base64url(serial_number)>
    import base64
    import hashlib

    serial = data.get("serial_number", "")
    # Create deterministic API key from serial
    api_key = "ak-" + base64.urlsafe_b64encode(
        hashlib.sha256(serial.encode()).digest()
    )[:32].decode().rstrip("=")

    expires_at = data.get("expiration", "")
    fingerprint = data.get("certificate", "")[:64]  # First 64 chars as fingerprint

    # Parse metadata back for policies
    try:
        meta = json.loads(payload["metadata"])
    except Exception:
        meta = {}

    return {
        "ok": True,
        "api_key": api_key,
        "api_key_prefix": api_key[:11],
        "fingerprint": fingerprint[:16],
        "expires_at": expires_at,
        "policies": {
            "max_rpm": int(meta.get("max_rpm", 60)),
            "max_tpm": int(meta.get("max_tpm", 100000)),
            "allowed_models": meta.get("allowed_models", "").split(",") if meta.get("allowed_models") else [],
            "ip_whitelist": meta.get("ip_whitelist", "").split(",") if meta.get("ip_whitelist") else [],
            "org_id": org_id,
            "key_name": key_name,
        },
    }


# ── Key Validation (called by Gateway on every request) ─────────────────

def vault_validate_key(api_key: str, redis_module=None) -> dict:
    """
    Validate API key against Vault with Redis caching.

    Returns: { valid, org_id, policies, error, cached }
    """
    if not VAULT_ENABLED:
        return {"valid": False, "error": "vault_disabled", "cached": False}

    # 1. Check Redis cache (60s TTL)
    r = _get_redis(redis_module)
    if r:
        cached = r.get(f"vault:key:{api_key[:32]}")
        if cached:
            try:
                data = json.loads(cached)
                data["cached"] = True
                return data
            except Exception:
                pass

    # 2. Validate via Vault API
    # Vault PKI doesn't have a direct "validate" endpoint,
    # so we use the cert serial lookup or a custom endpoint.
    # For now: use Vault KV secrets engine as key store
    kv_path = f"secret/data/aither/keys/{api_key[:32]}"
    ok, data, err = _vault_api("GET", kv_path)

    if not ok:
        # Cache negative result briefly (10s)
        if r:
            r.setex(f"vault:key:{api_key[:32]}", 10, json.dumps(
                {"valid": False, "error": err, "cached": False}))
        return {"valid": False, "error": err, "cached": False}

    # 3. Extract policies
    key_data = data.get("data", data)
    policies = key_data.get("policies", {})
    if isinstance(policies, str):
        try:
            policies = json.loads(policies)
        except Exception:
            policies = {}

    result = {
        "valid": True,
        "org_id": key_data.get("org_id", "unknown"),
        "user_id": key_data.get("user_id", ""),
        "key_name": key_data.get("key_name", "vault"),
        "policies": {
            "max_rpm": int(policies.get("max_rpm", 300)),
            "max_tpm": int(policies.get("max_tpm", 100000)),
            "allowed_models": policies.get("allowed_models", []),
            "ip_whitelist": policies.get("ip_whitelist", []),
        },
        "expires_at": key_data.get("expires_at", ""),
        "cached": False,
    }

    # 4. Cache in Redis (60s)
    if r:
        r.setex(f"vault:key:{api_key[:32]}", 60, json.dumps(result))

    return result


def vault_revoke_key(api_key: str) -> dict:
    """Revoke API key in Vault."""
    if not VAULT_ENABLED:
        return {"ok": False, "error": "vault_disabled"}

    # Try KV delete first, then PKI revoke
    ok, data, err = _vault_api("DELETE", f"secret/data/aither/keys/{api_key[:32]}")
    if not ok:
        return {"ok": False, "error": err}

    # Clear Redis cache
    r = _get_redis()
    if r:
        r.delete(f"vault:key:{api_key[:32]}")

    return {"ok": True, "revoked": api_key[:16] + "..."}


# ── Health Check ───────────────────────────────────────────────────────

def vault_health() -> dict:
    """Check Vault connectivity and seal status."""
    if not VAULT_ENABLED:
        return {"enabled": False, "status": "disabled"}

    ok, data, err = _vault_api("GET", "sys/health")
    if not ok:
        return {"enabled": True, "status": "unreachable", "error": err}

    return {
        "enabled": True,
        "status": "ok" if data.get("initialized") else "not_initialized",
        "sealed": data.get("sealed", True),
        "version": data.get("version", ""),
    }
