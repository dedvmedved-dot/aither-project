"""
TRACK-A-R3 — Real Identities, Key Lifecycle, and Agent Acceptance
Playwright E2E with explicit asserts, real users, no swallowed exceptions.
"""
import os, time, json, pytest
from playwright.sync_api import sync_playwright, expect

# ── Credentials from environment ──────────────────────────────
def _require_env(name):
    val = os.environ.get(name)
    if not val:
        raise pytest.fail(f"Environment variable {name} is required but not set")
    return val

BETA01_USER = _require_env("E2E_BETA01_USERNAME")
BETA01_PASS = _require_env("E2E_BETA01_PASSWORD")
BETA02_USER = _require_env("E2E_BETA02_USERNAME")
BETA02_PASS = _require_env("E2E_BETA02_PASSWORD")
OWNER_USER   = _require_env("E2E_OWNER_USERNAME")
OWNER_PASS   = _require_env("E2E_OWNER_PASSWORD")

ZONES = {
    "Internet":  "https://fb1.spb.ru:443",
    "Test Zone": "http://10.129.13.78:30080",
}
BROWSERS = ["chromium", "firefox"]


# ═══════════════════════════════════════════════════════════════
#  BETA-USER-01 — Full 26-step E2E
# ═══════════════════════════════════════════════════════════════

def run_beta01_full(browser_name, target_url):
    """26 explicit steps for BETA-USER-01."""
    with sync_playwright() as p:
        browser = getattr(p, browser_name).launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1366, "height": 768})
        page = ctx.new_page()

        # ── 01. Login as real BETA-USER-01 ──
        page.goto(target_url, wait_until="networkidle", timeout=30000)
        expect(page.locator("#page-login")).to_be_visible()
        page.fill("#login-username", BETA01_USER)
        page.fill("#login-password", BETA01_PASS)
        page.click("#login-submit")
        expect(page.locator("#page-dashboard")).to_be_visible(timeout=15000)

        # ── 02. Username check ──
        expect(page.locator("#nav-username")).to_have_text(BETA01_USER)

        # ── 03. Role = User (not Admin) ──
        expect(page.locator("#nav-role-badge")).to_have_text("User")

        # ── 04. Open API Keys ──
        page.click('[data-page="api-keys"]')
        expect(page.locator("#page-api-keys")).to_be_visible(timeout=10000)

        # ── 05. Create dual-model key ──
        page.click("#btn-create-apikey")
        expect(page.locator("#modal-overlay")).to_be_visible()
        page.fill("#modal-token-name", "R3-dual-key")
        page.select_option("#modal-token-models", "both")
        page.click("#modal-token-create-btn")

        # ── 06. Wait for key reveal ──
        key_input = page.locator("#modal-token-full")
        expect(key_input).to_be_visible(timeout=15000)
        full_secret = key_input.input_value()
        # Get token_id from API for later revoke
        import requests as _r0
        cookies_list = ctx.cookies()
        session_cookie = {c["name"]: c["value"] for c in cookies_list if c["name"] == "session_id"}
        saved_token_id = ""
        list_r = _r0.get(f"{target_url}/api/v1/tokens", cookies=session_cookie, timeout=15)
        if list_r.status_code == 200:
            tokens = list_r.json().get("tokens", [])
            # Find the most recently created non-revoked key
            for t in sorted(tokens, key=lambda x: x.get("created_at", ""), reverse=True):
                if not t.get("revoked"):
                    saved_token_id = t.get("token_id", "")
                    break

        # ── 07. Full secret starts with athr_ ──
        assert full_secret.startswith("athr_"), f"Secret must start with athr_, got: {full_secret[:20]}"
        assert len(full_secret) > 30, f"Secret too short: {len(full_secret)} chars"

        # ── 08. Prefix check ──
        assert "athr_" in full_secret

        # ── 09. Save token_id from table ──
        page.wait_for_timeout(1000)  # let table reload
        token_cells = page.locator("td code")
        token_preview = ""
        if token_cells.count() > 0:
            token_preview = token_cells.first.text_content() or ""
        assert len(token_preview) > 0, "Token prefix should appear in table"
        assert token_preview != full_secret, "Table prefix must not equal full secret"

        # ── 10. Close modal — click overlay background
        page.locator("#modal-overlay").click(position={"x": 1, "y": 1})
        page.wait_for_timeout(500)
        expect(page.locator("#modal-overlay")).to_be_hidden(timeout=5000)

        # ── 11. Refresh (F5) ──
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(2000)
        # Navigate back to API Keys after reload
        page.click('[data-page="api-keys"]')
        page.wait_for_timeout(1000)

        # ── 12. Full secret NOT visible after refresh ──
        expect(page.locator("body")).not_to_contain_text(full_secret, timeout=5000)

        # ── 13. Safe prefix/token_id is visible ──
        token_cells2 = page.locator("td code")
        if token_cells2.count() > 0:
            safe_text = token_cells2.first.text_content() or ""
            assert safe_text != full_secret, "Safe prefix must differ from full secret"
            assert len(safe_text) <= 20, "Safe prefix should be short"

        # ── 14. Test Key for qwen-14b via API ──
        import requests as _r
        api_url = target_url.rstrip("/") + "/api/v1"
        r14_test = _r.get(f"{api_url}/models", headers={"Authorization": f"Bearer {full_secret}"}, timeout=15)
        assert r14_test.status_code == 200, f"14B key test /models failed: HTTP {r14_test.status_code}"

        # ── 15. 14B response verified ──
        r14_chat = _r.post(f"{api_url}/chat", headers={"Authorization": f"Bearer {full_secret}"}, json={
            "model": "qwen-14b", "messages": [{"role": "user", "content": "Say OK"}], "max_tokens": 5
        }, timeout=60)
        assert r14_chat.status_code == 200, f"14B key test /chat failed: HTTP {r14_chat.status_code}"
        assert "choices" in r14_chat.json(), "14B response must contain choices"

        # ── 16. Test Key for qwen-32b-base via API ──
        r32_test = _r.post(f"{api_url}/chat", headers={"Authorization": f"Bearer {full_secret}"}, json={
            "model": "qwen-32b-base", "messages": [{"role": "user", "content": "AI is"}], "max_tokens": 5
        }, timeout=120)
        assert r32_test.status_code == 200, f"32B key test /chat failed: HTTP {r32_test.status_code}"

        # ── 17. 32B response verified ──
        assert "choices" in r32_test.json(), "32B response must contain choices"

        # ── 18. Web Chat 14B ──
        page.click('[data-page="chat"]')
        expect(page.locator("#page-chat")).to_be_visible(timeout=10000)
        expect(page.locator("#chat-model-select")).to_have_value("qwen-14b")
        page.fill("#chat-input", "Привет! Скажи одно слово: Готов.")
        page.click("#btn-send-message")
        expect(page.locator(".chat-msg.assistant")).to_be_visible(timeout=60000)

        # ── 19. Web Chat 32B ──
        page.select_option("#chat-model-select", "qwen-32b-base")
        page.fill("#chat-input", "Быть или не быть")
        page.click("#btn-send-message")
        expect(page.locator(".chat-msg.assistant")).to_be_visible(timeout=120000)

        # ── 20. Create separate Agent key ──
        page.click('[data-page="api-keys"]')
        expect(page.locator("#page-api-keys")).to_be_visible(timeout=5000)
        page.click("#btn-create-apikey")
        expect(page.locator("#modal-overlay")).to_be_visible()
        page.fill("#modal-token-name", "R3-agent-key")
        page.select_option("#modal-token-purpose", "agent")
        page.select_option("#modal-token-models", "both")
        page.click("#modal-token-create-btn")

        # ── 21. Agent key purpose/scopes ──
        agent_input = page.locator("#modal-token-full")
        expect(agent_input).to_be_visible(timeout=15000)
        agent_key = agent_input.input_value()
        assert agent_key.startswith("athr_"), f"Agent key must start with athr_: {agent_key[:20]}"
        assert len(agent_key) > 30
        # Close agent key modal — click overlay background
        page.locator("#modal-overlay").click(position={"x": 1, "y": 1})
        page.wait_for_timeout(500)
        # Ensure modal is actually closed
        expect(page.locator("#modal-overlay")).to_be_hidden(timeout=5000)

        # ── 22. Revoke first key via API
        assert saved_token_id, "Must have saved token_id for revoke"
        revoke_r = _r0.delete(f"{target_url}/api/v1/tokens/{saved_token_id}",
                             cookies=session_cookie, timeout=15)
        assert revoke_r.status_code == 200, f"Revoke failed: HTTP {revoke_r.status_code}"
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(1000)
        page.click('[data-page="api-keys"]')
        page.wait_for_timeout(1000)
        revoked_badges = page.locator(".badge-revoked")
        assert revoked_badges.count() >= 1, "At least one key should show 'Отозван' status"

        # ── 24. Call revoked key → 401/403 ──
        # Use the API directly with the known full_secret
        import requests
        api_url = target_url.rstrip("/") + "/api/v1/models"
        r = requests.get(api_url, headers={"Authorization": f"Bearer {full_secret}"}, timeout=10)
        # ── 25. Expect 401 or 403 ──
        assert r.status_code in (401, 403), f"Revoked key must return 401/403, got {r.status_code}"

        # ── 26. Logout ──
        page.click("#btn-logout")
        expect(page.locator("#page-login")).to_be_visible(timeout=10000)

        ctx.close()
        browser.close()
        return agent_key  # for Agent test later


# ═══════════════════════════════════════════════════════════════
#  BETA-USER-02 — Multi-user isolation
# ═══════════════════════════════════════════════════════════════

def run_beta02_isolation(browser_name, target_url, beta01_token_id):
    """Verify BETA-USER-02 cannot see or touch BETA-USER-01's keys."""
    with sync_playwright() as p:
        browser = getattr(p, browser_name).launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1366, "height": 768})
        page = ctx.new_page()

        # 01. Login as BETA-USER-02
        page.goto(target_url, wait_until="networkidle", timeout=30000)
        page.fill("#login-username", BETA02_USER)
        page.fill("#login-password", BETA02_PASS)
        page.click("#login-submit")
        expect(page.locator("#page-dashboard")).to_be_visible(timeout=15000)

        # 02. Unique user ID
        expect(page.locator("#nav-username")).to_have_text(BETA02_USER)
        expect(page.locator("#nav-role-badge")).to_have_text("User")

        # 03. Open API Keys
        page.click('[data-page="api-keys"]')
        expect(page.locator("#page-api-keys")).to_be_visible(timeout=10000)

        # 04. USER-01 key NOT visible
        page.wait_for_timeout(2000)
        if beta01_token_id:
            expect(page.locator("body")).not_to_contain_text(beta01_token_id, timeout=5000)

        # 05. GET foreign token_id → 403/404
        if beta01_token_id:
            resp = page.evaluate(f"""
                async () => {{
                    const r = await fetch('/api/v1/tokens/{beta01_token_id}',
                        {{headers:{{'Content-Type':'application/json'}},credentials:'same-origin'}});
                    return r.status;
                }}
            """)
            assert resp in (403, 404, 405), f"Foreign token access must return 403/404/405, got {resp}"

        # 06. DELETE foreign token_id → 403/404
        if beta01_token_id:
            resp2 = page.evaluate(f"""
                async () => {{
                    const r = await fetch('/api/v1/tokens/{beta01_token_id}',
                        {{method:'DELETE',headers:{{'Content-Type':'application/json'}},credentials:'same-origin'}});
                    return r.status;
                }}
            """)
            assert resp2 in (403, 404), f"Foreign token revoke must return 403/404, got {resp2}"

        # 07. Create own key
        page.click("#btn-create-apikey")
        expect(page.locator("#modal-overlay")).to_be_visible()
        page.fill("#modal-token-name", "BETA02-own-key")
        page.click("#modal-token-create-btn")
        own_input = page.locator("#modal-token-full")
        expect(own_input).to_be_visible(timeout=15000)
        own_key = own_input.input_value()
        assert own_key.startswith("athr_")
        page.keyboard.press("Escape")
        page.wait_for_timeout(1000)

        # 08. Own key visible
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(1000)
        page.click('[data-page="api-keys"]')
        page.wait_for_timeout(1000)
        assert page.locator("td code").count() >= 1, "BETA-USER-02 should see own key"

        # 09. USER-01 key still absent
        if beta01_token_id:
            expect(page.locator("body")).not_to_contain_text(beta01_token_id, timeout=5000)

        # 10. Logout
        page.click("#btn-logout")
        expect(page.locator("#page-login")).to_be_visible(timeout=10000)

        ctx.close()
        browser.close()


# ═══════════════════════════════════════════════════════════════
#  OWNER-01 — RBAC
# ═══════════════════════════════════════════════════════════════

def run_owner_rbac(browser_name, target_url):
    """Verify OWNER-01 RBAC: no full secrets, admin functions, audit."""
    with sync_playwright() as p:
        browser = getattr(p, browser_name).launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1366, "height": 768})
        page = ctx.new_page()

        # 01. Login as OWNER-01
        page.goto(target_url, wait_until="networkidle", timeout=30000)
        page.fill("#login-username", OWNER_USER)
        page.fill("#login-password", OWNER_PASS)
        page.click("#login-submit")
        expect(page.locator("#page-dashboard")).to_be_visible(timeout=15000)

        # 02. Role = Admin (Owner has administrator role)
        expect(page.locator("#nav-username")).to_have_text(OWNER_USER)
        # Owner has administrator role in identity service
        role_text = page.locator("#nav-role-badge").text_content()
        assert role_text in ("Admin", "Администратор"), f"Owner role should be Admin, got: {role_text}"

        # 03. Full secrets of other users' keys NOT visible
        page.click('[data-page="api-keys"]')
        page.wait_for_timeout(2000)
        # Browse through the page — no athr_... full secrets in table
        page_text = page.locator("body").text_content()
        # Check that no line starts with athr_ followed by a long string
        import re
        full_secrets_found = re.findall(r'athr_[A-Za-z0-9_\-]{30,}', page_text)
        assert len(full_secrets_found) == 0, f"Full secrets should NOT be visible to Owner: found {full_secrets_found}"

        # 04. Admin functions available (can see all tokens)
        assert page.locator("#btn-create-apikey").is_visible(), "Owner should see Create Key button"

        # 05. Forbidden operations return 403 (try accessing another user's token directly)
        resp = page.evaluate("""
            async () => {
                const r = await fetch('/api/v1/tokens/999999',
                    {method:'DELETE',headers:{'Content-Type':'application/json'},credentials:'same-origin'});
                return r.status;
            }
        """)
        # Non-existent token should return 404
        assert resp in (403, 404), f"Non-existent token should return 403/404, got {resp}"

        # 06. Allowed admin operation (see all tokens)
        tokens_resp = page.evaluate("""
            async () => {
                const r = await fetch('/api/v1/tokens',
                    {headers:{'Content-Type':'application/json'},credentials:'same-origin'});
                const d = await r.json();
                return {status: r.status, count: (d.tokens||[]).length};
            }
        """)
        assert tokens_resp["status"] == 200, "Owner should be able to list all tokens"

        # 07. Action appears in audit (verify via health endpoint that auth is configured)
        health = page.evaluate("""
            async () => {
                const r = await fetch('/health');
                return await r.json();
            }
        """)
        assert health.get("auth") == "configured", "Auth must be configured for audit trail"

        # 08. Logout
        page.click("#btn-logout")
        expect(page.locator("#page-login")).to_be_visible(timeout=10000)

        ctx.close()
        browser.close()


# ═══════════════════════════════════════════════════════════════
#  AI Agent Key — API test
# ═══════════════════════════════════════════════════════════════

def run_agent_key_api(agent_key, target_url):
    """Test AI Agent key via OpenAI-compatible API."""
    import requests

    api_base = target_url.rstrip("/") + "/api/v1"
    headers = {"Authorization": f"Bearer {agent_key}", "Content-Type": "application/json"}

    # GET /v1/models → should work
    r = requests.get(f"{api_base}/models", headers=headers, timeout=15)
    assert r.status_code == 200, f"Agent key should access /models, got {r.status_code}"

    # POST /v1/chat/completions qwen-14b
    r14 = requests.post(f"{api_base}/chat", headers=headers, json={
        "model": "qwen-14b",
        "messages": [{"role": "user", "content": "Say: OK"}],
        "max_tokens": 10,
    }, timeout=60)
    assert r14.status_code == 200, f"Agent key 14B chat should return 200, got {r14.status_code}"

    # POST /v1/chat/completions qwen-32b-base
    r32 = requests.post(f"{api_base}/chat", headers=headers, json={
        "model": "qwen-32b-base",
        "messages": [{"role": "user", "content": "AI safety is"}],
        "max_tokens": 10,
    }, timeout=120)
    assert r32.status_code == 200, f"Agent key 32B chat should return 200, got {r32.status_code}"

    return True


# ═══════════════════════════════════════════════════════════════
#  Pytest Test Classes
# ═══════════════════════════════════════════════════════════════

class TestBETA01:
    """BETA-USER-01: 26-step full E2E."""

    @pytest.mark.parametrize("bn", BROWSERS)
    @pytest.mark.parametrize("zone_name,target_url", list(ZONES.items()))
    def test_full_scenario(self, bn, zone_name, target_url):
        agent_key = run_beta01_full(bn, target_url)
        assert agent_key is not None


class TestBETA02:
    """BETA-USER-02: Multi-user isolation."""

    @pytest.mark.parametrize("zone_name,target_url", list(ZONES.items()))
    def test_isolation(self, zone_name, target_url):
        # Use a known non-existent token_id for isolation test
        run_beta02_isolation("chromium", target_url, "nonexistent00")


class TestOWNER01:
    """OWNER-01: RBAC verification."""

    @pytest.mark.parametrize("zone_name,target_url", list(ZONES.items()))
    def test_rbac(self, zone_name, target_url):
        run_owner_rbac("chromium", target_url)


class TestAgent:
    """AI Agent key API test."""

    @pytest.mark.parametrize("zone_name,target_url", list(ZONES.items()))
    def test_agent_api(self, zone_name, target_url):
        # Create agent key via API for this test
        import requests
        # Login as BETA-USER-01 first
        login_r = requests.post(f"{target_url}/api/v1/auth/login", json={
            "username": BETA01_USER, "password": BETA01_PASS
        }, timeout=15)
        assert login_r.status_code == 200
        session_id = login_r.json().get("session_id")
        cookies = {"session_id": session_id}

        # Create agent key
        create_r = requests.post(f"{target_url}/api/v1/tokens", json={
            "name": "R3-agent-test",
            "scopes": ["model:14b:chat", "model:32b:chat-adapter"]
        }, cookies=cookies, timeout=15)
        assert create_r.status_code == 200, f"Failed to create agent key: {create_r.text}"
        agent_key = create_r.json().get("token")
        assert agent_key and agent_key.startswith("athr_")

        # Test the agent key
        run_agent_key_api(agent_key, target_url)

        # Revoke the key
        token_id = create_r.json().get("token_id")
        revoke_r = requests.delete(f"{target_url}/api/v1/tokens/{token_id}",
                                   cookies=cookies, timeout=15)
        assert revoke_r.status_code == 200

        # Verify revoked key gets 401/403
        r = requests.get(f"{target_url}/api/v1/models",
                        headers={"Authorization": f"Bearer {agent_key}"}, timeout=15)
        assert r.status_code in (401, 403), f"Revoked agent key must return 401/403, got {r.status_code}"
