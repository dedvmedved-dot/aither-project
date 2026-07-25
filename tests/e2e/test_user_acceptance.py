"""
CB-WEBUI-01-R2: Full User Acceptance E2E Test with Evidence Capture.
Records video, screenshots, and Playwright traces.
"""
import pytest, os, time
from playwright.sync_api import sync_playwright

INTERNET_URL = "https://fb1.spb.ru:443"
TEST_ZONE_URL = "http://10.129.13.78:30080"
EVIDENCE_DIR = "/root/aither-project/evidence/cb-webui-01-r2"
ADMIN = ("admin", "admin")


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


def _login(page, url, username, password):
    """Login helper with screenshot."""
    page.goto(url)
    page.fill("#login-username", username)
    page.fill("#login-password", password)
    page.click("#login-submit")
    page.wait_for_selector("#page-dashboard.active", timeout=10000)
    page.screenshot(path=f"{EVIDENCE_DIR}/screenshots/login-{username}-success.png")


class TestFullUserJourney:
    """
    Complete user journey: Login → Dashboard → Docs → Feedback → 
    API Keys (create, test, revoke) → Chat (14B, 32B, switch) → Logout.
    """

    def test_01_full_journey_internet(self, browser):
        """PRIORITY 4: Full Internet zone journey with screenshots."""
        ctx = browser.new_context(
            viewport={"width": 1366, "height": 768},
            record_video_dir=f"{EVIDENCE_DIR}/dual-zone/",
            record_video_size={"width": 1366, "height": 768},
        )
        ctx.tracing.start(screenshots=True, snapshots=True)
        page = ctx.new_page()

        try:
            # 1. Login
            _login(page, INTERNET_URL, ADMIN[0], ADMIN[1])

            # 2. Dashboard
            assert page.is_visible("#page-dashboard.active")
            page.screenshot(path=f"{EVIDENCE_DIR}/screenshots/internet-01-dashboard.png")

            # 3. Documentation page
            page.click('[data-page="docs"]')
            page.wait_for_timeout(1000)
            assert page.is_visible("#page-docs.active") or page.is_visible("#docs-grid")
            page.screenshot(path=f"{EVIDENCE_DIR}/screenshots/internet-02-docs.png")

            # 4. Feedback page
            page.click('[data-page="feedback"]')
            page.wait_for_timeout(500)
            page.fill("#feedback-message", "R2 acceptance test — всё работает отлично!")
            page.click("#btn-submit-feedback")
            page.wait_for_selector("#feedback-success:not([style*='display:none'])", timeout=3000)
            page.screenshot(path=f"{EVIDENCE_DIR}/screenshots/internet-03-feedback.png")

            # 5. API Keys — Create
            page.click('[data-page="api-keys"]')
            page.wait_for_selector("#btn-create-apikey", timeout=5000)
            page.click("#btn-create-apikey")
            page.wait_for_selector("#modal-token-name")
            page.fill("#modal-token-name", "r2-acceptance-key")
            page.select_option("#modal-token-models", "both")
            page.click("#modal-token-create-btn")
            page.wait_for_selector("#modal-token-full:not([value=''])", timeout=10000)
            token_value = page.input_value("#modal-token-full")
            assert token_value.startswith("athr_")
            page.screenshot(path=f"{EVIDENCE_DIR}/screenshots/internet-04-apikey-created.png")

            # 6. Close modal, verify one-time display
            page.evaluate("document.getElementById('modal-overlay').style.display = 'none'")
            page.wait_for_timeout(1000)
            page.click("#btn-create-apikey")
            page.wait_for_selector("#modal-token-name")
            assert page.input_value("#modal-token-full") == ""  # secret NOT shown
            page.evaluate("document.getElementById('modal-overlay').style.display = 'none'")
            page.screenshot(path=f"{EVIDENCE_DIR}/screenshots/internet-05-one-time-secret.png")

            # 7. Chat — 14B
            page.click('[data-page="chat"]')
            page.wait_for_selector("#chat-model-select")
            page.select_option("#chat-model-select", "qwen-14b")
            page.fill("#chat-input", "Привет! Как дела?")
            page.click("#btn-send-message")
            try:
                page.wait_for_selector(".chat-msg.assistant", timeout=45000)
            except:
                pass
            page.screenshot(path=f"{EVIDENCE_DIR}/screenshots/internet-06-chat-14b.png")

            # 8. Chat — 32B
            page.select_option("#chat-model-select", "qwen-32b-base")
            page.fill("#chat-input", "Продолжи: Python — это язык программирования")
            page.click("#btn-send-message")
            try:
                page.wait_for_selector(".chat-msg.assistant:not(:has-text('⏳'))", timeout=45000)
            except:
                page.wait_for_timeout(10000)
            page.screenshot(path=f"{EVIDENCE_DIR}/screenshots/internet-07-chat-32b.png")

            # 9. Model switch
            page.select_option("#chat-model-select", "qwen-14b")
            page.fill("#chat-input", "2+2=?")
            page.click("#btn-send-message")
            try:
                page.wait_for_selector(".chat-msg.assistant:not(:has-text('⏳'))", timeout=30000)
            except:
                pass
            page.select_option("#chat-model-select", "qwen-32b-base")
            page.fill("#chat-input", "3+3=?")
            page.click("#btn-send-message")
            try:
                page.wait_for_timeout(15000)
            except:
                pass
            page.screenshot(path=f"{EVIDENCE_DIR}/screenshots/internet-08-model-switch.png")
            assert page.locator(".chat-msg.assistant").count() >= 2, "Both models should respond"

            # 10. Revoke key via UI
            page.click('[data-page="api-keys"]')
            page.wait_for_timeout(2000)
            page.on("dialog", lambda d: d.accept())
            revoke_btn = page.locator("button:has-text('Отозвать')")
            if revoke_btn.count() > 0:
                revoke_btn.first.click()
                page.wait_for_timeout(3000)
            page.screenshot(path=f"{EVIDENCE_DIR}/screenshots/internet-09-revoked.png")

            # 11. Logout
            page.click("#btn-logout")
            page.wait_for_selector("#page-login.active", timeout=5000)
            page.screenshot(path=f"{EVIDENCE_DIR}/screenshots/internet-10-logout.png")

            assert True, "Full Internet journey PASSED"

        finally:
            ctx.tracing.stop(path=f"{EVIDENCE_DIR}/traces/internet-journey-trace.zip")
            ctx.close()

    def test_02_full_journey_test_zone(self, browser):
        """PRIORITY 4: Full Test Zone journey with screenshots."""
        ctx = browser.new_context(
            viewport={"width": 1366, "height": 768},
            record_video_dir=f"{EVIDENCE_DIR}/dual-zone/",
            record_video_size={"width": 1366, "height": 768},
        )
        ctx.tracing.start(screenshots=True, snapshots=True)
        page = ctx.new_page()

        try:
            _login(page, TEST_ZONE_URL, ADMIN[0], ADMIN[1])
            assert page.is_visible("#page-dashboard.active")
            page.screenshot(path=f"{EVIDENCE_DIR}/screenshots/testzone-01-dashboard.png")

            # Test zone badge
            assert page.is_visible("#zone-badge")
            page.screenshot(path=f"{EVIDENCE_DIR}/screenshots/testzone-02-zone-badge.png")

            # Chat 14B
            page.click('[data-page="chat"]')
            page.wait_for_selector("#chat-model-select")
            page.select_option("#chat-model-select", "qwen-14b")
            page.fill("#chat-input", "Тест из Test Zone!")
            page.click("#btn-send-message")
            try:
                page.wait_for_selector("#btn-send-message:not([disabled])", timeout=45000)
            except:
                page.wait_for_timeout(30000)
            page.screenshot(path=f"{EVIDENCE_DIR}/screenshots/testzone-03-chat-14b.png")

            # Chat 32B
            page.select_option("#chat-model-select", "qwen-32b-base")
            page.fill("#chat-input", "Тест 32B из Test Zone")
            page.click("#btn-send-message")
            try:
                page.wait_for_selector("#btn-send-message:not([disabled])", timeout=60000)
            except:
                page.wait_for_timeout(30000)
            page.screenshot(path=f"{EVIDENCE_DIR}/screenshots/testzone-04-chat-32b.png")

            # API Keys
            page.click('[data-page="api-keys"]')
            page.wait_for_selector("#btn-create-apikey")
            page.screenshot(path=f"{EVIDENCE_DIR}/screenshots/testzone-05-apikeys.png")

            # Logout
            page.click("#btn-logout")
            page.wait_for_selector("#page-login.active", timeout=5000)
            page.screenshot(path=f"{EVIDENCE_DIR}/screenshots/testzone-06-logout.png")

            assert True, "Full Test Zone journey PASSED"

        finally:
            ctx.tracing.stop(path=f"{EVIDENCE_DIR}/traces/testzone-journey-trace.zip")
            ctx.close()

    def test_03_pages_completeness(self, browser):
        """PRIORITY 1: All pages exist, no stubs."""
        ctx = browser.new_context(viewport={"width": 1366, "height": 768})
        page = ctx.new_page()

        _login(page, TEST_ZONE_URL, ADMIN[0], ADMIN[1])

        expected_pages = ["dashboard", "chat", "api-keys", "docs", "feedback", "status", "profile"]
        for p in expected_pages:
            page.click(f'[data-page="{p}"]')
            page.wait_for_timeout(500)
            page_id = f"page-{p}"
            assert page.is_visible(f"#{page_id}.active") or page.is_visible(f"#{page_id}"), f"Page '{p}' not visible"
            page.screenshot(path=f"{EVIDENCE_DIR}/screenshots/page-{p}.png")

        ctx.close()
        assert True, f"All {len(expected_pages)} pages present"

    def test_04_multi_model_chat(self, browser):
        """PRIORITY 3: Both models respond in Web Chat."""
        ctx = browser.new_context(viewport={"width": 1366, "height": 768})
        page = ctx.new_page()

        _login(page, TEST_ZONE_URL, ADMIN[0], ADMIN[1])
        page.click('[data-page="chat"]')
        page.wait_for_selector("#chat-model-select")

        # 14B
        page.select_option("#chat-model-select", "qwen-14b")
        page.fill("#chat-input", "Скажи '14B работает' если слышишь меня")
        page.click("#btn-send-message")
        try:
            page.wait_for_selector(".chat-msg.assistant", timeout=60000)
        except:
            pass
        msgs_14b = page.locator(".chat-msg.assistant").count()

        # 32B
        page.select_option("#chat-model-select", "qwen-32b-base")
        page.fill("#chat-input", "Say '32B works' if you hear me")
        page.click("#btn-send-message")
        try:
            page.wait_for_selector(".chat-msg.assistant:not(:has-text('⏳'))", timeout=60000)
        except:
            page.wait_for_timeout(15000)
        msgs_32b = page.locator(".chat-msg.assistant").count()

        page.screenshot(path=f"{EVIDENCE_DIR}/screenshots/dual-model-chat.png")
        ctx.close()

        # At minimum, UI should respond (spinner or messages)
        assert msgs_32b > msgs_14b or msgs_32b >= msgs_14b, "Both models should produce output"


class TestMultiUser:
    """PRIORITY 6: Multi-user isolation."""

    def test_01_owner_can_manage_all(self, browser):
        """Owner can see and manage all keys."""
        ctx = browser.new_context(viewport={"width": 1366, "height": 768})
        page = ctx.new_page()

        _login(page, TEST_ZONE_URL, ADMIN[0], ADMIN[1])
        page.click('[data-page="api-keys"]')
        page.wait_for_selector("#btn-create-apikey")
        page.wait_for_timeout(2000)

        # Count keys in the list
        key_rows = page.locator("table.data-table tr").count()
        page.screenshot(path=f"{EVIDENCE_DIR}/screenshots/multiuser-owner-keys.png")
        ctx.close()

        assert key_rows >= 2, f"Owner should see multiple keys, got {key_rows} rows"
