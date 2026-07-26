# U1.3-OPS-R2 — 20_DEVIATIONS_AND_LIMITATIONS

**Date/Time (UTC):** 2026-07-26

## Resolved Defects (from U1.3-OPS-R1)

| ID | Description | Status |
|----|-------------|--------|
| OPS-R1-001 | Final report placeholders | RESOLVED |
| OPS-R1-002 | Fabricated SHA | RESOLVED (real: 2ed4b4c0a83be...) |
| OPS-R1-003 | Missing raw evidence | RESOLVED |
| OPS-R1-004 | Shutdown misclassified | CORRECTED (BLOCKED, honest) |
| OPS-R1-005 | Incomplete ops docs | RESOLVED |

## Critical Defects

**0 critical defects open.**

## High Defects

**0 high defects open.**

## Medium Defects

**0 medium defects open.**

## Known Limitations

| Limitation | Severity | Mitigation |
|-----------|----------|------------|
| No isolated test environment | Medium | Shutdown test not executed (BLOCKED, honest) |
| Prometheus/Grafana not deployed | Medium | Manual health checks; documented in Monitoring Guide |
| Full DR drill not performed | Low | Backup/Restore procedures documented; test restore procedure defined |
| Internet DNS resolution slow (~5s) | Low | Environment-level; does not affect availability (all probes 200) |
| Single-node control plane | Low | Worker node available for failover of stateless workloads |
| Volume snapshots depend on CSI driver | Low | Procedure documented for when CSI supports it |

## User Handover

PROHIBITED — awaiting external audit.

## Controlled Beta

BLOCKED — U1.3-OPS not yet accepted.

## Hermes Status

STOPPED — awaiting ChatGPT external audit (after Commit C).
