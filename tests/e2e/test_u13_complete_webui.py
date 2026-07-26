"""
U1.3-WUI — Complete User Web UI E2E Acceptance Tests
Tests: chat, dual-model, API keys (KEY_A/KEY_B), agent connection, zones, browsers.
"""
import os, pytest, requests
from playwright.sync_api import sync_playwright, expect

# ── Credentials ────────────────────────────────────────────────
def _env(name):
    val = os.environ.get(name)
    if not val:
        pytest.fail(f"Environment variable {name} is required but not set")
    return val

BETA01_USER = _env("E2E_BETA01_USERNAME")
BETA01_PASS = _env("E2E_BETA01_PASSWORD")
BETA02_USER = _env("E2E_BETA02_USERNAME")
BETA02_PASS = _env("E2E_BETA02_PASSWORD")

ZONES = {
    "Internet":  "https://fb1.spb.ru:443",
    "Test Zone": "http://10.129.13.78:30080",
}
BROWSERS = ["chromium", "firefox"]

MODEL_A = "qwen-14b"
MODEL_B = "qwen-32b-base"

# ═══════════════════════════════════════════════════════════════
#  Helper: login via browser
# ═══════════════════════════════════════════════════════════════

def login(page, target_url, username, password):
    page.goto(target_url, wait_until="networkidle", timeout=30000)
    expect(page.locator("#page-login")).to_be_visible()
    page.fill("#login-username", username)
    page.fill("#login-password", password)
    page.click("#login-submit")
    expect(page.locator("#page-dashboard")).to_be_visible(timeout=15000)
    # Verify nav populated
    expect(page.locator("#nav-username")).to_have_text(username)


# ═══════════════════════════════════════════════════════════════
#  Helper: send chat message and wait for response
# ═══════════════════════════════════════════════════════════════

def chat_send(page, model_value, message, timeout=120000):
    """Select model, send message, wait for assistant response."""
    page.click('[data-page="chat"]')
    page.wait_for_timeout(500)
    page.select_option("#chat-model-select", model_value)
    page.wait_for_timeout(500)
    page.fill("#chat-input", message)
    page.click("#btn-send-message")
    expect(page.locator(".chat-msg.assistant")).to_be_visible(timeout=timeout)


# ═══════════════════════════════════════════════════════════════
#  Helper: create API key via Web UI
# ═══════════════════════════════════════════════════════════════

def create_key_via_ui(page, key_name, model_value):
    """Create API key, return (full_secret, token_id)."""
    page.click('[data-page="api-keys"]')
    page.wait_for_timeout(500)
    page.click("#btn-create-apikey")
    expect(page.locator("#modal-overlay")).to_be_visible()
    page.fill("#modal-token-name", key_name)
    if model_value:
        page.select_option("#modal-token-models", model_value)
    page.click("#modal-token-create-btn")

    key_input = page.locator("#modal-token-full")
    expect(key_input).to_be_visible(timeout=15000)
    full_secret = key_input.input_value()
    assert full_secret.startswith("athr_"), f"Key must start with athr_: {full_secret[:20]}"

    # Get token_id from API
    cookies = page.context.cookies()
    session_cookie = {c["name"]: c["value"] for c in cookies if c["name"] == "session_id"}
    list_r = requests.get(
        f"{page.url.rstrip('/').replace('/index.html','').replace('#','')}/api/v1/tokens",
        cookies=session_cookie, timeout=15, verify=True
    )
    token_id = ""
    if list_r.status_code == 200:
        tokens = list_r.json().get("tokens", [])
        for t in sorted(tokens, key=lambda x: x.get("created_at", ""), reverse=True):
            if not t.get("revoked"):
                token_id = t.get("token_id", "")
                break

    # Close modal via overlay click
    page.locator("#modal-overlay").click(position={"x": 1, "y": 1})
    page.wait_for_timeout(500)
    expect(page.locator("#modal-overlay")).to_be_hidden(timeout=5000)

    return full_secret, token_id


# ═══════════════════════════════════════════════════════════════
#  Test: Chat — MODEL_A and MODEL_B
# ═══════════════════════════════════════════════════════════════

class TestChat:
    """WUI-CHAT-001 through WUI-CHAT-008"""

    @pytest.mark.parametrize("bn", BROWSERS)
    @pytest.mark.parametrize("zone_name,target_url", list(ZONES.items()))
    def test_chat_model_a(self, bn, zone_name, target_url):
        """Chat with MODEL_A (qwen-14b)"""
        with sync_playwright() as p:
            browser = getattr(p, bn).launch(headless=True)
            ctx = browser.new_context(viewport={"width": 1366, "height": 768})
            page = ctx.new_page()

            login(page, target_url, BETA01_USER, BETA01_PASS)
            chat_send(page, MODEL_A, "Привет! Скажи одно слово: Готов.")

            ctx.close()
            browser.close()

    @pytest.mark.parametrize("bn", BROWSERS)
    @pytest.mark.parametrize("zone_name,target_url", list(ZONES.items()))
    def test_chat_model_b(self, bn, zone_name, target_url):
        """Chat with MODEL_B (qwen-32b-base)"""
        with sync_playwright() as p:
            browser = getattr(p, bn).launch(headless=True)
            ctx = browser.new_context(viewport={"width": 1366, "height": 768})
            page = ctx.new_page()

            login(page, target_url, BETA01_USER, BETA01_PASS)
            chat_send(page, MODEL_B, "Заверши фразу: Искусственный интеллект — это", timeout=180000)

            ctx.close()
            browser.close()

    @pytest.mark.parametrize("bn", BROWSERS)
    @pytest.mark.parametrize("zone_name,target_url", list(ZONES.items()))
    def test_model_switch(self, bn, zone_name, target_url):
        """Switch between models in chat"""
        with sync_playwright() as p:
            browser = getattr(p, bn).launch(headless=True)
            ctx = browser.new_context(viewport={"width": 1366, "height": 768})
            page = ctx.new_page()

            login(page, target_url, BETA02_USER, BETA02_PASS)
            chat_send(page, MODEL_A, "Hi.")
            # Switch to MODEL_B and send another message
            page.select_option("#chat-model-select", MODEL_B)
            page.fill("#chat-input", "Hello again.")
            page.click("#btn-send-message")
            expect(page.locator(".chat-msg.assistant").last).to_be_visible(timeout=180000)

            ctx.close()
            browser.close()


# ═══════════════════════════════════════════════════════════════
#  Test: API Keys — KEY_A and KEY_B
# ═══════════════════════════════════════════════════════════════

class TestApiKeys:
    """WUI-KEY-001 through WUI-KEY-008"""

    @pytest.mark.parametrize("zone_name,target_url", list(ZONES.items()))
    def test_key_a_creation(self, zone_name, target_url):
        """Create KEY_A (14b-only) via Web UI"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(viewport={"width": 1366, "height": 768})
            page = ctx.new_page()

            login(page, target_url, BETA01_USER, BETA01_PASS)
            full_secret, token_id = create_key_via_ui(page, f"U13-KEY-A-{zone_name[:4]}", "qwen-14b")

            # Verify key works for 14B
            api_base = target_url.rstrip("/") + "/api/v1"
            r = requests.post(
                f"{api_base}/chat",
                headers={"Authorization": f"Bearer {full_secret}"},
                json={"model": MODEL_A, "messages": [{"role": "user", "content": "OK"}], "max_tokens": 3},
                timeout=60, verify=True
            )
            assert r.status_code == 200, f"KEY_A should access MODEL_A, got {r.status_code}"

            # Revoke
            if token_id:
                cookies = ctx.cookies()
                sc = {c["name"]: c["value"] for c in cookies if c["name"] == "session_id"}
                requests.delete(f"{target_url}/api/v1/tokens/{token_id}", cookies=sc, timeout=15, verify=True)

            ctx.close()
            browser.close()

    @pytest.mark.parametrize("zone_name,target_url", list(ZONES.items()))
    def test_key_b_creation(self, zone_name, target_url):
        """Create KEY_B (32b-only) via Web UI"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(viewport={"width": 1366, "height": 768})
            page = ctx.new_page()

            login(page, target_url, BETA02_USER, BETA02_PASS)
            full_secret, token_id = create_key_via_ui(page, f"U13-KEY-B-{zone_name[:4]}", "qwen-32b-base")

            # Verify key works for 32B
            api_base = target_url.rstrip("/") + "/api/v1"
            r = requests.post(
                f"{api_base}/chat",
                headers={"Authorization": f"Bearer {full_secret}"},
                json={"model": MODEL_B, "messages": [{"role": "user", "content": "AI is"}], "max_tokens": 3},
                timeout=120, verify=True
            )
            assert r.status_code == 200, f"KEY_B should access MODEL_B, got {r.status_code}"

            # Revoke
            if token_id:
                cookies = ctx.cookies()
                sc = {c["name"]: c["value"] for c in cookies if c["name"] == "session_id"}
                requests.delete(f"{target_url}/api/v1/tokens/{token_id}", cookies=sc, timeout=15, verify=True)

            ctx.close()
            browser.close()

    def test_one_time_secret(self):
        """One-time secret: full secret hidden after modal close"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(viewport={"width": 1366, "height": 768})
            page = ctx.new_page()

            login(page, ZONES["Internet"], BETA01_USER, BETA01_PASS)
            full_secret, token_id = create_key_via_ui(page, "U13-ONETIME", "qwen-14b")

            # After modal close, full secret should NOT be visible
            page.reload(wait_until="networkidle")
            page.wait_for_timeout(1000)
            page.click('[data-page="api-keys"]')
            page.wait_for_timeout(1000)
            expect(page.locator("body")).not_to_contain_text(full_secret, timeout=5000)

            # Revoke
            if token_id:
                cookies = ctx.cookies()
                sc = {c["name"]: c["value"] for c in cookies if c["name"] == "session_id"}
                requests.delete(f"{ZONES['Internet']}/api/v1/tokens/{token_id}", cookies=sc, timeout=15, verify=True)

            ctx.close()
            browser.close()

    def test_revoke_denial(self):
        """Revoked key returns 401/403"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(viewport={"width": 1366, "height": 768})
            page = ctx.new_page()

            login(page, ZONES["Internet"], BETA01_USER, BETA01_PASS)
            full_secret, token_id = create_key_via_ui(page, "U13-REVOKE-TEST", "both")

            assert token_id, "Must have token_id for revoke"
            cookies = ctx.cookies()
            sc = {c["name"]: c["value"] for c in cookies if c["name"] == "session_id"}

            # Revoke
            r = requests.delete(
                f"{ZONES['Internet']}/api/v1/tokens/{token_id}",
                cookies=sc, timeout=15, verify=True
            )
            assert r.status_code == 200, f"Revoke failed: {r.status_code}"

            # Verify revoked
            r2 = requests.get(
                f"{ZONES['Internet']}/api/v1/models",
                headers={"Authorization": f"Bearer {full_secret}"},
                timeout=10, verify=True
            )
            assert r2.status_code in (401, 403), f"Revoked key must return 401/403, got {r2.status_code}"

            ctx.close()
            browser.close()


# ═══════════════════════════════════════════════════════════════
#  Test: AI Agent Connection
# ═══════════════════════════════════════════════════════════════

class TestAgent:
    """AGENT-001 through AGENT-004"""

    @pytest.mark.parametrize("zone_name,target_url", list(ZONES.items()))
    def test_agent_model_a(self, zone_name, target_url):
        """AI Agent connects to MODEL_A"""
        api_base = target_url.rstrip("/") + "/api/v1"

        # Create key via API
        login_r = requests.post(f"{target_url}/api/v1/auth/login", json={
            "username": BETA01_USER, "password": BETA01_PASS
        }, timeout=15, verify=True)
        assert login_r.status_code == 200
        session_id = login_r.json().get("session_id")
        cookies = {"session_id": session_id}

        create_r = requests.post(f"{target_url}/api/v1/tokens", json={
            "name": "U13-AGENT-A", "scopes": ["model:14b:chat"]
        }, cookies=cookies, timeout=15, verify=True)
        assert create_r.status_code == 200
        key = create_r.json().get("token")
        token_id = create_r.json().get("token_id")

        # Agent request to MODEL_A
        r = requests.post(f"{api_base}/chat", headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json"
        }, json={"model": MODEL_A, "messages": [{"role": "user", "content": "Say: OK"}], "max_tokens": 5}, timeout=60, verify=True)
        assert r.status_code == 200, f"Agent MODEL_A failed: {r.status_code}"
        assert "choices" in r.json()

        # Cleanup
        requests.delete(f"{target_url}/api/v1/tokens/{token_id}", cookies=cookies, timeout=15, verify=True)

    @pytest.mark.parametrize("zone_name,target_url", list(ZONES.items()))
    def test_agent_model_b(self, zone_name, target_url):
        """AI Agent connects to MODEL_B"""
        api_base = target_url.rstrip("/") + "/api/v1"

        login_r = requests.post(f"{target_url}/api/v1/auth/login", json={
            "username": BETA02_USER, "password": BETA02_PASS
        }, timeout=15, verify=True)
        assert login_r.status_code == 200
        session_id = login_r.json().get("session_id")
        cookies = {"session_id": session_id}

        create_r = requests.post(f"{target_url}/api/v1/tokens", json={
            "name": "U13-AGENT-B", "scopes": ["model:32b:chat-adapter"]
        }, cookies=cookies, timeout=15, verify=True)
        assert create_r.status_code == 200
        key = create_r.json().get("token")
        token_id = create_r.json().get("token_id")

        r = requests.post(f"{api_base}/chat", headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json"
        }, json={"model": MODEL_B, "messages": [{"role": "user", "content": "AI is"}], "max_tokens": 5}, timeout=120, verify=True)
        assert r.status_code == 200, f"Agent MODEL_B failed: {r.status_code}"

        requests.delete(f"{target_url}/api/v1/tokens/{token_id}", cookies=cookies, timeout=15, verify=True)

    @pytest.mark.parametrize("zone_name,target_url", list(ZONES.items()))
    def test_agent_revoked_denial(self, zone_name, target_url):
        """Revoked agent key returns 401/403"""
        login_r = requests.post(f"{target_url}/api/v1/auth/login", json={
            "username": BETA01_USER, "password": BETA01_PASS
        }, timeout=15, verify=True)
        session_id = login_r.json().get("session_id")
        cookies = {"session_id": session_id}

        create_r = requests.post(f"{target_url}/api/v1/tokens", json={
            "name": "U13-AGENT-REVOKE", "scopes": ["model:14b:chat"]
        }, cookies=cookies, timeout=15, verify=True)
        key = create_r.json().get("token")
        token_id = create_r.json().get("token_id")

        # Revoke
        requests.delete(f"{target_url}/api/v1/tokens/{token_id}", cookies=cookies, timeout=15, verify=True)

        # Should be denied
        r = requests.get(f"{target_url.rstrip('/')}/api/v1/models", headers={
            "Authorization": f"Bearer {key}"
        }, timeout=10, verify=True)
        assert r.status_code in (401, 403), f"Revoked agent key must return 401/403, got {r.status_code}"


# ═══════════════════════════════════════════════════════════════
#  Test: UI Sanity
# ═══════════════════════════════════════════════════════════════

class TestUISanity:
    """Web UI sanity checks"""

    @pytest.mark.parametrize("zone_name,target_url", list(ZONES.items()))
    def test_agent_page_accessible(self, zone_name, target_url):
        """AI Agent page renders correctly"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(viewport={"width": 1366, "height": 768})
            page = ctx.new_page()

            login(page, target_url, BETA01_USER, BETA01_PASS)
            page.click('[data-page="agent"]')
            page.wait_for_timeout(1000)
            expect(page.locator("#page-agent")).to_be_visible()
            expect(page.locator("#agent-content")).to_be_visible()

            ctx.close()
            browser.close()

    @pytest.mark.parametrize("zone_name,target_url", list(ZONES.items()))
    def test_dashboard_populated(self, zone_name, target_url):
        """Dashboard shows user info after login"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(viewport={"width": 1366, "height": 768})
            page = ctx.new_page()

            login(page, target_url, BETA02_USER, BETA02_PASS)

            # Dashboard should have populated data
            expect(page.locator("#dash-username")).not_to_be_empty()
            expect(page.locator("#dash-role")).not_to_be_empty()
            expect(page.locator("#dash-zone")).not_to_be_empty()
            expect(page.locator("#nav-username")).to_have_text(BETA02_USER)

            ctx.close()
            browser.close()
