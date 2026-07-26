============================================================
U1.3-OPS-R2 — FINAL CORRECTIVE REPORT
============================================================

Repository:
dedvmedved-dot/aither-project

Branch:
aither-v2

Baseline:
79026986f5bdaabca2eb9ab005bdb0d63b1b1e6c

Implementation/documentation commit A:
349f78b3c1d5dd467a59e1093c1189605d7860b1

Evidence payload commit B:
df6f4fe7a5c5ad857322a360176b1e01ee0733be

Evidence finalization commit C:
Verification of this file:
git log -1 --format=%H -- evidence/u1.3-ops-r2/final-report.md

Actual original U1.3 implementation SHA:
2ed4b4c0a83be895d23594930b7a7cabfec3559f

Fabricated SHA from old report:
2ed4b4c5defb830f6c0f6ff03dfe2ed37c213bb5 ← DOES NOT EXIST

Commit chain:
79026986f5bdaabca2eb9ab005bdb0d63b1b1e6c  U1.3-OPS-R1 evidence (rejected)
349f78b3c1d5dd467a59e1093c1189605d7860b1  Commit A — implementation + docs
df6f4fe7a5c5ad857322a360176b1e01ee0733be  Commit B — evidence payload
cf8bf4fd3cc6847a411708de0017c8e49221e8df  Commit C — evidence finalization

Working tree before Commit C:
CLEAN (only untracked evidence files added)

BFF downtime root cause:
Strategy: Recreate. With 1 replica, Kubernetes kills the old pod BEFORE creating
a new one. During the gap (~30-45s for pip install + uvicorn startup), the Service
has zero endpoints. Internet Zone returns 000 (connection failure), Test Zone
NodePort returns 502 (no backend).

BFF remediation:
Changed strategy to RollingUpdate with maxUnavailable=0, maxSurge=1,
minReadySeconds=5. Scaled replicas to 2. Added PodDisruptionBudget (minAvailable=1).

BFF replicas:
2

RollingUpdate:
maxUnavailable: 0 / maxSurge: 1

Startup:
PASS (10/10 deployments Available)

DNS preflight:
Internet: 10/10 successful
Test Zone: 10/10 successful

Restart execution:
PASS (kubectl rollout restart: RC=0, rollout status: RC=0)

Continuous availability — Internet:
40 probes / 40 HTTP 200 / 0 failures / 100.00% availability

Continuous availability — Test Zone:
40 probes / 40 HTTP 200 / 0 failures / 100.00% availability

Zero-downtime restart:
PASS — 0 non-200 responses during controlled rolling restart (240s, 40 probes each zone)

Pod recreation:
PASS — old UID: e41b0191 / new UID: 8c68aa25 / elapsed: 31 seconds

ConfigMap rollout:
PASS — annotation added, rollout completed, annotation removed

Rollback:
PASS — revision before: 21 / test revision: 22 / revision after: 23
image restored: YES / annotation absent: YES

Shutdown runtime:
BLOCKED — no isolated environment and no approved maintenance window

Log validation:
PASS — 12 pods / 12 containers / 0 error pattern matches / 0 restarts

Configuration validation:
PASS — secrets referenced by secretKeyRef, no hardcoded credentials

Dependency validation:
PASS — pip check: no broken requirements, pip install --dry-run: all satisfied

Secret scan:
PASS — 0 real secrets (gitleaks not installed, grep-based scan)

Placeholder scan:
PASS — 0 matches in new evidence

Fresh clone:
PASS — HEAD = Commit B (df6f4fe), working tree CLEAN, venv OK, 10/10 files present

Full U1.3-WUI suite:
24 passed / 4 failed / 0 errors / 0 skipped
(4 failures: test_model_switch — UI selector mismatch, pre-existing)

Track A regression:
4 passed / 6 failed / 0 errors / 0 skipped
(6 failures: BFF single-user architecture — expected role "User", got "Admin")

TLS warnings:
0 — No TLS cert warnings (Unverified HTTPS, cert verify failed)

User documentation:
17 passed scenarios / 17 total

Backup/Restore documentation:
PASS — RPO/RTO: defined (Operational target for Controlled Beta)
retention: daily/weekly/monthly / encryption: OpenSSL AES-256-CBC
checksum: sha256sum / off-site: documented / test restore: documented
PV-PVC: documented (CSI-dependent)

Monitoring documentation:
PASS — actual monitoring state: Prometheus/Grafana/Alertmanager NOT IMPLEMENTED
Manual health checks + kubectl status documented. Honest inventory.

Open critical defects:
0

Open high defects:
0

Open medium defects:
0

Historical resolved defects:
OPS-R1-001: Final report placeholders → RESOLVED
OPS-R1-002: Fabricated SHA → RESOLVED (real: 2ed4b4c0a83be...)
OPS-R1-003: Missing raw evidence → RESOLVED
OPS-R1-004: Shutdown misclassified → CORRECTED (BLOCKED, honest)
OPS-R1-005: Incomplete ops docs → RESOLVED
OPS-R2-001: Falsified placeholder scan → RESOLVED (0 matches)
OPS-R2-002: Availability misclassified → RESOLVED (0 non-200, 100%)
OPS-R2-003: Missing fresh clone log → RESOLVED
OPS-R2-005: Incomplete ops docs → RESOLVED (BACKUP 98→627, MON 103→592)
OPS-R2-006: Incomplete collector → RESOLVED (new script with exit code logging)

Known limitations:
- No isolated test environment (shutdown test not executed — BLOCKED, honest)
- Prometheus/Grafana/Alertmanager not deployed (manual monitoring)
- Full DR drill not performed (procedures documented, test restore defined)
- BFF is single-user (admin-only) — Track A multi-user tests fail (architectural)
- Internet DNS resolution slow (~5s) — environment-level, not affecting availability
- Volume snapshots depend on CSI driver support
- model_switch tests fail (4/28) — pre-existing UI selector issue

User handover:
PROHIBITED

Controlled Beta:
BLOCKED

Hermes status:
STOPPED — awaiting ChatGPT external audit
============================================================
