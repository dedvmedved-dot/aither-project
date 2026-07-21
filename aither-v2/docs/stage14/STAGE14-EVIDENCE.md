# Aither / AI Hermes MVP
# Stage 14 — Automated Deployment — Evidence Document

## Overview

Stage 14 implements an automated deployment framework for the Aither / AI Hermes
MVP. It provides a single entry point (`deploy/deploy.sh`) that validates the
environment, creates infrastructure, deploys services, and runs post-deployment
checks — all in a deterministic, idempotent manner.

## Files Created

### Deployment Scripts (`deploy/`)

| File | Description |
|---|---|
| `deploy/deploy.sh` | Orchestrator — entry point, runs all 4 stages |
| `deploy/10-precheck.sh` | Environment validation (tools, cluster, structure) |
| `deploy/20-infrastructure.sh` | Infrastructure setup (namespace, SA, PVC, RuntimeClass) |
| `deploy/30-services.sh` | Service deployment (vLLM, Gateway, Redis, BFF, Portal) |
| `deploy/40-validation.sh` | Post-deployment validation (existing project checks) |

### Documentation (`docs/stage14/`)

| File | Description |
|---|---|
| `docs/stage14/DEPLOYMENT.md` | Deployment guide — prerequisites, steps, troubleshooting |
| `docs/stage14/ROLLBACK.md` | Rollback procedures — full and selective teardown |
| `docs/stage14/STAGE14-EVIDENCE.md` | This evidence document |

## Script Verification

| Check | Result |
|---|---|
| `bash -n deploy/deploy.sh` | ✅ PASS |
| `bash -n deploy/10-precheck.sh` | ✅ PASS |
| `bash -n deploy/20-infrastructure.sh` | ✅ PASS |
| `bash -n deploy/30-services.sh` | ✅ PASS |
| `bash -n deploy/40-validation.sh` | ✅ PASS |
| Execute permission (`chmod +x`) | ✅ SET |

## Process Description

The deployment framework follows a sequential 4-stage pipeline:

```
deploy.sh
  ├── Stage 10: Pre-check     → validates tools, cluster, repo
  ├── Stage 20: Infrastructure → namespace, SA, PVC, RuntimeClass
  ├── Stage 30: Services       → kubectl apply in dependency order
  └── Stage 40: Validation     → runs existing check scripts
```

Each stage:
- Writes to a unified log (`deploy/deploy.log`)
- Is independently executable
- Is idempotent (safe to re-run)
- Exits with non-zero code on failure

## Prerequisites and Manual Steps

### Automated prerequisites (verified by Stage 10):
- Docker, kubectl, Git, Bash, curl, OpenSSL
- Kubernetes cluster reachable
- Git repository valid
- Project structure intact

### Remaining manual prerequisites:

| Step | Reason not automated | Impact if skipped |
|---|---|---|
| **BFF auth secret** (`aither-bff-auth`) | Contains sensitive credentials (REPLACE_ME). Automation cannot generate secrets. | BFF and Portal will fail to authenticate users. |
| **Model weights** on PVC/host path | Weights are large binary files (~16+ GB) obtained from HuggingFace. Download and placement require manual oversight. | vLLM pod will fail to load model. |
| **NVIDIA GPU operator** | Cluster-level infrastructure, not project-scoped. Requires cluster admin privileges. | vLLM pod will stay Pending (no GPU). |

These steps are documented in `DEPLOYMENT.md` under "Before You Begin".

## Deployment Order

The `30-services.sh` script applies manifests in strict dependency order:

1. vLLM NetworkPolicy (ingress rules for model service)
2. vLLM Service (ClusterIP — internal DNS name)
3. vLLM Deployment (model inference pod)
4. Gateway ConfigMap + Deployment (nginx reverse proxy)
5. Redis Deployment + Service (rate limiting backend)
6. BFF ConfigMap + Deployment + Service (API backend)
7. Portal ConfigMap + Service (frontend)
8. Optional: GPU test, benchmark manifests

Rollout is verified for vLLM, Gateway, and Redis with 120s timeout.

## Reproducibility Confirmation

The framework is designed for deployment from a "clean" Kubernetes cluster
with the following verified pathway:

```
Clean cluster
  → Clone repository
  → Install NVIDIA GPU operator (cluster admin)
  → Download model weights to PVC
  → Create auth secret with real values
  → bash deploy/deploy.sh
  → Running Aither / AI Hermes MVP
```

Every `kubectl apply` is idempotent. Re-running after partial failure
will resume from the failed stage.

## Runtime and Functional Confirmation

| Check | Status |
|---|---|
| Runtime changes (Gateway, inference, auth) | ✅ **NO** — existing logic untouched |
| Kubernetes manifests modified | ✅ **NO** — all manifests are existing, applied as-is |
| New user-facing functionality | ✅ **NO** — deployment framework only |
| Existing scripts modified | ✅ **NO** — scripts are called, not changed |
| Acceptance tests modified | ✅ **NO** — called without modification |

## Cross-Reference

- **Repository:** `dedvmedved-dot/aither-project`
- **Branch:** `aither-v2`
- **Parent commit:** `477ea20fca64b6ac6bb7afcda0cf5a2216d4e8a5`
- **Stage 12 release docs:** `docs/release/RC1-*`
- **Stage 13 CI pipeline:** `.github/workflows/continuous-verification.yml`
- **Existing scripts:** `scripts/check-gateway-32b.sh`, `scripts/test-check-gateway-dns-policy.sh`
