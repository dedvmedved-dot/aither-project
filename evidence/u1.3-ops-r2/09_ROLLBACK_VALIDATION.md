# U1.3-OPS-R2 — 09_ROLLBACK_VALIDATION

**Date/Time (UTC):** 2026-07-26T02:22:09Z

## Procedure

1. Record pre-rollback revision and image
2. Create test revision (patch pod-template annotation)
3. Wait for rollout
4. Execute `kubectl rollout undo`
5. Wait for rollout
6. Verify image restored, annotation cleared

## Results

| Parameter | Value |
|-----------|-------|
| REV_BEFORE | 21 |
| REV_TEST | 22 |
| REV_AFTER | 23 |
| IMAGE_BEFORE | python:3.11-slim |
| IMAGE_AFTER | python:3.11-slim |
| Image restored | YES ✓ |
| Rollback marker cleared | YES ✓ |

## Verification

| Check | Result |
|-------|--------|
| Rollout undo exit code | 0 |
| Rollout status | successfully rolled out |
| Image matches pre-rollout | ✓ |
| Annotation absent | ✓ |
| Final available replicas | 2/2 |

## Rollback: PASS

Raw log: `logs/09-rollback.log`
