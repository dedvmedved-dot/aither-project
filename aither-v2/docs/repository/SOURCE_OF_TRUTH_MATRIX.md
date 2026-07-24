# Source of Truth Matrix

> Mapping of knowledge domains to their authoritative source documents and locations.

---

| Domain | Source of Truth | Location | Verification |
|--------|-----------------|----------|--------------|
| **Project governance** | PROJECT_MASTER.md | `docs/project-control/PROJECT_MASTER.md` | ✅ Synced with CHAT_HANDOVER.md |
| **Stage audit trail** | CHAT_HANDOVER.md | `docs/project-control/CHAT_HANDOVER.md` | ✅ Append-only historical record |
| **Current MVP status** | current-mvp-status.md | `docs/mvp-roadmap/00-governance/current-mvp-status.md` | ✅ Synced with PROJECT_MASTER |
| **Release classification** | v1.0.md | `docs/release/v1.0.md` | ✅ NO-GO status documented |
| **Stage 10-10G audit** | Various reports | `reports/stage10*/` | ✅ 7 sub-stages documented |
| **Stage U1.0 results** | 11_FINAL_STATUS.md | `reports/stage-u1/u1-0/11_FINAL_STATUS.md` | ✅ PASSED WITH FINDINGS |
| **User access architecture** | USER_ACCESS_ARCHITECTURE.md | `docs/user-launch/USER_ACCESS_ARCHITECTURE.md` | ✅ Stage U1.0 deliverable |
| **Endpoint inventory** | ENDPOINT_MATRIX.md | `docs/user-launch/ENDPOINT_MATRIX.md` | ✅ Current + target state |
| **Security baseline** | ACCESS_SECURITY_BASELINE.md | `docs/user-launch/ACCESS_SECURITY_BASELINE.md` | ✅ 11 sections |
| **Architecture decisions** | ADR_U1_ACCESS.md | `docs/user-launch/ADR_U1_ACCESS.md` | ✅ 7 ADRs |
| **Stage U1 roadmap** | STAGE_U1_ROADMAP.md | `docs/user-launch/STAGE_U1_ROADMAP.md` | ✅ U0.A-U1.7 |
| **CI/CD state** | .github/workflows/ | `.github/workflows/` | ✅ 3 workflows |
| **Service code** | services/ | `aither-v2/services/` | ✅ 7 service components |
| **K8s manifests (MVP)** | manifests/mvp-roadmap/ | `aither-v2/manifests/mvp-roadmap/` | ✅ 15 manifest files |
| **K8s manifests (historical)** | manifests/ (root) | `manifests/` | Historical (superseded) |
| **Gateway code (historical)** | gateway/ | `gateway/` | Historical |
| **Portal code (historical)** | portal/ | `portal/` | Historical |
| **Beta acceptance** | BA-02R reports | `reports/ba02r/` | ✅ 11 report files |
| **RC1 readiness** | RC1 report | `reports/rc1/` | ✅ READY WITH KNOWN LIMITATIONS |
| **RC2 production** | RC2 reports | `reports/rc2/` | ✅ Production claims |
| **Offline deployment** | offline-deploy/ | `offline-deploy/` | Standalone package |
| **Fine-tuning** | fine-tuning/ | `fine-tuning/` | Standalone scripts |
| **LLM Wiki KB** | wiki/ | `wiki/` | Knowledge base |
| **Reference docs** | references/ | `references/` | Reference material |
| **Hardware inventory** | hosts/ | `hosts/` | Server specs |
| **Grafana dashboards** | grafana/ | `grafana/` | Monitoring config |
| **DB migrations** | db/migrations/ | `db/migrations/` | SQL schema changes |
| **Usage collector** | Usage-Collector/ | `Usage-Collector/` | Usage tracking |

## Source of Truth Rules

1. **Git committed state** is always authoritative over working tree
2. **PROJECT_MASTER.md** supersedes individual stage reports for global status
3. **CHAT_HANDOVER.md** is the definitive audit trail — never modify historical entries
4. **Stage reports** are frozen snapshots — do NOT update after stage completion
5. **Service code** in `services/` is authoritative over historical `gateway/` and `portal/`
6. **aither-v2/manifests/** is authoritative over root-level `manifests/`
7. **Real runtime state** (K8s cluster) is the operational SOT — not accessible in this stage
