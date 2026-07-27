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
    """Validate JWT delegation token or API key. Fail-closed: unknown token → 401."""
    if not token:
        return AuthResult(status="denied", reason="missing_token")

    # API key (ak-...)
    if token.startswith("ak-"):
        return await _check_api_key(token, app)

    # JWT RS256
    pubkey = settings.jwt_public_key
    if pubkey:
        try:
            payload = pyjwt.decode(token, pubkey, algorithms=settings.jwt_algorithms)
            # Validate basic claims
            if not payload.get("org_id"):
                return AuthResult(status="denied", reason="missing_org_id")
            if settings.jwt_issuer and payload.get("iss") != settings.jwt_issuer:
                return AuthResult(status="denied", reason="invalid_issuer")
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

    # Unknown token — fail-closed (no legacy_key fallback allowed)
    return AuthResult(status="denied", reason="invalid_token")


async def _check_api_key(token: str, app) -> AuthResult:
    """Validate ak-* API key against database. Fail-closed on DB error."""
    db_pool = app.state.db
    if not db_pool:
        logger.warning("API key check skipped: no DB pool")
        return AuthResult(status="denied", reason="invalid_key")
    try:
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT pk.org_id, pk.status, COALESCE(ba.tier, pk.tier, 'free') as tier "
                    "FROM portal_api_keys pk LEFT JOIN billing_accounts ba USING (org_id) "
                    "WHERE pk.api_key = %s",
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
        # Fail-closed: DB error → deny
    return AuthResult(status="denied", reason="invalid_key")


def check_admin(request) -> bool:
    """Verify admin API key from request headers. Constant-time comparison."""
    admin_key = settings.admin_api_key
    if not admin_key:
        return False
    provided = request.headers.get("X-Admin-Key", "")
    return hashlib.sha256(provided.encode()).hexdigest() == hashlib.sha256(admin_key.encode()).hexdigest()


def verify_api_key(token: str) -> bool:
    """Quick check: is this an ak-* token?"""
    return token.startswith("ak-") and len(token) > 10
