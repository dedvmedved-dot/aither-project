# API Stability Test Results (v2 — 100 requests)

**Date:** 2026-07-19  
**Method:** `kubectl get --raw='/readyz' --request-timeout=5s`  
**Source:** Admin VPS (remote via bastion)

---

## Results

| Metric | Value |
|---|---|
| Total requests | 100 |
| **Success** | **47** |
| **Failure (timeout)** | **53** |
| **Success rate** | **47.0%** |
| Latency (avg) | 329 ms |
| Latency (p50) | 328 ms |
| Latency (p95) | 348 ms |
| Latency (p99) | 356 ms |
| Latency (max) | 356 ms |

## Pattern

- Requests 1–15: All OK (100%)
- Requests 16–17: Intermittent FAIL (2 failures)
- Requests 18–49: All OK (100%)
- **Requests 50–100: MASSIVE FAILURE — 53 consecutive timeouts**

## Analysis

The API server at `10.129.13.78:6443` becomes completely unresponsive after ~50 requests. This is NOT a cold-start issue — the API server was already running before the test (warm-up request succeeded). The pattern suggests:

1. **Connection pool exhaustion** on the API server side
2. **etcd timeout** cascading to API server
3. **TCP/HTTP2 connection leak** through the bastion
4. **Inference load on n8 control-plane** contributing to resource exhaustion

## Previous test vs Current

| Test | Success rate | Notes |
|---|---|---|
| 30 requests (earlier) | 96.7% (29/30) | One cold-start timeout only |
| 100 requests (now) | 47.0% | Collapse after ~50 requests |

The earlier 30-request test was insufficient to detect the instability pattern.

## Recommendation

1. Run parallel test from local `n8` (`/etc/kubernetes/admin.conf`) to isolate bastion/network
2. Check `kube-apiserver` logs and etcd health
3. Check TCP connection limits and `etcd --max-txn-ops`
4. Move inference off control-plane (n8) before production use
