# U1.3-OPS-R2 — 19_ACCEPTANCE_MATRIX

**Date/Time (UTC):** 2026-07-26

| ID | Requirement | Command | Raw Evidence | Result | Auditor Note |
|----|-------------|---------|-------------|--------|-------------|
| AM-01 | Git baseline | git rev-parse HEAD | logs/01-git-baseline.log | PASS | 79026986f5bda... |
| AM-02 | Commit separation A/B/C | git log --oneline | 01_BASELINE.md | PASS | A=349f78b, B=df6f4fe, C=cf8bf4fd3cc6847a411708de0017c8e49221e8df |
| AM-03 | Collector script | scripts/ops/u13_ops_r2_collect.sh | source file | PASS | set +e/set -e pattern |
| AM-04 | Probe correctness | scripts/ops/http_availability_probe.py | source file | PASS | TLS enforced, parallel, CSV+JSON |
| AM-05 | DNS preflight | 10× curl each zone | logs/04-dns-preflight.log | PASS | 10/10 both zones |
| AM-06 | Restart execution | kubectl rollout restart | logs/06-rollout-restart.log | PASS | RC=0 |
| AM-07 | Continuous availability Internet | python3 probe 240s | logs/05-availability-probe.log | PASS | 40/40 HTTP 200, 100% |
| AM-08 | Continuous availability Test Zone | python3 probe 240s | logs/05-availability-probe.log | PASS | 40/40 HTTP 200, 100% |
| AM-09 | Zero-downtime restart | RollingUpdate maxUnavail=0 | 06_CONTINUOUS_AVAILABILITY.md | PASS | 0 non-200 during restart |
| AM-10 | Pod recreation | kubectl delete pod + wait | logs/07-pod-recreation.log | PASS | UID changed, 31s |
| AM-11 | ConfigMap rollout | annotate + rollout + remove | logs/08-configmap-rollout.log | PASS | Annotation cleared |
| AM-12 | Rollback | rollout undo + verify | logs/09-rollback.log | PASS | Image restored, marker cleared |
| AM-13 | Shutdown runtime | N/A (BLOCKED) | 10_SHUTDOWN_VALIDATION.md | BLOCKED | No isolated environment |
| AM-14 | Log scan | grep 14 patterns | logs/11-log-scan.log | PASS | 0 errors, 0 restarts |
| AM-15 | Configuration scan | kubectl get secrets + deployments | logs/12-config-scan.log | PASS | No hardcoded creds |
| AM-16 | Dependency validation | pip check + dry-run | logs/13-dependency-scan.log | PASS | No broken reqs |
| AM-17 | Secret scan | grep patterns | logs/14-secret-scan.log | PASS | 0 real secrets |
| AM-18 | Fresh clone | git clone + venv + verify | logs/15-fresh-clone.log | PASS | HEAD=Commit B, clean |
| AM-19 | Full WUI suite | pytest test_u13_complete_webui | junit/u13-wui-full.xml | FAIL | 24/28 passed, 4 failed — model_switch strict-mode selector (.chat-msg.assistant resolves to 2 elements after 2 messages) |
| AM-20 | Track A regression | pytest test_r3_identities | junit/track-a-regression.xml | FAIL | 4/10 passed, 6 failed — BFF single-user admin architecture (tests require multi-user roles "User" vs "Admin") |
| AM-21 | TLS cert verification | grep TLS cert warnings | junit/ | PASS | 0 warnings |
| AM-22 | User documentation | 17 scenarios | 17_USER_DOCUMENTATION_AUDIT.md | PASS | 17/17 documented |
| AM-23 | Backup/Restore documentation | Section completeness | 13_BACKUP_RESTORE_AUDIT.md | PASS | All sections present |
| AM-24 | Monitoring documentation | Honesty check | 14_MONITORING_AUDIT.md | PASS | Prometheus/Grafana: NOT IMPLEMENTED |
| AM-25 | Placeholder scan | grep patterns | placeholder-scan.txt | PASS | 0 matches in new evidence |
| AM-26 | Clean working tree | git status --porcelain | logs/19-final-git-state.log | PASS | Clean after commit |
| AM-27 | Local/Remote match | git rev-parse vs ls-remote | logs/19-final-git-state.log | PASS | Verified |

## Summary

- PASS: 22
- FAIL: 2 (AM-19: WUI 24/28 model_switch, AM-20: Track A 4/10 BFF single-user)
- BLOCKED: 1 (AM-13: shutdown — no isolated environment)
- NOT APPLICABLE: 0
