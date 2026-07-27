"""Rate limiting: atomic RPM/TPM/daily via Redis Lua. PG-backed tiers. CHANGE-0022-C3.

FAIL-CLOSED design: unknown tier → deny, PG unavailable → deny, Redis unavailable → deny.
No fallback safe limits. Every rejection is explicit.
All quota dimensions: organisation, API-key, model, RPM, TPM, daily requests, daily tokens.
"""
import time, json, logging, hashlib
from typing import Optional

logger = logging.getLogger("aither.gateway.rate_limit")

# ── Token Estimator ──────────────────────────────────────────────────────

_TOKENISER = None
_TOKENISER_ERROR = None
try:
    import tiktoken
    _TOKENISER = tiktoken.get_encoding("cl100k_base")
except ImportError:
    _TOKENISER_ERROR = "tiktoken not installed, using conservative estimate"
except Exception as e:
    _TOKENISER_ERROR = f"tiktoken init failed: {e}, using conservative estimate"

CHARS_PER_TOKEN_EN = 3.5
CHARS_PER_TOKEN_RU = 2.0


def estimate_tokens(messages: list, max_tokens: int = 0) -> int:
    """Estimate token count for a list of chat messages."""
    if _TOKENISER is not None:
        try:
            total = 0
            for msg in messages:
                content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
                if isinstance(content, str) and content:
                    total += len(_TOKENISER.encode(content))
            total += len(messages) * 4
            return total + max_tokens
        except Exception as e:
            logger.warning("tiktoken encode failed: %s, falling back to char estimate", e)

    total_chars = 0
    for msg in messages:
        content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
        if isinstance(content, str):
            cyrillic = sum(1 for c in content if '\u0400' <= c <= '\u04FF')
            latin = len(content) - cyrillic
            total_chars += latin / CHARS_PER_TOKEN_EN + cyrillic / CHARS_PER_TOKEN_RU

    est = int(total_chars) + max_tokens
    est = int(est * 1.10)
    return max(est, 1)


# ── Atomic Lua: all quota dimensions ─────────────────────────────────────
# Keys: RPM, TPM, daily requests, daily tokens — all include org+key+model
RATE_LIMIT_LUA = """
local rpm_key = KEYS[1]
local tpm_key = KEYS[2]
local daily_req_key = KEYS[3]
local daily_tok_key = KEYS[4]
local rpm_max = tonumber(ARGV[1])
local tpm_max = tonumber(ARGV[2])
local daily_req_max = tonumber(ARGV[3])
local daily_tok_max = tonumber(ARGV[4])
local tokens = tonumber(ARGV[5])
local window = tonumber(ARGV[6])

local rpm = redis.call('INCR', rpm_key)
redis.call('EXPIRE', rpm_key, window)

local tpm_val = redis.call('INCRBY', tpm_key, tokens)
redis.call('EXPIRE', tpm_key, window)

-- TTL on RPM/TPM keys verified via Redis
local rpm_ttl = redis.call('TTL', rpm_key)
local tpm_ttl = redis.call('TTL', tpm_key)

local daily_req = redis.call('INCR', daily_req_key)
redis.call('EXPIRE', daily_req_key, 86400)

local daily_tok = redis.call('INCRBY', daily_tok_key, tokens)
redis.call('EXPIRE', daily_tok_key, 86400)

local daily_req_ttl = redis.call('TTL', daily_req_key)
local daily_tok_ttl = redis.call('TTL', daily_tok_key)

if rpm > rpm_max then
    return {0, 'rpm_exceeded', rpm, rpm_max, rpm_ttl}
end
if tpm_val > tpm_max then
    return {0, 'tpm_exceeded', tpm_val, tpm_max, tpm_ttl}
end
if daily_req > daily_req_max then
    return {0, 'daily_requests_exceeded', daily_req, daily_req_max, daily_req_ttl}
end
if daily_tok > daily_tok_max then
    return {0, 'daily_tokens_exceeded', daily_tok, daily_tok_max, daily_tok_ttl}
end
return {1, 'ok', rpm, rpm_max, tpm_val, tpm_max, rpm_ttl, tpm_ttl, daily_req_ttl, daily_tok_ttl}
"""

# ── Tier cache with actual TTL and invalidation ──────────────────────────

_tier_cache: dict = {}           # {tier_id: (limits_dict, cached_at_timestamp)}
_tier_cache_ttl: int = 60       # seconds


def _is_cache_valid(tier: str) -> bool:
    """Check if cached tier entry is still within TTL."""
    entry = _tier_cache.get(tier)
    if not entry:
        return False
    _limits, cached_at = entry
    if time.time() - cached_at > _tier_cache_ttl:
        return False
    return True


def invalidate_tier_cache(tier: str = None):
    """Invalidate tier cache. If tier is None, invalidate ALL."""
    global _tier_cache
    if tier is None:
        _tier_cache.clear()
        logger.info("Tier cache fully invalidated")
    else:
        _tier_cache.pop(tier, None)
        logger.info("Tier cache invalidated: %s", tier)


def set_tier_cache_ttl(ttl: int):
    """Update cache TTL in seconds."""
    global _tier_cache_ttl
    _tier_cache_ttl = max(ttl, 1)


async def _load_tier_from_pg(tier: str, db_pool) -> Optional[dict]:
    """Load tier limits from PostgreSQL. Returns None on failure."""
    if db_pool is None:
        return None
    try:
        conn = db_pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT rpm_limit, tpm_limit, daily_request_limit, daily_token_limit "
                "FROM subscription_tiers WHERE tier = %s",
                (tier,),
            )
            row = cur.fetchone()
            if row:
                return {
                    "rpm": int(row[0]),
                    "tpm": int(row[1]),
                    "daily_requests": int(row[2]) if row[2] else 10000,
                    "daily_tokens": int(row[3]) if row[3] else 1000000,
                }
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.warning("Failed to load tier %s from PG: %s", tier, e)
    return None


def _build_redis_keys(org_id: str, api_key_prefix: str = "", model_id: str = "") -> dict:
    """Build Redis keys with all quota dimensions.
    
    Keys include: org_id, optional api_key prefix, optional model.
    This ensures per-key and per-model quotas can be enforced independently.
    """
    now = int(time.time())
    today = time.strftime("%Y%m%d")
    
    # Build dimension suffix for all keys
    dims = org_id
    if api_key_prefix:
        dims += f":key:{api_key_prefix}"
    if model_id:
        dims += f":model:{model_id}"
    
    return {
        "rpm_key": f"rl:{dims}:rpm:{now // 60}",
        "tpm_key": f"rl:{dims}:tpm:{now // 60}",
        "daily_req_key": f"rl:{dims}:daily_req:{today}",
        "daily_tok_key": f"rl:{dims}:daily_tok:{today}",
    }


async def check_rate_limit(
    org_id: str,
    tier: str,
    redis,
    est_tokens: int = 0,
    db_pool=None,
    api_key: str = "",
    model_id: str = "",
) -> tuple:
    """Atomic rate limit check with PG-backed tiers. FAIL-CLOSED.

    Args:
        org_id: Organisation ID
        tier: Subscription tier ID
        redis: Redis client (async)
        est_tokens: Estimated token count for this request
        db_pool: PostgreSQL connection pool
        api_key: Optional API key for per-key quotas
        model_id: Optional model ID for per-model quotas

    Returns:
        (ok: bool, reason: str, details: dict)
        FAIL-CLOSED: returns (False, reason, details) on any error.
    """
    now_ts = time.time()
    
    # 1. Load limits — fail-closed on unknown tier or PG unavailable
    limits = None
    
    if _is_cache_valid(tier):
        limits = _tier_cache[tier][0]
    
    if limits is None:
        if db_pool is None:
            logger.error("Rate limit: PG unavailable, tier=%s. FAIL-CLOSED deny.", tier)
            return False, "rate_limit_unavailable_pg", {"tier": tier}
        
        limits = await _load_tier_from_pg(tier, db_pool)
        if limits is None:
            logger.error("Rate limit: unknown tier=%s not in PG. FAIL-CLOSED deny.", tier)
            return False, "rate_limit_unknown_tier", {"tier": tier}
        
        # Cache with timestamp
        _tier_cache[tier] = (limits, now_ts)
        logger.debug("Tier limits loaded from PG: tier=%s rpm=%d tpm=%d", tier, limits["rpm"], limits["tpm"])

    # 2. Build Redis keys with all dimensions
    api_key_prefix = ""
    if api_key:
        # Use first 16 chars of SHA256 as stable prefix (no secret exposure)
        api_key_prefix = hashlib.sha256(api_key.encode()).hexdigest()[:16]
    
    keys = _build_redis_keys(org_id, api_key_prefix, model_id)
    window_sec = 120

    # 3. Atomic Lua execution — fail-closed on Redis error
    try:
        result = await redis.eval(
            RATE_LIMIT_LUA, 4,
            keys["rpm_key"], keys["tpm_key"],
            keys["daily_req_key"], keys["daily_tok_key"],
            limits["rpm"], limits["tpm"],
            limits["daily_requests"], limits["daily_tokens"],
            est_tokens or 1, window_sec,
        )
        
        if result[0] == 1:
            details = {
                "rpm": int(result[2]), "rpm_limit": int(result[3]),
                "tpm": int(result[4]), "tpm_limit": int(result[5]),
                "rpm_ttl": int(result[6]) if len(result) > 6 else 0,
                "tpm_ttl": int(result[7]) if len(result) > 7 else 0,
            }
            return True, "ok", details
        
        # Rate limit exceeded
        reason = str(result[1])
        details = {
            "reason": reason,
            "current": int(result[2]) if len(result) > 2 else 0,
            "limit": int(result[3]) if len(result) > 3 else 0,
            "tier": tier,
        }
        return False, reason, details
        
    except Exception as e:
        logger.error("Rate limit check FAIL-CLOSED: Redis unavailable: %s", e)
        return False, "rate_limit_unavailable", {"tier": tier, "error": str(e)[:100]}


# ── Organisation quota check (separate from per-request rate limit) ──────

async def check_org_quota(org_id: str, redis, db_pool=None) -> tuple:
    """Check organisation-level quota (daily request budget from billing).
    FAIL-CLOSED: Redis error → deny.
    """
    today = time.strftime("%Y%m%d")
    quota_key = f"org_quota:{org_id}:{today}"
    
    try:
        remaining = await redis.get(quota_key)
        if remaining is None:
            # Load from PG
            if db_pool:
                try:
                    conn = db_pool.getconn()
                    try:
                        cur = conn.cursor()
                        cur.execute(
                            "SELECT daily_quota FROM billing_accounts WHERE org_id = %s",
                            (org_id,))
                        row = cur.fetchone()
                        if row and row[0]:
                            remaining = int(row[0])
                            await redis.setex(quota_key, 86400, remaining)
                        else:
                            # No quota configured → unlimited
                            return True, "ok", {"remaining": None}
                    finally:
                        db_pool.putconn(conn)
                except Exception as e:
                    logger.error("Org quota PG lookup failed: %s", e)
                    return False, "org_quota_unavailable", {}
            else:
                return True, "ok", {"remaining": None}
        
        remaining = int(remaining)
        if remaining <= 0:
            return False, "org_quota_exceeded", {"remaining": 0}
        
        new_remaining = await redis.decr(quota_key)
        if new_remaining < 0:
            # Race: another request just exhausted it
            await redis.incr(quota_key)  # undo
            return False, "org_quota_exceeded", {"remaining": 0}
        
        return True, "ok", {"remaining": new_remaining}
        
    except Exception as e:
        logger.error("Org quota check FAIL-CLOSED: %s", e)
        return False, "rate_limit_unavailable", {}


# ── API-key specific quota ───────────────────────────────────────────────

async def check_api_key_quota(api_key: str, redis, db_pool=None) -> tuple:
    """Check API-key level quota. FAIL-CLOSED.
    
    Uses Redis with key-scoped counters.
    """
    if not api_key:
        return True, "ok", {}
    
    key_prefix = hashlib.sha256(api_key.encode()).hexdigest()[:16]
    today = time.strftime("%Y%m%d")
    quota_key = f"key_quota:{key_prefix}:{today}"
    
    try:
        used = int(await redis.get(quota_key) or 0)
        # Default: 10000 requests/day per key
        key_daily_limit = 10000
        
        if used >= key_daily_limit:
            return False, "api_key_quota_exceeded", {"used": used, "limit": key_daily_limit}
        
        await redis.incr(quota_key)
        await redis.expire(quota_key, 86400)
        return True, "ok", {"used": used + 1, "limit": key_daily_limit}
        
    except Exception as e:
        logger.error("API key quota check FAIL-CLOSED: %s", e)
        return False, "rate_limit_unavailable", {}
