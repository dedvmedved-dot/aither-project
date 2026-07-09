"""
Aither Gateway — Prometheus Metrics (TTFT, throughput, billing).
Exposes /metrics endpoint for Prometheus scraping.
"""

import time
import threading
from collections import defaultdict

# ── In-memory metrics store ─────────────────────────────────────

class Metrics:
    """Thread-safe Prometheus-compatible metrics registry."""

    def __init__(self):
        self.lock = threading.Lock()

        # TTFT histogram (seconds) — per model
        # Buckets: 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60
        self.ttft_buckets = [0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60]
        self.ttft = defaultdict(lambda: {"count": 0, "sum": 0.0, "buckets": {b: 0 for b in self.ttft_buckets}})

        # Request counters
        self.requests_total = defaultdict(int)  # key: model:org:status
        self.tokens_total = defaultdict(int)    # key: model:org:type (input/output/total)
        self.billing_errors = defaultdict(int)  # key: org:error
        self.drain_blocks = defaultdict(int)    # key: model
        self.active_requests = 0                # gauge

    def observe_ttft(self, model: str, seconds: float):
        """Record TTFT for a model."""
        with self.lock:
            entry = self.ttft[model]
            entry["count"] += 1
            entry["sum"] += seconds
            for b in self.ttft_buckets:
                if seconds <= b:
                    entry["buckets"][b] += 1

    def incr_request(self, model: str, org_id: str, status: str):
        with self.lock:
            self.requests_total[f"{model}:{org_id}:{status}"] += 1

    def incr_tokens(self, model: str, org_id: str, type_: str, amount: int):
        with self.lock:
            self.tokens_total[f"{model}:{org_id}:{type_}"] += amount

    def incr_billing_error(self, org_id: str, error: str):
        with self.lock:
            self.billing_errors[f"{org_id}:{error}"] += 1

    def incr_drain_block(self, model: str):
        with self.lock:
            self.drain_blocks[model] += 1

    def set_active_requests(self, count: int):
        with self.lock:
            self.active_requests = count

    def incr_active(self):
        with self.lock:
            self.active_requests += 1

    def decr_active(self):
        with self.lock:
            self.active_requests = max(0, self.active_requests - 1)

    def prometheus_text(self) -> str:
        """Render metrics in Prometheus text format."""
        with self.lock:
            lines = []

            # TTFT histogram
            for model, data in self.ttft.items():
                safe_model = model.replace(".", "_").replace("-", "_")
                prefix = f'gateway_ttft_seconds{{model="{model}"}}'
                lines.append(f"# HELP gateway_ttft_seconds TTFT per model")
                lines.append(f"# TYPE gateway_ttft_seconds histogram")
                lines.append(f"{prefix}_count {data['count']}")
                lines.append(f"{prefix}_sum {data['sum']:.6f}")
                for b in self.ttft_buckets:
                    lines.append(f'{prefix}_bucket{{le="{b}"}} {data["buckets"][b]}')
                lines.append(f'{prefix}_bucket{{le="+Inf"}} {data["count"]}')

            # Requests counter
            lines.append("# HELP gateway_requests_total Total requests")
            lines.append("# TYPE gateway_requests_total counter")
            for key, val in self.requests_total.items():
                model, org, status = key.split(":", 2)
                lines.append(f'gateway_requests_total{{model="{model}",org_id="{org}",status="{status}"}} {val}')

            # Tokens counter
            lines.append("# HELP gateway_tokens_total Total tokens processed")
            lines.append("# TYPE gateway_tokens_total counter")
            for key, val in self.tokens_total.items():
                parts = key.split(":", 2)
                if len(parts) == 3:
                    model, org, type_ = parts
                    lines.append(f'gateway_tokens_total{{model="{model}",org_id="{org}",type="{type_}"}} {val}')

            # Billing errors
            lines.append("# HELP gateway_billing_errors_total Billing errors")
            lines.append("# TYPE gateway_billing_errors_total counter")
            for key, val in self.billing_errors.items():
                org, error = key.split(":", 1)
                lines.append(f'gateway_billing_errors_total{{org_id="{org}",error="{error}"}} {val}')

            # Drain blocks
            lines.append("# HELP gateway_drain_blocks_total Drain-blocked requests")
            lines.append("# TYPE gateway_drain_blocks_total counter")
            for model, val in self.drain_blocks.items():
                lines.append(f'gateway_drain_blocks_total{{model="{model}"}} {val}')

            # Active requests (gauge)
            lines.append("# HELP gateway_active_requests Active in-flight requests")
            lines.append("# TYPE gateway_active_requests gauge")
            lines.append(f"gateway_active_requests {self.active_requests}")

            # Uptime
            if hasattr(self, 'start_time'):
                uptime = time.time() - self.start_time
                lines.append("# HELP gateway_uptime_seconds Gateway process uptime")
                lines.append("# TYPE gateway_uptime_seconds gauge")
                lines.append(f"gateway_uptime_seconds {uptime:.0f}")

            return "\n".join(lines) + "\n"


# ── Singleton ────────────────────────────────────────────────────

metrics = Metrics()
metrics.start_time = time.time()


# ── Summary helpers ──────────────────────────────────────────────

def metrics_summary() -> dict:
    """Human-readable summary for admin endpoint."""
    with metrics.lock:
        ttft_summary = {}
        for model, data in metrics.ttft.items():
            if data["count"] > 0:
                ttft_summary[model] = {
                    "count": data["count"],
                    "avg_seconds": round(data["sum"] / data["count"], 3),
                    "p50_seconds": _approx_percentile(data, 0.50),
                    "p95_seconds": _approx_percentile(data, 0.95),
                    "p99_seconds": _approx_percentile(data, 0.99),
                }

        return {
            "active_requests": metrics.active_requests,
            "total_requests": sum(metrics.requests_total.values()),
            "total_tokens": sum(v for k, v in metrics.tokens_total.items() if ":total" in k),
            "ttft_by_model": ttft_summary,
        }


def _approx_percentile(data: dict, p: float) -> float:
    """Approximate percentile from histogram buckets."""
    if data["count"] == 0:
        return 0
    target = data["count"] * p
    cumulative = 0
    for b in sorted(data["buckets"].keys()):
        cumulative += data["buckets"][b]
        if cumulative >= target:
            return round(b, 3)
    return max(data["buckets"].keys()) if data["buckets"] else 0
