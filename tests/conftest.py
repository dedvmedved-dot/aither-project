"""
Aither AI Platform — shared test fixtures and configuration.

Pytest conftest providing:
- Base URLs for Internet and Test zones
- Admin auth fixture
- HTTP session fixtures (real requests with TLS verification disabled)
- Test data constants

Usage:
    cd /root/aither-project && python -m pytest tests/ -v
"""

import os
import warnings

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.exceptions import InsecureRequestWarning


# ── Environment variable overrides ──────────────────────────────────
INTERNET_BASE_URL = os.environ.get("AITHER_INTERNET_URL", "https://localhost:443")
TEST_ZONE_BASE_URL = os.environ.get("AITHER_TEST_ZONE_URL", "http://10.129.13.78:30080")

ADMIN_USERNAME = os.environ.get("AITHER_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("AITHER_ADMIN_PASS", "admin")

# Suppress InsecureRequestWarning for local/dev TLS (cert is for fb1.spb.ru)
warnings.filterwarnings("ignore", category=InsecureRequestWarning)


# ── Helper: create a requests session with TLS verification disabled ─
def _create_verify_off_session() -> requests.Session:
    """Create a requests Session with TLS verification disabled (for dev)."""
    sess = requests.Session()
    sess.verify = False
    # Retry adapter for flaky network
    adapter = HTTPAdapter(max_retries=2)
    sess.mount("https://", adapter)
    sess.mount("http://", adapter)
    return sess


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def base_url():
    """Base URL for the Internet-zone BFF API (no trailing slash).

    Defaults to https://localhost:443 but can be overridden via
    AITHER_INTERNET_URL env var.
    """
    return INTERNET_BASE_URL


@pytest.fixture(scope="session")
def test_zone_url():
    """Base URL for the Test-zone BFF API (HTTP, no TLS).

    Defaults to http://10.129.13.78:30080 but can be overridden via
    AITHER_TEST_ZONE_URL env var.
    """
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
    """Requests session with TLS verification disabled (for dev certs)."""
    return _create_verify_off_session()


@pytest.fixture(scope="session")
def admin_credentials():
    """Admin username and password tuple."""
    return ADMIN_USERNAME, ADMIN_PASSWORD


@pytest.fixture(scope="session")
def admin_auth_headers(http_session, api_base, admin_credentials):
    """Authenticate with admin credentials and return auth headers + session cookie.

    Returns a dict with:
        - 'Authorization': Bearer token (if the API returns one)
        - 'Cookie': session cookie (for cookie-based auth)
        - 'session_id': raw session identifier
    """
    username, password = admin_credentials
    resp = http_session.post(
        f"{api_base}/auth/login",
        json={"username": username, "password": password},
        timeout=30,
    )
    if resp.status_code == 200:
        data = resp.json()
        headers = {"Content-Type": "application/json"}
        # Check for bearer token
        token = data.get("access_token") or data.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        # Pass through cookies
        if resp.cookies:
            cookie_str = "; ".join(
                f"{c.name}={c.value}" for c in resp.cookies
            )
            headers["Cookie"] = cookie_str
        # Store session id for reference
        headers["X-Session-ID"] = data.get("session_id", "")
        return headers
    else:
        pytest.fail(
            f"Admin auth failed: {resp.status_code} {resp.text[:300]}"
        )


@pytest.fixture(scope="session")
def admin_cookies(http_session, api_base, admin_credentials):
    """Return just the cookies dict after admin login (for non-JSON API calls)."""
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
    """A fresh HTTP session (no auth state) for each test."""
    return _create_verify_off_session()


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
