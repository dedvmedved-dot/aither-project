"""Config tests — env vars, feature flags."""
import pytest

def test_settings_singleton():
    from config import settings, Settings
    assert isinstance(settings, Settings)
    assert hasattr(settings, 'redis_host')
    assert hasattr(settings, 'pg_url')
    assert hasattr(settings, 'billing_enabled')

def test_feature_flags_exist():
    from config import settings
    flags = ['auth_enabled', 'rate_limit_enabled', 'billing_enabled',
             'security_enabled', 'security_egress_enabled', 'usage_enabled',
             'metrics_enabled', 'vault_enabled', 'siem_enabled', 'rag_enabled']
    for f in flags:
        assert hasattr(settings, f), f"Missing flag: {f}"

def test_pg_url_fallback():
    from config import settings
    assert settings.pg_url, "PG_URL should be set or built from individual vars"
