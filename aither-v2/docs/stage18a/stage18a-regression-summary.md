# Stage 18A — Regression Summary

## Regression Tests

| Test ID | Test | Expected | Actual | Result | Evidence |
|---------|------|----------|--------|--------|----------|
| R-01 | Kubernetes nodes Ready | Both nodes Ready | n7: Ready, n8: Ready | PASS | `kubectl get nodes` 2026-07-22 |
| R-02 | CRI functional | crictl info: RuntimeReady=true, NetworkReady=true | RuntimeReady: true, NetworkReady: true | PASS | SSH to n8 — `crictl info` |
| R-03 | containerd active | systemctl is-active containerd: active | active (both nodes) | PASS | SSH to n8/n7 |
| R-04 | Persistent registry available | GET /v2/ → 200 OK | `{}` 200 OK | PASS | SSH to n8 — `curl localhost:5000/v2/` |
| R-05 | Stage 18A image pullable | crictl pull succeeds | `Image is up to date` | PASS | SSH to n8 — `crictl pull` |
| R-06 | Workload Running | All 3 Stage 18A pods Running 1/1 | identity ✅, portal-backend ✅, ai-platform ✅ | PASS | `kubectl get pods -n aither-inference` |
| R-07 | Rollout successful | rollout status: success | All 3 deployments successfully rolled out | PASS | `kubectl rollout status deployment/...` |
| R-08 | Health checks (identity) | GET /health → 200 | 200 OK (port-forward verified) | PASS | Stage 18I evidence |
| R-09 | Health checks (portal-backend) | GET /health → 200 | 200 OK (kubelet probes + logs) | PASS | Stage 18I + kubelet pod describe |
| R-10 | Health checks (ai-platform) | GET /health → 200 | 200 OK (kubelet probes + logs) | PASS | Stage 18I + kubelet pod describe |
| R-11 | Image digest match | Pod Image ID matches built digest | All 3 SHA-256 digests match | PASS | `kubectl describe pod` vs registry |
| R-12 | Pre-existing pods stable | Other pods unaffected | All pre-existing pods Running | PASS | `kubectl get pods -A` |
| R-13 | Git diff --check clean | No whitespace errors | CLEAN | PASS | `git diff --check` |
| R-14 | Registry catalog preserved | 3 repositories | 3 repositories: aither-identity, aither-portal-backend, aither-ai-platform | PASS | `curl localhost:5000/v2/_catalog` |

## Summary

- **Total tests:** 14
- **PASS:** 14
- **FAIL:** 0
- **NOT RUN:** 0
- **BLOCKED:** 0

No destructive tests were performed. System remains in working state after all tests.
