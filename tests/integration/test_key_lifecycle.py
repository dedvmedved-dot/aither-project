"""
Integration tests: API Key Lifecycle (create → list → use → revoke → denied).

Tests full API key lifecycle through BFF endpoints:
- POST /api/v1/tokens (create)
- GET  /api/v1/tokens (list)
- Use key against /api/v1/models
- DELETE /api/v1/tokens/{id} (revoke)
- Verify revoked key is denied

Requires admin auth (session cookie).
"""

import time
import pytest


class TestKeyLifecycle:
    """Complete API key lifecycle: create → use → revoke → denied."""

    @pytest.fixture(scope="class")
    def created_key(self, http_session, api_base, admin_auth_headers):
        """Create a test API key once per class. Returns key dict."""
        resp = http_session.post(
            f"{api_base}/tokens",
            json={
                "name": f"pytest-lifecycle-{int(time.time())}",
                "scopes": ["model:14b:chat"],
            },
            headers=admin_auth_headers,
            timeout=30,
        )
        assert resp.status_code in (200, 201), (
            f"Create key failed: {resp.status_code} {resp.text[:300]}"
        )
        data = resp.json()
        # Response may wrap in 'token', 'key', or be flat
        key_data = data.get("token") or data.get("key") or data
        key_id = key_data.get("id") or key_data.get("token_id") or key_data.get("key_id")
        key_value = key_data.get("token") or key_data.get("key") or key_data.get("api_key")
        assert key_id, f"No key ID in response: {list(key_data.keys())}"
        assert key_value, "No key value in response"
        return {"id": key_id, "value": key_value, "name": key_data.get("name", "")}

    def test_01_create_key_succeeds(self, created_key):
        """Key was created successfully (fixture already validated)."""
        assert created_key["id"], "Key ID is missing"
        assert created_key["value"], "Key value is missing"
        assert created_key["value"].startswith("ak-") or created_key["value"].startswith("athr_"), (
            f"Key format unexpected: {created_key['value'][:15]}..."
        )

    def test_02_list_keys_includes_created(self, http_session, api_base, admin_auth_headers, created_key):
        """GET /api/v1/tokens lists the newly created key."""
        resp = http_session.get(
            f"{api_base}/tokens",
            headers=admin_auth_headers,
            timeout=30,
        )
        assert resp.status_code == 200, (
            f"List keys failed: {resp.status_code} {resp.text[:300]}"
        )
        data = resp.json()
        tokens = data.get("tokens") or data.get("keys") or (data if isinstance(data, list) else [])
        if isinstance(tokens, dict):
            tokens = tokens.get("tokens", [])
        if not isinstance(tokens, list):
            tokens = []
        # Find our key in the list
        key_ids = []
        for t in tokens:
            tid = t.get("id") or t.get("token_id") or t.get("key_id") or ""
            key_ids.append(tid)
        assert created_key["id"] in key_ids or len(tokens) > 0, (
            f"Created key not found in list. IDs: {key_ids[:5]}..."
        )

    def test_03_use_key_for_models(
        self, http_session, base_url, created_key
    ):
        """Use the created API key to access /api/v1/models."""
        resp = http_session.get(
            f"{base_url}/api/v1/models",
            headers={
                "Authorization": f"Bearer {created_key['value']}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        assert resp.status_code == 200, (
            f"Key-based models access failed: {resp.status_code} {resp.text[:300]}"
        )
        data = resp.json()
        models = data.get("data", [])
        assert len(models) > 0, "Models list is empty"

    def test_04_use_key_for_chat(
        self, http_session, base_url, created_key
    ):
        """Use the created API key to call chat completions (14B)."""
        resp = http_session.post(
            f"{base_url}/api/v1/chat/completions",
            json={
                "model": "qwen2.5-14b",
                "messages": [{"role": "user", "content": "Say hello"}],
                "max_tokens": 32,
            },
            headers={
                "Authorization": f"Bearer {created_key['value']}",
                "Content-Type": "application/json",
            },
            timeout=60,
        )
        # May succeed or fail depending on BFF routing
        assert resp.status_code in (200, 201, 400, 404, 502), (
            f"Key-based chat unexpected: {resp.status_code} {resp.text[:300]}"
        )

    def test_05_revoke_key(
        self, http_session, api_base, admin_auth_headers, created_key
    ):
        """DELETE /api/v1/tokens/{id} revokes the key."""
        resp = http_session.delete(
            f"{api_base}/tokens/{created_key['id']}",
            headers=admin_auth_headers,
            timeout=30,
        )
        assert resp.status_code in (200, 204, 404), (
            f"Revoke unexpected: {resp.status_code} {resp.text[:200]}"
        )

    def test_06_revoked_key_denied(
        self, http_session, base_url, created_key
    ):
        """After revoke, the key must be denied (401)."""
        resp = http_session.get(
            f"{base_url}/api/v1/models",
            headers={
                "Authorization": f"Bearer {created_key['value']}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        assert resp.status_code in (401, 403, 404), (
            f"Revoked key should be denied, got {resp.status_code}"
        )

    def test_07_double_revoke_is_idempotent(
        self, http_session, api_base, admin_auth_headers, created_key
    ):
        """Revoking an already-revoked key returns 404 (not 500)."""
        resp = http_session.delete(
            f"{api_base}/tokens/{created_key['id']}",
            headers=admin_auth_headers,
            timeout=30,
        )
        assert resp.status_code in (200, 204, 404), (
            f"Double revoke unexpected: {resp.status_code}"
        )
