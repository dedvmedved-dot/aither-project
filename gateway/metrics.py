"""
Aither Gateway — Prometheus Metrics (singleton).
Pipeline updates counters; /metrics exposes them. CHANGE-0022-C2.
"""
import time
import threading
from collections import defaultdict


class MetricsRegistry:
    """Thread-safe singleton metrics registry."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        self.lock = threading.Lock()
        self.ttft_buckets = [0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
        self._counters = defaultdict(int)
        self._gauges = {}
        self._ttft = defaultdict(lambda: {"count": 0, "sum": 0.0, "buckets": {b: 0 for b in self.ttft_buckets}})

    # ── Counter operations ──
    def incr(self, name: str, labels: dict = None):
        key = self._metric_key(name, labels)
        with self.lock:
            self._counters[key] += 1

    def incrby(self, name: str, amount: int, labels: dict = None):
        key = self._metric_key(name, labels)
        with self.lock:
            self._counters[key] += amount

    def set_gauge(self, name: str, value: float):
        with self.lock:
            self._gauges[name] = value

    def observe_ttft(self, model: str, seconds: float):
        with self.lock:
            entry = self._ttft[model]
            entry["count"] += 1
            entry["sum"] += seconds
            for b in self.ttft_buckets:
                if seconds <= b:
                    entry["buckets"][b] += 1

    # ── Convenience methods for pipeline ──
    def request_total(self, model: str = "", status: str = ""):
        self.incr("gateway_requests_total", {"model": model, "status": status})

    def auth_denied(self, reason: str = ""):
        self.incr("gateway_auth_denied_total", {"reason": reason})

    def rate_limit_denied(self, tier: str = ""):
        self.incr("gateway_rate_limit_denied_total", {"tier": tier})

    def security_denied(self, direction: str = "input"):
        self.incr("gateway_security_denied_total", {"direction": direction})

    def billing_event(self, operation: str = ""):
        self.incr(f"gateway_billing_{operation}_total")

    def upstream_error(self, error_type: str = ""):
        self.incr("gateway_upstream_errors_total", {"type": error_type})

    def tokens(self, model: str, input_tokens: int, output_tokens: int):
        self.incrby("gateway_input_tokens_total", input_tokens, {"model": model})
        self.incrby("gateway_output_tokens_total", output_tokens, {"model": model})

    def siem_delivery_failure(self):
        self.incr("gateway_siem_delivery_failures_total")

    # ── Helpers ──
    @staticmethod
    def _metric_key(name: str, labels: dict = None) -> str:
        if not labels:
            return name
        safe = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()) if v)
        return f"{name}{{{safe}}}"

    # ── Prometheus text output ──
    def prometheus_text(self) -> str:
        with self.lock:
            lines = ["# HELP gateway_requests_total Total requests",
                     "# TYPE gateway_requests_total counter",
                     "# HELP gateway_tokens_total Total tokens",
                     "# TYPE gateway_tokens_total counter",
                     "# HELP gateway_billing_total Billing operations",
                     "# TYPE gateway_billing_total counter",
                     "# HELP gateway_auth_denied_total Auth denials",
                     "# TYPE gateway_auth_denied_total counter",
                     "# HELP gateway_rate_limit_denied_total Rate limit denials",
                     "# TYPE gateway_rate_limit_denied_total counter",
                     "# HELP gateway_security_denied_total Security denials",
                     "# TYPE gateway_security_denied_total counter",
                     "# HELP gateway_upstream_errors_total Upstream errors",
                     "# TYPE gateway_upstream_errors_total counter",
                     "# HELP gateway_siem_delivery_failures_total SIEM delivery failures",
                     "# TYPE gateway_siem_delivery_failures_total counter",
                     f"# HELP gateway_active_requests Gauge",
                     f"# TYPE gateway_active_requests gauge"]

            for key, val in sorted(self._counters.items()):
                lines.append(f"{key} {val}")
            for name, val in sorted(self._gauges.items()):
                lines.append(f"{name} {val}")
            for model, data in self._ttft.items():
                safe = model.replace(".", "_").replace("-", "_")
                prefix = f'gateway_ttft_seconds{{model="{model}"}}'
                lines.append(f"# HELP gateway_ttft_seconds_{{model=\"{model}\"}} TTFT histogram")
                lines.append(f"# TYPE gateway_ttft_seconds histogram")
                lines.append(f"{prefix}_count {data['count']}")
                lines.append(f"{prefix}_sum {data['sum']:.6f}")
                for b in self.ttft_buckets:
                    lines.append(f'{prefix}_bucket{{le="{b}"}} {data["buckets"][b]}')

            lines.append("")
            return "\n".join(lines)


# Singleton instance
metrics = MetricsRegistry()
