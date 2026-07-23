# Stage 10 — Documentation Consistency Audit

## Task 8 — Cross-Document Contradiction Analysis

### Documents Reviewed
1. `README.md` (repo root)
2. `ROADMAP.md` (repo root)
3. `status.md` (repo root)
4. `FEATURES.md` (repo root)
5. `aither-v2/docs/project-control/PROJECT_MASTER.md`
6. `aither-v2/docs/project-control/CHAT_HANDOVER.md`
7. `aither-v2/docs/releases/v1.0.md`
8. `aither-v2/reports/rc2/production-readiness.md`

---

## Contradiction 1: Architecture Mismatch

| Document | Architecture Described |
|----------|----------------------|
| `README.md` | VPS2 (130.17.1.90) → Cisco VPN → 40.51 YADRO → Python API Gateway → vLLM 14B |
| `status.md` | Same VPS2-based architecture, references `10.129.13.78:30900` (Python Gateway) |
| `FEATURES.md` | Consumption Layer → Security Layer → Control Plane → K8s (different abstraction) |
| `releases/v1.0.md` | Current aither-v2 K8s architecture (n7/n8, nginx-gateway-32b, Portal → AI Platform → Gateway → vLLM 32B) |

**Issue:** `README.md` and `status.md` describe a completely different deployment (VPS2-based, Python Gateway, 40.51 YADRO, RTX 6000 GPUs). The current aither-v2 K8s cluster (n7 bootsman, n8 control-plane, A100 GPU, nginx gateway) is **not reflected** in the root README.

**Severity:** MAJOR — root documentation contradicts actual deployed architecture.

---

## Contradiction 2: Release Status

| Document | Claims |
|----------|--------|
| `releases/v1.0.md` (committed) | "Aither AI Platform v1.0 is the first **production-ready release**" — Version: 1.0.0, Codename: **Production v1.0** |
| `PROJECT_MASTER.md` | Stage 09: PASSED WITH FINDINGS / CONNECTOR VERIFIED. PROD-READY-01: OPEN |
| `CHAT_HANDOVER.md` | "Production-readiness remains open." "Stage 09: NOT APPROVED." |
| `reports/rc2/production-readiness.md` | "ACCEPTABLE for v1.0" with GO recommendation |

**Issue:** The release notes declare "Production v1.0" and "production-ready release," but:
- The project master explicitly states PROD-READY-01 is OPEN
- CHAT_HANDOVER says "not production-ready"
- Stage 09 has findings (Gateway CrashLoopBackOff history, MissingClusterDNS)
- Infrastructure blockers (K8s API timeouts, no TLS, no monitoring) are unresolved

**Severity:** MAJOR — v1.0.md contradicts the project's own governance documents.

---

## Contradiction 3: RC2 Production Readiness vs Governance

| Document | Conclusion |
|----------|-----------|
| `reports/rc2/production-readiness.md` | "Verdict: ✅ ACCEPTABLE for v1.0" — implies production GO |
| `PROJECT_MASTER.md` | PROD-READY-01: OPEN — no production readiness approved |
| `CHAT_HANDOVER.md` | "Production-readiness remains open" |

**Issue:** The RC2 production readiness report recommends GO/ACCEPTABLE, but the governance layer has never approved it.

**Severity:** MAJOR — report conclusion contradicts project governance.

---

## Contradiction 4: RC2 Report Claims vs Evidence

| Claim in RC2 Report | Actual Status |
|--------------------|--------------|
| "20 requests partial confirmation of 1000" | 20 ≠ 1000. Acknowledged as FALSE in `rc2r-corrections.md` |
| "Stability: Hermes 20x at 0.47s avg, 100% success" | 24h Long Run: NOT TESTED. 1000 requests: NOT TESTED |
| "GO" recommendation | Production blockers exist (K8s API timeout, no TLS, SQLite lock, no monitoring) |

**Issue:** RC2 reports contain claims that overstate actual test coverage. The local `rc2r-corrections.md` document (not in Git) explicitly identifies these contradictions.

**Severity:** MAJOR — report data integrity issue.

---

## Additional Minor Issues

| Issue | Details |
|-------|---------|
| `ROADMAP.md` last updated 09.07.2026 — predates RC1/RC2 stages | No mention of Stages 17-19, RC1, RC2, or RC2R |
| `FEATURES.md` references features not in current MVP (billing, organizations, quotas) | Describes a different, more feature-rich system |
| `status.md` references SSH passwords (`sshpass -p 'root'`) | Security anti-pattern documented in root |
| No single architecture diagram committed | Each document describes a slightly different topology |

---

## Summary

| # | Contradiction | Severity | Documents Involved |
|---|--------------|----------|-------------------|
| 1 | Architecture mismatch (VPS2 vs K8s cluster) | MAJOR | README, status.md vs releases/v1.0.md |
| 2 | "Production v1.0" vs "PROD-READY-01: OPEN" | MAJOR | releases/v1.0.md vs PROJECT_MASTER.md |
| 3 | RC2 recommends GO but governance says OPEN | MAJOR | rc2/production-readiness.md vs PROJECT_MASTER.md |
| 4 | RC2 report overstates test coverage | MAJOR | rc2 reports vs actual test evidence |

**Overall:** The documentation has **4 major contradictions** between root-level docs (README, status.md) and the actual aither-v2 K8s deployment. Release notes and production readiness reports claim a status that the project governance has explicitly not approved.
