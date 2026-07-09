"""
Aither Gateway — Admin Management API.
Queue monitoring, model health, drain control, reaper status.
"""

import json
import time

# ── Queue Monitoring ──────────────────────────────────────────────

def admin_queues(r) -> dict:
    """Return Redis queue/rate-limit stats for all active orgs."""
    now = int(time.time())
    window = now // 60  # current 1-min window

    orgs = {}
    # Scan for RPM keys
    rpm_keys = r.keys(f"rl:*:rpm:{window}")
    for key in rpm_keys:
        parts = key.split(":")
        if len(parts) < 3:
            continue
        org_id = parts[1]
        if org_id not in orgs:
            orgs[org_id] = {"org_id": org_id, "rpm": 0, "tpm": 0, "daily": 0}

        orgs[org_id]["rpm"] = int(r.get(key) or 0)

    # TPM keys
    tpm_keys = r.keys(f"rl:*:tpm:{window}")
    for key in tpm_keys:
        parts = key.split(":")
        if len(parts) < 3:
            continue
        org_id = parts[1]
        if org_id not in orgs:
            orgs[org_id] = {"org_id": org_id, "rpm": 0, "tpm": 0, "daily": 0}
        orgs[org_id]["tpm"] = int(r.get(key) or 0)

    # Daily counters
    today = time.strftime("%Y-%m-%d")
    daily_keys = r.keys(f"rl:*:daily:{today}")
    for key in daily_keys:
        parts = key.split(":")
        if len(parts) < 3:
            continue
        org_id = parts[1]
        if org_id not in orgs:
            orgs[org_id] = {"org_id": org_id, "rpm": 0, "tpm": 0, "daily": 0}
        orgs[org_id]["daily"] = int(r.get(key) or 0)

    # Tier info from Redis cache
    tier_keys = r.keys("org_tier:*")
    tiers = {}
    for key in tier_keys:
        org_id = key.replace("org_tier:", "")
        tiers[org_id] = r.get(key)

    # Enrich with tier
    result = []
    for oid, data in orgs.items():
        data["tier"] = tiers.get(oid, "unknown")
        result.append(data)

    # Sort: highest RPM first
    result.sort(key=lambda x: x["rpm"], reverse=True)

    return {
        "window": f"minute_{window}",
        "active_orgs": len(result),
        "orgs": result[:50],  # top 50
    }


# ── Model Management ──────────────────────────────────────────────

# In-memory drain set (models currently drained)
DRAINED_MODELS: set = set()

# Redis key for persistent drain state
DRAIN_REDIS_KEY = "admin:drained_models"


def _load_drained(r) -> set:
    """Load drained models from Redis."""
    try:
        val = r.get(DRAIN_REDIS_KEY)
        if val:
            return set(json.loads(val))
    except:
        pass
    return set()


def _save_drained(r, drained: set):
    """Persist drained models to Redis."""
    try:
        r.set(DRAIN_REDIS_KEY, json.dumps(list(drained)))
    except:
        pass


def admin_models(catalog_registry, r) -> list:
    """Return model catalog with health and drain status."""
    from catalog import health_check

    if not catalog_registry:
        from catalog import load_catalog
        load_catalog()

    drained = _load_drained(r)
    result = []
    for name, entry in catalog_registry.items():
        backend = entry["backend"]
        alive = health_check(backend)
        result.append({
            "name": name,
            "display_name": entry.get("display_name", name),
            "backend": backend,
            "model_path": entry.get("model_path", ""),
            "max_tokens": entry.get("max_tokens", 4096),
            "status": entry.get("status", "active"),
            "health": "healthy" if alive else "unhealthy",
            "drained": name in drained,
        })

    return result


def admin_drain(model_name: str, r) -> dict:
    """Drain a model: stop routing requests to it."""
    drained = _load_drained(r)
    drained.add(model_name)
    _save_drained(r, drained)
    DRAINED_MODELS.add(model_name)
    return {"model": model_name, "drained": True, "drained_models": sorted(list(drained))}


def admin_undrain(model_name: str, r) -> dict:
    """Undrain a model: resume routing."""
    drained = _load_drained(r)
    drained.discard(model_name)
    _save_drained(r, drained)
    DRAINED_MODELS.discard(model_name)
    return {"model": model_name, "drained": False, "drained_models": sorted(list(drained))}


def is_model_drained(model_name: str, r) -> bool:
    """Check if a model is currently drained."""
    drained = _load_drained(r)
    return model_name in drained


# ── Health Check ──────────────────────────────────────────────────

def admin_health(db_pool, r, catalog_registry) -> dict:
    """Full health check: backends, Redis, PostgreSQL, reaper."""
    from catalog import health_summary

    result = {
        "status": "ok",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "components": {},
    }

    # Redis
    try:
        r.ping()
        result["components"]["redis"] = {"status": "healthy"}
    except:
        result["components"]["redis"] = {"status": "unhealthy"}
        result["status"] = "degraded"

    # PostgreSQL
    try:
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            result["components"]["postgresql"] = {"status": "healthy"}
        finally:
            db_pool.putconn(conn)
    except:
        result["components"]["postgresql"] = {"status": "unhealthy"}
        result["status"] = "degraded"

    # Model backends
    backends = {}
    unhealthy = 0
    for name, entry in catalog_registry.items():
        backend = entry["backend"]
        if backend not in backends:
            from catalog import health_check
            alive = health_check(backend)
            backends[backend] = {"alive": alive, "models": []}
            if not alive:
                unhealthy += 1
        backends[backend]["models"].append(name)

    result["components"]["backends"] = {
        "total": len(backends),
        "healthy": len(backends) - unhealthy,
        "unhealthy": unhealthy,
        "details": {
            url: {"healthy": data["alive"], "models": data["models"]}
            for url, data in backends.items()
        }
    }

    # Reaper
    try:
        last_run = r.get("admin:reaper:last_run")
        stuck_refunded = r.get("admin:reaper:last_refunded")
        result["components"]["reaper"] = {
            "last_run": last_run or "never",
            "last_refunded": int(stuck_refunded) if stuck_refunded else 0,
        }
    except:
        pass

    return result


# ── Org Details ───────────────────────────────────────────────────

def admin_org_detail(org_id: str, db_pool, r) -> dict:
    """Detailed stats for a single org."""
    result: dict = {"org_id": org_id}

    # Balance
    try:
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT balance, reserved, tier FROM billing_accounts WHERE org_id=%s",
                    (org_id,))
                row = cur.fetchone()
                if row:
                    result["balance"] = int(row[0])
                    result["reserved"] = int(row[1])
                    result["tier"] = row[2] or "free"
                else:
                    result["balance"] = 0
                    result["reserved"] = 0
                    result["tier"] = "free"

                # Today's usage
                today = time.strftime("%Y-%m-%d")
                cur.execute(
                    "SELECT count(*), coalesce(sum(total_tokens),0) "
                    "FROM usage_records WHERE org_id=%s AND created_at::date=%s",
                    (org_id, today))
                cnt, tokens = cur.fetchone()
                result["requests_today"] = int(cnt or 0)
                result["tokens_today"] = int(tokens or 0)
        finally:
            db_pool.putconn(conn)
    except Exception as e:
        result["error"] = str(e)

    # Current rate limits
    now = int(time.time())
    window = now // 60
    result["current_rpm"] = int(r.get(f"rl:{org_id}:rpm:{window}") or 0)
    result["current_tpm"] = int(r.get(f"rl:{org_id}:tpm:{window}") or 0)

    # Tier limits
    tier = result.get("tier", "free")
    tl = r.hgetall(f"tier:{tier}")
    if tl:
        result["rpm_limit"] = int(tl.get("rpm", 300))
        result["tpm_limit"] = int(tl.get("tpm", 100000))

    return result


# ── Reaper Status ─────────────────────────────────────────────────

def admin_reaper(r) -> dict:
    """Current reaper status from Redis."""
    try:
        last_run = r.get("admin:reaper:last_run") or "never"
        last_refunded = r.get("admin:reaper:last_refunded") or "0"
        return {
            "last_run": last_run,
            "last_refunded": int(last_refunded),
        }
    except:
        return {"last_run": "unknown", "last_refunded": 0}
