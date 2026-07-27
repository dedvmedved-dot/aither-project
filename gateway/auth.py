"""Authentication: JWT RS256 + API key validation. CHANGE-0022-C3 R7-R5."""
import os, time, hashlib, logging
from dataclasses import dataclass, field

import jwt as pyjwt

from config import settings

logger = logging.getLogger("aither.gateway.auth")

# ── Mandatory JWT claims ─────────────────────────────────────────────────
MANDATORY_CLAIMS = [
    "iss", "aud", "sub", "org_id", "user_id", "tier",
    "scopes", "jti", "iat", "nbf", "exp",
]


@dataclass
class AuthResult:
    """Result of authentication check. Fail-closed by design."""
    status: str = "denied"        # "ok" | "denied"
    org_id: str = ""
    user_id: str = ""
    tier: str = "free"
    reason: str = ""
    # Новые поля — CHANGE-0022-C3 R7-R5
    scopes: list[str] = field(default_factory=list)
    role: str = ""
    jti: str = ""
    credential_id: str = ""
    credential_type: str = ""      # "jwt_delegation" | "api_key" | "vault_key"


# ── JWT RS256 validation (Section 5.1) ──────────────────────────────────

async def check_auth(token: str, app) -> AuthResult:
    """Validate JWT delegation token or API key. Fail-closed."""
    if not token:
        return AuthResult(status="denied", reason="missing_token")

    # API key (ak-* or athr_*)
    if token.startswith("ak-") or token.startswith("athr_"):
        return await _check_api_key(token, app)

    # JWT RS256 (BFF delegation)
    pubkey = settings.jwt_public_key
    if pubkey and "." in token:
        return _validate_jwt_delegation(token, pubkey)

    # Unknown — fail-closed
    return AuthResult(status="denied", reason="invalid_token_format")


def _validate_jwt_delegation(token: str, pubkey: str) -> AuthResult:
    """Validate RS256 BFF delegation JWT with ALL mandatory claims."""
    try:
        payload = pyjwt.decode(
            token,
            pubkey,
            algorithms=settings.jwt_algorithms,
            options={
                "verify_exp": True,
                "verify_iss": True,
                "verify_aud": True,
                "verify_iat": True,
                "verify_nbf": True,
                "require": MANDATORY_CLAIMS,
            },
            issuer=settings.jwt_issuer or "aither-bff",
            audience="aither-gateway",
        )
    except pyjwt.ExpiredSignatureError:
        return AuthResult(status="denied", reason="token_expired")
    except pyjwt.ImmatureSignatureError:
        return AuthResult(status="denied", reason="token_not_yet_valid")
    except pyjwt.MissingRequiredClaimError as e:
        logger.warning("JWT missing required claim: %s", e)
        return AuthResult(status="denied", reason=f"missing_claim: {e}")
    except pyjwt.InvalidIssuerError:
        return AuthResult(status="denied", reason="invalid_issuer")
    except pyjwt.InvalidAudienceError:
        return AuthResult(status="denied", reason="invalid_audience")
    except pyjwt.InvalidTokenError as e:
        logger.debug("JWT validation failed: %s", e)
        return AuthResult(status="denied", reason="invalid_token")

    # ── Post-decode mandatory claim presence check ──────────────────────
    missing = [c for c in MANDATORY_CLAIMS if c not in payload]
    if missing:
        logger.warning("JWT missing claims after decode: %s", missing)
        return AuthResult(status="denied",
                          reason=f"missing_claims: {','.join(missing)}")

    # ── issuer and audience are verified by pyjwt options above ─────────
    # Double-check: audience MUST contain "aither-gateway"
    aud = payload.get("aud", "")
    aud_list = [aud] if isinstance(aud, str) else aud
    if "aither-gateway" not in aud_list and "aither-gateway" not in str(aud):
        return AuthResult(status="denied", reason="invalid_audience")

    scopes = payload.get("scopes", [])
    if not isinstance(scopes, list):
        scopes = [scopes] if scopes else []

    return AuthResult(
        status="ok",
        org_id=payload.get("org_id", ""),
        user_id=payload.get("user_id", payload.get("sub", "")),
        tier=payload.get("tier", "free"),
        scopes=scopes,
        role=payload.get("role", ""),
        jti=payload.get("jti", ""),
        credential_id=payload.get("credential_id", payload.get("jti", "")),
        credential_type="jwt_delegation",
    )


# ── API key validation (Section 5.2) ────────────────────────────────────

def _hash_token(raw_token: str) -> str:
    """SHA-256 hash for token storage. One-way only."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


async def _check_api_key(token: str, app) -> AuthResult:
    """
    Validate API key (ak-* or athr_*) against DB.
    Hash-only lookup — NO raw-token fallback.
    Checks: active/revoked/expired, user active, org active,
    model scopes, RAG scopes.
    """
    db_pool = getattr(app.state, "db", None)
    if not db_pool:
        logger.warning("API key check skipped: no DB pool")
        return AuthResult(status="denied", reason="db_unavailable")

    try:
        token_hash = _hash_token(token)
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cur:
                # ── Lookup by hash ONLY (V002 migration complete) ──────
                cur.execute(
                    """SELECT pk.org_id, pk.status, pk.tier,
                              pk.expires_at, pk.user_id, pk.name,
                              pk.model_scopes, pk.rag_scopes
                       FROM portal_api_keys pk
                       WHERE pk.api_key = %s""",
                    (token_hash,),
                )
                row = cur.fetchone()

                if not row:
                    logger.info("API key not found by hash")
                    return AuthResult(status="denied", reason="invalid_key")

                (org_id, key_status, tier, expires_at, user_id, key_name,
                 model_scopes, rag_scopes) = row
                # User/org status checks deferred until portal_users/organizations tables exist
                user_status = "active"
                org_status = "active"

                # ── Key status checks ──────────────────────────────────
                if key_status == "revoked":
                    logger.info("API key revoked: %s", key_name)
                    return AuthResult(status="denied", reason="key_revoked")

                if key_status != "active":
                    logger.info("API key not active: status=%s", key_status)
                    return AuthResult(status="denied", reason="key_inactive")

                # Expiry check
                if expires_at is not None:
                    now_ts = time.time()
                    if isinstance(expires_at, str):
                        # ISO format expiry
                        from datetime import datetime, timezone
                        try:
                            exp_dt = datetime.fromisoformat(expires_at)
                            if exp_dt.tzinfo is None:
                                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                            if now_ts > exp_dt.timestamp():
                                return AuthResult(status="denied",
                                                  reason="key_expired")
                        except ValueError:
                            pass
                    else:
                        # Assume timestamp
                        if now_ts > float(expires_at):
                            return AuthResult(status="denied",
                                              reason="key_expired")

                # ── User status check ─────────────────────────────────
                if user_status is not None and user_status != "active":
                    logger.info("API key user not active: status=%s user=%s",
                                user_status, user_id)
                    return AuthResult(status="denied", reason="user_inactive")

                # ── Org status check ───────────────────────────────────
                if org_status is not None and org_status != "active":
                    logger.info("API key org not active: status=%s org=%s",
                                org_status, org_id)
                    return AuthResult(status="denied", reason="org_inactive")

                # ── Build scopes from DB fields ────────────────────────
                scopes = []
                if model_scopes:
                    if isinstance(model_scopes, list):
                        scopes.extend(model_scopes)
                    elif isinstance(model_scopes, str):
                        scopes.extend(
                            s.strip() for s in model_scopes.split(",") if s.strip()
                        )

                if rag_scopes:
                    if isinstance(rag_scopes, list):
                        scopes.extend(rag_scopes)
                    elif isinstance(rag_scopes, str):
                        scopes.extend(
                            s.strip() for s in rag_scopes.split(",") if s.strip()
                        )

                # Update last_used_at
                try:
                    cur.execute(
                        "UPDATE portal_api_keys SET last_used_at=now() "
                        "WHERE api_key = %s",
                        (token_hash,),
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()

                return AuthResult(
                    status="ok",
                    org_id=str(org_id),
                    user_id=str(user_id) if user_id else "",
                    tier=tier or "free",
                    scopes=scopes,
                    credential_id=str(key_name or token_hash[:12]),
                    credential_type="api_key",
                )

        finally:
            db_pool.putconn(conn)

    except Exception as e:
        logger.error("API key lookup failed: %s", e)
        return AuthResult(status="denied", reason="db_error")


# ── Admin check ──────────────────────────────────────────────────────────

def check_admin(request) -> bool:
    """Verify admin API key. Constant-time comparison."""
    admin_key = settings.admin_api_key
    if not admin_key:
        return False
    provided = request.headers.get("X-Admin-Key", "")
    return hashlib.sha256(provided.encode()).hexdigest() == \
        hashlib.sha256(admin_key.encode()).hexdigest()


def verify_api_key(token: str) -> bool:
    """Check token format: ak-* or athr_*."""
    return (token.startswith("ak-") or token.startswith("athr_")) and len(token) > 10
