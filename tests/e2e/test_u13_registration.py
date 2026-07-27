"""
U1.3-OPS-R7-R6 — Registration E2E Acceptance Tests (28 tests)
Tests: input validation, invite validation, successful registration,
       post-login, duplicate prevention, scope verification.
Covers both zones via Playwright UI and direct API calls.
"""
import os, uuid, pytest, requests
from playwright.sync_api import sync_playwright, expect

# ── Environment ────────────────────────────────────────────────
def _env(name, fallback=None):
    val = os.environ.get(name)
    if not val and fallback is None:
        pytest.fail(f"Environment variable {name} is required but not set")
    return val or fallback

BETA01_USER = _env("E2E_BETA01_USERNAME")
INVITE_A = _env("E2E_INVITE_A", "hj_GFaoJFq7KFeg3uclyOfCLS6D6P56Y")
INVITE_B = _env("E2E_INVITE_B", "aLHmu-2OI5L5nu9Z44mlZ-Zikoc5qmBH")

ZONES = {
    "Internet":  "https://fb1.spb.ru:443",
    "Test Zone": "http://10.129.13.78:30080",
}
BROWSERS = ["chromium", "firefox"]

def _gen_test_user():
    uid = uuid.uuid4().hex[:8]
    return f"regtest_{uid}", f"TestPass_{uid}_!2345"


# ═══════════════════════════════════════════════════════════════
#  PLAYWRIGHT UI TESTS (12 tests)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("browser_type", BROWSERS)
@pytest.mark.parametrize("zone_name,url", list(ZONES.items()))
def test_reg_form_accessible(browser_type, zone_name, url):
    """01-04: Registration form is accessible from login page."""
    with sync_playwright() as p:
        browser = getattr(p, browser_type).launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1366, "height": 768})
        page = ctx.new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)
        expect(page.locator("#page-login")).to_be_visible(timeout=10000)
        expect(page.locator("#btn-show-register")).to_be_visible(timeout=10000)
        page.click("#btn-show-register")
        expect(page.locator("#page-register")).to_be_visible(timeout=10000)
        expect(page.locator("#reg-username")).to_be_visible()
        expect(page.locator("#reg-password")).to_be_visible()
        expect(page.locator("#reg-password-confirm")).to_be_visible()
        expect(page.locator("#reg-invite")).to_be_visible()
        expect(page.locator("#register-submit")).to_be_visible()
        browser.close()


@pytest.mark.parametrize("zone_name,url", list(ZONES.items()))
def test_reg_invalid_invite_ui(zone_name, url):
    """05-06: UI shows error for invalid invite code."""
    username, password = _gen_test_user()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1366, "height": 768})
        page = ctx.new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.click("#btn-show-register")
        expect(page.locator("#page-register")).to_be_visible(timeout=10000)
        page.fill("#reg-username", username)
        page.fill("#reg-password", password)
        page.fill("#reg-password-confirm", password)
        page.fill("#reg-invite", "INVALID_CODE_12345")
        page.click("#register-submit")
        page.wait_for_timeout(2000)
        # Should stay on register page (error shown)
        expect(page.locator("#page-register")).to_be_visible(timeout=5000)
        expect(page.locator("#register-error")).to_be_visible(timeout=5000)
        browser.close()


@pytest.mark.parametrize("zone_name,url", list(ZONES.items()))
def test_reg_successful_ui(zone_name, url):
    """07-08: Successful registration via UI redirects to dashboard."""
    username, password = _gen_test_user()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1366, "height": 768})
        page = ctx.new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.click("#btn-show-register")
        expect(page.locator("#page-register")).to_be_visible(timeout=10000)
        page.fill("#reg-username", username)
        page.fill("#reg-password", password)
        page.fill("#reg-password-confirm", password)
        page.fill("#reg-invite", INVITE_A)
        page.click("#register-submit")
        # Success redirects to dashboard after 2s
        page.wait_for_timeout(3000)
        expect(page.locator("#page-dashboard")).to_be_visible(timeout=15000)
        expect(page.locator("#nav-username")).to_have_text(username)
        browser.close()


@pytest.mark.parametrize("zone_name,url", list(ZONES.items()))
def test_reg_post_login_ui(zone_name, url):
    """09-10: User can log in after registration."""
    username, password = _gen_test_user()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1366, "height": 768})
        page = ctx.new_page()

        # Register
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.click("#btn-show-register")
        expect(page.locator("#page-register")).to_be_visible(timeout=10000)
        page.fill("#reg-username", username)
        page.fill("#reg-password", password)
        page.fill("#reg-password-confirm", password)
        page.fill("#reg-invite", INVITE_B)
        page.click("#register-submit")
        page.wait_for_timeout(3000)
        expect(page.locator("#page-dashboard")).to_be_visible(timeout=15000)

        # Logout
        page.click("#btn-logout")
        page.wait_for_timeout(1000)
        expect(page.locator("#page-login")).to_be_visible(timeout=10000)

        # Login with new credentials
        page.fill("#login-username", username)
        page.fill("#login-password", password)
        page.click("#login-submit")
        expect(page.locator("#page-dashboard")).to_be_visible(timeout=15000)
        expect(page.locator("#nav-username")).to_have_text(username)
        browser.close()


@pytest.mark.parametrize("zone_name,url", list(ZONES.items()))
def test_reg_duplicate_username_ui(zone_name, url):
    """11-12: Duplicate username registration is rejected."""
    username, password = _gen_test_user()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1366, "height": 768})

        # First registration — succeeds
        page = ctx.new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.click("#btn-show-register")
        expect(page.locator("#page-register")).to_be_visible(timeout=10000)
        page.fill("#reg-username", username)
        page.fill("#reg-password", password)
        page.fill("#reg-password-confirm", password)
        page.fill("#reg-invite", INVITE_A)
        page.click("#register-submit")
        page.wait_for_timeout(3000)
        expect(page.locator("#page-dashboard")).to_be_visible(timeout=15000)
        # Wait for nav bar with logout button to render
        expect(page.locator("#btn-logout")).to_be_visible(timeout=10000)
        page.click("#btn-logout")
        # Wait for logout to complete — login page must appear
        page.wait_for_timeout(2000)
        expect(page.locator("#page-login")).to_be_visible(timeout=10000)
        page.close()

        # Second registration with same username — fails
        page2 = ctx.new_page()
        page2.goto(url, wait_until="networkidle", timeout=30000)
        expect(page2.locator("#page-login")).to_be_visible(timeout=10000)
        expect(page2.locator("#btn-show-register")).to_be_visible(timeout=5000)
        page2.click("#btn-show-register")
        expect(page2.locator("#page-register")).to_be_visible(timeout=10000)
        page2.fill("#reg-username", username)
        page2.fill("#reg-password", "Different_Pass_999!")
        page2.fill("#reg-password-confirm", "Different_Pass_999!")
        page2.fill("#reg-invite", INVITE_B)
        page2.click("#register-submit")
        page2.wait_for_timeout(2000)
        expect(page2.locator("#page-register")).to_be_visible(timeout=5000)
        expect(page2.locator("#register-error")).to_be_visible(timeout=5000)
        browser.close()


# ═══════════════════════════════════════════════════════════════
#  DIRECT API TESTS (16 tests)
# ═══════════════════════════════════════════════════════════════

def _post_register(url, username, password, confirm, invite):
    return requests.post(
        f"{url}/api/v1/auth/register",
        json={
            "username": username,
            "password": password,
            "password_confirmation": confirm,
            "invite_code": invite,
        },
        timeout=15,
        verify=False,
    )


@pytest.mark.parametrize("zone_name,url", list(ZONES.items()))
def test_api_invalid_username_short(zone_name, url):
    """13-14: Reject username < 3 chars."""
    r = _post_register(url, "ab", "ValidPass12345!", "ValidPass12345!", INVITE_A)
    assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text[:100]}"


@pytest.mark.parametrize("zone_name,url", list(ZONES.items()))
def test_api_invalid_username_chars(zone_name, url):
    """15-16: Reject username with invalid characters."""
    r = _post_register(url, "bad user!", "ValidPass12345!", "ValidPass12345!", INVITE_A)
    assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text[:100]}"


@pytest.mark.parametrize("zone_name,url", list(ZONES.items()))
def test_api_reserved_username(zone_name, url):
    """17-18: Reject reserved usernames."""
    for name in ["admin", "root", "system"]:
        r = _post_register(url, name, "ValidPass12345!", "ValidPass12345!", INVITE_A)
        assert r.status_code == 400, f"Expected 400 for '{name}', got {r.status_code}: {r.text[:100]}"


@pytest.mark.parametrize("zone_name,url", list(ZONES.items()))
def test_api_password_short(zone_name, url):
    """19-20: Reject password < 12 chars."""
    username, _ = _gen_test_user()
    r = _post_register(url, username, "Short1!", "Short1!", INVITE_A)
    assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text[:100]}"


@pytest.mark.parametrize("zone_name,url", list(ZONES.items()))
def test_api_password_mismatch(zone_name, url):
    """21-22: Reject password confirmation mismatch."""
    username, _ = _gen_test_user()
    r = _post_register(url, username, "ValidPass12345!", "DifferentPass99!", INVITE_A)
    assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text[:100]}"


@pytest.mark.parametrize("zone_name,url", list(ZONES.items()))
def test_api_password_equals_username(zone_name, url):
    """23-24: Reject password matching username."""
    username, _ = _gen_test_user()
    r = _post_register(url, username, username, username, INVITE_A)
    assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text[:100]}"


@pytest.mark.parametrize("zone_name,url", list(ZONES.items()))
def test_api_invalid_invite(zone_name, url):
    """25-26: Reject invalid invite code."""
    username, password = _gen_test_user()
    r = _post_register(url, username, password, password, "INVALID_FAKE_CODE")
    assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text[:100]}"


@pytest.mark.parametrize("zone_name,url", list(ZONES.items()))
def test_api_successful_registration(zone_name, url):
    """27-28: Successful registration returns session + scopes."""
    username, password = _gen_test_user()
    r = _post_register(url, username, password, password, INVITE_A)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert data["status"] == "ok"
    assert "session_id" in data
    assert data["user"]["username"] == username
    assert data["user"]["role"] == "registered_user"
    assert "model_scopes" in data["user"]
    scopes = data["user"]["model_scopes"]
    assert "model:14b:chat" in scopes, f"Missing 14b scope in {scopes}"
    assert "model:32b:chat-adapter" in scopes, f"Missing 32b scope in {scopes}"
    assert "session_id" in r.cookies or "set-cookie" in str(r.headers).lower()
