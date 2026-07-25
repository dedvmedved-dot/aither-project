"""
Unit tests: API Key Generation

Tests the API key generation logic used by Aither platform.
API keys are format: "ak-" + 48 hex chars (24 random bytes).
"""

import re
from secrets import token_hex, token_urlsafe


# ── Reference implementations (mirror portal/server.ts logic) ──────

def generate_api_key(prefix: str = "ak-", byte_length: int = 24) -> str:
    """Generate an API key: ak- + 24 random bytes as hex.

    Mirrors: server.ts → 'ak-' + randomBytes(24).toString('hex')
    """
    return prefix + token_hex(byte_length)


def generate_api_key_prefix(key: str) -> str:
    """Extract key prefix: first 11 chars (ak-XXXXXXXX).

    Mirrors: server.ts → apiKey.slice(0, 11)
    """
    return key[:11]


def generate_short_token_id(prefix: str = "tk_", byte_length: int = 12) -> str:
    """Generate a token ID: tk_ + 12 random bytes hex."""
    return prefix + token_hex(byte_length)


# ── Tests ───────────────────────────────────────────────────────────

class TestApiKeyGeneration:
    """Tests for AK-style API key generation (ak- prefix)."""

    def test_key_starts_with_ak_prefix(self):
        """API keys must start with 'ak-'."""
        key = generate_api_key()
        assert key.startswith("ak-"), f"Key does not start with 'ak-': {key[:10]}..."

    def test_key_has_correct_length(self):
        """ak- + 24 bytes hex = 3 + 48 = 51 characters."""
        key = generate_api_key()
        assert len(key) == 51, f"Expected 51 chars, got {len(key)}: {key}"

    def test_key_is_hex_after_prefix(self):
        """Chars after 'ak-' must be lowercase hex."""
        key = generate_api_key()
        hex_part = key[3:]
        assert re.fullmatch(r"[0-9a-f]{48}", hex_part), (
            f"Non-hex chars in: {hex_part[:20]}..."
        )

    def test_keys_are_unique(self):
        """Multiple generated keys must not collide."""
        keys = {generate_api_key() for _ in range(100)}
        assert len(keys) == 100, (
            f"Collision detected: only {len(keys)} unique out of 100"
        )

    def test_key_unpredictable(self):
        """Consecutive keys must differ beyond just the last few chars."""
        k1 = generate_api_key()
        k2 = generate_api_key()
        # At least 30 chars must differ (out of 48 hex chars)
        hex1, hex2 = k1[3:], k2[3:]
        diffs = sum(1 for a, b in zip(hex1, hex2) if a != b)
        assert diffs >= 30, f"Only {diffs}/48 chars differ — weak entropy?"


class TestKeyPrefixExtraction:
    """Tests for key prefix extraction (used in DB/api responses)."""

    def test_prefix_length(self):
        """Prefix must be 11 chars: 'ak-' + first 8 hex chars."""
        key = "ak-a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6"
        prefix = generate_api_key_prefix(key)
        assert len(prefix) == 11, f"Expected 11 chars, got {len(prefix)}"
        assert prefix == "ak-a1b2c3d4", f"Unexpected prefix: {prefix}"

    def test_prefix_consistent_with_key(self):
        """Prefix must be substring of the original key."""
        key = generate_api_key()
        prefix = generate_api_key_prefix(key)
        assert key.startswith(prefix), (
            f"Prefix '{prefix}' not at start of key '{key}'"
        )

    def test_prefix_does_not_reveal_full_key(self):
        """Prefix must be safe to display: only first 11 of 51 chars."""
        key = generate_api_key()
        prefix = generate_api_key_prefix(key)
        assert len(prefix) < len(key), "Prefix equals full key — information leak!"
        assert key[11:] not in prefix


class TestTokenIdGeneration:
    """Tests for short token IDs (tk_ prefix, used in some endpoints)."""

    def test_token_id_format(self):
        """Token ID format: tk_ + 24 hex chars."""
        tid = generate_short_token_id()
        assert tid.startswith("tk_"), f"Wrong prefix: {tid}"
        assert re.fullmatch(r"tk_[0-9a-f]{24}", tid), f"Bad format: {tid}"

    def test_token_id_length(self):
        """tk_ + 12 bytes hex = 3 + 24 = 27 chars."""
        tid = generate_short_token_id()
        assert len(tid) == 27, f"Expected 27, got {len(tid)}"
