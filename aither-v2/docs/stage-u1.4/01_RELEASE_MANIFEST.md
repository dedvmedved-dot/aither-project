# Release Manifest — U1.4 Beta-1

## Kubernetes Components

| Component | Deployment | Image | ConfigMap/Secret |
|---|---|---|---|
| ai-platform | aither-ai-platform (1 replica) | `10.129.13.78:5000/ai-platform:u1.2-persistence-20260725-0004` | Env: GATEWAY_URL, VLLM_14B_URL, VLLM_API_KEY |
| nginx-gateway-32b | nginx-gateway-32b (2 replicas) | `nginx:alpine` | ConfigMap `nginx-gateway-32b` → `nginx.conf` |
| vllm-14b-instruct | vllm-14b-instruct (1 replica, GPU n7) | `vllm/vllm-openai@sha256:6cf9808...` | Args: model, dtype, gpu-memory, tensor-parallel |
| vllm-32b-gptq | vllm-32b-gptq (1 replica, GPU n7) | `vllm/vllm-openai@sha256:6cf9808...` | Args: model, dtype, gpu-memory, tensor-parallel |
| aither-identity | aither-identity (1 replica) | `10.129.13.78:5000/aither-identity:stage18a-82fe433` | SQLite DB |
| aither-bff | aither-bff (1 replica) | `python:3.11-slim` | Routing logic |
| aither-portal-backend | aither-portal-backend (1 replica) | `10.129.13.78:5000/aither-portal-backend:ba02-014f91b` | — |
| aither-redis-rate-limit | aither-redis-rate-limit (1 replica) | `redis:7-alpine` | — |
| aither-portal-frontend | aither-portal-frontend (1 replica) | `nginx:stable-alpine` | — |
| aither-portal | aither-portal (1 replica) | `nginx:alpine` | — |

## VPS2 Edge Components

| Component | Container | Image | Configuration |
|---|---|---|---|
| VPN Client | vpn-cisco | `vpn-cisco-o` (local) | Entrypoint: `vpn-cisco-entrypoint.sh` |
| Reverse Proxy | aither-failover-nginx | `nginx:alpine` | Bind mount: `/root/nginx-failover.conf` |

## Services

| Service | Type | Port | External |
|---|---|---|---|
| ai-platform | NodePort | 30902 | ✅ :30902 |
| nginx-gateway-32b | NodePort | 30901 | VPS2 only |
| VPS2 nginx :443 | Docker port | 443 | ✅ fb1.spb.ru |
| VPS2 nginx :10443 | Docker port | 10443 | ✅ fb1.spb.ru:10443 |

## Databases
| Database | Location | Backup |
|---|---|---|
| ai-platform (SQLite) | Pod `/data/ai-platform.db` | Manual only |
| Identity (SQLite) | Pod `/data/identity.db` | Manual only |

## Git References
- Repository: `github.com/dedvmedved-dot/aither-project`
- Branch: `aither-v2`
- Source-of-truth: `services/`, `scripts/`, `docs/`, `03-vllm-14b-deploy/manifests/`
