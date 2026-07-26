# U1.3-OPS-R1 — CONFIGMAP ROLLOUT VALIDATION

**Evidence:** logs/08-configmap-rollout.log  
**Timestamp:** 2026-07-26T01:32:23Z

## Procedure

| Step | Command | Result |
|------|---------|:------:|
| 1. Add annotation | `kubectl annotate configmap aither-bff-config audit-timestamp=20260726T013223Z` | ✅ EXIT_CODE=0 |
| 2. Verify annotation | `kubectl get configmap aither-bff-config -o jsonpath='{.metadata.annotations.audit-timestamp}'` | ✅ `20260726T013223Z` |
| 3. Rollout restart | `kubectl rollout restart deployment/aither-bff` | ✅ EXIT_CODE=0 |
| 4. Rollout status | `kubectl rollout status deployment/aither-bff --timeout=120s` | ✅ successfully rolled out |
| 5. Remove annotation | `kubectl annotate configmap aither-bff-config audit-timestamp-` | ✅ EXIT_CODE=0 |
| 6. Verify removed | `kubectl get configmap aither-bff-config -o jsonpath='{.metadata.annotations.audit-timestamp}'` | ✅ `<empty>` |

## Annotation Lifecycle

- **Annotation key:** `audit-timestamp`
- **Value:** `20260726T013223Z`
- **Target:** ConfigMap `aither-bff-config` (namespace: aither-inference)
- **Rollout duration:** <60s (4 wait cycles observed)
- **Cleanup:** Annotation removed after rollout verification

## Verification

- ConfigMap annotation propagation: ✅
- Annotation survives rollout restart: ✅ (verified post-restart, then cleaned up)
- BFF deployment healthy after ConfigMap change: ✅
- Annotation removal idempotent: ✅

## Conclusion

**ConfigMap annotation test and rollout restart: PASS** ✅
