"""CB-WEBUI-01 E2E Tests — Playwright"""
import pytest
from playwright.sync_api import sync_playwright, Page, expect
import re

BASE_URL = "http://10.129.13.78:30080"
ADMIN_USER = "admin"
ADMIN_PASS = "admin"

@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()

@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 1366, "height": 768})
    page = context.new_page()
    yield page
    context.close()

def login(page, username=ADMIN_USER, password=ADMIN_PASS):
    page.goto(BASE_URL)
    page.fill("#login-username", username)
    page.fill("#login-password", password)
    page.click("#login-submit")
    page.wait_for_selector("#page-dashboard.active", timeout=10000)

class TestLogin:
    def test_login_success(self, page):
        login(page)
        assert page.is_visible("#page-dashboard.active")
        assert page.text_content("#nav-username") == ADMIN_USER

    def test_login_failure(self, page):
        page.goto(BASE_URL)
        page.fill("#login-username", "wrong")
        page.fill("#login-password", "wrong")
        page.click("#login-submit")
        page.wait_for_selector("#login-error:not([style*='display:none'])", timeout=5000)
        assert page.is_visible("#login-error")

    def test_logout(self, page):
        login(page)
        page.click("#btn-logout")
        page.wait_for_selector("#page-login.active", timeout=5000)
        assert page.is_visible("#page-login.active")

class TestChat:
    def test_chat_14b(self, page):
        login(page)
        page.click('[data-page="chat"]')
        page.wait_for_selector("#chat-model-select", timeout=5000)
        # Select 14B model
        page.select_option("#chat-model-select", "qwen-14b")
        # Send message
        page.fill("#chat-input", "Привет! Как дела?")
        page.click("#btn-send-message")
        # Wait for response (up to 60s)
        page.wait_for_selector(".chat-msg.assistant:not(:has-text('⏳'))", timeout=60000)
        # Verify response exists
        messages = page.locator(".chat-msg.assistant")
        assert messages.count() >= 1

    def test_chat_32b(self, page):
        login(page)
        page.click('[data-page="chat"]')
        page.wait_for_selector("#chat-model-select", timeout=5000)
        page.select_option("#chat-model-select", "qwen-32b-base")
        page.fill("#chat-input", "Продолжи: Искусственный интеллект — это")
        page.click("#btn-send-message")
        page.wait_for_selector(".chat-msg.assistant:not(:has-text('⏳'))", timeout=60000)
        messages = page.locator(".chat-msg.assistant")
        assert messages.count() >= 1

    def test_model_switch(self, page):
        login(page)
        page.click('[data-page="chat"]')
        page.wait_for_selector("#chat-model-select", timeout=5000)
        # Chat with 14B
        page.select_option("#chat-model-select", "qwen-14b")
        page.fill("#chat-input", "Коротко: 2+2=?")
        page.click("#btn-send-message")
        page.wait_for_timeout(15000)
        # Switch to 32B
        page.select_option("#chat-model-select", "qwen-32b-base")
        page.fill("#chat-input", "Продолжи: Python это")
        page.click("#btn-send-message")
        page.wait_for_selector(".chat-msg.assistant:not(:has-text('⏳'))", timeout=60000)
        # Should have messages from both models
        messages = page.locator(".chat-msg.assistant")
        assert messages.count() >= 2

class TestAPIKeys:
    def test_create_key(self, page):
        login(page)
        page.click('[data-page="api-keys"]')
        page.wait_for_selector("#btn-create-apikey", timeout=5000)
        page.click("#btn-create-apikey")
        page.wait_for_selector("#modal-token-name", timeout=5000)
        page.fill("#modal-token-name", "e2e-test-key")
        page.select_option("#modal-token-models", "both")
        page.click("#modal-token-create-btn")
        # Wait for token to appear
        page.wait_for_selector("#modal-token-full:not([value=''])", timeout=10000)
        token_value = page.input_value("#modal-token-full")
        assert token_value.startswith("athr_")
        assert len(token_value) > 20

    def test_key_one_time_display(self, page):
        login(page)
        page.click('[data-page="api-keys"]')
        page.wait_for_selector("#btn-create-apikey", timeout=5000)
        page.click("#btn-create-apikey")
        page.wait_for_selector("#modal-token-name", timeout=5000)
        page.fill("#modal-token-name", "one-time-test")
        page.click("#modal-token-create-btn")
        page.wait_for_selector("#modal-token-full:not([value=''])", timeout=10000)
        # Close modal
        page.click("text=Отмена")
        # Reopen API keys - should NOT show full secret
        page.click("#btn-create-apikey")
        page.wait_for_selector("#modal-token-name", timeout=5000)
        # The modal should have empty full key field
        assert page.input_value("#modal-token-full") == ""

    def test_revoke_key(self, page):
        login(page)
        page.click('[data-page="api-keys"]')
        page.wait_for_selector("#btn-create-apikey", timeout=5000)
        # Create a key
        page.click("#btn-create-apikey")
        page.wait_for_selector("#modal-token-name", timeout=5000)
        page.fill("#modal-token-name", "revoke-test")
        page.click("#modal-token-create-btn")
        page.wait_for_selector("#modal-token-full:not([value=''])", timeout=10000)
        token_value = page.input_value("#modal-token-full")
        page.click("text=Отмена")
        page.wait_for_timeout(1000)
        # Revoke it
        page.on("dialog", lambda d: d.accept())
        revoke_btn = page.locator("button:has-text('Отозвать')").first
        if revoke_btn.is_visible():
            revoke_btn.click()
            page.wait_for_timeout(2000)
        # Verify the key no longer works via API
        import requests, urllib3
        urllib3.disable_warnings()
        r = requests.get("https://localhost:443/api/v1/models",
                        headers={"Authorization": f"Bearer {token_value}"},
                        verify=False)
        assert r.status_code == 401
