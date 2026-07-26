# U1.3-OPS-R2 — 02_IMPLEMENTATION_CHANGES

**Date/Time (UTC):** 2026-07-26T02:09:00Z

## Changes Made

### 1. BFF Deployment Strategy (Root Cause Fix)

**File:** `aither-v2/manifests/mvp-roadmap/05-bff/bff-mvp.yaml`

| Parameter | Before | After |
|-----------|--------|-------|
| Strategy | `Recreate` | `RollingUpdate` |
| maxUnavailable | N/A | `0` |
| maxSurge | N/A | `1` |
| Replicas | `1` | `2` |
| minReadySeconds | `0` | `5` |

**Rationale:** `Recreate` + 1 replica = guaranteed downtime during restart. `RollingUpdate` with `maxUnavailable: 0` ensures service continuity — new pod must be Ready before old pod is terminated.

### 2. PodDisruptionBudget

**File:** `aither-v2/manifests/mvp-roadmap/05-bff/bff-pdb.yaml` (NEW)

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
spec:
  minAvailable: 1
```

Ensures at least 1 BFF pod is always available during voluntary disruptions.

### 3. Evidence Collector Script

**File:** `scripts/ops/u13_ops_r2_collect.sh` (NEW)

Corrected from R1: uses `set +e`/`set -e` pattern in `run_logged()` to guarantee exit code capture regardless of `set -e`. Separate functions for each collection phase.

### 4. HTTP Availability Probe

**File:** `scripts/ops/http_availability_probe.py` (NEW)

Python 3.11 probe with:
- TLS verification enabled (TLS enforced, no insecure fallback)
- Independent per-zone probing
- Parallel execution via ThreadPoolExecutor
- Per-probe timestamps, status, latency
- DNS/TLS/timeout/connection failure classification
- CSV output + JSON summary
- Non-zero exit on any non-200

## Resource Validation

| Resource | Available |
|----------|-----------|
| CPU (n7-gpu) | 222m / 0% |
| CPU (n8-gpu) | 1412m / 1% |
| Memory (n7-gpu) | 34.8 Gi / 4% |
| Memory (n8-gpu) | 40.8 Gi / 5% |

BFF resource requests: 200m CPU, 256Mi memory. Adding 1 replica consumes <0.2% of available cluster resources. Safe.

## Runtime Verification

| Check | Result |
|-------|--------|
| Apply manifest | PASS (exit 0) |
| Rollout status | PASS (2/2 available) |
| 2 pods Running | PASS |
| 2 endpoints | PASS |
| PDB active | PASS |
| Test Zone /health | PASS (200) |
| Internet Zone /health | BLOCKED (DNS timeout — environment level) |
