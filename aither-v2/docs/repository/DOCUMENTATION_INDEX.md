# Documentation Index

> Classification of all documentation files by category.
> Total documented: ~450+ files across both aither-v2/ and root directories.

---

## 1. Project Governance (docs/project-control/)

| File | Description |
|------|-------------|
| `PROJECT_MASTER.md` | Master governance document — stage status, roles, risks |
| `CHAT_HANDOVER.md` | Audit trail — stage-by-stage decisions and findings |
| other files (8) | Governance support documents |

**Total: 10 files**

## 2. MVP Roadmap & Stage Docs (docs/mvp-roadmap/)

254 files covering stages 11-19, RC1 readiness, governance subdirectories.

| Stage | Files | Focus |
|-------|-------|-------|
| Stage 11 | 3 | Documentation |
| Stage 13 | 3 | Documentation |
| Stage 14 | 3 | Documentation |
| Stage 15 | 4 | Acceptance |
| Stage 16 | 10 | Acceptance testing |
| Stage 17 | 15 | Observability |
| Stage 18 | 4 | Documentation |
| Stage 18A | 14 | Registry, deployment |
| Stage 18B | 17 | Final rollout, recovery |
| Stage 10 | 14 | Repository audit standards |
| Others | ~167 | Governance, evidence, reports |

## 3. User Launch (Track A) — docs/user-launch/

| File | Description |
|------|-------------|
| `USER_ACCESS_ARCHITECTURE.md` | External/internal access architecture |
| `ENDPOINT_MATRIX.md` | Endpoint inventory with status |
| `ACCESS_SECURITY_BASELINE.md` | Security requirements baseline |
| `STAGE_U1_ROADMAP.md` | Stage U1 roadmap (U1.0 → U1.7) |
| `ADR_U1_ACCESS.md` | Architecture Decision Records |

**Total: 5 files**

## 4. Release Documentation (docs/release/)

| File | Description |
|------|-------------|
| `v1.0.md` | Production release notes |
| Other files | Release metadata |

**Total: 4 files**

## 5. Stage Reports (reports/)

| Report Set | Files | Description |
|------------|-------|-------------|
| Stage 10 audit | 11 | Repository audit findings |
| Stage 10B (RC2R) | 5 | Evidence quarantine |
| BA-02R | 11 | Beta acceptance reports |
| RC1 | 8 | Release readiness |
| RC2 | 2 | Production reports |
| Stage U1.0 | 12 | User Launch evidence |

**Total: 70 files**

## 6. Root-Level Documentation

| Category | Files | Description |
|----------|-------|-------------|
| `docs/` (root) | 28 | API reference, security, integration, runbooks |
| `docs/stage10/` | 10 | Publishing instructions, standards, checklists |
| `references/` | 10 | BMC, K3s/K8s, TR architecture, YADRO lab |
| `wiki/` | 10 | LLM Wiki knowledge base |
| `offline-deploy/docs/` | 8 | Offline deployment guides |

**Total: ~56 files**

## 7. Architecture Documentation

| Location | Files | Description |
|----------|-------|-------------|
| `diagrams/` | 15 | Architecture diagrams (DOT, SVG, JPG, PNG) |
| `aither-article/` | 7 | Article with SVG diagrams |
| `docs/diagrams/` | ~10 | Stage-specific diagrams |
| `docs/user-launch/USER_ACCESS_ARCHITECTURE.md` | 1 | Access architecture |

**Total: ~33 files**

## 8. Configuration Documentation

| Location | Files | Description |
|----------|-------|-------------|
| `configs/` | 5 | nginx, BFF configs |
| `offline-deploy/configs/` | 3 | Template configs |
| `gateway/catalog.yaml` | 1 | Model catalog |

**Total: ~9 files**

## 9. Infrastructure Documentation

| Location | Files | Description |
|----------|-------|-------------|
| `hosts/` | 3 | Hardware inventory |
| `manifests/` (root) | 22 | K8s deployment plans, network plans |
| `k8s/hpa/` | 5 | HPA documentation |

**Total: ~30 files**

## 10. Code Documentation

| Location | Files | Description |
|----------|-------|-------------|
| Inline in services/ | 21 | Service code with docstrings |
| `gateway/` | 12 | Python gateway with documentation |
| `portal/` | 35 | TypeScript/JS portal code |
| `fine-tuning/` | 8 | Training scripts |

**Total: ~76 files**

## Summary by Category

| Category | Approx. Files |
|----------|---------------|
| Project Governance | 10 |
| MVP Stage Documentation | 254 |
| User Launch (Track A) | 5 |
| Release Documentation | 4 |
| Stage Reports | 70 |
| Root-Level Documentation | 56 |
| Architecture (diagrams) | 33 |
| Configuration | 9 |
| Infrastructure | 30 |
| Code Documentation | 76 |
| **Total documented** | **~547** |
