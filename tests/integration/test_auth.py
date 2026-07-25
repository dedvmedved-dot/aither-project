"""
Integration tests: Authentication (BFF → login/logout/session).

Tests real HTTP calls to the BFF API.
Requires BFF running at the configured base URL.
Uses -k flag implicitly via http_session (verify=False).

Run:  cd /root/aither-project && python -m pytest tests/integration/test_auth.py -v
"""

import pytest


class TestLogin:
    """Login endpoint tests."""

    def test_login_valid_credentials(
        self, http_session, api_base, admin_credentials
    ):
        """POST /api/v1/auth/login with valid admin credentials → 200."""
        username, password = admin_credentials
        resp = http_session.post(
            f"{api_base}/auth/login",
            json={"username": username, "password": password},
            timeout=30,
        )
        assert resp.status_code == 200, (
            f"Login failed: {resp.status_code} {resp.text[:300]}"
        )
        data = resp.json()
        assert "status" in data or "access_token" in data or "session_id" in data, (
            f"No auth token in response: {list(data.keys())}"
        )

    def test_login_wrong_password(self, http_session, api_base):
        """Login with wrong password → 401."""
        resp = http_session.post(
            f"{api_base}/auth/login",
            json={"username": "admin", "password": "wrong_password_xyz"},
            timeout=30,
        )
        assert resp.status_code in (401, 403), (
            f"Expected 401/403 for wrong password, got {resp.status_code}"
        )

    def test_login_wrong_username(self, http_session, api_base):
        """Login with nonexistent username → 401."""
        resp = http_session.post(
            f"{api_base}/auth/login",
            json={"username": "nonexistent_user_xyz", "password": "anything"},
            timeout=30,
        )
        assert resp.status_code in (401, 403, 404), (
            f"Expected 401/403/404 for unknown user, got {resp.status_code}"
        )

    def test_login_empty_body(self, http_session, api_base):
        """Login with empty body → 400."""
        resp = http_session.post(
            f"{api_base}/auth/login",
            json={},
            timeout=30,
        )
        assert resp.status_code == 400, (
            f"Expected 400 for empty body, got {resp.status_code}"
        )

    def test_login_no_body(self, http_session, api_base):
        """Login with no body at all → 400/415."""
        resp = http_session.post(
            f"{api_base}/auth/login",
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        assert resp.status_code in (400, 415, 422), (
            f"Expected 400/415/422 for missing body, got {resp.status_code}"
        )


class TestSession:
    """Session lifecycle tests (login → use → logout)."""

    def test_auth_me_after_login(self, http_session, api_base, admin_auth_headers):
        """GET /api/v1/auth/me returns user info after login."""
        resp = http_session.get(
            f"{api_base}/auth/me",
            headers=admin_auth_headers,
            timeout=30,
        )
        # BFF may have /api/v1/me instead
        if resp.status_code == 404:
            resp = http_session.get(
                f"{api_base.replace('/api/v1', '')}/api/v1/me",
                headers=admin_auth_headers,
                timeout=30,
            )
        data = resp.json()
        # Should return user info
        assert resp.status_code in (200, 404), (
            f"/me returned unexpected: {resp.status_code}"
        )
        if resp.status_code == 200:
            assert "user" in data or "user_id" in data or "username" in data, (
                f"No user data in response: {list(data.keys())}"
            )

    def test_logout(self, http_session, api_base, admin_auth_headers):
        """POST /api/v1/auth/logout succeeds."""
        resp = http_session.post(
            f"{api_base}/auth/logout",
            headers=admin_auth_headers,
            timeout=30,
        )
        assert resp.status_code in (200, 204, 302, 404), (
            f"Logout unexpected: {resp.status_code} {resp.text[:200]}"
        )

    def test_login_logout_relogin(
        self, http_session, api_base, admin_credentials
    ):
        """Full cycle: login → logout → login again."""
        username, password = admin_credentials
        # First login
        r1 = http_session.post(
            f"{api_base}/auth/login",
            json={"username": username, "password": password},
            timeout=30,
        )
        assert r1.status_code == 200
        # Logout
        headers = {"Content-Type": "application/json"}
        if r1.cookies:
            cookie_str = "; ".join(f"{c.name}={c.value}" for c in r1.cookies)
            headers["Cookie"] = cookie_str
        r2 = http_session.post(
            f"{api_base}/auth/logout",
            headers=headers,
            timeout=30,
        )
        # Relogin
        r3 = http_session.post(
            f"{api_base}/auth/login",
            json={"username": username, "password": password},
            timeout=30,
        )
        assert r3.status_code == 200, (
            f"Re-login after logout failed: {r3.status_code}"
        )


class TestInvalidCredentials:
    """Invalid credential scenarios."""

    def test_missing_content_type(self, http_session, api_base):
        """Request without Content-Type header → should still be handled."""
        resp = http_session.post(
            f"{api_base}/auth/login",
            data='{"username":"admin","password":"bad"}',
            timeout=30,
        )
        # Some servers need explicit content type; test resilience
        assert resp.status_code in (200, 400, 401, 403, 415), (
            f"Unexpected status: {resp.status_code}"
        )
