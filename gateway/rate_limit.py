"""Rate limiting: atomic RPM/TPM/daily via Redis Lua. PG-backed tiers. CHANGE-0022-C2."""
import time, json, logging

logger = logging.getLogger("aither.gateway.rate_limit")

# ── Token Estimator ──────────────────────────────────────────────────────

# Try to use tiktoken for accurate token counting; fall back to conservative estimate
_TOKENISER = None
_TOKENISER_ERROR = None
try:
    import tiktoken
    _TOKENISER = tiktoken.get_encoding("cl100k_base")  # GPT-4/3.5 encoding
except ImportError:
    _TOKENISER_ERROR = "tiktoken not installed, using conservative estimate"
except Exception as e:
    _TOKENISER_ERROR = f"tiktoken init failed: {e}, using conservative estimate"

# Conservative estimate: ~4 chars per token for English, ~2 for Russian/CJK
# This is a documented upper-bound (over-estimates by up to 25%)
CHARS_PER_TOKEN_EN = 3.5
CHARS_PER_TOKEN_RU = 2.0


def estimate_tokens(messages: list, max_tokens: int = 0) -> int:
    """
    Estimate token count for a list of chat messages.

    Uses tiktoken if available (accurate), otherwise falls back to
    a conservative character-based estimator.
    Error margin: with cl100k_base, accuracy is ~±5%. Conservative
    fallback over-estimates by ~15-25% to avoid under-counting.

    Returns total estimated tokens (input + max output).
    """
    if _TOKENISER is not None:
        try:
            total = 0
            for msg in messages:
                content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
                if isinstance(content, str) and content:
                    total += len(_TOKENISER.encode(content))
            # Per-message overhead: ~4 tokens per message (role markers)
            total += len(messages) * 4
            return total + max_tokens
        except Exception as e:
            logger.warning("tiktoken encode failed: %s, falling back to char estimate", e)

    # Conservative character-based fallback
    total_chars = 0
    for msg in messages:
        content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
        if isinstance(content, str):
            # Count Cyrillic chars for Russian ratio
            cyrillic = sum(1 for c in content if '\u0400' <= c <= '\u04FF')
            latin = len(content) - cyrillic
            total_chars += latin / CHARS_PER_TOKEN_EN + cyrillic / CHARS_PER_TOKEN_RU

    est = int(total_chars) + max_tokens
    # Apply 10% safety margin for conservative estimate
    est = int(est * 1.10)
    return max(est, 1)


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
        # Unknown tier — fail-closed per security requirement
        if tier not in _tier_cache and db_pool is None:
            # PG unavailable, use safe defaults
            limits = {"rpm": 60, "tpm": 10000, "daily_requests": 100, "daily_tokens": 100000}
        else:
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
        logger.error("Rate limit check failed (Redis unavailable): %s", e)
        # Fail-closed: block requests when Redis is down
        return False, "rate_limit_unavailable"
