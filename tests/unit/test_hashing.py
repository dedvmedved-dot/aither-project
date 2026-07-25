"""
Unit tests: Password Hashing (scrypt) and API Key Hashing (SHA-256).

Mirrors logic from portal/server.ts:
- Password: scryptSync(password, salt, 64) → "salt:hash"
- API keys: stored as plain + prefix in DB (hashing noted as future work)
"""

import hashlib
import re
from secrets import token_hex


# ── Reference implementations ───────────────────────────────────────

def hash_password(password: str) -> str:
    """scrypt password hashing: random 16-byte salt + 64-byte hash.

    Mirrors: server.ts → hashPassword()
    """
    from hashlib import scrypt
    salt = token_hex(16)  # 16 bytes = 32 hex chars
    hash_bytes = scrypt(
        password.encode("utf-8"),
        salt=salt.encode("utf-8"),
        n=16384, r=8, p=1, dklen=64,
    )
    hash_hex = hash_bytes.hex()
    return f"{salt}:{hash_hex}"


def verify_password(password: str, stored: str) -> bool:
    """Verify scrypt password against stored hash.

    Mirrors: server.ts → verifyPassword()
    """
    from hashlib import scrypt
    parts = stored.split(":")
    if len(parts) != 2:
        return False
    salt, expected_hash = parts
    derived = scrypt(
        password.encode("utf-8"),
        salt=salt.encode("utf-8"),
        n=16384, r=8, p=1, dklen=64,
    )
    return derived.hex() == expected_hash


def sha256_hash(value: str) -> str:
    """SHA-256 hash for API key storage (future path).

    Mirrors: Python's hashlib.sha256
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def mask_secret(secret: str, visible_start: int = 6, visible_end: int = 4) -> str:
    """Mask a secret: show first N + last M chars, asterisks in middle.

    Used when displaying API keys in UI/logs.
    """
    if len(secret) <= visible_start + visible_end + 4:
        return "*" * min(len(secret), 12)
    return (
        secret[:visible_start]
        + "*" * (len(secret) - visible_start - visible_end)
        + secret[-visible_end:]
    )


# ── Tests: Password Hashing ─────────────────────────────────────────

class TestPasswordHashing:
    """scrypt password hashing tests."""

    def test_hash_produces_valid_format(self):
        """Hash must be 'salt:hash' with 32-char hex salt and 128-char hex hash."""
        h = hash_password("test_password")
        assert ":" in h, f"No colon in hash: {h}"
        salt, hash_part = h.split(":")
        assert len(salt) == 32, f"Salt wrong length: {len(salt)}"
        assert re.fullmatch(r"[0-9a-f]{32}", salt), f"Salt not hex: {salt}"
        assert len(hash_part) == 128, f"Hash wrong length: {len(hash_part)}"
        assert re.fullmatch(r"[0-9a-f]{128}", hash_part), "Hash not hex"

    def test_verify_correct_password(self):
        """Correct password must verify successfully."""
        h = hash_password("secure123")
        assert verify_password("secure123", h), "Correct password failed verification"

    def test_verify_wrong_password(self):
        """Wrong password must NOT verify."""
        h = hash_password("secure123")
        assert not verify_password("wrong_pass", h), "Wrong password passed verification!"

    def test_verify_corrupted_hash(self):
        """Corrupted hash must return False, not crash."""
        assert not verify_password("anything", "bad:hash:extra")
        assert not verify_password("anything", "no_colon")
        assert not verify_password("anything", "")

    def test_hash_is_deterministic_for_same_salt(self):
        """Given the same salt, scrypt must produce the same hash
        (used to test our verification logic)."""
        from hashlib import scrypt
        salt = "a" * 32
        h1 = scrypt(b"test", salt=b"a" * 32, n=16384, r=8, p=1, dklen=64).hex()
        h2 = scrypt(b"test", salt=b"a" * 32, n=16384, r=8, p=1, dklen=64).hex()
        assert h1 == h2, "scrypt not deterministic"

    def test_salts_are_unique(self):
        """Each hash must use a different salt."""
        salts = {hash_password("pw").split(":")[0] for _ in range(20)}
        assert len(salts) == 20, f"Salt collision: only {len(salts)} unique"


# ── Tests: API Key Hashing ──────────────────────────────────────────

class TestApiKeyHashing:
    """SHA-256 hashing for API keys (future DB storage path)."""

    def test_sha256_is_deterministic(self):
        """Same input → same SHA-256 hash."""
        h1 = sha256_hash("ak-test-key-001")
        h2 = sha256_hash("ak-test-key-001")
        assert h1 == h2, "SHA-256 not deterministic"

    def test_sha256_different_inputs(self):
        """Different keys → different hashes."""
        h1 = sha256_hash("ak-key-a")
        h2 = sha256_hash("ak-key-b")
        assert h1 != h2, "Different keys produced same hash"

    def test_sha256_length(self):
        """SHA-256 always produces 64 hex chars (32 bytes)."""
        h = sha256_hash("any_value_here")
        assert len(h) == 64, f"Expected 64 chars, got {len(h)}"
        assert re.fullmatch(r"[0-9a-f]{64}", h), "Not hex"


# ── Tests: Secret Masking ───────────────────────────────────────────

class TestSecretMasking:
    """Tests for secret/token masking in UI and API responses."""

    def test_mask_shows_prefix_and_suffix(self):
        """Mask shows first 6 and last 4 chars."""
        secret = "ak-a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6"
        masked = mask_secret(secret)
        assert masked.startswith("ak-a1b"), f"Bad mask start: {masked}"
        assert masked.endswith("a5b6"), f"Bad mask end: {masked}"

    def test_mask_hides_middle(self):
        """The masked portion must not contain any original middle chars."""
        secret = "ak-a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6"
        masked = mask_secret(secret, visible_start=6, visible_end=4)
        assert "*" * (len(secret) - 10) in masked, "Mask does not contain asterisks"

    def test_mask_short_secret(self):
        """Very short secrets get fully masked."""
        assert mask_secret("abc") == "***"
        assert mask_secret("short") in ("*****", "********")  # length may vary
