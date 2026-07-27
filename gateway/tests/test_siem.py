"""SIEM tests — module structure, event functions."""
import pytest

def test_siem_import():
    from siem import send_event, init_siem
    assert callable(send_event)

def test_siem_event_functions():
    from siem import (auth_success, auth_failure, rate_limit_exceeded,
                       security_input_block, security_output_block,
                       billing_reserve, billing_settle, billing_refund,
                       admin_action, upstream_error, dependency_failure)
    for fn in [auth_success, auth_failure, rate_limit_exceeded,
               security_input_block, security_output_block,
               billing_reserve, billing_settle, billing_refund,
               admin_action, upstream_error, dependency_failure]:
        assert callable(fn)

def test_siem_noop_when_disabled():
    """send_event should not raise when SIEM is disabled."""
    from siem import send_event
    send_event("test_event", severity=5, key="value")  # should not raise
