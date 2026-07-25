"""
Integration tests: Completion with qwen-32b-base.

Tests BFF completion endpoint with the 32B base model.
The 32B returns completions (not dialog) — uses 'text' field.

Requires BFF running and 32B vLLM backend available.
"""

import pytest


class TestChat32B:
    """Completion tests with qwen-32b-base."""

    def test_completion_basic(
        self, http_session, api_base, admin_auth_headers
    ):
        """Basic text completion — 32B continues the prompt."""
        payload = {
            "model": "qwen-32b-base",
            "messages": [
                {"role": "user", "content": "Искусственный интеллект — это"}
            ],
            "max_tokens": 128,
            "temperature": 0.3,
        }
        resp = http_session.post(
            f"{api_base}/chat",
            json=payload,
            headers=admin_auth_headers,
            timeout=90,
        )
        assert resp.status_code == 200, (
            f"32B failed: {resp.status_code} {resp.text[:400]}"
        )
        data = resp.json()
        assert "choices" in data, f"No 'choices' in 32B response: {list(data.keys())}"
        choice = data["choices"][0]
        # 32B may return 'text' (completion) or 'message.content'
        content = choice.get("text") or ""
        if not content:
            content = choice.get("message", {}).get("content", "")
        assert len(content) > 0, "Empty completion from 32B"

    def test_completion_russian_language(
        self, http_session, api_base, admin_auth_headers
    ):
        """Russian prompt → Russian completion."""
        payload = {
            "model": "qwen-32b-base",
            "messages": [
                {"role": "user", "content": "Основные принципы квантовой механики включают"}
            ],
            "max_tokens": 200,
            "temperature": 0.3,
        }
        resp = http_session.post(
            f"{api_base}/chat",
            json=payload,
            headers=admin_auth_headers,
            timeout=90,
        )
        assert resp.status_code == 200, f"32B Russian failed: {resp.status_code}"
        data = resp.json()
        content = ""
        if "choices" in data and len(data["choices"]) > 0:
            choice = data["choices"][0]
            content = choice.get("text") or choice.get("message", {}).get("content", "")
        cyrillic = sum(1 for c in content if "\u0400" <= c <= "\u04FF")
        assert cyrillic > 5, (
            f"32B completion has only {cyrillic} Cyrillic chars: {content[:200]}"
        )

    def test_completion_style_differs_from_chat(
        self, http_session, api_base, admin_auth_headers
    ):
        """32B completion should NOT start with greeting (unlike 14B chat)."""
        # Give a neutral prompt
        payload = {
            "model": "qwen-32b-base",
            "messages": [
                {"role": "user", "content": "Солнечная система состоит из"}
            ],
            "max_tokens": 100,
            "temperature": 0.3,
        }
        resp = http_session.post(
            f"{api_base}/chat",
            json=payload,
            headers=admin_auth_headers,
            timeout=90,
        )
        if resp.status_code == 200:
            data = resp.json()
            content = ""
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                content = choice.get("text") or choice.get("message", {}).get("content", "")
            # Completion should continue the sentence, not start a dialog
            assert len(content) > 0
            # Should NOT be a greeting-style start
            greeting_words = ["здравствуйте", "привет", "добрый день"]
            first_word = content.strip().lower().split()[0] if content.strip() else ""
            assert first_word not in greeting_words, (
                f"32B base model responded like a chat model: {content[:100]}"
            )

    def test_completion_max_tokens_respected(
        self, http_session, api_base, admin_auth_headers
    ):
        """Request with low max_tokens must produce short response."""
        payload = {
            "model": "qwen-32b-base",
            "messages": [
                {"role": "user", "content": "The history of computing begins with"}
            ],
            "max_tokens": 20,
            "temperature": 0.3,
        }
        resp = http_session.post(
            f"{api_base}/chat",
            json=payload,
            headers=admin_auth_headers,
            timeout=60,
        )
        if resp.status_code == 200:
            data = resp.json()
            content = ""
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                content = choice.get("text") or choice.get("message", {}).get("content", "")
            # Response should be roughly within token limit
            # (rough estimate: ~4 chars per token)
            assert len(content) < 500, (
                f"Response too long for 20 max_tokens: {len(content)} chars"
            )

    def test_completion_without_auth(self, fresh_http_session, api_base):
        """Completion without authentication → 401."""
        resp = fresh_http_session.post(
            f"{api_base}/chat",
            json={
                "model": "qwen-32b-base",
                "messages": [{"role": "user", "content": "test"}],
            },
            timeout=30,
        )
        assert resp.status_code in (401, 403), (
            f"Expected 401/403 without auth, got {resp.status_code}"
        )
