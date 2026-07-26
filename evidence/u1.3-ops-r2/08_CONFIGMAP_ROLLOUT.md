# U1.3-OPS-R2 — 08_CONFIGMAP_ROLLOUT

**Date/Time (UTC):** 2026-07-26T02:20:36Z

## Procedure

1. Annotate ConfigMap `aither-bff-config` with `ops.aither/u13-ops-r2`
2. Verify annotation present
3. `kubectl rollout restart deployment/aither-bff`
4. Wait for rollout to complete
5. Remove annotation
6. Verify annotation removed

## Results

| Step | Result |
|------|--------|
| Annotation added | 20260726T022036Z |
| Annotation verified | ✓ |
| Rollout restart | EXIT_CODE=0 |
| Rollout status | successfully rolled out |
| New ReplicaSet | 648757b4bb |
| Annotation removed | ✓ |
| Annotation absent after removal | YES |

## Final State

| Pod | Status | Age |
|-----|--------|-----|
| aither-bff-648757b4bb-9tvzj | Running | 41s |
| aither-bff-648757b4bb-srx7r | Running | 76s |
| Available replicas | 2/2 |

## ConfigMap Rollout: PASS

Raw log: `logs/08-configmap-rollout.log`
