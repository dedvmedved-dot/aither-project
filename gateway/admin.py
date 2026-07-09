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


# ── User Management ───────────────────────────────────────────────

def admin_users(db_pool) -> list:
    """List all users with org count."""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.user_id, u.email, u.display_name, u.oauth_provider,
                       u.created_at, u.last_login_at,
                       count(m.org_id) as org_count
                FROM portal_users u
                LEFT JOIN portal_org_members m ON u.user_id=m.user_id AND m.status='active'
                GROUP BY u.user_id ORDER BY u.created_at DESC LIMIT 100
            """)
            rows = cur.fetchall()
            return [
                {
                    "user_id": str(r[0]), "email": r[1], "display_name": r[2],
                    "provider": r[3], "created_at": str(r[4]),
                    "last_login": str(r[5]) if r[5] else None,
                    "org_count": r[6],
                }
                for r in rows
            ]
    finally:
        db_pool.putconn(conn)


def admin_user_detail(user_id: str, db_pool) -> dict:
    """User detail with memberships."""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, email, display_name, oauth_provider, created_at, last_login_at "
                "FROM portal_users WHERE user_id::text=%s", (user_id,))
            u = cur.fetchone()
            if not u:
                return {"error": "user not found"}

            cur.execute("""
                SELECT m.org_id, o.name, m.role, m.status
                FROM portal_org_members m
                JOIN portal_organizations o ON m.org_id=o.org_id
                WHERE m.user_id::text=%s
            """, (user_id,))
            orgs = [{"org_id": str(r[0]), "name": r[1], "role": r[2], "status": r[3]} for r in cur.fetchall()]

            return {
                "user_id": str(u[0]), "email": u[1], "display_name": u[2],
                "provider": u[3], "created_at": str(u[4]),
                "last_login": str(u[5]) if u[5] else None,
                "orgs": orgs,
            }
    finally:
        db_pool.putconn(conn)


def admin_user_update_role(user_id: str, role: str, db_pool) -> dict:
    """Update a user's role in all their org memberships."""
    valid_roles = {"owner", "billing_admin", "developer", "viewer"}
    if role not in valid_roles:
        return {"error": f"invalid role: {role}, must be one of {valid_roles}"}

    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE portal_org_members SET role=%s WHERE user_id::text=%s",
                (role, user_id))
            updated = cur.rowcount
        conn.commit()
        return {"user_id": user_id, "role": role, "updated_memberships": updated}
    finally:
        db_pool.putconn(conn)


# ── Token Management ──────────────────────────────────────────────

def admin_tokens_add(org_id: str, amount: int, db_pool) -> dict:
    """Add tokens to org balance."""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE billing_accounts SET balance=balance+%s, updated_at=now() "
                "WHERE org_id=%s RETURNING balance",
                (amount, org_id))
            row = cur.fetchone()
            if not row:
                return {"error": "org not found"}
        conn.commit()
        return {"org_id": org_id, "added": amount, "new_balance": int(row[0])}
    finally:
        db_pool.putconn(conn)


def admin_tokens_subtract(org_id: str, amount: int, db_pool) -> dict:
    """Subtract tokens from org balance."""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE billing_accounts SET balance=GREATEST(0, balance-%s), updated_at=now() "
                "WHERE org_id=%s RETURNING balance",
                (amount, org_id))
            row = cur.fetchone()
            if not row:
                return {"error": "org not found"}
        conn.commit()
        return {"org_id": org_id, "subtracted": amount, "new_balance": int(row[0])}
    finally:
        db_pool.putconn(conn)


# ── Tier Management ────────────────────────────────────────────────

def admin_tiers(db_pool) -> list:
    """List all subscription tiers with limits."""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT tier_id, name, description, rpm_limit, tpm_limit,
                       daily_request_limit, models, rag_enabled, priority,
                       price_rub_month, features
                FROM subscription_tiers ORDER BY priority
            """)
            return [
                {
                    "tier_id": r[0], "name": r[1], "description": r[2],
                    "rpm_limit": r[3], "tpm_limit": r[4],
                    "daily_limit": r[5], "models": r[6], "rag": r[7],
                    "priority": r[8], "price_rub": r[9], "features": r[10],
                }
                for r in cur.fetchall()
            ]
    finally:
        db_pool.putconn(conn)


def admin_tier_set_limits(tier_id: str, rpm: int, tpm: int, daily: int, db_pool) -> dict:
    """Update tier rate limits."""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE subscription_tiers SET rpm_limit=%s, tpm_limit=%s, "
                "daily_request_limit=%s WHERE tier_id=%s",
                (rpm, tpm, daily, tier_id))
            if cur.rowcount == 0:
                return {"error": "tier not found"}
        conn.commit()
        # Also update Redis cache
        return {"tier_id": tier_id, "rpm": rpm, "tpm": tpm, "daily": daily}
    finally:
        db_pool.putconn(conn)


def admin_org_set_tier(org_id: str, tier: str, db_pool, r) -> dict:
    """Change org subscription tier."""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE billing_accounts SET tier=%s, updated_at=now() "
                "WHERE org_id=%s RETURNING balance",
                (tier, org_id))
            row = cur.fetchone()
            if not row:
                return {"error": "org not found"}
        conn.commit()
        # Update Redis tier cache
        try:
            r.set(f"org_tier:{org_id}", tier)
            # Also cache tier limits for rate limiter
            tl = r.hgetall(f"tier:{tier}")
            if not tl:
                cur.execute(
                    "SELECT rpm_limit, tpm_limit FROM subscription_tiers WHERE tier_id=%s",
                    (tier,))
                tr = cur.fetchone()
                if tr:
                    r.hset(f"tier:{tier}", mapping={"rpm": tr[0], "tpm": tr[1]})
        except:
            pass
        return {"org_id": org_id, "tier": tier, "balance": int(row[0])}
    finally:
        db_pool.putconn(conn)
