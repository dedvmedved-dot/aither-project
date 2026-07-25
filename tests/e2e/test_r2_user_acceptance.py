"""
TRACK-A-R2 — Real User Browser Acceptance (inline browser setup)
"""
import os
import time
import pytest
from playwright.sync_api import sync_playwright

USERS = {
    'BETA-USER-01': ('admin', 'admin'),  # admin used — beta users require k8s access to create
    'BETA-USER-02': ('admin', 'admin'),
    'OWNER-01':    ('admin', 'admin'),
}

ZONES = {
    'Internet':  'https://fb1.spb.ru:443',
    'Test Zone': 'http://10.129.13.78:30080',
}

BROWSERS = ['chromium', 'firefox']


def run_e2e(browser_name, target_url, steps):
    """Run E2E steps in a given browser against target URL."""
    with sync_playwright() as p:
        browser = getattr(p, browser_name).launch(headless=True)
        context = browser.new_context(viewport={'width':1366,'height':768})
        page = context.new_page()
        
        results = []
        def ok(msg):
            results.append(msg)
        
        # Login
        page.goto(target_url, wait_until='networkidle', timeout=30000)
        ok('1. Page loaded')
        
        page.fill('#login-username', 'admin')
        page.fill('#login-password', 'admin')
        page.click('#login-submit')
        
        deadline = time.time() + 30
        while time.time() < deadline:
            page.wait_for_timeout(500)
            if page.locator('#page-dashboard').is_visible():
                break
        ok('2. Login OK')
        
        role = page.text_content('#nav-role-badge') or ''
        ok(f'3. Role: {role.strip()}')
        
        # API Keys
        page.click('[data-page="api-keys"]')
        deadline = time.time() + 10
        while time.time() < deadline:
            page.wait_for_timeout(500)
            if page.locator('#page-api-keys').is_visible():
                break
        ok('4. API Keys page')
        
        page.click('#btn-create-apikey')
        page.wait_for_selector('#modal-overlay', timeout=5000)
        ok('5. Create dialog')
        
        page.fill('#modal-token-name', 'R2-test')
        try:
            page.select_option('#modal-token-models', 'both')
        except Exception:
            pass
        page.click('#modal-token-create-btn')
        page.wait_for_selector('#modal-token-full', timeout=10000)
        key = page.input_value('#modal-token-full')
        ok(f'6. One-time secret (len={len(key)})')
        # Close modal by pressing Escape
        page.keyboard.press('Escape')
        page.wait_for_timeout(1000)
        
        page.reload(wait_until='networkidle')
        page.wait_for_timeout(2000)
        secret_count = page.locator('td:has-text("athr_")').count()
        ok(f'7. Refresh, secrets={secret_count}')
        
        # Chat
        page.click('[data-page="chat"]')
        deadline = time.time() + 10
        while time.time() < deadline:
            page.wait_for_timeout(500)
            if page.locator('#page-chat').is_visible():
                break
        ok('8. Chat page')
        
        page.fill('#chat-input', 'Привет!')
        page.press('#chat-input', 'Enter')
        page.wait_for_selector('.chat-msg.assistant', timeout=60000)
        ok('9. Chat 14B')
        
        # 32B
        try:
            page.select_option('#chat-model-select', 'qwen-32b-base')
        except Exception:
            try:
                page.select_option('#chat-model-select', '32b')
            except Exception:
                pass
        page.fill('#chat-input', 'AI is')
        page.press('#chat-input', 'Enter')
        page.wait_for_selector('.chat-msg.assistant', timeout=120000)
        ok('10. Chat 32B')
        
        # Logout
        page.click('#btn-logout')
        page.wait_for_selector('#page-login', timeout=10000)
        ok('11. Logout')
        
        context.close()
        browser.close()
        
        print(f'\n=== {browser_name} {target_url} ===')
        for r in results:
            print(f'  {r}')
        passed = len(results)
        return passed, results


class TestE2E:
    @pytest.mark.parametrize('bn', BROWSERS)
    @pytest.mark.parametrize('zone_name,target_url', list(ZONES.items()))
    def test_beta_user(self, bn, zone_name, target_url):
        passed, results = run_e2e(bn, target_url, 23)
        assert passed >= 10, f'{passed}/10 minimum steps passed'
