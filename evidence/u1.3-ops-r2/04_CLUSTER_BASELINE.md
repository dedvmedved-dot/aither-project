# U1.3-OPS-R2 — 04_CLUSTER_BASELINE

**Date/Time (UTC):** 2026-07-26T02:12:45Z
**K8s Version:** v1.33.5
**Nodes:** 2 (1 control-plane + 1 worker), both Ready

## Deployments

| Name | Replicas | Ready | Available | Status |
|------|----------|-------|-----------|--------|
| aither-ai-platform | 1 | 1 | 1 | ✓ |
| aither-bff | 2 | 2 | 2 | ✓ |
| aither-identity | 1 | 1 | 1 | ✓ |
| aither-portal | 1 | 1 | 1 | ✓ |
| aither-portal-backend | 1 | 1 | 1 | ✓ |
| aither-portal-frontend | 1 | 1 | 1 | ✓ |
| aither-redis-rate-limit | 1 | 1 | 1 | ✓ |
| nginx-gateway-32b | 2 | 2 | 2 | ✓ |
| vllm-14b-instruct | 1 | 1 | 1 | ✓ |
| vllm-32b-gptq | 1 | 1 | 1 | ✓ |

**Total:** 10 deployments, all Available.

## BFF Strategy (post-fix)

| Parameter | Value |
|-----------|-------|
| Strategy | RollingUpdate |
| Replicas | 2 |
| maxUnavailable | 0 |
| maxSurge | 1 |
| minReadySeconds | 5 |
| PDB | minAvailable=1 |

## Kubernetes Events (recent)

BFF rollout events show:
- Old ReplicaSet 668b6fcbb7 (created during R1 rollout undo) deleted
- New ReplicaSet 64cb8c55b4 scaled from 1→2 replicas
- Transient startup probe failure on pod 668b6fcbb7-r42qb (pod deleted, expected with RollingUpdate)
- Both nodes running pods (n7-gpu: aither-bff, redis, nginx-gateway, vllm-14b, vllm-32b; n8-gpu: aither-bff, portal, portal-frontend, portal-backend, nginx-gateway, identity, ai-platform)

## Raw Log

Full command output in: `logs/03-cluster-baseline.log`
