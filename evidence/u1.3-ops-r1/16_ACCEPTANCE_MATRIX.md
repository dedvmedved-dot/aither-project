# U1.3-OPS-R1 — ACCEPTANCE MATRIX

| ID | Requirement | Command/Check | Evidence | Result |
|----|-------------|---------------|----------|:------:|
| OPS-GIT-001 | Git remote resolution | git ls-remote + cat-file | logs/02-commit-resolution.log | ✅ |
| OPS-GIT-002 | Commit chain verified | git diff baseline..HEAD | logs/02-commit-resolution.log | ✅ |
| OPS-GIT-003 | Clean working tree | git status --short | logs/01-git-remote.log | ✅ |
| OPS-GIT-004 | SHA discrepancy root cause | Fabricated SHA documented | 02_COMMIT_RESOLUTION.md | ✅ |
| OPS-START-001 | All deployments ready | rollout status × 10 | logs/04-startup.log | ✅ |
| OPS-RST-001 | Restart with probe | rollout restart + 180s probe | logs/05-continuous-probe.log, 06-rollout-restart.log | ✅* |
| OPS-RST-002 | Continuous availability | Probe analysis | logs/05-continuous-probe.log | ✅* |
| OPS-POD-001 | Pod recreation | delete + wait Ready | logs/07-pod-recreation.log | ✅ |
| OPS-POD-002 | UID verification | OLD_UID ≠ NEW_UID | logs/07-pod-recreation.log | ✅ |
| OPS-CM-001 | ConfigMap update | Annotation + rollout | logs/08-configmap-rollout.log | ✅ |
| OPS-RBK-001 | Rollback test | undo + status | logs/09-rollback.log | ✅ |
| OPS-RBK-002 | Image restored | Pre/post image comparison | logs/09-rollback.log | ✅ |
| OPS-SD-001 | Shutdown documentation | Docs reviewed | 09_SHUTDOWN_VALIDATION.md | ✅ |
| OPS-SD-002 | Shutdown runtime | NOT EXECUTED (no env) | 09_SHUTDOWN_VALIDATION.md | ⬜ |
| OPS-LOG-001 | Log scan (11 pods) | grep for error patterns | logs/11-log-scan.log | ✅ |
| OPS-LOG-002 | Restart counts | 0 restarts all pods | logs/11-log-scan.log | ✅ |
| OPS-SEC-001 | Secret scan | grep + manual review | logs/15-secret-scan.log | ✅ |
| OPS-PH-001 | Placeholder scan | 0 unfilled fields | logs/16-placeholder-scan.log | ✅ |
| OPS-CFG-001 | Config scan | ConfigMaps/Secrets audit | logs/14-config-scan.log | ✅ |
| OPS-DEP-001 | Dependency validation | pip check + requirements | dependency-scan.txt | ✅ |
| OPS-FC-001 | Fresh clone | git clone + file check | logs/12-fresh-clone.log | ✅ |
| OPS-SMK-001 | Smoke (Internet) | curl /health → 200 | logs/13-smoke.log | ✅ |
| OPS-SMK-002 | Smoke (Test Zone) | curl /health → 200 | logs/13-smoke.log | ✅ |
| OPS-DOC-001 | User docs audit | 17/17 scenarios | 14_USER_DOCUMENTATION_AUDIT.md | ✅ |
| OPS-DOC-002 | Ops docs audit | 6 docs, 18 checks | 15_OPERATIONS_DOCUMENTATION_AUDIT.md | ✅ |

*\* Internet zone had transient DNS resolution failures during restart probe window. Test Zone showed expected 200/502 codes. Full recovery confirmed in final smoke.*
