# Stale and Orphan Evidence — Stage U0.A

## Definition

- **Stale**: Files that reference superseded states, frozen snapshots from completed stages
- **Orphan**: Files whose purpose or context is no longer current
- **Historical artifacts**: Files on the `main` branch that don't exist on `aither-v2`

## Stale Files (in aither-v2/)

### Stage 10 reports (snapshots frozen at stage completion)

| File | Reason | Severity |
|------|--------|----------|
| `reports/stage10/` (11 files) | Stage 10 was FAILED, superseded by 10A-10G | 🟢 Low — historical record |
| Various `reports/stage10b/` (5 files) | RC2R evidence quarantine — frozen | 🟢 Low |
| Various `reports/ba02r/` (11 files) | Beta acceptance — complete | 🟢 Low |
| Various `reports/rc1/` (8 files) | RC1 readiness — complete | 🟢 Low |

### Legacy placeholder directories

| Directory | Content | Status |
|-----------|---------|--------|
| `aither-v2/01-k8s-gpu-operator/` | 3 files (INSTRUCTIONS.md, README.md, DEPLOYMENT.md) | 🟢 Low — legacy stage docs |
| `aither-v2/02-containerd-nvidia-runtime/` | 6 files (docs + .gitkeep) | 🟢 Low |
| `aither-v2/03-vllm-14b-deploy/` | 40 files (docs + manifests) | 🟡 Medium — legacy deployment manifests |
| `aither-v2/04-tensor-parallelism/` | 1 file (.gitkeep) | 🟢 Low — placeholder |
| `aither-v2/05-gateway-redis/` | 1 file (.gitkeep) | 🟢 Low — placeholder |
| `aither-v2/06-portal-spa-bff-sse/` | 1 file (.gitkeep) | 🟢 Low — placeholder |
| `aither-v2/07-oauth/` | 1 file (.gitkeep) | 🟢 Low — placeholder |

## Orphaned Root-Level Files (not in aither-v2/)

These files exist at the repository root and are NOT referenced by any active aither-v2/ process:

### Duplicate content clusters

| Cluster | Files | Count |
|---------|-------|-------|
| aither-article | `aither-article/article.md`, `aither-send/article.md`, `aither-send (2)/article.md` | 3 copies |
| aither-send SVGs | `aither-send/architecture.svg`, `aither-send (2)/architecture.svg` (and deployment, gpu-stack, request-flow, tensor-parallelism) | 12 copies total |
| article variants | `article.md`, `aither-article/article.md` | Multiple variants |

### Stale infrastructure references

| File | Purpose | Status |
|------|---------|--------|
| `gateway/` (11 Python files) | Standalone gateway implementation | 🟡 Medium — superseded by aither-v2 gateway |
| `portal/` (30+ files) | Standalone portal implementation | 🟡 Medium — superseded by aither-v2 services/ |
| `manifests/` (22 files) | Root-level K8s manifests | 🟡 Medium — superseded by aither-v2 manifests/ |
| `configs/` | VPS1/VPS3 configs | 🟡 Medium — historical deployment |
| `offline-deploy/` (35 files) | Offline deployment package | 🟡 Medium — historical |
| `fine-tuning/` (8 files) | Fine-tuning scripts | 🟡 Medium — not in current aither-v2 workflow |
| `k8s/hpa/` (5 files) | HPA configs | 🟡 Medium |
| `grafana/` (3 files) | Grafana dashboards | 🟢 Low |
| `docs/` (root) (30+ files) | Root-level documentation | 🟡 Medium — many may be stale |
| `references/` (10 files) | Reference docs | 🟢 Low |

## Observations

1. **aither-v2/ is the active workspace** with all current services, manifests, docs, and evidence
2. **Root-level directories** represent an earlier architectural phase before aither-v2/ was established
3. **Main branch content** (~73 commits) has significant overlap with root-level content
4. **No true orphan files** — all tracked files serve some historical or reference purpose
5. **Recommended action**: Migrate or archive root-level files during cleanup
