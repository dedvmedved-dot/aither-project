# Directory Catalog

> Complete description of all significant directories in the Aither Project repository.

---

## Active Workspace: `aither-v2/` (563 files)

### `aither-v2/docs/` (364 files)
Primary documentation directory.

| Subdirectory | Files | Purpose |
|-------------|-------|---------|
| `docs/mvp-roadmap/` | 254 | MVP roadmap documents: governance, stages 11-19, RC1 readiness, evidence |
| `docs/stage18b/` | 17 | Stage 18B — final rollout, acceptance, evidence |
| `docs/stage17/` | 15 | Stage 17 — observability and monitoring |
| `docs/stage18a/` | 14 | Stage 18A — registry and deployment |
| `docs/stage10/` | 14 | Stage 10 — repository audit standards |
| `docs/stage16/` | 10 | Stage 16 — acceptance testing |
| `docs/project-control/` | 10 | PROJECT_MASTER.md, CHAT_HANDOVER.md, governance |
| `docs/stage18/` | 4 | Stage 18 documentation |
| `docs/stage15/` | 4 | Stage 15 documentation |
| `docs/user-launch/` | 5 | Track A — User Launch documents |
| `docs/release/` | 4 | Release notes |
| `docs/stage14/` | 3 | Stage 14 documentation |
| `docs/stage13/` | 3 | Stage 13 documentation |
| `docs/stage11/` | 3 | Stage 11 documentation |

### `aither-v2/reports/` (70 files)
Stage reports and evidence.

| Subdirectory | Files | Purpose |
|-------------|-------|---------|
| `reports/beta/` | 16 | Beta acceptance test reports |
| `reports/stage-u1/` | 12 | Stage U1.0 reports |
| `reports/stage10/` | 11 | Stage 10 repository audit reports |
| `reports/ba02r/` | 11 | BA-02R acceptance reports |
| `reports/rc1/` | 8 | RC1 readiness reports |
| `reports/stage10b/` | 5 | Stage 10B RC2R evidence quarantine |
| `reports/rc2/` | 2 | RC2 production reports |

### `aither-v2/services/` (21 files)
Service code for the Aither platform.

| Subdirectory | Files | Service |
|-------------|-------|---------|
| `services/portal-frontend/` | 6 | Portal frontend (nginx, HTML, CSS, JS) |
| `services/identity/` | 5 | Identity service (auth, users) |
| `services/portal-backend/` | 4 | Portal backend (BFF proxy) |
| `services/ai-platform/` | 4 | AI Platform (model serving, API keys) |
| `services/portal/` | 1 | Portal (legacy) |
| `services/bff/` | 1 | BFF (legacy) |

### `aither-v2/scripts/` (16 files)
Automation and test scripts.

| File/Subdir | Purpose |
|-------------|---------|
| `scripts/mvp/` | MVP deploy scripts |
| Various `.sh` files | Stage-specific test scripts (15-17) |
| `scripts/scan-secrets.sh` | Secret scan |
| `scripts/restore.sh` | Restore script |

### `aither-v2/manifests/` (15 files)
K8s manifests for MVP roadmap components.

### `aither-v2/tools/` (10 files)
Utility tools.

| Subdirectory | Purpose |
|-------------|---------|
| `tools/benchmarks/` | Performance benchmarks |
| `tools/bff/` | BFF tools |
| `tools/portal/` | Portal tools |

### `aither-v2/deploy/` (5 files)
Deployment shell scripts.

### `aither-v2/evidence/` (4 files)
Evidence files: `evidence/rc2/` (2 files).

### `aither-v2/release/` (4 files)
Release artifacts: `release/mvp-rc1/` (4 .gitkeep, empty).

### Legacy Directories

| Directory | Files | Description |
|-----------|-------|-------------|
| `03-vllm-14b-deploy/` | 40 | Legacy vLLM 14B deployment (docs + manifests) |
| `02-containerd-nvidia-runtime/` | 6 | Legacy containerd/NVIDIA runtime docs |
| `01-k8s-gpu-operator/` | 3 | Legacy K8s GPU operator docs |

### Placeholder Directories
Each contains a single `.gitkeep` (empty):
- `04-tensor-parallelism/`
- `05-gateway-redis/`
- `06-portal-spa-bff-sse/`
- `07-oauth/`

---

## Root Level (outside aither-v2/, 292 files)

### `gateway/` (11 files)
Historical standalone gateway implementation: `admin.py`, `catalog.py`, `gateway.py`, `hybrid_rag.py`, `metrics.py`, `reaper.py`, `routing.py`, `security.py`, `security_egress.py`, `vault.py`, `wiki_graph.py`, `catalog.yaml`.

### `portal/` (35 files)
Historical standalone portal: TypeScript server, Dockerfile, nginx config, static assets, BFF, delegation keys.

### `manifests/` (22 files)
Historical K8s manifests: ChromaDB, embeddings, gateway deployments, HPA, network plans, observability stack.

### `docs/` (root) (28 files)
Historical documentation: API reference, architecture, security, integration, monitoring, RBAC, stage-4 features.

### `offline-deploy/` (35 files)
Complete offline deployment package: K8s manifests, scripts, configs, documentation (architecture, deployment, admin, user, security, troubleshooting, upgrade guides).

### `diagrams/` (15 files)
Architecture diagrams in DOT, SVG, JPG, PNG formats.

### `configs/` (5 files)
Historical configs: nginx failover, VPS1/VPS3 nginx, BFF wrapper.

### `references/` (10 files)
Reference documentation: BMC admin, K3s vs K8s, RedOS, YADRO lab, TR1/TR2 architecture docs.

### `wiki/` (10 files)
LLM Wiki knowledge base: concept docs, entity docs, index, schema.

### `fine-tuning/` (8 files)
Fine-tuning scripts: LoRA, QLoRA, PEFT conversion, K8s jobs.

### `Usage-Collector/` (5 files)
Usage collector documentation and protocol.

### `k8s/hpa/` (5 files)
HPA configs: adapter, gateway, prometheus, HPA definitions.

### `grafana/` (3 files)
Grafana dashboards: GPU overview, vLLM inference, nginx config.

### `.github/workflows/` (3 files)
CI/CD workflows.

### `aither-article/` (7 files)
Aither platform article with SVG diagrams.

### `aither-send/` and `aither-send (2)/` (12 files each)
Duplicates of aither-article content.

### `db/migrations/` (3 files)
Database migration SQL files.

### `hosts/` (3 files)
Hardware inventory.

### `archive/` (2 files)
Archived documents (memory, user profile).

### `delegation/` (1 file)
Public PEM key.

### Root files
Various historical files: `README.md`, `ROADMAP.md`, `FEATURES.md`, `status.md`, `tr-status.md`, `plan.md`, `bortovoy-zhurnal.md`, `brief.md`, `article.md`, `nginx-failover.conf`, `nvidia_drv.txt`, `.gitignore`.
