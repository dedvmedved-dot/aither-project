#!/usr/bin/env python3
"""
U1.3-OPS-R2 HTTP Availability Probe

Requirements:
- Python 3.11+
- TLS verification enabled for HTTPS
- Independent Internet and Test Zone probing
- Parallel probing
- Per-probe timestamps
- CSV/JSONL output
- Summary statistics
- Non-zero exit on any non-200
"""

import argparse
import csv
import json
import signal
import sys
import time
import urllib.request
import urllib.error
import ssl
import socket
import concurrent.futures
from datetime import datetime, timezone
from typing import Optional


class ProbeResult:
    def __init__(self, zone: str, url: str):
        self.zone = zone
        self.url = url
        self.probe_num: int = 0
        self.timestamp: str = ""
        self.http_status: Optional[int] = None
        self.latency_seconds: float = 0.0
        self.error_type: Optional[str] = None  # dns_failure, tls_failure, timeout, connection_failure, http_error
        self.error_message: str = ""

    def to_dict(self):
        return {
            "zone": self.zone,
            "url": self.url,
            "probe_num": self.probe_num,
            "timestamp": self.timestamp,
            "http_status": self.http_status,
            "latency_seconds": round(self.latency_seconds, 4),
            "error_type": self.error_type,
            "error_message": self.error_message,
        }


def probe_single(url: str, zone: str, probe_num: int, connect_timeout: int, request_timeout: int) -> ProbeResult:
    """Execute a single HTTP probe and return structured result."""
    result = ProbeResult(zone, url)
    result.probe_num = probe_num
    result.timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    start = time.monotonic()

    try:
        ctx = None
        if url.startswith("https://"):
            ctx = ssl.create_default_context()
            # TLS verification is ON by default — TLS is enforced

        req = urllib.request.Request(url, method="GET")
        resp = urllib.request.urlopen(req, timeout=request_timeout, context=ctx)

        result.http_status = resp.getcode()
        result.latency_seconds = time.monotonic() - start

    except urllib.error.HTTPError as e:
        result.http_status = e.code
        result.latency_seconds = time.monotonic() - start
        if result.http_status != 200:
            result.error_type = "http_error"
            result.error_message = f"HTTP {e.code}: {e.reason}"

    except urllib.error.URLError as e:
        result.latency_seconds = time.monotonic() - start
        reason_str = str(e.reason)

        if isinstance(e.reason, socket.gaierror):
            result.error_type = "dns_failure"
            result.error_message = f"DNS failure: {e.reason}"
        elif "CERTIFICATE_VERIFY_FAILED" in reason_str or "SSL" in reason_str or "certificate" in reason_str.lower():
            result.error_type = "tls_failure"
            result.error_message = f"TLS failure: {e.reason}"
        elif isinstance(e.reason, TimeoutError) or "timed out" in reason_str.lower():
            result.error_type = "timeout"
            result.error_message = f"Timeout: {e.reason}"
        else:
            result.error_type = "connection_failure"
            result.error_message = f"Connection failure: {e.reason}"

    except socket.timeout:
        result.latency_seconds = time.monotonic() - start
        result.error_type = "timeout"
        result.error_message = "Socket timeout"

    except Exception as e:
        result.latency_seconds = time.monotonic() - start
        result.error_type = "connection_failure"
        result.error_message = f"Unexpected error: {type(e).__name__}: {e}"

    return result


def generate_summary(zone: str, results: list[ProbeResult], planned_duration: int, planned_interval: int) -> dict:
    """Generate summary statistics for a zone."""
    actual_count = len(results)
    http_200 = sum(1 for r in results if r.http_status == 200)
    non_200 = sum(1 for r in results if r.http_status is not None and r.http_status != 200)
    dns_failures = sum(1 for r in results if r.error_type == "dns_failure")
    tls_failures = sum(1 for r in results if r.error_type == "tls_failure")
    timeouts = sum(1 for r in results if r.error_type == "timeout")
    connection_failures = sum(1 for r in results if r.error_type == "connection_failure")

    # Find consecutive failures
    max_consecutive = 0
    current_consecutive = 0
    first_failure_ts = ""
    last_failure_ts = ""
    for r in results:
        is_failure = (r.http_status != 200) or (r.error_type is not None)
        if is_failure:
            current_consecutive += 1
            max_consecutive = max(max_consecutive, current_consecutive)
            if not first_failure_ts:
                first_failure_ts = r.timestamp
            last_failure_ts = r.timestamp
        else:
            current_consecutive = 0

    if actual_count > 0:
        # Determine actual duration from first to last probe
        first_ts = datetime.fromisoformat(results[0].timestamp.replace("Z", "+00:00"))
        last_ts = datetime.fromisoformat(results[-1].timestamp.replace("Z", "+00:00"))
        actual_duration = (last_ts - first_ts).total_seconds()
        availability_pct = round((http_200 / actual_count) * 100, 2)
    else:
        actual_duration = 0.0
        availability_pct = 0.0

    exit_status = "PASS" if non_200 == 0 and dns_failures == 0 and tls_failures == 0 and timeouts == 0 else "FAIL"

    return {
        "zone": zone,
        "planned_duration_seconds": planned_duration,
        "actual_duration_seconds": round(actual_duration, 2),
        "planned_interval_seconds": planned_interval,
        "actual_probe_count": actual_count,
        "http_200_count": http_200,
        "non_200_count": non_200,
        "dns_failure_count": dns_failures,
        "tls_failure_count": tls_failures,
        "timeout_count": timeouts,
        "connection_failure_count": connection_failures,
        "max_consecutive_failures": max_consecutive,
        "first_failure_timestamp": first_failure_ts,
        "last_failure_timestamp": last_failure_ts,
        "availability_percent": availability_pct,
        "exit_status": exit_status,
    }


def main():
    parser = argparse.ArgumentParser(description="U1.3-OPS-R2 HTTP Availability Probe")
    parser.add_argument("--url", action="append", required=True,
                        help="URL in format 'zone=https://url', e.g. 'internet=https://fb1.spb.ru/health'")
    parser.add_argument("--duration", type=int, required=True,
                        help="Total probing duration in seconds")
    parser.add_argument("--interval", type=int, required=True,
                        help="Interval between probes in seconds")
    parser.add_argument("--connect-timeout", type=int, default=3,
                        help="Connect timeout in seconds")
    parser.add_argument("--request-timeout", type=int, default=10,
                        help="Request timeout in seconds")
    parser.add_argument("--output", required=True,
                        help="Path to CSV output log")
    parser.add_argument("--summary", required=True,
                        help="Path to JSON summary output")

    args = parser.parse_args()

    # Parse URLs
    targets = []
    for url_spec in args.url:
        zone, url = url_spec.split("=", 1)
        targets.append((zone, url))

    print(f"Probe started: {datetime.now(timezone.utc).isoformat()}")
    print(f"Duration: {args.duration}s, Interval: {args.interval}s")
    print(f"Targets: {[(z, u) for z, u in targets]}")
    print()

    # Write CSV header
    fieldnames = ["zone", "url", "probe_num", "timestamp", "http_status", "latency_seconds", "error_type", "error_message"]
    csvfile = open(args.output, "w", newline="")
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    # Results per zone
    results: dict[str, list[ProbeResult]] = {zone: [] for zone, _ in targets}

    probe_num = 0
    start_time = time.monotonic()
    overall_pass = True

    def probe_all_targets(p_num):
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(targets)) as executor:
            futures = {
                executor.submit(probe_single, url, zone, p_num, args.connect_timeout, args.request_timeout): zone
                for zone, url in targets
            }
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results[result.zone].append(result)
                writer.writerow(result.to_dict())
                csvfile.flush()

                status_str = str(result.http_status) if result.http_status else "ERR"
                err_str = f" [{result.error_type}]" if result.error_type else ""
                print(f"[{result.timestamp}] {result.zone:12s} probe={result.probe_num:4d} "
                      f"status={status_str:>4s} latency={result.latency_seconds:.3f}s{err_str}")

                if result.http_status != 200 or result.error_type:
                    nonlocal overall_pass
                    overall_pass = False

    # Signal handling for clean exit
    interrupted = False

    def handle_signal(sig, frame):
        nonlocal interrupted
        interrupted = True
        print("\nSignal received, finishing current probes...")

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    while True:
        elapsed = time.monotonic() - start_time
        if elapsed >= args.duration or interrupted:
            break

        probe_num += 1
        probe_all_targets(probe_num)

        if interrupted:
            break

        remaining = args.duration - (time.monotonic() - start_time)
        if remaining > 0:
            time.sleep(min(args.interval, remaining))

    csvfile.close()

    # Generate summaries
    summaries = []
    for zone, _ in targets:
        summary = generate_summary(zone, results[zone], args.duration, args.interval)
        summaries.append(summary)

    # Determine overall status
    all_pass = all(s["exit_status"] == "PASS" for s in summaries)

    full_summary = {
        "probe_start": datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat(),
        "probe_end": datetime.now(timezone.utc).isoformat(),
        "total_probes": probe_num,
        "targets": [{"zone": z, "url": u} for z, u in targets],
        "zone_summaries": summaries,
        "overall_status": "PASS" if all_pass else "FAIL",
    }

    with open(args.summary, "w") as f:
        json.dump(full_summary, f, indent=2)

    print(f"\n{'='*60}")
    for s in summaries:
        print(f"Zone: {s['zone']}")
        print(f"  Probes: {s['actual_probe_count']}")
        print(f"  HTTP 200: {s['http_200_count']}")
        print(f"  Non-200: {s['non_200_count']}")
        print(f"  DNS failures: {s['dns_failure_count']}")
        print(f"  TLS failures: {s['tls_failure_count']}")
        print(f"  Timeouts: {s['timeout_count']}")
        print(f"  Availability: {s['availability_percent']}%")
        print(f"  Status: {s['exit_status']}")
        print()

    print(f"Overall: {'PASS' if all_pass else 'FAIL'}")
    print(f"Summary written to: {args.summary}")
    print(f"CSV log written to: {args.output}")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
