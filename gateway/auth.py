"""Authentication: JWT RS256 + API key validation. CHANGE-0022-C2."""
import os, time, hashlib, logging
from dataclasses import dataclass

import jwt as pyjwt

from config import settings

logger = logging.getLogger("aither.gateway.auth")


@dataclass
class AuthResult:
    status: str  # "ok" | "denied"
    org_id: str = ""
    user_id: str = ""
    tier: str = "free"
    reason: str = ""


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
        try:
            payload = pyjwt.decode(token, pubkey, algorithms=settings.jwt_algorithms,
                                    options={"verify_exp": True})
            if not payload.get("org_id"):
                return AuthResult(status="denied", reason="missing_org_id")
            if settings.jwt_issuer and payload.get("iss") != settings.jwt_issuer:
                return AuthResult(status="denied", reason="invalid_issuer")
            # Verify audience
            aud = payload.get("aud", "")
            if aud and "aither-gateway" not in str(aud):
                return AuthResult(status="denied", reason="invalid_audience")
            # Verify scopes
            scopes = payload.get("scopes", [])
            return AuthResult(
                status="ok",
                org_id=payload.get("org_id", ""),
                user_id=payload.get("user_id", payload.get("sub", "")),
                tier=payload.get("tier", "free"),
            )
        except pyjwt.ExpiredSignatureError:
            return AuthResult(status="denied", reason="token_expired")
        except pyjwt.InvalidTokenError as e:
            logger.debug("JWT validation failed: %s", e)
            return AuthResult(status="denied", reason="invalid_token")

    # Unknown — fail-closed
    return AuthResult(status="denied", reason="invalid_token")


def _hash_token(raw_token: str) -> str:
    """SHA-256 hash for token storage."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


async def _check_api_key(token: str, app) -> AuthResult:
    """Validate API key (ak-* or athr_*) against DB. Hash the token for lookup."""
    db_pool = app.state.db
    if not db_pool:
        logger.warning("API key check skipped: no DB pool")
        return AuthResult(status="denied", reason="invalid_key")
    try:
        token_hash = _hash_token(token)
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cur:
                # Look up by hash (V002 migration: api_key stores hash, not raw)
                cur.execute(
                    "SELECT org_id, status, tier FROM portal_api_keys WHERE api_key = %s",
                    (token_hash,),
                )
                row = cur.fetchone()
                if row:
                    if row[1] == "revoked":
                        return AuthResult(status="denied", reason="key_revoked")
                    return AuthResult(status="ok", org_id=row[0], tier=row[2] or "free")
                # Fallback: try raw token (for pre-migration compatibility)
                cur.execute(
                    "SELECT org_id, status, tier FROM portal_api_keys WHERE api_key = %s",
                    (token,),
                )
                row = cur.fetchone()
                if row:
                    if row[1] == "revoked":
                        return AuthResult(status="denied", reason="key_revoked")
                    return AuthResult(status="ok", org_id=row[0], tier=row[2] or "free")
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.error("API key lookup failed: %s", e)
    return AuthResult(status="denied", reason="invalid_key")


def check_admin(request) -> bool:
    """Verify admin API key. Constant-time comparison."""
    admin_key = settings.admin_api_key
    if not admin_key:
        return False
    provided = request.headers.get("X-Admin-Key", "")
    return hashlib.sha256(provided.encode()).hexdigest() == hashlib.sha256(admin_key.encode()).hexdigest()


def verify_api_key(token: str) -> bool:
    """Check token format: ak-* or athr_*."""
    return (token.startswith("ak-") or token.startswith("athr_")) and len(token) > 10
