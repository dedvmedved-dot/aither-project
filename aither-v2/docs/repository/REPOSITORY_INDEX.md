# Repository Index

## Repository Structure (top-level)

```
/root/aither-v2/
├── aither-v2/                          ← Active working directory (563 files)
│   ├── docs/                           ← Documentation (364 files)
│   ├── reports/                        ← Stage reports (70 files)
│   ├── manifests/                      ← K8s manifests (15 files)
│   ├── services/                       ← Service code (21 files)
│   ├── scripts/                        ← Automation scripts (16 files)
│   ├── tools/                          ← Utility tools (10 files)
│   ├── deploy/                         ← Deployment scripts (5 files)
│   ├── evidence/                       ← Evidence files (4 files)
│   ├── release/                        ← Release artifacts (4 files)
│   ├── 03-vllm-14b-deploy/             ← Legacy vLLM deploy (40 files)
│   ├── 02-containerd-nvidia-runtime/   ← Legacy containerd docs (6 files)
│   ├── 01-k8s-gpu-operator/            ← Legacy K8s GPU docs (3 files)
│   ├── 04-tensor-parallelism/..07-oauth/ ← Placeholder dirs (1 .gitkeep each)
│   └── playwright/                     ← E2E tests (not tracked in git)
│
├── gateway/             ← Historical gateway code (11 files)
├── portal/              ← Historical portal code (35 files)
├── manifests/           ← Historical K8s manifests (22 files)
├── docs/                ← Historical documentation (28 files)
├── diagrams/            ← Architecture diagrams (15 files)
├── offline-deploy/      ← Offline deployment package (35 files)
├── configs/             ← Historical configs (5 files)
├── references/          ← Reference documentation (10 files)
├── wiki/                ← LLM Wiki knowledge base (10 files)
├── fine-tuning/         ← Fine-tuning scripts (8 files)
├── k8s/                 ← HPA configs (5 files)
├── grafana/             ← Grafana dashboards (3 files)
├── db/                  ← DB migrations (3 files)
├── Usage-Collector/     ← Usage tracking docs (5 files)
├── aither-article/      ← Article content (7 files)
├── aither-send/         ← Duplicate of aither-article (6 files)
├── aither-send (2)/     ← Duplicate of aither-article (6 files)
├── .github/             ← CI/CD workflows (3 files)
├── archive/             ← Archived docs (2 files)
├── delegation/          ← Public key (1 file)
├── hosts/               ← Hardware inventory (3 files)
├── .gitignore           ← Git ignore rules
├── README.md            ← Root README
├── ROADMAP.md           ← Root ROADMAP
└── (other root files)   ← Various historical artifacts
```

## File Counts Summary

| Location | Count | Category |
|----------|-------|----------|
| `aither-v2/` | 563 | Active workspace |
| Root level (outside aither-v2/) | 292 | Historical/Reference |
| **Total tracked** | **855** | |

## Subdirectory Breakdown (aither-v2/)

| Subdirectory | Files | Notes |
|-------------|-------|-------|
| `docs/` | 364 | Project control, MVP roadmap, user launch, releases, stages 10-18 |
| `reports/` | 70 | Stage reports (10, 10b, ba02r, rc1, rc2, stage-u1) |
| `03-vllm-14b-deploy/` | 40 | Legacy vLLM 14B deployment |
| `services/` | 21 | Portal frontend, backend, identity, AI platform, BFF |
| `scripts/` | 16 | Automation and test scripts |
| `manifests/` | 15 | MVP roadmap K8s manifests |
| `tools/` | 10 | Benchmarks, BFF, portal tools |
| `deploy/` | 5 | Deployment scripts |
| `release/` | 4 | MVP-RC1 release artifacts (empty .gitkeep) |
| `evidence/` | 4 | RC2 evidence files |
| `02-containerd/` | 6 | Legacy containerd docs |
| `01-k8s-gpu-operator/` | 3 | Legacy GPU operator docs |
| Placeholders (04-07) | 4 | Empty .gitkeep only |
| `.gitkeep` | 1 | Root .gitkeep |
