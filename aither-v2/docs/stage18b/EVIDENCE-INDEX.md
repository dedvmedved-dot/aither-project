# Stage 18B — Evidence Index

| ID | File | Purpose | Method |
|----|------|---------|--------|
| E-01 | ARCHITECTURE-VALIDATION.md | Cluster topology, CRI status, service inventory | kubectl + SSH |
| E-02 | REGISTRY-PERSISTENCE.md | Registry catalog, tags, digest verification | curl + kubectl describe |
| E-03 | SECRET-LIFECYCLE-VALIDATION.md | Secret existence, UID tracking, deploy safety | kubectl + grep |
| E-04 | CRI-RUNTIME-RECOVERY.md | containerd restart tests (n7, n8, registry) | SSH + systemctl |
| E-05 | SERVICE-DATA-PERSISTENCE.md | Persistent marker survival test | kubectl + SSH (crictl exec) |
| E-06 | SECURITY-VALIDATION.md | Secret scan, repository integrity | grep + review |
| E-07 | REGRESSION-SUMMARY.md | Full regression matrix (42 tests) | All methods |
| E-08 | DEPLOYMENT-REPRODUCIBILITY.md | Deploy script output, idempotency | Script execution |
| E-09 | FAILURE-INJECTION.md | Failure-path validation (7 scenarios with actual tests) | Script execution + mock kubectl |
| E-10 | RUNTIME-EVIDENCE.md | Live system state snapshot | kubectl + SSH |
| E-11 | PRE-COMMIT-MANIFEST.md | File inventory and acceptance criteria | Git + review |
| E-12 | OPERATIONAL-RUNBOOK.md | Operational procedures | Documentation |
| E-13 | FINAL-REPORT.md | Stage 18B-C1 final report | Consolidation |
| E-14 | ACCEPTANCE-MATRIX.md | AC-01 through AC-30 with evidence IDs | Consolidation |
| E-15 | RUNTIME-EVIDENCE.md (AI Platform Corrective section) | AI Platform pod deletion, replacement, marker preservation, health ×3 (Stage 18B-C3) | kubectl + crictl exec via SSH |
| E-16 | SERVICE-DATA-PERSISTENCE.md | Historical marker clarification — three markers explained | Documentation |

## Acceptance Criteria Coverage

| Criterion | Covered By |
|-----------|-----------|
| AC-01 Accepted baseline HEAD confirmed | R-01 |
| AC-02 Cluster API reachable | R-03 |
| AC-03 All required nodes Ready | R-04 |
| AC-04 containerd operational | R-05 |
| AC-05 Registry available after restart | R-30 |
| AC-06 Registry catalog preserved | R-31 |
| AC-07 Required image digests recorded | R-10 |
| AC-08 Working Secret exists | R-11 |
| AC-09 Real Secret values not exposed | R-12 |
| AC-10 Deploy does not create/overwrite Secret | R-20 |
| AC-11 Missing Secret non-zero exit | R-13 |
| AC-12 Deployment exit 0 | R-14 |
| AC-13 Repeated deployment exit 0 | R-18 |
| AC-14 Deployment is idempotent | R-19 |
| AC-15 All deployments Available | R-15,16,17 |
| AC-16 All required pods Ready | R-25,26,27 |
| AC-17 Health endpoints pass repeatedly | R-22,23,24 |
| AC-18 Pod deletion recovery | R-25,26,27 (E-15 for ai-platform) |
| AC-19 First node runtime restart | R-28 |
| AC-20 Second node runtime restart | R-29 |
| AC-21 Persistent data survives pod recovery | R-33 |
| AC-22 PVC/PV bindings valid | R-21 |
| AC-23 Rollout failure path non-zero exit | R-36 |
| AC-24 Failure diagnostics emitted | R-37 |
| AC-25 Scripts pass bash syntax | R-38 |
| AC-26 No real secrets in repository | R-40 |
| AC-27 Documentation matches behavior | R-42 |
| AC-28 Evidence index complete | E-16 (this file) |
| AC-29 git diff --check clean | R-41 |
| AC-30 Stage 18B commits verified | ✅ Confirmed (fa7aefbf + 9adb2f4, no force push) |
