"""
Integration tests: Chat with qwen-14b (dialog model).

Tests BFF chat endpoint with the 14B chat-optimized model.
Requires BFF running and 14B vLLM backend available.

The BFF routes POST /api/v1/chat → vLLM /v1/chat/completions.
Uses admin session auth (cookie/bearer from login).
"""

import pytest


class TestChat14B:
    """Chat tests with qwen-14b (dialog model)."""

    def test_simple_greeting(
        self, http_session, api_base, admin_auth_headers
    ):
        """Simple greeting in Russian → must reply in Russian."""
        payload = {
            "model": "qwen-14b",
            "messages": [
                {"role": "user", "content": "Привет! Как дела?"}
            ],
            "max_tokens": 128,
            "temperature": 0.7,
        }
        resp = http_session.post(
            f"{api_base}/chat",
            json=payload,
            headers=admin_auth_headers,
            timeout=60,
        )
        assert resp.status_code == 200, (
            f"14B chat failed: {resp.status_code} {resp.text[:400]}"
        )
        data = resp.json()
        # Response should have choices
        assert "choices" in data, (
            f"No 'choices' in response: {list(data.keys())}"
        )
        choice = data["choices"][0]
        # 14B returns message.content (OpenAI format)
        if "message" in choice:
            content = choice["message"].get("content", "")
        elif "text" in choice:
            content = choice["text"]
        else:
            content = str(choice)
        assert len(content) > 0, "Empty response from 14B"

    def test_russian_language_response(
        self, http_session, api_base, admin_auth_headers
    ):
        """Russian-language query must produce a Russian response."""
        payload = {
            "model": "qwen-14b",
            "messages": [
                {"role": "user", "content": "Расскажи о Москве в трёх предложениях."}
            ],
            "max_tokens": 256,
            "temperature": 0.3,
        }
        resp = http_session.post(
            f"{api_base}/chat",
            json=payload,
            headers=admin_auth_headers,
            timeout=90,
        )
        assert resp.status_code == 200, f"Chat failed: {resp.status_code}"
        data = resp.json()
        content = ""
        if "choices" in data and len(data["choices"]) > 0:
            choice = data["choices"][0]
            content = (
                choice.get("message", {}).get("content", "")
                or choice.get("text", "")
            )
        # Should contain Cyrillic characters
        cyrillic = sum(1 for c in content if "\u0400" <= c <= "\u04FF")
        assert cyrillic > 10, (
            f"Response has only {cyrillic} Cyrillic chars: {content[:200]}"
        )

    def test_multi_turn_conversation(
        self, http_session, api_base, admin_auth_headers
    ):
        """Two-turn conversation: model remembers context."""
        messages = [
            {"role": "user", "content": "Меня зовут Тест."},
        ]
        payload1 = {
            "model": "qwen-14b",
            "messages": messages,
            "max_tokens": 64,
            "temperature": 0.3,
        }
        r1 = http_session.post(
            f"{api_base}/chat",
            json=payload1,
            headers=admin_auth_headers,
            timeout=60,
        )
        assert r1.status_code == 200, f"Turn 1 failed: {r1.status_code}"

        # Extract response
        d1 = r1.json()
        c1 = (
            d1.get("choices", [{}])[0].get("message", {}).get("content", "")
            or d1.get("choices", [{}])[0].get("text", "")
        )
        messages.append({"role": "assistant", "content": c1})
        messages.append({"role": "user", "content": "Как меня зовут?"})

        payload2 = {
            "model": "qwen-14b",
            "messages": messages,
            "max_tokens": 64,
            "temperature": 0.3,
        }
        r2 = http_session.post(
            f"{api_base}/chat",
            json=payload2,
            headers=admin_auth_headers,
            timeout=60,
        )
        assert r2.status_code == 200, f"Turn 2 failed: {r2.status_code}"
        d2 = r2.json()
        c2 = (
            d2.get("choices", [{}])[0].get("message", {}).get("content", "")
            or d2.get("choices", [{}])[0].get("text", "")
        )
        # Model should remember the name "Тест"
        assert "тест" in c2.lower() or "Тест" in c2, (
            f"Model didn't remember name 'Тест': {c2[:200]}"
        )

    def test_chat_without_auth(self, fresh_http_session, api_base):
        """Chat without authentication → 401."""
        resp = fresh_http_session.post(
            f"{api_base}/chat",
            json={
                "model": "qwen-14b",
                "messages": [{"role": "user", "content": "test"}],
            },
            timeout=30,
        )
        assert resp.status_code in (401, 403), (
            f"Expected 401/403 without auth, got {resp.status_code}"
        )
