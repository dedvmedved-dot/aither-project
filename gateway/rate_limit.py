"""Rate limiting: atomic RPM/TPM/daily via Redis Lua. PG-backed tiers. CHANGE-0022-C2."""
import time, json, logging

logger = logging.getLogger("aither.gateway.rate_limit")

# Atomic Lua: RPM + TPM + daily counters
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

local tpm = redis.call('INCRBY', tpm_key, tokens)
redis.call('EXPIRE', tpm_key, window)

local daily_req = redis.call('INCR', daily_req_key)
redis.call('EXPIRE', daily_req_key, 86400)

local daily_tok = redis.call('INCRBY', daily_tok_key, tokens)
redis.call('EXPIRE', daily_tok_key, 86400)

if rpm > rpm_max then
    return {0, 'rpm_exceeded', rpm, rpm_max}
end
if tpm > tpm_max then
    return {0, 'tpm_exceeded', tpm, tpm_max}
end
if daily_req > daily_req_max then
    return {0, 'daily_requests_exceeded', daily_req, daily_req_max}
end
if daily_tok > daily_tok_max then
    return {0, 'daily_tokens_exceeded', daily_tok, daily_tok_max}
end
return {1, 'ok', rpm, rpm_max, tpm, tpm_max}
"""

# PG-backed tier cache
_tier_cache = {}
_cache_ttl = 60


async def _load_tier_from_pg(tier: str, db_pool) -> dict:
    """Load tier limits from PostgreSQL, with Redis cache layer."""
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
                return {"rpm": row[0], "tpm": row[1], "daily_requests": row[2], "daily_tokens": row[3]}
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        logger.warning("Failed to load tier %s from PG: %s", tier, e)
    return {}


async def check_rate_limit(org_id: str, tier: str, redis, est_tokens: int = 0, db_pool=None) -> tuple:
    """Atomic rate limit check with PG-backed tiers. Returns (ok: bool, reason: str)."""
    # Load limits from cache or PG
    limits = _tier_cache.get(tier)
    if not limits:
        if db_pool:
            limits = await _load_tier_from_pg(tier, db_pool)
            if limits:
                _tier_cache[tier] = limits

    if not limits:
        limits = {"rpm": 300, "tpm": 100_000, "daily_requests": 1000, "daily_tokens": 1_000_000}

    now = int(time.time())
    window_sec = 120

    rpm_key = f"rl:{org_id}:rpm:{now // 60}"
    tpm_key = f"rl:{org_id}:tpm:{now // 60}"
    daily_req_key = f"rl:{org_id}:daily_req:{time.strftime('%Y%m%d')}"
    daily_tok_key = f"rl:{org_id}:daily_tok:{time.strftime('%Y%m%d')}"

    try:
        result = await redis.eval(
            RATE_LIMIT_LUA, 4,
            rpm_key, tpm_key, daily_req_key, daily_tok_key,
            limits["rpm"], limits["tpm"],
            limits["daily_requests"], limits["daily_tokens"],
            est_tokens or 1, window_sec,
        )
        if result[0] == 1:
            return True, "ok"
        return False, str(result[1])
    except Exception as e:
        logger.error("Rate limit check failed: %s", e)
        return False, "rate_limit_unavailable"
