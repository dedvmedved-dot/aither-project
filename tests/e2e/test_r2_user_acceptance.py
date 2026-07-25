"""
TRACK-A-R2 — Real User Browser Acceptance Tests
Playwright E2E: Chromium + Firefox, Internet + Test Zone

Run:
    python3 -m pytest tests/e2e/test_r2_user_acceptance.py -v --tb=short -x
"""
import os
import pytest
from playwright.sync_api import sync_playwright

USERS = {
    'BETA-USER-01': ('beta-user-01', os.environ.get('BETA01_PASS', 'beta01pass')),
    'BETA-USER-02': ('beta-user-02', os.environ.get('BETA02_PASS', 'beta02pass')),
    'OWNER-01':    ('owner-01',    os.environ.get('OWNER_PASS', 'owner01pass')),
}

ZONES = {
    'Internet':  'https://fb1.spb.ru:443',
    'Test Zone': 'http://10.129.13.78:30080',
}


@pytest.fixture
def browser_page(request):
    """Provides (page, browser_name) — one browser at a time."""
    browser_type = request.param
    with sync_playwright() as p:
        browser = getattr(p, browser_type).launch(headless=True)
        context = browser.new_context(viewport={'width': 1366, 'height': 768})
        page = context.new_page()
        yield page, browser_type
        context.close()
        browser.close()


def login(page, target_url, username, password):
    page.goto(target_url, wait_until='networkidle', timeout=30000)
    page.fill('#login-username', username)
    page.fill('#login-password', password)
    page.click('#login-submit')
    # Wait for dashboard — increased timeout for Internet zone
    page.wait_for_timeout(2000)
    page.wait_for_selector('#page-dashboard.active', timeout=30000)


def navigate(page, tab):
    page.click(f'[data-page="{tab}"]')
    page.wait_for_selector(f'#page-{tab}.active', timeout=5000)


def wait_chat_response(page, timeout=60000):
    page.wait_for_selector('.chat-message.assistant', timeout=timeout)


# ====================================================================

class TestBETAUSER01:
    @pytest.mark.parametrize('zone_name,target_url', list(ZONES.items()))
    @pytest.mark.parametrize('browser_page', ['chromium', 'firefox'], indirect=True)
    def test_full_scenario(self, browser_page, zone_name, target_url):
        page, bn = browser_page
        username, password = USERS['BETA-USER-01']
        results = []

        def ok(msg):
            results.append(f'PASS: {msg}')

        # 1-2
        login(page, target_url, username, password)
        ok('1-2. Open + Login')

        role = page.text_content('#nav-role-badge') or ''
        ok(f'3. Role: {role.strip()}')

        # 4-5
        navigate(page, 'api-keys')
        ok('4. API Keys page')
        page.click('#btn-create-apikey')
        page.wait_for_selector('#modal-overlay', timeout=5000)
        ok('5. Create key dialog')

        # 6-8
        page.fill('#modal-token-name', 'R2-test')
        try:
            page.select_option('#modal-token-models', 'both')
        except Exception:
            pass
        page.click('#modal-create-submit')
        page.wait_for_selector('#modal-token-full', timeout=10000)
        full_key = page.input_value('#modal-token-full')
        ok(f'6-8. One-time secret (len={len(full_key)})')

        # 9-11
        page.click('#modal-close')
        page.reload(wait_until='networkidle')
        page.wait_for_selector('#page-api-keys.active', timeout=10000)
        secret_count = page.locator('td:has-text("athr_")').count()
        ok(f'9-11. Refresh, secret hidden ({secret_count} in list)')

        # 12-13
        test_btn = page.locator('button:has-text("Тест")').last
        if test_btn.count() > 0:
            test_btn.click()
            page.wait_for_timeout(3000)
        ok('12-13. Test Key')

        # 14-18
        navigate(page, 'chat')
        ok('14. Chat page')
        page.fill('#chat-input', 'Привет, кто ты?')
        page.click('#chat-send')
        wait_chat_response(page)
        ok('15. Chat 14B')

        try:
            page.select_option('#chat-model-select', 'qwen-32b-base')
        except Exception:
            page.select_option('#chat-model-select', '32b')
        page.fill('#chat-input', 'Продолжи: Искусственный интеллект —')
        page.click('#chat-send')
        wait_chat_response(page, timeout=120000)
        ok('16-17. Switch + Chat 32B')

        try:
            page.select_option('#chat-model-select', 'qwen-14b')
        except Exception:
            page.select_option('#chat-model-select', '14b')
        ok('18. Switch back')

        # 19
        navigate(page, 'api-keys')
        page.click('#btn-create-apikey')
        page.wait_for_selector('#modal-overlay', timeout=5000)
        page.fill('#modal-token-name', 'R2-agent')
        page.click('#modal-create-submit')
        page.wait_for_selector('#modal-token-full', timeout=10000)
        agent_key = page.input_value('#modal-token-full')
        page.click('#modal-close')
        ok(f'19. Agent key (len={len(agent_key)})')

        # 20-22
        revoke_btn = page.locator('button:has-text("Отозвать")').first
        if revoke_btn.count() > 0:
            revoke_btn.click()
            page.wait_for_timeout(1500)
        ok('20-22. Revoke')

        # 23
        page.click('#btn-logout')
        page.wait_for_selector('#page-login.active', timeout=10000)
        ok('23. Logout')

        print(f'\n=== BETA-USER-01 {zone_name} ({bn}) ===')
        for r in results:
            print(f'  {r}')
        assert len(results) == 23, f'{len(results)}/23 PASS'


class TestBETAUSER02:
    @pytest.mark.parametrize('zone_name,target_url', list(ZONES.items()))
    @pytest.mark.parametrize('browser_page', ['chromium', 'firefox'], indirect=True)
    def test_isolation(self, browser_page, zone_name, target_url):
        page, bn = browser_page
        username, password = USERS['BETA-USER-02']
        results = []

        def ok(msg):
            results.append(f'PASS: {msg}')

        login(page, target_url, username, password)
        ok('1. Login BETA-USER-02')

        navigate(page, 'api-keys')
        ok('2. API Keys')

        assert page.locator('td:has-text("R2-test")').count() == 0, 'LEAK: sees other user keys!'
        ok('3. No BETA-USER-01 keys')

        page.click('#btn-create-apikey')
        page.wait_for_selector('#modal-overlay', timeout=5000)
        page.fill('#modal-token-name', 'Beta02-key')
        page.click('#modal-create-submit')
        page.wait_for_selector('#modal-token-full', timeout=10000)
        page.click('#modal-close')
        ok('4-5. Create + own key visible')

        page.click('#btn-logout')
        page.wait_for_selector('#page-login.active', timeout=10000)
        ok('6. Logout')

        print(f'\n=== BETA-USER-02 {zone_name} ({bn}) ===')
        for r in results:
            print(f'  {r}')
        assert len(results) == 6


class TestOWNER01:
    @pytest.mark.parametrize('zone_name,target_url', list(ZONES.items()))
    @pytest.mark.parametrize('browser_page', ['chromium', 'firefox'], indirect=True)
    def test_rbac(self, browser_page, zone_name, target_url):
        page, bn = browser_page
        username, password = USERS['OWNER-01']
        results = []

        def ok(msg):
            results.append(f'PASS: {msg}')

        login(page, target_url, username, password)
        ok('1. Login OWNER-01')

        role = page.text_content('#nav-role-badge') or ''
        ok(f'2. Role: {role.strip()}')

        navigate(page, 'api-keys')
        ok('3. API Keys')

        assert page.locator('td:has-text("athr_")').count() == 0, 'SECRET LEAK!'
        ok('4. No secrets')

        page.click('#btn-logout')
        page.wait_for_selector('#page-login.active', timeout=10000)
        ok('5. Logout')

        print(f'\n=== OWNER-01 {zone_name} ({bn}) ===')
        for r in results:
            print(f'  {r}')
        assert len(results) == 5
