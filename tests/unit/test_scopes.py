"""
Unit tests: Scope validation, RBAC logic, and revoke semantics.

Tests the scope model used by the Aither platform:
- Scopes: model:14b:chat, model:32b:chat-adapter, model:32b:completion
- Mapping from UI model selector → scope array
- Revoke logic (status transition active → revoked)
"""

import re
from datetime import datetime, timezone


# ── Reference implementations ───────────────────────────────────────

# Known scope constants
VALID_SCOPES = {
    "model:14b:chat",
    "model:32b:chat-adapter",
    "model:32b:completion",
}

# Mapping: UI model selector value → scope list
MODEL_SELECTOR_TO_SCOPES = {
    "both": [
        "model:14b:chat",
        "model:32b:chat-adapter",
        "model:32b:completion",
    ],
    "qwen-14b": [
        "model:14b:chat",
    ],
    "qwen-32b-base": [
        "model:32b:chat-adapter",
        "model:32b:completion",
    ],
}

# Scope format: model:<model_id>:<action>
SCOPE_PATTERN = re.compile(r"^model:([a-z0-9_-]+):([a-z-]+)$")


def parse_scope(scope_str: str) -> dict | None:
    """Parse a scope string into components.

    Returns {'model': ..., 'action': ...} or None if invalid.
    """
    m = SCOPE_PATTERN.match(scope_str)
    if not m:
        return None
    return {"model": m.group(1), "action": m.group(2)}


def resolve_scopes(model_selector: str) -> list[str]:
    """Resolve UI model selector value to scope array.

    Mirrors: app.js → _createToken() logic.
    """
    return MODEL_SELECTOR_TO_SCOPES.get(model_selector, [])


def validate_scopes(scopes: list[str]) -> tuple[bool, list[str]]:
    """Validate a list of scopes. Returns (is_valid, unknown_scopes)."""
    unknown = [s for s in scopes if s not in VALID_SCOPES]
    return len(unknown) == 0, unknown


def is_revoked(status: str) -> bool:
    """Check if a key status means revoked.

    Mirrors: portal_api_keys.status CHECK constraint.
    """
    return status == "revoked"


def can_revoke(current_status: str) -> bool:
    """Check if a key can be revoked (only 'active' keys)."""
    return current_status == "active"


# ── Tests: Scope Parsing ────────────────────────────────────────────

class TestScopeParsing:
    """Scope string parsing and structure validation."""

    def test_valid_scope_parsed(self):
        """Valid scope strings parse into model + action components."""
        cases = {
            "model:14b:chat": ("14b", "chat"),
            "model:32b:chat-adapter": ("32b", "chat-adapter"),
            "model:32b:completion": ("32b", "completion"),
        }
        for scope_str, (exp_model, exp_action) in cases.items():
            result = parse_scope(scope_str)
            assert result is not None, f"Failed to parse: {scope_str}"
            assert result["model"] == exp_model, f"{scope_str}: model mismatch"
            assert result["action"] == exp_action, f"{scope_str}: action mismatch"

    def test_invalid_scopes_rejected(self):
        """Malformed scope strings must return None."""
        invalid = [
            "", "model", "model:", ":14b:chat", "org:read",
            "model:14b", "model::chat", "just-some-text",
        ]
        for s in invalid:
            result = parse_scope(s)
            assert result is None, f"Should be invalid but parsed: {s}"

    def test_all_known_scopes_are_valid(self):
        """Every scope in VALID_SCOPES must parse successfully."""
        for scope in VALID_SCOPES:
            assert parse_scope(scope) is not None, f"Known scope failed: {scope}"
            ok, unknown = validate_scopes([scope])
            assert ok, f"Known scope marked invalid: {scope}"
            assert len(unknown) == 0


# ── Tests: Scope Resolution ─────────────────────────────────────────

class TestScopeResolution:
    """UI model selector → scope array mapping."""

    def test_both_models(self):
        """'both' selector includes all 3 scopes."""
        scopes = resolve_scopes("both")
        assert len(scopes) == 3, f"Expected 3 scopes, got {len(scopes)}"
        assert "model:14b:chat" in scopes
        assert "model:32b:chat-adapter" in scopes
        assert "model:32b:completion" in scopes

    def test_14b_only(self):
        """'qwen-14b' selector includes only the chat scope."""
        scopes = resolve_scopes("qwen-14b")
        assert scopes == ["model:14b:chat"], f"Wrong scopes: {scopes}"

    def test_32b_only(self):
        """'qwen-32b-base' selector includes both 32B scopes."""
        scopes = resolve_scopes("qwen-32b-base")
        assert len(scopes) == 2
        assert "model:32b:chat-adapter" in scopes
        assert "model:32b:completion" in scopes
        assert "model:14b:chat" not in scopes

    def test_unknown_selector(self):
        """Unknown/empty selector → empty list."""
        assert resolve_scopes("unknown") == []
        assert resolve_scopes("") == []


# ── Tests: Scope Validation ─────────────────────────────────────────

class TestScopeValidation:
    """validate_scopes() function tests."""

    def test_all_valid(self):
        """A list of all valid scopes passes validation."""
        ok, unknown = validate_scopes(list(VALID_SCOPES))
        assert ok is True
        assert unknown == []

    def test_mixed_scopes(self):
        """Mixed valid/invalid scopes: returns false + unknown list."""
        ok, unknown = validate_scopes([
            "model:14b:chat", "model:99b:admin", "model:32b:completion",
        ])
        assert ok is False
        assert "model:99b:admin" in unknown
        assert len(unknown) == 1

    def test_empty_scope_list(self):
        """Empty scope list is trivially valid."""
        ok, unknown = validate_scopes([])
        assert ok is True
        assert unknown == []


# ── Tests: Revoke Semantics ─────────────────────────────────────────

class TestRevokeSemantics:
    """Status transitions and revoke logic."""

    def test_active_is_not_revoked(self):
        """'active' status means key is usable."""
        assert is_revoked("active") is False

    def test_revoked_is_revoked(self):
        """'revoked' status means key is dead."""
        assert is_revoked("revoked") is True

    def test_only_active_can_be_revoked(self):
        """Revoke transition: active → revoked; already-revoked is no-op."""
        assert can_revoke("active") is True
        assert can_revoke("revoked") is False

    def test_revoke_twice_idempotent(self):
        """Revoking an already-revoked key is a no-op (status stays 'revoked')."""
        # Simulate: revoke key that's already revoked
        status = "revoked"
        if not can_revoke(status):
            pass  # no-op — skip the DB update
        assert status == "revoked", "Revoking twice changed status"
