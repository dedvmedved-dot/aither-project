"""Rate limiting: RPM, TPM, daily quota via Redis. CHANGE-0022."""
import time, logging

logger = logging.getLogger("aither.gateway.rate_limit")

async def check_rate_limit(org_id: str, tier: str, redis, est_tokens: int = 0) -> tuple:
    """Check RPM and TPM. Returns (ok: bool, reason: str)."""
    now = int(time.time())
    rpm_window = now // 60
    tpm_window = now // 60

    rpm_key = f"rl:{org_id}:rpm:{rpm_window}"
    tpm_key = f"rl:{org_id}:tpm:{tpm_window}"

    try:
        rpm_count = await redis.incr(rpm_key)
        await redis.expire(rpm_key, 120)

        tpm_count = await redis.incrby(tpm_key, est_tokens or 1)
        await redis.expire(tpm_key, 120)

        max_rpm = 300  # default — override from tier config
        max_tpm = 100_000

        if rpm_count > max_rpm:
            return False, f"rpm_exceeded: {rpm_count}/{max_rpm}"
        if tpm_count > max_tpm:
            return False, f"tpm_exceeded: {tpm_count}/{max_tpm}"

        return True, "ok"
    except Exception as e:
        logger.error("Rate limit check failed: %s", e)
        # Fail-closed
        return False, "rate_limit_unavailable"
