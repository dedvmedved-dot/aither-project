# U1.3-OPS-R2 — 06_CONTINUOUS_AVAILABILITY

**Date/Time (UTC):** 2026-07-26T02:14:50Z — 2026-07-26T02:18:54Z
**Probe duration:** 240 seconds
**Probe interval:** 1 second

## Internet Zone (https://fb1.spb.ru/health)

| Metric | Value |
|--------|-------|
| Total probes | 40 |
| HTTP 200 | 40 |
| Non-200 | 0 |
| DNS failures | 0 |
| TLS failures | 0 |
| Timeouts | 0 |
| Connection failures | 0 |
| Max consecutive failures | 0 |
| Availability | 100.00% |
| Exit status | **PASS** |

## Test Zone (http://10.129.13.78:30080/health)

| Metric | Value |
|--------|-------|
| Total probes | 40 |
| HTTP 200 | 40 |
| Non-200 | 0 |
| DNS failures | 0 |
| TLS failures | 0 |
| Timeouts | 0 |
| Connection failures | 0 |
| Max consecutive failures | 0 |
| Availability | 100.00% |
| Exit status | **PASS** |

## Zero-downtime restart

| Metric | Result |
|--------|--------|
| Non-200 during restart | 0 |
| Endpoint loss | None detected |
| Zero-downtime achieved | **PASS** |

## Summary

**Continuous availability: PASS** — 40/40 probes HTTP 200 for both zones during controlled rolling restart. The `RollingUpdate` strategy with `maxUnavailable: 0` successfully eliminated the downtime previously caused by the `Recreate` strategy.

Raw evidence: `logs/05-availability-probe.log`, `availability-summary.json`
