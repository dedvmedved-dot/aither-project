"""
Vault Integration — external API key management with security policies.
CHANGE-0022-C5: K8s auth via projected service-account token (no static VAULT_TOKEN).

Architecture:
  BFF → Vault PKI (create key) → cache in local PostgreSQL
  Gateway → Vault (validate key) → Redis cache → apply policies

Auth flow (CHANGE-0022-C5):
  1. Read projected SA token from VAULT_SA_TOKEN_PATH
  2. POST auth/kubernetes/login → Vault client token
  3. Use returned client token for all subsequent API calls
  4. Token TTL: 1h (from Vault role), auto-refresh on expiry

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
import ssl
import urllib.request
import urllib.error

# ── Configuration ──────────────────────────────────────────────────────

VAULT_ENABLED = os.environ.get("VAULT_ENABLED", "false").lower() == "true"
VAULT_REQUIRED = os.environ.get("VAULT_REQUIRED", "false").lower() == "true"
VAULT_ADDR = os.environ.get("VAULT_ADDR", "https://vault.vault.svc:8200")
VAULT_ROLE = os.environ.get("VAULT_ROLE", "aither-gateway")
VAULT_AUTH_PATH = os.environ.get("VAULT_AUTH_PATH", "kubernetes")
VAULT_CA_CERT = os.environ.get("VAULT_CA_CERT", "/vault/ca/ca.crt")
VAULT_SA_TOKEN_PATH = os.environ.get("VAULT_SA_TOKEN_PATH", "/var/run/secrets/vault/token")
VAULT_PKI_PATH = os.environ.get("VAULT_PKI_PATH", "aither-pki")
VAULT_PKI_ROLE = os.environ.get("VAULT_PKI_ROLE", "api-key")
VAULT_REQUEST_TIMEOUT = int(os.environ.get("VAULT_TIMEOUT", "5"))

# ── Vault client token (obtained via K8s auth) ─────────────────────────

_vault_client_token = None
_vault_token_expiry = 0.0
_vault_token_lock = __import__('threading').Lock()


def _read_sa_token() -> str:
    """Read projected SA token from disk."""
    try:
        with open(VAULT_SA_TOKEN_PATH, 'r') as f:
            return f.read().strip()
    except Exception as e:
        raise RuntimeError(f"vault_sa_token_unreadable: {e}")


def _vault_login() -> str:
    """
    Login to Vault via K8s auth using projected SA token.
    Returns client token string.
    """
    sa_token = _read_sa_token()
    login_path = f"auth/{VAULT_AUTH_PATH}/login"
    body = json.dumps({"role": VAULT_ROLE, "jwt": sa_token}).encode()

    url = f"{VAULT_ADDR}/v1/{login_path}"
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")

    ctx = _build_ssl_context()

    try:
        with urllib.request.urlopen(req, timeout=VAULT_REQUEST_TIMEOUT, context=ctx) as resp:
            result = json.loads(resp.read())
            auth_data = result.get("auth", {})
            client_token = auth_data.get("client_token", "")
            lease_duration = auth_data.get("lease_duration", 3600)
            if not client_token:
                raise RuntimeError(f"vault_login_no_token: {result}")
            global _vault_client_token, _vault_token_expiry
            _vault_client_token = client_token
            _vault_token_expiry = time.time() + lease_duration - 60  # refresh 60s before expiry
            return client_token
    except urllib.error.HTTPError as e:
        try:
            error_body = json.loads(e.read())
            errors = error_body.get("errors", [str(e)])
            raise RuntimeError(f"vault_login_http_{e.code}: {'; '.join(errors)}")
        except Exception:
            raise RuntimeError(f"vault_login_http_{e.code}")
    except Exception as e:
        raise RuntimeError(f"vault_login_failed: {e}")


def _get_vault_token() -> str:
    """Get or refresh Vault client token. Thread-safe."""
    global _vault_client_token, _vault_token_expiry
    with _vault_token_lock:
        if _vault_client_token and time.time() < _vault_token_expiry:
            return _vault_client_token
        return _vault_login()


def _build_ssl_context() -> ssl.SSLContext | None:
    """Build SSL context with Vault CA cert if configured."""
    if not VAULT_ADDR.startswith("https://"):
        return None
    ctx = ssl.create_default_context()
    try:
        ctx.load_verify_locations(VAULT_CA_CERT)
    except Exception:
        # Fall back to system CA if Vault CA file not found
        pass
    return ctx


# Redis for caching (imported at use site to avoid circular imports)
_redis_client = None


def _get_redis(redis_module=None):
    """Lazy Redis client for cache."""
    global _redis_client
    if _redis_client is None and redis_module:
        try:
            redis_url = os.environ.get("REDIS_HOST", "aither-redis-rate-limit.aither-inference.svc")
            redis_port = int(os.environ.get("REDIS_PORT", "6379"))
            _redis_client = redis_module.Redis(
                host=redis_url, port=redis_port, decode_responses=True,
                socket_connect_timeout=2)
        except Exception:
            pass
    return _redis_client


def _vault_api(method: str, path: str, body: dict = None) -> tuple:
    """
    Call Vault HTTP API with K8s auth.
    Returns (ok: bool, data: dict, error: str).
    """
    if not VAULT_ENABLED:
        return False, {}, "vault_disabled"

    try:
        token = _get_vault_token()
    except Exception as e:
        return False, {}, f"vault_auth_failed: {e}"

    url = f"{VAULT_ADDR}/v1/{path}"
    headers = {
        "X-Vault-Token": token,
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body else None

    ctx = _build_ssl_context()

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=VAULT_REQUEST_TIMEOUT, context=ctx) as resp:
            result = json.loads(resp.read())
            return True, result.get("data", result), ""
    except urllib.error.HTTPError as e:
        if e.code == 403:
            # Token might be expired — force re-login and retry once
            global _vault_client_token
            with _vault_token_lock:
                _vault_client_token = None
            try:
                token = _get_vault_token()
                headers["X-Vault-Token"] = token
                req2 = urllib.request.Request(url, data=data, headers=headers, method=method)
                with urllib.request.urlopen(req2, timeout=VAULT_REQUEST_TIMEOUT, context=ctx) as resp2:
                    result = json.loads(resp2.read())
                    return True, result.get("data", result), ""
            except Exception as retry_err:
                return False, {}, f"vault_unreachable_after_retry: {retry_err}"
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

    import base64
    import hashlib

    serial = data.get("serial_number", "")
    api_key = "ak-" + base64.urlsafe_b64encode(
        hashlib.sha256(serial.encode()).digest()
    )[:32].decode().rstrip("=")

    expires_at = data.get("expiration", "")
    fingerprint = data.get("certificate", "")[:64]

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
    kv_path = f"secret/data/aither/keys/{api_key[:32]}"
    ok, data, err = _vault_api("GET", kv_path)

    if not ok:
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

    ok, data, err = _vault_api("DELETE", f"secret/data/aither/keys/{api_key[:32]}")
    if not ok:
        return {"ok": False, "error": err}

    r = _get_redis()
    if r:
        r.delete(f"vault:key:{api_key[:32]}")

    return {"ok": True, "revoked": api_key[:16] + "..."}


# ── Health Check ───────────────────────────────────────────────────────

def vault_health() -> dict:
    """
    Check Vault connectivity and seal status.
    CHANGE-0022-C5: Uses K8s auth (no static token).
    """
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
        "cluster_name": data.get("cluster_name", ""),
    }


def vault_login_and_check():
    """
    Full Vault readiness check (for /ready endpoint).
    CHANGE-0022-C5: Tests: reachable → unsealed → login → policy read.
    Returns dict with: reachable, unsealed, login, policy_read, error.
    """
    result = {"reachable": False, "unsealed": False, "login": False, "policy_read": False}

    # 1. Check reachable + unsealed via sys/health
    health = vault_health()
    if health.get("status") == "disabled":
        result["error"] = "vault_disabled"
        return result
    if health.get("status") == "unreachable":
        result["error"] = health.get("error", "vault_unreachable")
        return result
    result["reachable"] = True
    if not health.get("sealed", True):
        result["unsealed"] = True
    else:
        result["error"] = "vault_sealed"
        return result

    # 2. Test login via K8s auth
    try:
        token = _vault_login()
        result["login"] = True
    except Exception as e:
        result["error"] = f"vault_login_failed: {e}"
        return result

    # 3. Test policy read (verify we can read our own policy)
    try:
        ok, _, err = _vault_api("GET", f"sys/policies/acl/{VAULT_ROLE}")
        if ok:
            result["policy_read"] = True
        else:
            result["error"] = f"policy_read_failed: {err}"
    except Exception as e:
        result["error"] = f"policy_read_failed: {e}"

    return result
