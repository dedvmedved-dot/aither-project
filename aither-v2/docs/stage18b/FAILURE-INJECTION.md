# Stage 18B — Failure Injection

## Test Methodology

Each failure scenario was tested in isolation. The deploy script (`stage18a-deploy-services.sh`) was executed under controlled conditions that simulate each failure mode without affecting the production cluster.

## Test Results

| Test ID | Scenario | Method | Expected Exit | Actual Exit | Expected Message Contains | Actual Message | Production Impact |
|---------|----------|--------|---------------|-------------|--------------------------|----------------|-------------------|
| F-01 | Missing kubectl | Run script in PATH without kubectl | 1 | 1 | `kubectl not found in PATH` | `ERROR: kubectl not found in PATH` | ❌ None (isolated) |
| F-02 | Invalid cluster | Run with `KUBECONFIG=/dev/null` | 1 | 1 | `cluster is not reachable` | `ERROR: Kubernetes cluster is not reachable` | ❌ None (temporary kubeconfig) |
| F-03 | Missing namespace | Run with `NAMESPACE=nonexistent-test` | 1 | 1 | `Namespace.*does not exist` | `ERROR: Namespace 'nonexistent-stage18b-test' does not exist` | ❌ None (temporary env var) |
| F-04 | Missing Secret | Run with `NAMESPACE=aither-stage18b-negative` (no Secret present) | 1 | 1 | `Secret.*not found` | `ERROR: Secret 'aither-identity-secret' not found` | ❌ None (temporary namespace, deleted) |
| F-05 | Missing manifest | Run with modified script pointing to nonexistent file | 1 | 1 | `Manifest file not found` | `ERROR: Manifest file not found` | ❌ None (temporary copy) |
| F-06 | Rollout failure | Mock kubectl — rollout status returns exit 1 for aither-identity | 1 | 1 | `Rollout failed*` | `ERROR: Rollout failed for aither-identity` | ❌ None (mock kubectl, temp PATH) |
| F-07 | Diagnostics on failure | Same mock test — deployment + pod status | diagnostics emitted | ✅ emitted | diagnostics output | `NAME READY AVAILABLE`, pod `STATUS Running` | ❌ None (mock kubectl) |

## Diagnostics Verification

On rollout failure, the script outputs:
1. Deployment name
2. `kubectl get deployment <name> -n <ns> -o wide`
3. `kubectl get pods -n <ns> -l app=<name> -o wide`

This was confirmed by actual mock test (F-06) with mock kubectl rollout status returning exit 1. Diagnostics output was verified: `ERROR: Rollout failed for aither-identity` followed by deployment and pod status.

## Conclusion

All failure paths return non-zero exit codes with clear diagnostic messages. No production impact from any test.
