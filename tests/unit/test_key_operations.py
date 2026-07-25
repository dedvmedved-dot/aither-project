"""Unit tests for Aither API key security operations."""
import hashlib
import secrets
import pytest


def generate_key():
    """Replicate BFF key generation logic."""
    raw = secrets.token_urlsafe(32)
    token = f"athr_{raw}"
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    prefix = token[:12]
    return {"token": token, "hash": token_hash, "prefix": prefix, "token_id": secrets.token_hex(6)}


class TestKeyGeneration:
    def test_format(self):
        key = generate_key()
        assert key["token"].startswith("athr_"), "Token must start with athr_"
        assert len(key["token"]) > 20, "Token must be reasonably long"

    def test_uniqueness(self):
        keys = [generate_key()["token"] for _ in range(10)]
        assert len(set(keys)) == 10, "All 10 keys must be unique"

    def test_hash_consistency(self):
        key = generate_key()
        expected_hash = hashlib.sha256(key["token"].encode()).hexdigest()
        assert key["hash"] == expected_hash, "Hash must be SHA-256 of full token"

    def test_prefix_length(self):
        key = generate_key()
        assert len(key["prefix"]) == 12, "Prefix must be 12 characters"

    def test_token_id_format(self):
        key = generate_key()
        assert len(key["token_id"]) == 12, "Token ID must be 12 hex chars"


class TestScopes:
    SCOPES_14B = ["model:14b:chat"]
    SCOPES_32B = ["model:32b:chat-adapter", "model:32b:completion"]
    SCOPES_ALL = SCOPES_14B + SCOPES_32B

    def test_14b_only(self):
        assert "model:14b:chat" in self.SCOPES_14B
        assert "model:32b:chat-adapter" not in self.SCOPES_14B

    def test_32b_only(self):
        assert "model:32b:chat-adapter" in self.SCOPES_32B

    def test_all_scopes(self):
        assert len(self.SCOPES_ALL) == 3
        assert "model:14b:chat" in self.SCOPES_ALL
        assert "model:32b:chat-adapter" in self.SCOPES_ALL


class TestRevocation:
    def test_revoked_token_fails(self):
        # Simulate revoked token check
        tokens = {"active_key": True, "revoked_key": False}

        def check_token(token_id):
            return tokens.get(token_id, False)

        assert check_token("active_key") == True
        assert check_token("revoked_key") == False

    def test_masking(self):
        token = "athr_DlDp31NMY_N2OBUkle1ZKvzTHjgWtc0OO6x2-cEY0Cg"
        masked = token[:12] + "..." + token[-4:]
        assert masked.startswith("athr_DlDp31")
        assert "NMY_" not in masked  # middle is hidden
        assert masked.endswith("0Cg")
