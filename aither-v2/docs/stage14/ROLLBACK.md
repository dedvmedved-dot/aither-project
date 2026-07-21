# Aither / AI Hermes MVP
# Rollback Guide — Stage 14

## Overview

This document describes how to safely roll back an automated deployment.
All rollback procedures assume `kubectl` access to the target cluster and
the `aither-inference` namespace.

## What the Deployment Changes

The automated deployment (`deploy/deploy.sh`) applies the following
Kubernetes resources to the cluster:

| Stage | Resources | Namespace |
|---|---|---|
| 20 | Namespace `aither-inference` | global |
| 20 | ServiceAccount `vllm-sa` | aither-inference |
| 20 | RuntimeClass `nvidia` | global |
| 20 | PVC `model-storage` | aither-inference |
| 30 | vLLM NetworkPolicy | aither-inference |
| 30 | vLLM Service, Deployment | aither-inference |
| 30 | Gateway ConfigMap, Deployment | aither-inference |
| 30 | Redis Deployment, Service | aither-inference |
| 30 | BFF ConfigMap, Deployment, Service | aither-inference |
| 30 | Portal ConfigMap, Service | aither-inference |
| 30 | (Optional) GPU test, benchmarks | aither-inference |

It does **NOT** change:
- Cluster-level node configuration
- kubelet configuration
- Container runtime configuration
- External DNS records
- Persistent data outside PVCs

## Rollback Procedures

### Full Rollback (Complete Teardown)

Teardown the entire `aither-inference` namespace. **This deletes all data**
**including PVC contents.**

```bash
# 1. Delete all deployments, services, pods
kubectl delete namespace aither-inference

# 2. Wait for namespace termination
kubectl get namespace aither-inference  # Should show "Terminating" then disappear

# 3. Delete cluster-scoped resources (if no longer needed)
kubectl delete runtimeclass nvidia

# 4. Verify cleanup
kubectl get all -n aither-inference  # Should return "No resources found"
```

### Selective Rollback (Per-Service)

Roll back individual services without affecting others.

```bash
# Gateway
kubectl delete deployment nginx-gateway-32b -n aither-inference
kubectl delete configmap nginx-gateway-32b -n aither-inference

# vLLM
kubectl delete deployment vllm-14b-instruct -n aither-inference
kubectl delete service vllm-14b-instruct -n aither-inference
kubectl delete networkpolicy vllm-network-policy -n aither-inference

# Redis
kubectl delete deployment aither-redis-rate-limit -n aither-inference

# BFF
kubectl delete deployment aither-bff -n aither-inference
kubectl delete configmap aither-bff-config -n aither-inference

# Portal
kubectl delete deployment aither-portal -n aither-inference
kubectl delete configmap aither-portal-config -n aither-inference

# Secrets are preserved by default — delete explicitly if needed:
kubectl delete secret aither-bff-auth -n aither-inference
```

### Infrastructure Rollback

```bash
# PVC (deletes model data!)
kubectl delete pvc model-storage -n aither-inference

# ServiceAccount
kubectl delete serviceaccount vllm-sa -n aither-inference

# RuntimeClass
kubectl delete runtimeclass nvidia

# Namespace (deletes everything in it)
kubectl delete namespace aither-inference
```

## Re-deployment After Rollback

After a rollback, the system can be re-deployed from scratch:

```bash
# From the repository root
cd aither-v2/

# Full clean deployment
bash deploy/deploy.sh
```

The deployment framework is idempotent — running it after a selective
rollback will recreate only the missing resources.

## Limitations

1. **PVC data loss:** Deleting the namespace or PVC destroys model weight
   data. Ensure model weights are backed up or can be re-downloaded.

2. **Secrets not recreated:** The BFF auth secret (`aither-bff-auth`) is
   **not** managed by the deployment scripts — it must be created manually.
   A full namespace teardown deletes it.

3. **Cluster-level changes manual:** RuntimeClass, node labels, and GPU
   operator configuration must be rolled back manually if no longer needed.

4. **DNS changes:** If external DNS records were configured, they must be
   removed manually.

5. **Non-Kubernetes resources:** Any resources created outside kubectl
   (e.g., host-level mounts, systemd units) are not covered by this guide.

## Verification After Rollback

After a rollback, verify the cluster is in the expected state:

```bash
# Confirm namespace is gone
kubectl get namespace aither-inference 2>&1 | grep -q "NotFound" && echo "Namespace removed"

# Confirm no remaining Aither pods
kubectl get pods --all-namespaces | grep aither || echo "No Aither pods found"

# Confirm cluster health
kubectl cluster-info
```
