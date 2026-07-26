#!/usr/bin/env python3
"""
U1.3-OPS-R3 HTTP Availability Probe — CORRECTED

Fixes from R2 audit:
- time.time() for Unix timestamps (not monotonic)
- True 1-second interval between probe START times
- Parallel probing without blocking on completion
"""

import argparse
import csv
import json
import sys
import time
import urllib.request
import urllib.error
import ssl
import socket
import threading
from datetime import datetime, timezone


def probe_single(url: str, zone: str, probe_num: int, connect_timeout: int, request_timeout: int) -> dict:
    """Execute a single HTTP probe and return structured result."""
    result = {
        "zone": zone,
        "url": url,
        "probe_num": probe_num,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "http_status": None,
        "latency_seconds": 0.0,
        "error_type": None,
        "error_message": "",
    }

    start = time.time()

    try:
        ctx = None
        if url.startswith("https://"):
            ctx = ssl.create_default_context()

        req = urllib.request.Request(url, method="GET")
        resp = urllib.request.urlopen(req, timeout=request_timeout, context=ctx)

        result["http_status"] = resp.getcode()
        result["latency_seconds"] = round(time.time() - start, 4)

    except urllib.error.HTTPError as e:
        result["http_status"] = e.code
        result["latency_seconds"] = round(time.time() - start, 4)
        if e.code != 200:
            result["error_type"] = "http_error"
            result["error_message"] = f"HTTP {e.code}: {e.reason}"

    except urllib.error.URLError as e:
        result["latency_seconds"] = round(time.time() - start, 4)
        reason_str = str(e.reason)

        if isinstance(e.reason, socket.gaierror):
            result["error_type"] = "dns_failure"
            result["error_message"] = f"DNS failure: {e.reason}"
        elif "CERTIFICATE_VERIFY_FAILED" in reason_str or "SSL" in reason_str or "certificate" in reason_str.lower():
            result["error_type"] = "tls_failure"
            result["error_message"] = f"TLS failure: {e.reason}"
        elif isinstance(e.reason, TimeoutError) or "timed out" in reason_str.lower():
            result["error_type"] = "timeout"
            result["error_message"] = f"Timeout: {e.reason}"
        else:
            result["error_type"] = "connection_failure"
            result["error_message"] = f"Connection failure: {e.reason}"

    except socket.timeout:
        result["latency_seconds"] = round(time.time() - start, 4)
        result["error_type"] = "timeout"
        result["error_message"] = "Socket timeout"

    except Exception as e:
        result["latency_seconds"] = round(time.time() - start, 4)
        result["error_type"] = "connection_failure"
        result["error_message"] = f"Unexpected error: {type(e).__name__}: {e}"

    return result


def probe_worker(url: str, zone: str, probe_num: int, connect_timeout: int, request_timeout: int, results: list, lock: threading.Lock, writer, writer_lock: threading.Lock):
    """Worker function for threaded probing."""
    r = probe_single(url, zone, probe_num, connect_timeout, request_timeout)

    with lock:
        results.append(r)

    with writer_lock:
        writer.writerow(r)

    status_str = str(r["http_status"]) if r["http_status"] else "ERR"
    err_str = f" [{r['error_type']}]" if r["error_type"] else ""
    print(f"[{r['timestamp']}] {zone:12s} probe={probe_num:4d} "
          f"status={status_str:>4s} latency={r['latency_seconds']:.3f}s{err_str}")


def generate_summary(zone: str, results: list, planned_duration: int, planned_interval: int) -> dict:
    """Generate summary statistics for a zone."""
    actual_count = len(results)
    http_200 = sum(1 for r in results if r["http_status"] == 200)
    non_200 = sum(1 for r in results if r["http_status"] is not None and r["http_status"] != 200)
    dns_failures = sum(1 for r in results if r["error_type"] == "dns_failure")
    tls_failures = sum(1 for r in results if r["error_type"] == "tls_failure")
    timeouts = sum(1 for r in results if r["error_type"] == "timeout")
    connection_failures = sum(1 for r in results if r["error_type"] == "connection_failure")

    max_consecutive = 0
    current_consecutive = 0
    first_failure_ts = ""
    last_failure_ts = ""
    for r in results:
        is_failure = (r["http_status"] != 200) or (r["error_type"] is not None)
        if is_failure:
            current_consecutive += 1
            max_consecutive = max(max_consecutive, current_consecutive)
            if not first_failure_ts:
                first_failure_ts = r["timestamp"]
            last_failure_ts = r["timestamp"]
        else:
            current_consecutive = 0

    if actual_count > 0:
        first_r = results[0]
        last_r = results[-1]
        actual_duration = (datetime.fromisoformat(last_r["timestamp"].replace("Z", "+00:00")) -
                          datetime.fromisoformat(first_r["timestamp"].replace("Z", "+00:00"))).total_seconds()
        availability_pct = round((http_200 / actual_count) * 100, 2)
    else:
        actual_duration = 0.0
        availability_pct = 0.0

    # Expected probe count gate
    expected_count = planned_duration // planned_interval
    missing_probes = max(0, expected_count - actual_count)
    extra_probes = max(0, actual_count - expected_count)

    # Interval statistics
    interval_stats = {}
    if len(results) >= 2:
        sorted_results = sorted(results, key=lambda r: r["timestamp"])
        intervals = []
        for j in range(1, len(sorted_results)):
            try:
                t1 = datetime.fromisoformat(sorted_results[j-1]["timestamp"].replace("Z", "+00:00"))
                t2 = datetime.fromisoformat(sorted_results[j]["timestamp"].replace("Z", "+00:00"))
                intervals.append((t2 - t1).total_seconds())
            except Exception:
                pass
        if intervals:
            intervals_sorted = sorted(intervals)
            n = len(intervals_sorted)
            p95_idx = int(n * 0.95)
            in_range = sum(1 for x in intervals if 0.8 <= x <= 1.2)
            interval_stats = {
                "intervals_total": n,
                "intervals_in_range": in_range,
                "intervals_in_range_percent": round((in_range / n) * 100, 2) if n > 0 else 0.0,
                "min_interval_seconds": round(min(intervals_sorted), 3),
                "max_interval_seconds": round(max(intervals_sorted), 3),
                "avg_interval_seconds": round(sum(intervals_sorted) / n, 3),
                "p95_interval_seconds": round(intervals_sorted[min(p95_idx, n-1)], 3),
            }

    exit_status = "PASS" if (non_200 == 0 and dns_failures == 0 and tls_failures == 0 and timeouts == 0 and connection_failures == 0 and missing_probes == 0) else "FAIL"

    return {
        "zone": zone,
        "planned_duration_seconds": planned_duration,
        "actual_duration_seconds": round(actual_duration, 2),
        "planned_interval_seconds": planned_interval,
        "actual_probe_count": actual_count,
        "expected_probe_count": expected_count,
        "missing_probe_count": missing_probes,
        "extra_probe_count": extra_probes,
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
        "interval_statistics": interval_stats,
        "exit_status": exit_status,
    }


def main():
    parser = argparse.ArgumentParser(description="U1.3-OPS-R3 HTTP Availability Probe")
    parser.add_argument("--url", action="append", required=True,
                        help="URL in format 'zone=https://url'")
    parser.add_argument("--duration", type=int, required=True)
    parser.add_argument("--interval", type=int, required=True)
    parser.add_argument("--connect-timeout", type=int, default=3)
    parser.add_argument("--request-timeout", type=int, default=10)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary", required=True)

    args = parser.parse_args()

    targets = []
    for url_spec in args.url:
        zone, url = url_spec.split("=", 1)
        targets.append((zone, url))

    probe_start_ts = datetime.now(timezone.utc)
    print(f"Probe started: {probe_start_ts.isoformat()}")
    print(f"Duration: {args.duration}s, Interval: {args.interval}s")
    print(f"Targets: {[(z, u) for z, u in targets]}")
    print()

    fieldnames = ["zone", "url", "probe_num", "timestamp", "http_status", "latency_seconds", "error_type", "error_message"]
    csvfile = open(args.output, "w", newline="")
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    results: dict[str, list] = {zone: [] for zone, _ in targets}
    results_lock = threading.Lock()
    writer_lock = threading.Lock()

    probe_num = 0
    overall_pass = True

    # Fire probes at exact 1-second intervals
    next_fire = time.time()
    deadline = next_fire + args.duration
    all_threads = []  # Track all threads for proper join

    while time.time() < deadline:
        probe_num += 1

        # Spawn all zone probes in parallel (non-blocking)
        for zone, url in targets:
            t = threading.Thread(
                target=probe_worker,
                args=(url, zone, probe_num, args.connect_timeout, args.request_timeout,
                      results[zone], results_lock, writer, writer_lock),
                daemon=False
            )
            t.start()
            all_threads.append(t)

        # Wait for next interval
        next_fire += args.interval
        sleep_time = next_fire - time.time()
        if sleep_time > 0:
            time.sleep(sleep_time)

    # Join all remaining threads with timeout
    thread_timeout = max(args.request_timeout + 5, 15)
    for t in all_threads:
        t.join(timeout=thread_timeout)

    # Count threads that didn't finish
    unfinished = sum(1 for t in all_threads if t.is_alive())
    if unfinished > 0:
        print(f"WARNING: {unfinished} threads did not complete within timeout", file=sys.stderr)
        overall_pass = False  # Unfinished threads = FAIL

    csvfile.close()

    # Sort results before generating summaries
    for zone, _ in targets:
        results[zone].sort(key=lambda r: r["probe_num"])

    # Generate summaries
    summaries = []
    for zone, _ in targets:
        summary = generate_summary(zone, results[zone], args.duration, args.interval)
        summaries.append(summary)
        if (summary["non_200_count"] > 0 or summary["dns_failure_count"] > 0 or
            summary["tls_failure_count"] > 0 or summary["timeout_count"] > 0 or
            summary["connection_failure_count"] > 0 or summary["missing_probe_count"] > 0):
            overall_pass = False

    # Correct probe_start timestamp
    probe_start_iso = probe_start_ts.isoformat()

    full_summary = {
        "probe_start": probe_start_iso,
        "probe_end": datetime.now(timezone.utc).isoformat(),
        "total_probes": probe_num,
        "unfinished_threads": unfinished,
        "targets": [{"zone": z, "url": u} for z, u in targets],
        "zone_summaries": summaries,
        "overall_status": "PASS" if overall_pass else "FAIL",
    }

    with open(args.summary, "w") as f:
        json.dump(full_summary, f, indent=2)

    print(f"\n{'='*60}")
    for s in summaries:
        print(f"Zone: {s['zone']}")
        print(f"  Probes: {s['actual_probe_count']}  HTTP 200: {s['http_200_count']}  Non-200: {s['non_200_count']}")
        print(f"  DNS/TLS/Timeout: {s['dns_failure_count']}/{s['tls_failure_count']}/{s['timeout_count']}")
        print(f"  Availability: {s['availability_percent']}%  Status: {s['exit_status']}")
        print()

    print(f"Overall: {'PASS' if overall_pass else 'FAIL'}")
    print(f"Summary: {args.summary}  CSV: {args.output}")

    sys.exit(0 if overall_pass else 1)


if __name__ == "__main__":
    main()
