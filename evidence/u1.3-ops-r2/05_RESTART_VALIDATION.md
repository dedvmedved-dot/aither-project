# U1.3-OPS-R2 — 05_RESTART_VALIDATION

**Date/Time (UTC):** 2026-07-26T02:14:50Z (probe start)

## Restart Execution

| Check | Result |
|-------|--------|
| `kubectl rollout restart` exit code | 0 (PASS) |
| `kubectl rollout status` exit code | 0 (PASS) |
| Duration | ~42 seconds |
| New ReplicaSet | 75d9bf999c |
| Old ReplicaSet | 64cb8c55b4 (terminated) |

## Pre-restart state

| Parameter | Value |
|-----------|-------|
| Strategy | RollingUpdate |
| Replicas | 2 |
| maxUnavailable | 0 |
| maxSurge | 1 |
| minReadySeconds | 5 |
| PDB | minAvailable=1 |

## Post-restart state

| Parameter | Value |
|-----------|-------|
| Pods Running | 2/2 |
| Endpoints | 2 |
| Deployment Available | 2/2 |

## Restart Result: PASS

Raw logs: `logs/05-availability-probe.log`, `logs/06-rollout-restart.log`
