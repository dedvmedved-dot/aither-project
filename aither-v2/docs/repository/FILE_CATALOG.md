# File Catalog

> Complete catalog of all 855 tracked files in the Aither Project repository, grouped by directory.
> Generated from `git ls-files` at HEAD `11b0d6482ae667da4ed9d98edbe606272838b5c6`.

---

## A. `aither-v2/` — Active Workspace (563 files)

### `aither-v2/01-k8s-gpu-operator/` (3 files)
| File | Description |
|------|-------------|
| `DEPLOYMENT.md` | GPU operator deployment guide (legacy) |
| `INSTRUCTIONS.md` | GPU operator instructions (legacy) |
| `README.md` | GPU operator README (legacy) |

### `aither-v2/02-containerd-nvidia-runtime/` (6 files)
| File | Description |
|------|-------------|
| `docs/DEPLOYMENT.md` | containerd deployment guide |
| `docs/INSTRUCTIONS.md` | containerd instructions |
| `docs/README.md` | containerd docs README |
| `.gitkeep` | Placeholder |
| `config.toml` | containerd configuration |
| `hostconfig.json` | Host config for NVIDIA runtime |

### `aither-v2/03-vllm-14b-deploy/` (40 files)
| File | Description |
|------|-------------|
| `manifests/` | K8s manifests for vLLM 14B deployment |
| `docs/` | Deployment documentation |
| `docs/ARCHITECTURE.md` | Architecture overview |
| `docs/DEPLOYMENT.md` | Deployment instructions |
| `docs/INSTRUCTIONS.md` | Step-by-step instructions |
| `docs/README.md` | Directory README |
| `docs/summary.md` | Stage summary |
| (plus 33 others) | Various documentation and manifest files |

### `aither-v2/deploy/` (5 files)
| File | Description |
|------|-------------|
| `deploy-identity.sh` | Identity service deployment script |
| `deploy-platform.sh` | AI platform deployment script |
| `deploy-portal-backend.sh` | Portal backend deployment script |
| `deploy-portal-frontend.sh` | Portal frontend deployment script |
| `deploy.sh` | Master deployment script |

### `aither-v2/docs/` (364 files) — See DOCUMENTATION_INDEX.md for detailed breakdown
| Subdirectory | Count | Description |
|-------------|-------|-------------|
| `docs/mvp-roadmap/` | 254 | MVP roadmap: governance, stages, evidence (stages 11-19) |
| `docs/stage18b/` | 17 | Stage 18B: final rollout evidence |
| `docs/stage17/` | 15 | Stage 17: observability |
| `docs/stage18a/` | 14 | Stage 18A: registry transfer |
| `docs/stage10/` | 14 | Stage 10: repository audit standards |
| `docs/stage16/` | 10 | Stage 16: acceptance testing |
| `docs/project-control/` | 10 | PROJECT_MASTER, CHAT_HANDOVER, governance |
| `docs/user-launch/` | 5 | User Launch (Track A): architecture, roadmap, ADRs |
| `docs/stage18/` | 4 | Stage 18 docs |
| `docs/stage15/` | 4 | Stage 15 docs |
| `docs/release/` | 4 | Release notes (v1.0.md, etc.) |
| `docs/stage14/` | 3 | Stage 14 docs |
| `docs/stage13/` | 3 | Stage 13 docs |
| `docs/stage11/` | 3 | Stage 11 docs |

### `aither-v2/evidence/` (4 files)
| File | Description |
|------|-------------|
| `evidence/rc2/k8s-api-timeout.txt` | K8s API timeout evidence report |
| `evidence/rc2/vllm-pods-wide.txt` | vLLM pod evidence |
| `evidence/rc2/vllm-services.txt` | vLLM service evidence |
| `evidence/rc2/vllm-deployments-yaml.txt` | vLLM deployment YAML |

### `aither-v2/.gitkeep` (1 file)
Empty placeholder for the working directory.

### `aither-v2/manifests/` (15 files)
| File | Description |
|------|-------------|
| `manifests/mvp-roadmap/` (15 files) | K8s manifests for all MVP services |

### `aither-v2/playwright/` (E2E tests, not tracked in git)

### `aither-v2/release/` (4 files)
| File | Description |
|------|-------------|
| `release/mvp-rc1/` (4 .gitkeep) | Empty release artifact placeholders |

### `aither-v2/reports/` (70 files)
| Subdirectory | Count | Description |
|-------------|-------|-------------|
| `reports/beta/` | 16 | Beta acceptance reports |
| `reports/stage-u1/u1-0/` | 12 | Stage U1.0 evidence |
| `reports/stage10/` | 11 | Stage 10 audit reports |
| `reports/ba02r/` | 11 | BA-02R acceptance |
| `reports/rc1/` | 8 | RC1 readiness |
| `reports/stage10b/` | 5 | Stage 10B evidence quarantine |
| `reports/rc2/` | 2 | RC2 production reports |

### `aither-v2/scripts/` (16 files)
| File | Description |
|------|-------------|
| `scripts/mvp/` | MVP deployment scripts |
| Various `.sh` | Stage 15-17 test scripts, secret scan, restore |
| `scripts/test-stage17-observability.sh` | Stage 17 observability test |
| `scripts/test-stage16-acceptance.sh` | Stage 16 acceptance test |
| `scripts/test-gateway-32b-e2e.sh` | Gateway 32B E2E test |
| `scripts/check-gateway-32b.sh` | Gateway 32B health check |
| `scripts/scan-secrets.sh` | Secret scanning script |
| `scripts/stage18a-*.sh` | Stage 18A scripts (build, push, deploy, verify, transfer) |
| `scripts/restore.sh` | Restore script |

### `aither-v2/services/` (21 files)
| File | Description |
|------|-------------|
| `services/ai-platform/app/main.py` | AI Platform — FastAPI app |
| `services/ai-platform/app/requirements.txt` | Python dependencies |
| `services/ai-platform/Dockerfile` | Container image |
| `services/ai-platform/.dockerignore` | Docker ignore rules |
| `services/portal-frontend/nginx/nginx.conf` | nginx configuration |
| `services/portal-frontend/static/index.html` | Portal frontend HTML |
| `services/portal-frontend/static/styles.css` | Portal CSS |
| `services/portal-frontend/static/app.js` | Portal JavaScript app |
| `services/portal-frontend/Dockerfile` | Container image |
| `services/portal-frontend/nginx.conf` | nginx fallback config |
| `services/identity/app/main.py` | Identity service |
| `services/identity/app/requirements.txt` | Python dependencies |
| `services/identity/app/Dockerfile` | Container image |
| `services/identity/app/.dockerignore` | Docker ignore rules |
| `services/identity/app/wait-for-it.sh` | Startup wait script |
| `services/portal-backend/app/main.py` | Portal Backend (BFF) |
| `services/portal-backend/app/requirements.txt` | Python dependencies |
| `services/portal-backend/Dockerfile` | Container image |
| `services/portal-backend/.dockerignore` | Docker ignore rules |
| `services/portal/app.js` | Portal (legacy) |
| `services/bff/app.js` | BFF (legacy) |

### `aither-v2/tools/` (10 files)
| File | Description |
|------|-------------|
| `tools/benchmarks/` | Benchmark tools |
| `tools/bff/` | BFF utility tools |
| `tools/portal/` | Portal utility tools |

### Placeholder directories (4 files)
| File | Description |
|------|-------------|
| `04-tensor-parallelism/.gitkeep` | Empty placeholder |
| `05-gateway-redis/.gitkeep` | Empty placeholder |
| `06-portal-spa-bff-sse/.gitkeep` | Empty placeholder |
| `07-oauth/.gitkeep` | Empty placeholder |

---

## B. Root Level — Outside `aither-v2/` (292 files)

### `gateway/` (11 files)
| File | Description |
|------|-------------|
| `gateway.py`, `admin.py`, `catalog.py` | Core gateway logic |
| `hybrid_rag.py`, `routing.py`, `metrics.py` | RAG, routing, metrics |
| `security.py`, `security_egress.py` | Security modules |
| `reaper.py`, `vault.py`, `wiki_graph.py` | Cleanup, vault, Wiki graph |
| `catalog.yaml` | Model catalog |

### `portal/` (35 files)
| File | Description |
|------|-------------|
| `server.ts`, `server.js` | Portal server |
| `api-gateway.ts`, `ldap.ts`, `security.ts` | Auth modules |
| `bff/` | BFF implementation |
| `static/` | Static assets (HTML, JS, CSS) |
| `dist/` | Built artifacts |
| `Dockerfile`, `nginx.conf` | Container config |
| `docker-compose.yaml`, `docker-compose.yml` | Docker Compose |

### `manifests/` (22 files)
| File | Description |
|------|-------------|
| Various `.yaml`, `.md` | K8s manifests for ChromaDB, embeddings, gateway, vLLM, networking |
| `observability/` | Prometheus, Grafana, DCGM exporter |

### `docs/` (root, 28 files)
| File | Description |
|------|-------------|
| Various `.md`, `.yaml` | API reference, security audits, integration docs, runbooks |
| `stage10/` | Stage 10 standards (10 files) |
| `diagrams/` | Architecture diagrams in DOT/SVG |

### `offline-deploy/` (35 files)
| File | Description |
|------|-------------|
| `README.md`, `CHANGELOG.md`, `VERSION`, `Makefile` | Package metadata |
| `docs/` | 8 documentation files |
| `k8s/` | Deployment manifests (8 files) |
| `scripts/` | Admin scripts (6 files) |
| `tests/` | Smoke, API, security tests (3 files) |
| `configs/` | Config templates |
| `offline/` | Offline assets |

### `diagrams/` (15 files)
| File | Description |
|------|-------------|
| `architecture.dot`, `architecture.svg` | System architecture |
| `deployment.dot`, `deployment.svg` | Deployment topology |
| `gpu-stack.dot`, `gpu-stack.svg` | GPU stack |
| `request-flow.dot`, `request-flow.svg` | Request flow |
| `tensor-parallelism.dot`, `tensor-parallelism.svg` | TP diagrams |
| `yadro-topology.dot`, `yadro-topology.svg`, `yadro-topology.png` | YADRO topology |
| `article2-architecture.*` | Article architecture |

### `configs/` (5 files)
| File | Description |
|------|-------------|
| `nginx-failover.conf` | nginx failover config |
| `vps1/nginx-aither-failover.conf` | VPS1 nginx |
| `vps3/nginx-aither.conf`, `bff-wrapper.sh` | VPS3 configs |

### `references/` (10 files)
| File | Description |
|------|-------------|
| `bmc-admin-rights-guide.md` | BMC admin guide |
| `k3s-vs-k8s-analysis.md`, `k8s-vs-k3s.md` | K3s/K8s comparisons |
| `openbmc-admin-guide.md` | OpenBMC guide |
| `redos-version-analysis.md` | RedOS analysis |
| `single-node-adaptation.md` | Single-node adaptation |
| `TR1-Aither-architecture.md`, `TR2-Portal-Aither-v6.md` | TR architecture docs |
| `tr-gap-analysis.md` | Gap analysis |
| `yadro-lab-readme.md` | YADRO lab guide |

### `wiki/` (10 files)
| File | Description |
|------|-------------|
| `index.md`, `SCHEMA.md`, `log.md` | Wiki index, schema, changelog |
| `concepts/llm-wiki.md`, `concepts/multi-tenant-architecture.md` | Concept docs |
| `entities/ai-gateway.md`, `entities/chromadb.md`, `entities/security-egress.md`, `entities/siem-integration.md`, `entities/vault-pki.md`, `entities/vllm-inference.md` | Entity docs |

### `fine-tuning/` (8 files)
| File | Description |
|------|-------------|
| `convert_peft_format.py`, `convert_to_vllm.py` | Model conversion scripts |
| `train_lora_14b.py`, `train_lora_cpu.py` | LoRA training scripts |
| `train_lora_nopeft_14b.py`, `train_qlora_32b.py` | Alternative training scripts |
| `job-14b.yaml`, `job-32b.yaml` | K8s Job manifests |
| `dataset.jsonl` | Training dataset |

### `Usage-Collector/` (5 files)
| File | Description |
|------|-------------|
| `article.md`, `LOG.md`, `protocol.md` | Usage collector documentation |
| `schemes/` (3 files) | Architecture diagrams |

### `k8s/hpa/` (5 files)
| File | Description |
|------|-------------|
| `hpa.yaml`, `gateway-hpa.yaml` | HPA definitions |
| `adapter-config.yaml`, `prometheus-adapter.yaml` | Adapter configs |
| `prometheus-config.yaml` | Prometheus scrape config |

### `grafana/` (3 files)
| File | Description |
|------|-------------|
| `dashboards/gpu-overview.json` | GPU monitoring dashboard |
| `dashboards/vllm-inference.json` | vLLM inference dashboard |
| `nginx-grafana.conf` | Grafana nginx config |

### `db/migrations/` (3 files)
| File | Description |
|------|-------------|
| `006_org_id_text.sql` | Org ID migration |
| `007_subscription_tiers.sql` | Subscription tiers |
| `008_auth_tables_k8s.sql` | Auth tables for K8s |

### `.github/workflows/` (3 files)
| File | Description |
|------|-------------|
| `ci.yml` | CI workflow |
| `continuous-verification.yml` | Continuous verification |
| `deploy.yml` | Deploy workflow |

### `aither-article/` (7 files)
| File | Description |
|------|-------------|
| `article.md` | Aither platform article |
| `architecture.svg`, `deployment.svg`, `gpu-stack.svg` | SVG diagrams |
| `request-flow.svg`, `tensor-parallelism.svg`, `yadro-topology.svg` | SVG diagrams |

### `aither-send/` (6 files)
| File | Description |
|------|-------------|
| `article.md` | Copy of aither-article/article.md |
| `architecture.svg`, `deployment.svg`, `gpu-stack.svg` | SVG copies |
| `request-flow.svg`, `tensor-parallelism.svg` | SVG copies |

### `aither-send (2)/` (6 files)
| File | Description |
|------|-------------|
| Same structure as `aither-send/` (6 files) | Copy of aither-send |

### `hosts/` (3 files)
| File | Description |
|------|-------------|
| `40.51-specs.md` | Server specs |
| `hardware-inventory.md` | Hardware inventory |
| `inventory.yaml` | YAML inventory |

### `archive/` (2 files)
| File | Description |
|------|-------------|
| `memory-2026-07-05.md` | Archived memory |
| `user-profile-2026-07-05.md` | Archived user profile |

### `delegation/` (1 file)
| File | Description |
|------|-------------|
| `public.pem` | Public PEM key (non-sensitive) |

### Root markdown files
| File | Description |
|------|-------------|
| `README.md` | Project README |
| `ROADMAP.md` | Project roadmap |
| `FEATURES.md` | Feature list |
| `status.md` | Project status |
| `tr-status.md` | TR status |
| `plan.md` | Project plan |
| `roadmap.md` | Alternative roadmap |
| `article.md` | Article |
| `brief.md` | Project brief |
| `bortovoy-zhurnal.md` | Lab journal |
| `lab-journal.md` | Lab journal |
| `article2-billing-catalog-multinode.md` | Billing article |
| `article2-billing-catalog-multinode_academic.docx` | Academic version (binary) |

### Other root files
| File | Description |
|------|-------------|
| `.gitignore` | Git ignore rules |
| `nginx-failover.conf` | nginx config |
| `nvidia_drv.txt` | NVIDIA driver info |
| `ai_platform_architecture.html` | Architecture HTML |
| `aither_academic_docx_and_schemes.zip` | Academic zips |
| `aither-send.zip`, `aither-article.zip` | Archived articles |
