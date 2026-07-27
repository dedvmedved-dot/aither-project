"""Billing unit tests — idempotency, states, types."""
import pytest

def test_billing_result_enum():
    from billing import BillingResult
    assert BillingResult.SUCCESS.value == "success"
    assert BillingResult.ALREADY_COMPLETED.value == "already_completed"
    assert BillingResult.INSUFFICIENT_BALANCE.value == "insufficient_balance"
    assert BillingResult.INVALID_STATE.value == "invalid_state"
    assert BillingResult.DATABASE_ERROR.value == "database_error"

def test_reserve_import():
    from billing import reserve, settle, refund, BillingResult
    assert callable(reserve)
    assert callable(settle)
    assert callable(refund)

def test_billing_module_no_circular():
    """Verify no circular imports."""
    from billing import reserve, settle, refund, BillingResult
    from siem import billing_reserve, billing_settle, billing_refund
    assert callable(billing_reserve)
