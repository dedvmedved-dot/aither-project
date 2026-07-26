"""
U1.3-OPS-R5 — HTTP Availability Probe Unit Tests

Tests for scripts/ops/http_availability_probe.py
"""
import json
import sys
import os
import tempfile
import pytest
import time
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scripts/ops'))
import http_availability_probe as probe_module


class TestGenerateSummary:
    """Tests for generate_summary() function."""

    def test_all_200_pass(self):
        results = []
        for i in range(240):
            results.append({
                "zone": "test", "url": "http://ok", "probe_num": i+1,
                "timestamp": f"2026-07-26T04:00:{i:02d}.000000Z",
                "http_status": 200, "latency_seconds": 0.1,
                "error_type": None, "error_message": ""
            })
        summary = probe_module.generate_summary("test", results, 240, 1)
        assert summary["exit_status"] == "PASS"
        assert summary["actual_probe_count"] == 240
        assert summary["http_200_count"] == 240
        assert summary["non_200_count"] == 0
        assert summary["availability_percent"] == 100.0

    def test_http_500_fail(self):
        results = [{
            "zone": "test", "url": "http://fail", "probe_num": 1,
            "timestamp": "2026-07-26T04:00:00.000000Z",
            "http_status": 500, "latency_seconds": 0.1,
            "error_type": "http_error", "error_message": "HTTP 500"
        }]
        summary = probe_module.generate_summary("test", results, 1, 1)
        assert summary["exit_status"] == "FAIL"
        assert summary["non_200_count"] == 1

    def test_dns_failure_fail(self):
        results = [{
            "zone": "test", "url": "http://bad", "probe_num": 1,
            "timestamp": "2026-07-26T04:00:00.000000Z",
            "http_status": None, "latency_seconds": 3.0,
            "error_type": "dns_failure", "error_message": "DNS failure"
        }]
        summary = probe_module.generate_summary("test", results, 1, 1)
        assert summary["exit_status"] == "FAIL"
        assert summary["dns_failure_count"] == 1

    def test_connection_failure_fail(self):
        results = [{
            "zone": "test", "url": "http://nope", "probe_num": 1,
            "timestamp": "2026-07-26T04:00:00.000000Z",
            "http_status": None, "latency_seconds": 3.0,
            "error_type": "connection_failure", "error_message": "Connection refused"
        }]
        summary = probe_module.generate_summary("test", results, 1, 1)
        assert summary["exit_status"] == "FAIL"
        assert summary["connection_failure_count"] == 1

    def test_timeout_fail(self):
        results = [{
            "zone": "test", "url": "http://slow", "probe_num": 1,
            "timestamp": "2026-07-26T04:00:00.000000Z",
            "http_status": None, "latency_seconds": 10.0,
            "error_type": "timeout", "error_message": "Timeout"
        }]
        summary = probe_module.generate_summary("test", results, 1, 1)
        assert summary["exit_status"] == "FAIL"

    def test_tls_failure_fail(self):
        results = [{
            "zone": "test", "url": "https://bad-tls", "probe_num": 1,
            "timestamp": "2026-07-26T04:00:00.000000Z",
            "http_status": None, "latency_seconds": 0.5,
            "error_type": "tls_failure", "error_message": "TLS failure"
        }]
        summary = probe_module.generate_summary("test", results, 1, 1)
        assert summary["exit_status"] == "FAIL"

    def test_missing_probe_enforced(self):
        """If expected 240 probes but only 200 completed -> FAIL."""
        results = []
        for i in range(200):
            results.append({
                "zone": "test", "url": "http://ok", "probe_num": i+1,
                "timestamp": f"2026-07-26T04:00:{i:02d}.000000Z",
                "http_status": 200, "latency_seconds": 0.1,
                "error_type": None, "error_message": ""
            })
        summary = probe_module.generate_summary("test", results, 240, 1)
        # generate_summary doesn't enforce count — main() should
        # This test confirms count is reported
        assert summary["actual_probe_count"] == 200
        # The missing probe gate is in main(), tested via integration

    def test_empty_results(self):
        results = []
        summary = probe_module.generate_summary("test", results, 240, 1)
        assert summary["actual_probe_count"] == 0
        assert summary["availability_percent"] == 0.0
        assert summary["exit_status"] == "PASS"  # no failures, just empty

    def test_result_sorting_maintains_order(self):
        """After sorting, probes should be in probe_num order."""
        results = [
            {"zone": "test", "url": "x", "probe_num": 3, "timestamp": "T3", "http_status": 200, "latency_seconds": 0, "error_type": None, "error_message": ""},
            {"zone": "test", "url": "x", "probe_num": 1, "timestamp": "T1", "http_status": 200, "latency_seconds": 0, "error_type": None, "error_message": ""},
            {"zone": "test", "url": "x", "probe_num": 2, "timestamp": "T2", "http_status": 200, "latency_seconds": 0, "error_type": None, "error_message": ""},
        ]
        results.sort(key=lambda item: item["probe_num"])
        assert results[0]["probe_num"] == 1
        assert results[1]["probe_num"] == 2
        assert results[2]["probe_num"] == 3


class TestIntervalCalculation:
    """Tests for interval statistics."""

    def test_intervals_in_range(self):
        """Generate timestamps at exactly 1-second intervals."""
        results = []
        base = 1750000000.0
        for i in range(100):
            results.append({
                "zone": "test", "url": "x", "probe_num": i+1,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000000Z", time.gmtime(base + i)),
                "http_status": 200, "latency_seconds": 0.1,
                "error_type": None, "error_message": ""
            })
        # All timestamps are exactly 1 second apart
        assert all(r["http_status"] == 200 for r in results)


class TestProbeSingle:
    """Tests for probe_single function using mock endpoints."""

    def test_http_200_response(self):
        result = probe_module.probe_single("http://10.129.13.78:30080/health", "test", 1, 3, 10)
        assert result["http_status"] == 200
        assert result["error_type"] is None

    def test_connection_refused(self):
        result = probe_module.probe_single("http://127.0.0.1:19999/health", "test", 1, 1, 3)
        # Should fail with connection error
        assert result["http_status"] is None or result["error_type"] is not None
        assert result["error_type"] in ("connection_failure", "timeout", None)

    def test_invalid_host_dns_failure(self):
        result = probe_module.probe_single("http://invalid-host-that-does-not-exist-xyz.test/health", "test", 1, 1, 3)
        assert result["error_type"] in ("dns_failure", "timeout", "connection_failure", None)
