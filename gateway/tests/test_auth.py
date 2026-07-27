"""Auth unit tests — JWT, API key, admin."""
import pytest

def test_auth_result_dataclass():
    from auth import AuthResult
    r = AuthResult(status="ok", org_id="org1", tier="free")
    assert r.status == "ok"
    assert r.org_id == "org1"

def test_verify_api_key():
    from auth import verify_api_key
    assert verify_api_key("ak-test1234567890abcdef") is True
    assert verify_api_key("athr_test123") is False
    assert verify_api_key("") is False

def test_check_admin_no_key():
    from auth import check_admin
    from unittest.mock import MagicMock
    req = MagicMock()
    req.headers = {"X-Admin-Key": ""}
    # Without ADMIN_API_KEY env, should return False
    assert check_admin(req) is False

def test_auth_imports():
    from auth import check_auth, check_admin, AuthResult
    assert callable(check_auth)
    assert callable(check_admin)
