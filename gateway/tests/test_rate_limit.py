"""Rate limiting tests — Lua script structure."""
import pytest

def test_rate_limit_import():
    from rate_limit import check_rate_limit
    assert callable(check_rate_limit)

def test_lua_script_present():
    from rate_limit import RATE_LIMIT_LUA
    assert "local rpm" in RATE_LIMIT_LUA
    assert "INCR" in RATE_LIMIT_LUA
    assert "EXPIRE" in RATE_LIMIT_LUA

def test_tier_limits():
    from rate_limit import TIER_LIMITS
    assert "free" in TIER_LIMITS
    assert "rpm" in TIER_LIMITS["free"]
    assert "tpm" in TIER_LIMITS["free"]
