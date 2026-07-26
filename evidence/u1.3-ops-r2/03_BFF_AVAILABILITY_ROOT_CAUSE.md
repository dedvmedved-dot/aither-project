# U1.3-OPS-R2 — 03_BFF_AVAILABILITY_ROOT_CAUSE

**Date/Time (UTC):** 2026-07-26T02:07:20Z

## Deployment Configuration (Live)

| Parameter | Value |
|-----------|-------|
| Strategy | **Recreate** |
| Replicas | 1 |
| maxUnavailable | N/A (Recreate) |
| maxSurge | N/A (Recreate) |
| minReadySeconds | 0 |
| PDB | **None** |
| Readiness Probe | HTTP GET /health, initialDelay=10s, period=10s |
| Startup Probe | HTTP GET /health, initialDelay=30s, period=5s, failureThreshold=30 |

## Deployment Configuration (Git Manifest)

| Parameter | Value |
|-----------|-------|
| Strategy | **Recreate** |
| Replicas | 1 |

**Live ↔ Git match: YES** — both use `Recreate`.

## Root Cause

### Primary Cause: Recreate Strategy

The BFF deployment uses `strategy.type: Recreate`. Kubernetes documentation states:

> "The Recreate strategy kills all existing Pods *before* new ones are created."

With `Recreate`:
1. `kubectl rollout restart` triggers new ReplicaSet
2. Kubernetes **terminates** the current pod
3. Endpoint is removed from the Service
4. New pod starts (pip install + uvicorn — ~30-45 seconds)
5. New pod passes readiness probe
6. Endpoint is added back

**During step 2-6: NO endpoints exist for the service.**

### Secondary Factor: Single Replica

With 1 replica and `Recreate`, there is zero redundancy. The service has exactly one backend — when it's removed, nothing remains to serve traffic.

### Tertiary Factor: No PDB

No PodDisruptionBudget exists. With a PDB (`minAvailable: 1`), Kubernetes would refuse voluntary disruptions that violate the budget (though `Recreate` + 1 replica renders PDB ineffective).

### Why Internet Zone got `000` vs Test Zone getting `502`

- **Test Zone** (`http://10.129.13.78:30080`): NodePort with no backend → nginx returns HTTP 502 Bad Gateway immediately.
- **Internet Zone** (`https://fb1.spb.ru`): Connection refused at the ingress level during the gap → curl exits with code 000 (connection failure).

## Observed Downtime

| Zone | HTTP Code | Duration | Root Cause |
|------|-----------|----------|------------|
| Internet | 000 | ~entire probe window | No endpoint, ingress returns connection failure |
| Test Zone | 502 | ~43 seconds | NodePort without backend, nginx 502 |

## Fix Required

Change strategy from `Recreate` to `RollingUpdate` with:
- `maxUnavailable: 0` (never drop below desired replicas)
- `maxSurge: 1` (allow one extra pod during rollout)
- `minReadySeconds: 5` (wait for pod to stabilize)
- Scale to `replicas: 2` for redundancy
- Add PodDisruptionBudget with `minAvailable: 1`

## Raw Log

Full command output in: `logs/02-bff-root-cause.log`
