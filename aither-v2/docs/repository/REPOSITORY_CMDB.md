# Repository CMDB

> Configuration Management Database — catalog of Configuration Items (CIs) in the Aither Project repository.

---

## CI Catalog

| CI ID | Type | Name | Location | Version | Status | Dependencies |
|-------|------|------|----------|---------|--------|--------------|
| CI-001 | Document | PROJECT_MASTER.md | `docs/project-control/` | v1.0 | ACTIVE | All stage docs |
| CI-002 | Document | CHAT_HANDOVER.md | `docs/project-control/` | v1.0 | ACTIVE | PROJECT_MASTER |
| CI-003 | Document | current-mvp-status.md | `docs/mvp-roadmap/00-governance/` | v1.0 | ACTIVE | PROJECT_MASTER |
| CI-004 | Document | USER_ACCESS_ARCHITECTURE.md | `docs/user-launch/` | v1.0 | ACTIVE | — |
| CI-005 | Document | ENDPOINT_MATRIX.md | `docs/user-launch/` | v1.0 | ACTIVE | CI-004 |
| CI-006 | Document | ACCESS_SECURITY_BASELINE.md | `docs/user-launch/` | v1.0 | ACTIVE | CI-004 |
| CI-007 | Document | STAGE_U1_ROADMAP.md | `docs/user-launch/` | v1.0 | ACTIVE | CI-004, CI-005 |
| CI-008 | Document | ADR_U1_ACCESS.md | `docs/user-launch/` | v1.0 | ACTIVE | CI-004 |
| CI-009 | Service | Identity Service | `services/identity/` | Latest | ACTIVE | PostgreSQL |
| CI-010 | Service | Portal Backend (BFF) | `services/portal-backend/` | Latest | ACTIVE | Identity, AI Platform |
| CI-011 | Service | Portal Frontend | `services/portal-frontend/` | Latest | ACTIVE | BFF |
| CI-012 | Service | AI Platform | `services/ai-platform/` | Latest | ACTIVE | Identity, Gateway |
| CI-013 | Manifest | MVP Roadmap Manifests | `manifests/mvp-roadmap/` | v1.0 | ACTIVE | K8s cluster |
| CI-014 | Report | Stage 10 Audit Reports | `reports/stage10/` | v1.0 | FROZEN | CI-001 |
| CI-015 | Report | Stage 10B Reports | `reports/stage10b/` | v1.0 | FROZEN | CI-001 |
| CI-016 | Report | BA-02R Reports | `reports/ba02r/` | v1.0 | FROZEN | CI-009..CI-012 |
| CI-017 | Report | RC1 Reports | `reports/rc1/` | v1.0 | FROZEN | CI-016 |
| CI-018 | Report | RC2 Reports | `reports/rc2/` | v1.0 | FROZEN | CI-017 |
| CI-019 | Report | Stage U1.0 Reports | `reports/stage-u1/u1-0/` | v1.0 | ACTIVE | CI-004..CI-008 |
| CI-020 | Script | Deploy Scripts | `deploy/` | v1.0 | ACTIVE | CI-009..CI-013 |
| CI-021 | Script | Test Scripts | `scripts/` | v1.0 | ACTIVE | CI-009..CI-012 |
| CI-022 | Tool | Benchmark Tools | `tools/benchmarks/` | v1.0 | ACTIVE | CI-012 |
| CI-023 | Config | nginx Config | `services/portal-frontend/nginx/nginx.conf` | v1.0 | ACTIVE | CI-011 |
| CI-024 | Config | nginx (root) | `services/portal-frontend/nginx.conf` | v1.0 | ACTIVE | CI-011 |
| CI-025 | CI/CD | GitHub Workflows | `.github/workflows/` | v1.0 | ACTIVE | GitHub |
| CI-026 | Legacy | Gateway (historical) | `gateway/` | v1.0 | ARCHIVED | — |
| CI-027 | Legacy | Portal (historical) | `portal/` | v1.0 | ARCHIVED | — |
| CI-028 | Legacy | Manifests (historical) | `manifests/` (root) | v1.0 | ARCHIVED | — |
| CI-029 | Package | Offline Deploy | `offline-deploy/` | v1.2.0 | ARCHIVED | — |
| CI-030 | Knowledge | LLM Wiki | `wiki/` | v1.0 | ACTIVE | — |
| CI-031 | Documentation | References | `references/` | v1.0 | ACTIVE | — |
| CI-032 | Documentation | Hardware Inventory | `hosts/` | v1.0 | ACTIVE | — |
| CI-033 | Dashboard | Grafana Dashboards | `grafana/dashboards/` | v1.0 | ACTIVE | Prometheus |
| CI-034 | Config | HPA Configs | `k8s/hpa/` | v1.0 | ARCHIVED | K8s cluster |
| CI-035 | Migration | DB Migrations | `db/migrations/` | v1.0 | ACTIVE | PostgreSQL |
| CI-036 | Script | Fine-tuning Scripts | `fine-tuning/` | v1.0 | ARCHIVED | GPU cluster |
| CI-037 | Article | Aither Article | `aither-article/` | v1.0 | ARCHIVED | — |
| CI-038 | Article | Aither Send (dup) | `aither-send/` | v1.0 | DUPLICATE | — |
| CI-039 | Article | Aither Send 2 (dup) | `aither-send (2)/` | v1.0 | DUPLICATE | — |
| CI-040 | Evidence | RC2 Evidence | `evidence/rc2/` | v1.0 | FROZEN | CI-018 |

## CI Status Legend

| Status | Meaning |
|--------|---------|
| ACTIVE | Currently used in the active workflow |
| FROZEN | Completed stage — historical snapshot |
| ARCHIVED | Superseded or historical — not in active use |
| DUPLICATE | Exact copy of another CI |

## CI Count by Type

| CI Type | Count |
|---------|-------|
| Document | 8 |
| Service | 4 |
| Manifest | 1 |
| Report | 6 |
| Script | 2 |
| Tool | 1 |
| Config | 2 |
| CI/CD | 1 |
| Legacy | 3 |
| Package | 1 |
| Knowledge | 1 |
| Dashboard | 1 |
| Migration | 1 |
| Article | 3 |
| Evidence | 1 |
| **Total** | **~40 CIs** |
