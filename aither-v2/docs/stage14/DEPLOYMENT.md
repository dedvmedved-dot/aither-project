# Aither / AI Hermes MVP
# Automated Deployment Guide — Stage 14

## Overview

The automated deployment framework deploys the entire Aither / AI Hermes MVP
from a clean Kubernetes cluster. It consists of an orchestrator and four
sequential stages, each focusing on a specific aspect of the deployment.

## Prerequisites

### Required Tools

| Tool | Version (min.) | Purpose |
|---|---|---|
| Docker | 24+ | Container runtime |
| Kubernetes (kubectl) | 1.28+ | Cluster management |
| Git | 2.30+ | Repository access |
| Bash | 5.0+ | Script execution |
| curl | 7.68+ | HTTP checks |
| OpenSSL | 1.1+ | Certificate generation |

### Optional Tools

| Tool | Purpose |
|---|---|
| Helm | (Future) package management |
| Docker Compose | Local development |

### Cluster Requirements

- Kubernetes cluster with at least 1 GPU-enabled worker node
- NVIDIA GPU operator or nvidia-container-runtime installed
- `kubectl` context pointing to the target cluster
- Sufficient cluster resources:
  - 2+ vCPU per node
  - 8+ GB RAM per node
  - GPU: NVIDIA with ≥16 GB VRAM (for vLLM models)

### Before You Begin

1. Clone the repository:
   ```bash
   git clone https://github.com/dedvmedved-dot/aither-project.git
   cd aither-project/aither-v2
   ```

2. Create the BFF auth secret (required for BFF and Portal to function):
   ```bash
   kubectl create namespace aither-inference
   # Edit the example file with your values, then apply:
   # vi manifests/mvp-roadmap/07-auth-api/bff-auth-secret.example.yaml
   kubectl apply -f manifests/mvp-roadmap/07-auth-api/bff-auth-secret.example.yaml
   ```

3. Ensure model weights are available on the cluster (PVC or host path).

4. Verify cluster connectivity:
   ```bash
   kubectl cluster-info
   ```

## Running the Deployment

### Full Deployment

```bash
bash deploy/deploy.sh
```

The orchestrator runs all 4 stages in sequence. If any stage fails, the
deployment stops immediately with a non-zero exit code.

### Pre-check Only

To verify the environment without deploying:

```bash
bash deploy/deploy.sh --check
```

This runs only **Stage 10 (Pre-check)** and exits. Use this before starting
a full deployment to confirm all requirements are met.

## Deployment Stages

### Stage 10: Environment Pre-check

Validates that all required tools and prerequisites are present.

**Checks performed:**
- Docker, kubectl, Git, Bash, curl, OpenSSL presence
- Optional tools: Helm, Docker Compose
- Kubernetes cluster reachability
- Git repository integrity
- Project directory structure

**Failure:** Deployment aborts if any mandatory tool or check fails.

### Stage 20: Infrastructure Setup

Creates the base Kubernetes infrastructure.

**Resources created:**
- Namespace: `aither-inference`
- ServiceAccount: `vllm-sa`
- RuntimeClass: `nvidia`
- PersistentVolumeClaim: `model-storage`

**Note:** The BFF auth secret (`aither-bff-auth`) must be created manually
before deployment. The script checks for its existence and warns if missing.

### Stage 30: Service Deployment

Deploys all application manifests in dependency order.

**Deployment order:**
1. vLLM NetworkPolicy
2. vLLM Service
3. vLLM Deployment (model inference)
4. Gateway (nginx-gateway-32b)
5. Redis Rate Limiting
6. BFF Backend
7. Portal Frontend
8. Optional: GPU test, benchmarks

**Rollout verification:** After applying manifests, the script waits for
vLLM, Gateway, and Redis deployments to reach ready state (120s timeout).

### Stage 40: Post-deployment Validation

Runs existing project checks against the deployed system.

**Checks performed:**
1. Gateway diagnostic (`scripts/check-gateway-32b.sh`)
2. DNS policy acceptance tests (`scripts/test-check-gateway-dns-policy.sh`)
3. E2E test (`scripts/test-gateway-32b-e2e.sh`)
4. Secrets scan (`scripts/scan-secrets.sh`)
5. Git cleanliness (`git diff --check`)

**Note:** These checks are existing project scripts — their logic is unchanged.

## Parameters

The orchestrator accepts:

| Option | Description |
|---|---|
| *(none)* | Full deployment (all 4 stages) |
| `--check` | Pre-check only (Stage 10) |
| `--help` | Show usage information |

## Expected Results

- Stage 10: All required tools found, cluster reachable
- Stage 20: Namespace, SA, PVC created successfully
- Stage 30: All pods reach Ready state within timeout
- Stage 40: Gateway diagnostic passes, acceptance tests pass

## Troubleshooting

| Problem | Likely Cause | Solution |
|---|---|---|
| `kubectl cluster-info` fails | No kubeconfig or wrong context | `kubectl config use-context <name>` |
| `docker` not found | Docker not installed | Install Docker Engine 24+ |
| vLLM pod stays Pending | Insufficient GPU resources | Check node GPU availability |
| Gateway pod CrashLoopBackOff | Missing upstream (vLLM not ready) | Wait for vLLM pod, check logs |
| BFF auth secret missing | Not created before deploy | Create from example manifest |
| Validation script exits 1 | Pre-existing issue unrelated to deploy | Check individual script output |
| Gateway diagnostic fails | DNS or connectivity issue | Run `scripts/check-gateway-32b.sh` manually |

## Logs

All deployment output is logged to `deploy/deploy.log`. Each stage writes
its own section with timestamps and exit codes.
