"""Metrics unit tests — singleton, counters, TTFT."""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(__file__) + '/..')

def test_metrics_singleton():
    from metrics import MetricsRegistry, metrics
    m1 = MetricsRegistry()
    m2 = MetricsRegistry()
    assert m1 is m2
    assert metrics is m1

def test_counter_increment():
    from metrics import metrics
    before = metrics.prometheus_text()
    metrics.incr("test_counter")
    after = metrics.prometheus_text()
    assert "test_counter" in after

def test_auth_denied():
    from metrics import metrics
    metrics.auth_denied("invalid_key")
    txt = metrics.prometheus_text()
    assert "gateway_auth_denied_total" in txt

def test_rate_limit_denied():
    from metrics import metrics
    metrics.rate_limit_denied("free")
    txt = metrics.prometheus_text()
    assert "gateway_rate_limit_denied_total" in txt

def test_security_denied():
    from metrics import metrics
    metrics.security_denied("input")
    txt = metrics.prometheus_text()
    assert "gateway_security_denied_total" in txt

def test_billing_events():
    from metrics import metrics
    metrics.billing_event("reserve")
    metrics.billing_event("settle")
    txt = metrics.prometheus_text()
    assert "gateway_billing_reserve_total" in txt or "billing" in txt

def test_ttft():
    from metrics import metrics
    metrics.observe_ttft("qwen-14b", 0.5)
    txt = metrics.prometheus_text()
    assert "gateway_ttft_seconds" in txt

def test_tokens():
    from metrics import metrics
    metrics.tokens("qwen-14b", 100, 50)
    txt = metrics.prometheus_text()
    assert "gateway_input_tokens_total" in txt
    assert "gateway_output_tokens_total" in txt
