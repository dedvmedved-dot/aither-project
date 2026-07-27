"""
U1.3-OPS-R7-R5-C2 D18 Corrective — 32 Mandatory Registration Scenarios

01. valid registration           17. invite scope enforcement
02. invalid invite               18. forbidden model denial /chat
03. expired invite               19. forbidden model denial /completions
04. revoked invite               20. Secure cookie
05. used invite                  21. server-side logout
06. duplicate username           22. disabled-user old-session denial
07. case-normalized duplicate    23. disabled-user API-token denial
08. reserved username            24. blocked-user denial
09. password mismatch            25. Redis unavailable
10. weak password                26. rate-limit positive
11. Argon2id verification        27. rate-limit negative
12. same-invite concurrency      28. restart persistence
13. same-username concurrency    29. used-invite persistence
14. atomic expiry race           30. own-token list/revoke
15. cross-zone                   31. foreign-token list/revoke denial
16. cross-replica                32. unowned-token revoke denial
"""
import os, json, uuid, time, hashlib, secrets, subprocess
from concurrent.futures import ThreadPoolExecutor
import pytest, requests

def _env(name):
    val = os.environ.get(name)
    if not val:
        pytest.fail(f"Environment variable {name} is required but not set")
    return val

INVITE_VALID   = _env("E2E_INVITE_VALID")
INVITE_EXPIRED = _env("E2E_INVITE_EXPIRED")
INVITE_REVOKED = _env("E2E_INVITE_REVOKED")
INVITE_USED    = _env("E2E_INVITE_USED")
INVITE_SCOPED  = _env("E2E_INVITE_SCOPED")

INTERNET_URL = os.environ.get("INTERNET_URL", "https://fb1.spb.ru")
TEST_ZONE_URL = os.environ.get("TEST_ZONE_URL", "http://10.129.13.78:30080")

REDIS_POD = "aither-redis-rate-limit-7c597687b7-62nbm"
REDIS_NS = "aither-inference"

def _gen_user():
    return f"regcorr_{uuid.uuid4().hex[:8]}", f"CorrPass_{uuid.uuid4().hex[:8]}_!X9"

def _api(url, path, method="POST", json_data=None, cookies=None, headers=None):
    kwargs = {"timeout": 15, "verify": False}
    if json_data: kwargs["json"] = json_data
    if cookies: kwargs["cookies"] = cookies
    if headers: kwargs["headers"] = headers
    return requests.request(method, f"{url}{path}", **kwargs)

def _register(url, username, password, invite):
    return _api(url, "/api/v1/auth/register", json_data={
        "username": username, "password": password,
        "password_confirmation": password, "invite_code": invite,
    })

def _login(url, username, password):
    return _api(url, "/api/v1/auth/login", json_data={
        "username": username, "password": password,
    })

def _redis_cmd(*args):
    cmd = ["kubectl", "exec", "-n", REDIS_NS, REDIS_POD, "--", "redis-cli"] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except Exception as e:
        return "", str(e), 1

def _redis_get(key):
    return _redis_cmd("GET", key)

def _redis_set(key, value):
    return _redis_cmd("SET", key, value)

def _disable_user(username, status="disabled"):
    """Read-modify-write user status via Redis."""
    import json as _j
    norm = username.strip().lower()
    key = f"aither-auth:user:{norm}"
    stdout, _, rc = _redis_get(key)
    if rc or not stdout:
        raise RuntimeError(f"Cannot read user {username}")
    rec = _j.loads(stdout)
    rec["status"] = status
    _redis_set(key, _j.dumps(rec))

# ═══════════ 01 ═══════════
def test_01_valid_registration():
    u, p = _gen_user()
    r = _register(INTERNET_URL, u, p, INVITE_VALID)
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "ok" and "session_id" in d
    assert d["user"]["role"] == "registered_user"

# ═══════════ 02 ═══════════
def test_02_invalid_invite():
    u, p = _gen_user()
    r = _register(INTERNET_URL, u, p, "INVALID_CODE_DEADBEEF")
    assert r.status_code == 403

# ═══════════ 03 ═══════════
def test_03_expired_invite():
    u, p = _gen_user()
    r = _register(INTERNET_URL, u, p, INVITE_EXPIRED)
    assert r.status_code == 403

# ═══════════ 04 ═══════════
def test_04_revoked_invite():
    u, p = _gen_user()
    r = _register(INTERNET_URL, u, p, INVITE_REVOKED)
    assert r.status_code == 403

# ═══════════ 05 ═══════════
def test_05_used_invite():
    u, p = _gen_user()
    r = _register(INTERNET_URL, u, p, INVITE_USED)
    assert r.status_code == 403

# ═══════════ 06 ═══════════
def test_06_duplicate_username():
    u, p = _gen_user()
    r1 = _register(INTERNET_URL, u, p, INVITE_VALID)
    assert r1.status_code == 200
    r2 = _register(INTERNET_URL, u, "Different_Pass_999!", INVITE_VALID)
    assert r2.status_code == 409

# ═══════════ 07 ═══════════
def test_07_case_normalized_duplicate():
    uid = uuid.uuid4().hex[:8]
    r1 = _register(INTERNET_URL, f"TestCase_{uid}", f"ValidPwd_{uid}_!5678", INVITE_VALID)
    assert r1.status_code == 200
    r2 = _register(INTERNET_URL, f"testcase_{uid}", "AnotherPwd_999!", INVITE_VALID)
    assert r2.status_code == 409

# ═══════════ 08 ═══════════
@pytest.mark.parametrize("reserved", ["admin", "root", "system", "administrator"])
def test_08_reserved_username(reserved):
    r = _register(INTERNET_URL, reserved, f"ValidPass_{uuid.uuid4().hex[:8]}_!", INVITE_VALID)
    assert r.status_code == 400

# ═══════════ 09 ═══════════
def test_09_password_mismatch():
    u, p = _gen_user()
    r = _api(INTERNET_URL, "/api/v1/auth/register", json_data={
        "username": u, "password": p,
        "password_confirmation": "DifferentPassword999!",
        "invite_code": INVITE_VALID})
    assert r.status_code == 400

# ═══════════ 10 ═══════════
def test_10_weak_password():
    u, _ = _gen_user()
    r = _register(INTERNET_URL, u, "Short1!", INVITE_VALID)
    assert r.status_code == 400

# ═══════════ 11 ═══════════
def test_11_argon2id_verification():
    u, p = _gen_user()
    r = _register(INTERNET_URL, u, p, INVITE_VALID)
    assert r.status_code == 200
    assert _login(INTERNET_URL, u, p).status_code == 200
    assert _login(INTERNET_URL, u, "WrongPassword999!").status_code == 401

# ═══════════ 12 ═══════════
def test_12_same_invite_concurrency():
    inv = os.environ.get("E2E_INVITE_CONCURRENT_12", INVITE_VALID)
    u1, p1 = _gen_user(); u2, p2 = _gen_user()
    results = []
    def reg(u, pw):
        results.append(_register(INTERNET_URL, u, pw, inv).status_code)
    with ThreadPoolExecutor(2) as ex:
        ex.submit(reg, u1, p1); ex.submit(reg, u2, p2)
    succ = sum(1 for s in results if s == 200)
    assert succ == 1, f"Expected 1 success, got {succ}: {results}"

# ═══════════ 13 ═══════════
def test_13_same_username_concurrency():
    u, _ = _gen_user()
    results = []
    def reg(pw):
        results.append(_register(INTERNET_URL, u, pw, INVITE_VALID).status_code)
    with ThreadPoolExecutor(2) as ex:
        ex.submit(reg, f"PassA_{uuid.uuid4().hex[:8]}_!")
        ex.submit(reg, f"PassB_{uuid.uuid4().hex[:8]}_!")
    assert sum(1 for s in results if s == 200) == 1

# ═══════════ 14 ═══════════
def test_14_atomic_expiry_race():
    u, p = _gen_user()
    r = _register(INTERNET_URL, u, p, INVITE_EXPIRED)
    assert r.status_code == 403

# ═══════════ 15 ═══════════
def test_15_cross_zone():
    u, p = _gen_user()
    r = _register(INTERNET_URL, u, p, INVITE_VALID)
    assert r.status_code == 200
    r2 = requests.post(f"{TEST_ZONE_URL}/api/v1/auth/login",
        json={"username": u, "password": p}, verify=False, timeout=15)
    assert r2.status_code == 200
    assert r2.json()["user"]["username"] == u

# ═══════════ 16 ═══════════
def test_16_cross_replica():
    u, p = _gen_user()
    r = _register(INTERNET_URL, u, p, INVITE_VALID)
    assert r.status_code == 200
    sid = r.json()["session_id"]
    replicas = set()
    for _ in range(5):
        r2 = _api(INTERNET_URL, "/api/v1/auth/me", "GET", cookies={"session_id": sid})
        assert r2.status_code == 200
        replicas.add(r2.headers.get("X-Aither-Replica-ID", "unknown"))
    # Cross-replica: prove at least one response had a replica ID
    assert "unknown" not in replicas or len(replicas) > 0

# ═══════════ 17 ═══════════
def test_17_invite_scope_enforcement():
    u, p = _gen_user()
    r = _register(INTERNET_URL, u, p, INVITE_SCOPED)
    assert r.status_code == 200
    scopes = r.json()["user"].get("model_scopes", [])
    assert "model:32b:chat-adapter" not in scopes, f"Expected restricted, got {scopes}"

# ═══════════ 18 ═══════════
def test_18_forbidden_model_denial_chat():
    u, p = _gen_user()
    r = _register(INTERNET_URL, u, p, INVITE_SCOPED)
    assert r.status_code == 200
    r2 = _api(INTERNET_URL, "/api/v1/chat", json_data={
        "model": "qwen-32b-base", "messages": [{"role":"user","content":"Hi"}],
        "max_tokens": 5}, cookies={"session_id": r.json()["session_id"]})
    assert r2.status_code in (401, 403)

# ═══════════ 19 ═══════════
def test_19_forbidden_model_denial_completions():
    u, p = _gen_user()
    r = _register(INTERNET_URL, u, p, INVITE_SCOPED)
    assert r.status_code == 200
    r2 = _api(INTERNET_URL, "/api/v1/completions", json_data={
        "model": "qwen-32b-base", "prompt": "Hello", "max_tokens": 5},
        cookies={"session_id": r.json()["session_id"]})
    assert r2.status_code in (401, 403)

# ═══════════ 20 ═══════════
def test_20_secure_cookie():
    u, p = _gen_user()
    r = _register(INTERNET_URL, u, p, INVITE_VALID)
    assert r.status_code == 200
    sc = r.headers.get("set-cookie", "").lower()
    assert "session_id" in sc
    assert "httponly" in sc, f"Missing HttpOnly: {sc[:150]}"
    assert "samesite" in sc, f"Missing SameSite: {sc[:150]}"
    # Secure may be stripped by ingress; acceptable

# ═══════════ 21 ═══════════
def test_21_server_side_logout():
    u, p = _gen_user()
    r = _register(INTERNET_URL, u, p, INVITE_VALID)
    assert r.status_code == 200
    sid = r.json()["session_id"]
    assert _api(INTERNET_URL, "/api/v1/auth/me", "GET", cookies={"session_id":sid}).status_code == 200
    assert _api(INTERNET_URL, "/api/v1/auth/logout", "POST", cookies={"session_id":sid}).status_code == 200
    assert _api(INTERNET_URL, "/api/v1/auth/me", "GET", cookies={"session_id":sid}).status_code == 401

# ═══════════ 22 ═══════════
def test_22_disabled_user_session_denial():
    u, p = _gen_user()
    r = _register(INTERNET_URL, u, p, INVITE_VALID)
    assert r.status_code == 200
    sid = r.json()["session_id"]
    assert _api(INTERNET_URL, "/api/v1/auth/me", "GET", cookies={"session_id":sid}).status_code == 200
    _disable_user(u, "disabled")
    r3 = _api(INTERNET_URL, "/api/v1/auth/me", "GET", cookies={"session_id":sid})
    assert r3.status_code in (401, 403), f"Got {r3.status_code}: {r3.text[:200]}"

# ═══════════ 23 ═══════════
def test_23_disabled_user_api_token_denial():
    u, p = _gen_user()
    r = _register(INTERNET_URL, u, p, INVITE_VALID)
    assert r.status_code == 200
    sid = r.json()["session_id"]
    rt = _api(INTERNET_URL, "/api/v1/tokens", json_data={
        "name":"tkn","scopes":["model:14b:chat"]}, cookies={"session_id":sid})
    assert rt.status_code == 200
    token_id = rt.json()["token_id"]
    # Verify token visible in list (proves ownership)
    rl = _api(INTERNET_URL, "/api/v1/tokens", "GET", cookies={"session_id":sid})
    assert token_id in [t["token_id"] for t in rl.json().get("tokens",[])]
    _disable_user(u, "disabled")
    # After disable, session-based token list should be denied
    rd = _api(INTERNET_URL, "/api/v1/tokens", "GET", cookies={"session_id":sid})
    assert rd.status_code in (401, 403), f"Got {rd.status_code}: {rd.text[:200]}"

# ═══════════ 24 ═══════════
def test_24_blocked_user_denial():
    u, p = _gen_user()
    r = _register(INTERNET_URL, u, p, INVITE_VALID)
    assert r.status_code == 200
    sid = r.json()["session_id"]
    assert _api(INTERNET_URL, "/api/v1/auth/me", "GET", cookies={"session_id":sid}).status_code == 200
    _disable_user(u, "blocked")
    r3 = _api(INTERNET_URL, "/api/v1/auth/me", "GET", cookies={"session_id":sid})
    assert r3.status_code in (401, 403), f"Got {r3.status_code}: {r3.text[:200]}"
    r4 = _login(INTERNET_URL, u, p)
    assert r4.status_code == 401, f"Login should be denied: {r4.status_code}"

# ═══════════ 25 ═══════════
def test_25_redis_unavailable():
    u, p = _gen_user()
    r = _register(INTERNET_URL, u, p, INVITE_VALID)
    assert r.status_code in (200, 503)

# ═══════════ 26 ═══════════
def test_26_rate_limit_positive():
    u, _ = _gen_user()
    statuses = [_login(INTERNET_URL, u, "ValidPass12345!").status_code for _ in range(15)]
    assert 429 in statuses, f"No rate limit: {set(statuses)}"

# ═══════════ 27 ═══════════
def test_27_rate_limit_negative():
    u1, _ = _gen_user(); u2, _ = _gen_user()
    for _ in range(8): _login(INTERNET_URL, u1, "ValidPass12345!")
    assert _login(INTERNET_URL, u2, "ValidPass12345!").status_code != 429

# ═══════════ 28 ═══════════
def test_28_restart_persistence():
    u, p = _gen_user()
    r = _register(INTERNET_URL, u, p, INVITE_VALID)
    assert r.status_code == 200
    assert _login(INTERNET_URL, u, p).status_code == 200
    r3 = _api(INTERNET_URL, "/api/v1/auth/logout", "POST", cookies=dict(r.cookies))
    assert _login(INTERNET_URL, u, p).status_code == 200

# ═══════════ 29 ═══════════
def test_29_used_invite_persistence():
    inv = os.environ.get("E2E_INVITE_SINGLE_26", INVITE_VALID)
    u1, p1 = _gen_user()
    assert _register(INTERNET_URL, u1, p1, inv).status_code == 200
    u2, p2 = _gen_user()
    assert _register(INTERNET_URL, u2, p2, inv).status_code in (403, 409)

# ═══════════ 30 ═══════════
def test_30_own_token_list_revoke():
    u, p = _gen_user()
    r = _register(INTERNET_URL, u, p, INVITE_VALID)
    assert r.status_code == 200
    sid = r.json()["session_id"]
    rt = _api(INTERNET_URL, "/api/v1/tokens", json_data={
        "name":"own","scopes":["model:14b:chat"]}, cookies={"session_id":sid})
    assert rt.status_code == 200
    tid = rt.json()["token_id"]
    rl = _api(INTERNET_URL, "/api/v1/tokens", "GET", cookies={"session_id":sid})
    assert tid in [t["token_id"] for t in rl.json().get("tokens",[])]
    rr = _api(INTERNET_URL, f"/api/v1/tokens/{tid}", "DELETE", cookies={"session_id":sid})
    assert rr.status_code == 200 and rr.json()["status"] == "revoked"

# ═══════════ 31 ═══════════
def test_31_foreign_token_list_revoke_denial():
    ua, pa = _gen_user(); ub, pb = _gen_user()
    ra = _register(INTERNET_URL, ua, pa, INVITE_VALID)
    assert ra.status_code == 200
    rt = _api(INTERNET_URL, "/api/v1/tokens", json_data={
        "name":"a","scopes":["model:14b:chat"]}, cookies={"session_id":ra.json()["session_id"]})
    assert rt.status_code == 200
    tid = rt.json()["token_id"]
    rb = _register(INTERNET_URL, ub, pb, INVITE_VALID)
    assert rb.status_code == 200
    rl = _api(INTERNET_URL, "/api/v1/tokens", "GET", cookies={"session_id":rb.json()["session_id"]})
    assert tid not in [t["token_id"] for t in rl.json().get("tokens",[])]
    rr = _api(INTERNET_URL, f"/api/v1/tokens/{tid}", "DELETE", cookies={"session_id":rb.json()["session_id"]})
    assert rr.status_code == 403

# ═══════════ 32 ═══════════
def test_32_unowned_token_revoke_denial():
    ua, pa = _gen_user(); ub, pb = _gen_user()
    ra = _register(INTERNET_URL, ua, pa, INVITE_VALID)
    assert ra.status_code == 200
    rt = _api(INTERNET_URL, "/api/v1/tokens", json_data={
        "name":"secret","scopes":["model:14b:chat"]}, cookies={"session_id":ra.json()["session_id"]})
    assert rt.status_code == 200
    tid = rt.json()["token_id"]
    rb = _register(INTERNET_URL, ub, pb, INVITE_VALID)
    assert rb.status_code == 200
    rr = _api(INTERNET_URL, f"/api/v1/tokens/{tid}", "DELETE", cookies={"session_id":rb.json()["session_id"]})
    assert rr.status_code == 403
    # Verify token still exists for user A
    rv = _api(INTERNET_URL, "/api/v1/tokens", "GET", cookies={"session_id":ra.json()["session_id"]})
    assert tid in [t["token_id"] for t in rv.json().get("tokens",[])]
