# Stage 18B-C1 — Acceptance Criteria Matrix

## Project

```text
Repository:   dedvmedved-dot/aither-project
Branch:       aither-v2
Baseline:     d1e641b602b61c36a0b965c6d4c3a2e37c312d10
```

## Matrix

| AC | Requirement | Result | Evidence ID | Evidence file | Notes |
| -- | ----------- | ------ | ----------- | ------------- | ----- |
| AC-01 | Accepted baseline HEAD confirmed | ✅ PASS | E-01 | REGRESSION-SUMMARY.md | `d1e641b602b61c36a0b965c6d4c3a2e37c312d10` |
| AC-02 | Cluster API reachable | ✅ PASS | E-02 | RUNTIME-EVIDENCE.md | `kubectl cluster-info` — reachable |
| AC-03 | All required nodes Ready | ✅ PASS | E-03 | RUNTIME-EVIDENCE.md | n7 Ready, n8 Ready |
| AC-04 | containerd operational on all required nodes | ✅ PASS | E-04 | CRI-RUNTIME-RECOVERY.md | n8: `systemctl is-active containerd` = active, crictl info RuntimeReady=true; n7: active (crictl: NOT INSTALLED, kubelet functional via pod scheduling) |
| AC-05 | Registry available after restart | ✅ PASS | E-05 | REGISTRY-PERSISTENCE.md | `systemctl restart aither-registry` → active, curl localhost:5000/v2/ → OK |
| AC-06 | Registry catalog preserved | ✅ PASS | E-06 | REGISTRY-PERSISTENCE.md | 3 repos: aither-identity, aither-portal-backend, aither-ai-platform (unchanged) |
| AC-07 | Required image digests recorded | ✅ PASS | E-07 | REGISTRY-PERSISTENCE.md | identity: `sha256:427314f...`, portal-backend: `sha256:940bc63...`, ai-platform: `sha256:ab2825f...` |
| AC-08 | Working Secret exists | ✅ PASS | E-08 | SECRET-LIFECYCLE-VALIDATION.md | `aither-identity-secret` in aither-inference |
| AC-09 | Real Secret values not exposed | ✅ PASS | E-09 | SECURITY-VALIDATION.md | No real secrets in repo; all matches are variable names, resource references, or documentation |
| AC-10 | Deploy does not create or overwrite Secret | ✅ PASS | E-10 | SECRET-LIFECYCLE-VALIDATION.md | Script checks existence, never creates or applies Secret; UID unchanged |
| AC-11 | Missing Secret returns non-zero exit | ✅ PASS | E-11 | FAILURE-INJECTION.md | `NAMESPACE=aither-stage18b-secret-test` → exit 1, clear error |
| AC-12 | Deployment completes with exit code 0 | ✅ PASS | E-12 | DEPLOYMENT-REPRODUCIBILITY.md | `./scripts/stage18a-deploy-services.sh` → exit 0 |
| AC-13 | Repeated deployment completes with exit code 0 | ✅ PASS | E-13 | DEPLOYMENT-REPRODUCIBILITY.md | Second run → exit 0, all `unchanged` |
| AC-14 | Deployment is idempotent | ✅ PASS | E-14 | DEPLOYMENT-REPRODUCIBILITY.md | Generations unchanged, no duplicate resources, Secret UID unchanged |
| AC-15 | All Aither deployments Available | ✅ PASS | E-15 | RUNTIME-EVIDENCE.md | 3 deployments, all Available (1/1) |
| AC-16 | All required pods Ready | ✅ PASS | E-16 | RUNTIME-EVIDENCE.md | identity, portal-backend, ai-platform — all Running 1/1 |
| AC-17 | Health endpoints pass repeatedly | ✅ PASS | E-17 | RUNTIME-EVIDENCE.md | ×3 each: identity HTTP 200, portal-backend HTTP 200, ai-platform HTTP 200 |
| AC-18 | Pod deletion recovery passes | ✅ PASS | E-15 | RUNTIME-EVIDENCE.md, SERVICE-DATA-PERSISTENCE.md | identity replacement verified (Stage 18B), portal-backend replacement verified (Stage 18B), **ai-platform replacement verified in Stage 18B-C3** (pod `-gxjcm` → `-bfgqn`, UID changed, rollout 1/1, health 200×3, marker preserved) |
| AC-19 | First node runtime restart passes | ✅ PASS | E-19 | CRI-RUNTIME-RECOVERY.md | n8: `systemctl restart containerd` → active, node Ready, CRI ready |
| AC-20 | Second node runtime restart passes | ✅ PASS | E-20 | CRI-RUNTIME-RECOVERY.md | n7: `systemctl restart containerd` → active, node Ready, pods Running |
| AC-21 | Persistent data survives pod recovery | ✅ PASS | E-15 | SERVICE-DATA-PERSISTENCE.md | Identity markers `stage18b-persistence-marker-1784738828` and `stage18b-c1-marker-1784740580` preserved; **AI Platform marker `stage18b-c3-ai-platform-marker-1784743322` preserved in Stage 18B-C3** |
| AC-22 | PVC/PV bindings remain valid | ✅ PASS | E-22 | SERVICE-DATA-PERSISTENCE.md | Both PVCs Bound, PVs Bound (Retain policy) |
| AC-23 | Rollout failure path returns non-zero exit | ✅ PASS | E-23 | FAILURE-INJECTION.md | Mock kubectl — rollout status exit 1 → actual deploy script exit 1 |
| AC-24 | Failure diagnostics are emitted | ✅ PASS | E-24 | FAILURE-INJECTION.md | `ERROR: Rollout failed`, deployment status, pod status all emitted |
| AC-25 | Scripts pass bash syntax checks | ✅ PASS | E-25 | REGRESSION-SUMMARY.md | `bash -n scripts/stage18a-deploy-services.sh` → SYNTAX OK |
| AC-26 | No real secrets in repository | ✅ PASS | E-26 | SECURITY-VALIDATION.md | Scan: no real secrets; all matches are variable names, documentation, or resource names |
| AC-27 | Documentation matches actual behavior | ✅ PASS | E-27 | ARCHITECTURE-VALIDATION.md | Cross-referenced — ports, namespaces, endpoints consistent |
| AC-28 | Evidence index is complete | ✅ PASS | E-28 | EVIDENCE-INDEX.md | All ACs mapped to evidence items |
| AC-29 | git diff --check is clean | ✅ PASS | E-29 | SECURITY-VALIDATION.md | No whitespace errors |
| AC-30 | Stage 18B pre-commit + corrective commits verified | ✅ PASS | E-30 | Git history: `fa7aefbf`, `9adb2f4` | Pre-commit validation completed before each commit. Post-commit verification successful. No force push / amend / rebase performed. Commits pushed to `aither-v2`. Connector audit for final acceptance pending. |

## Summary

```text
Acceptance criteria total:  30
PASS:                       30
FAIL:                       0
NOT RUN:                    0
BLOCKED:                    0
```

---

*Last updated: 2026-07-22T20:25:00Z*
*Stage: 18B-C1 Pre-Commit Evidence Completion*
