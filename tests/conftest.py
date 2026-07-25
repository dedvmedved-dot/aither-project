"""
Aither AI Platform — shared test fixtures and configuration (R2: TRUSTED TLS ONLY).

Pytest conftest providing:
- Base URLs for Internet and Test zones
- Admin auth fixture
- HTTP session fixtures (verify=True — trusted TLS only)
- Test data constants

Usage:
    cd /root/aither-project && python -m pytest tests/ -v
"""

import os
import pytest
import requests


# ── Environment variable overrides ──────────────────────────────────
INTERNET_BASE_URL = os.environ.get("AITHER_INTERNET_URL", "https://fb1.spb.ru:443")
TEST_ZONE_BASE_URL = os.environ.get("AITHER_TEST_ZONE_URL", "http://10.129.13.78:30080")

ADMIN_USERNAME = os.environ.get("AITHER_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("AITHER_ADMIN_PASS", "admin")

# NO verify=False. NO InsecureRequestWarning suppression. Trusted TLS only.


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def base_url():
    """Base URL for the Internet-zone BFF API (no trailing slash)."""
    return INTERNET_BASE_URL


@pytest.fixture(scope="session")
def test_zone_url():
    """Base URL for the Test-zone BFF API (HTTP, no TLS)."""
    return TEST_ZONE_BASE_URL


@pytest.fixture(scope="session")
def api_base(base_url):
    """Full API base path: <base_url>/api/v1"""
    return f"{base_url}/api/v1"


@pytest.fixture(scope="session")
def test_api_base(test_zone_url):
    """Full API base path for test zone: <test_zone_url>/api/v1"""
    return f"{test_zone_url}/api/v1"


@pytest.fixture(scope="session")
def http_session():
    """Requests session with TRUSTED TLS (verify=True, default). No verify=False."""
    return requests.Session()


@pytest.fixture(scope="session")
def admin_credentials():
    """Admin username and password tuple."""
    return ADMIN_USERNAME, ADMIN_PASSWORD


@pytest.fixture(scope="session")
def admin_auth_headers(http_session, api_base, admin_credentials):
    """Authenticate with admin credentials and return auth headers + session cookie."""
    username, password = admin_credentials
    resp = http_session.post(
        f"{api_base}/auth/login",
        json={"username": username, "password": password},
        timeout=30,
    )
    if resp.status_code == 200:
        data = resp.json()
        headers = {"Content-Type": "application/json"}
        token = data.get("access_token") or data.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if resp.cookies:
            cookie_str = "; ".join(f"{c.name}={c.value}" for c in resp.cookies)
            headers["Cookie"] = cookie_str
        headers["X-Session-ID"] = data.get("session_id", "")
        return headers
    else:
        pytest.fail(f"Admin auth failed: {resp.status_code} {resp.text[:300]}")


@pytest.fixture(scope="session")
def admin_cookies(http_session, api_base, admin_credentials):
    """Return just the cookies dict after admin login."""
    username, password = admin_credentials
    resp = http_session.post(
        f"{api_base}/auth/login",
        json={"username": username, "password": password},
        timeout=30,
    )
    if resp.status_code == 200:
        return dict(resp.cookies)
    pytest.fail(f"Admin auth (cookies) failed: {resp.status_code} {resp.text[:300]}")


@pytest.fixture
def fresh_http_session():
    """A fresh HTTP session with trusted TLS (verify=True)."""
    return requests.Session()


# ── Test data ───────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def test_models():
    """Known model IDs used by the platform."""
    return {
        "14b_chat": "qwen-14b",
        "14b_vllm": "qwen2.5-14b",
        "32b_base": "qwen-32b-base",
        "32b_vllm": "qwen2.5-32b",
    }


@pytest.fixture(scope="session")
def known_scopes():
    """All known scope strings for the platform."""
    return [
        "model:14b:chat",
        "model:32b:chat-adapter",
        "model:32b:completion",
    ]
