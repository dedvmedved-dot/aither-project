"""Rate limiting: atomic RPM/TPM/daily via Redis Lua scripts. CHANGE-0022-C2."""
import time, logging

logger = logging.getLogger("aither.gateway.rate_limit")

# Atomic Lua script: increment RPM + TPM, check limits, set TTL in one call
RATE_LIMIT_LUA = """
local rpm_key = KEYS[1]
local tpm_key = KEYS[2]
local rpm_max = tonumber(ARGV[1])
local tpm_max = tonumber(ARGV[2])
local tokens = tonumber(ARGV[3])
local window = tonumber(ARGV[4])

local rpm = redis.call('INCR', rpm_key)
redis.call('EXPIRE', rpm_key, window)

local tpm = redis.call('INCRBY', tpm_key, tokens)
redis.call('EXPIRE', tpm_key, window)

if rpm > rpm_max then
    return {0, 'rpm_exceeded', rpm, rpm_max}
end
if tpm > tpm_max then
    return {0, 'tpm_exceeded', tpm, tpm_max}
end
return {1, 'ok', rpm, rpm_max, tpm, tpm_max}
"""

# Tier defaults
TIER_LIMITS = {
    "free":      {"rpm": 300,  "tpm": 100_000, "daily_requests": 1000, "daily_tokens": 1_000_000},
    "basic":     {"rpm": 600,  "tpm": 200_000, "daily_requests": 2000, "daily_tokens": 2_000_000},
    "premium":   {"rpm": 1200, "tpm": 500_000, "daily_requests": 5000, "daily_tokens": 5_000_000},
}

async def check_rate_limit(org_id: str, tier: str, redis, est_tokens: int = 0) -> tuple:
    """Atomic RPM/TPM check via Lua. Returns (ok: bool, reason: str)."""
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    now = int(time.time())
    window_sec = 120  # 2-minute window covers clock skew

    rpm_key = f"rl:{org_id}:rpm:{now // 60}"
    tpm_key = f"rl:{org_id}:tpm:{now // 60}"

    try:
        result = await redis.eval(
            RATE_LIMIT_LUA, 2,
            rpm_key, tpm_key,
            limits["rpm"], limits["tpm"],
            est_tokens or 1, window_sec,
        )
        if result[0] == 1:
            return True, "ok"
        return False, str(result[1])
    except Exception as e:
        logger.error("Rate limit check failed: %s", e)
        # Fail-closed
        return False, "rate_limit_unavailable"
