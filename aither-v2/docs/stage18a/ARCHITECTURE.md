# Stage 18A — Architecture Overview

## Service Architecture

The Stage 18A deployment delivers three Aither microservices to a two-node Kubernetes cluster via a private container registry.

### Nodes

| Node | Role | IP | Kubernetes Role |
|---|---|---|---|
| n7 (`bootsmam-k8s-clnt01-n7-gpu`) | Worker | 10.129.13.77 | Worker |
| n8 (`bootsman-k8s-clnt01-n8-gpu`) | Control Plane | 10.129.13.78 | Control Plane |
| Build host | Build | 10.129.100.141 | - |

### Services

| Service | Image | Port | Data Path | State |
|---|---|---|---|---|
| aither-identity | `10.129.13.78:5000/aither-identity:stage18a-82fe433` | 8000 | `/data/aither/identity` (PVC) | Running on n8 |
| aither-portal-backend | `10.129.13.78:5000/aither-portal-backend:stage18a-82fe433` | 8000 | Stateless | Running on n8 |
| aither-ai-platform | `10.129.13.78:5000/aither-ai-platform:stage18a-82fe433` | 8000 | `/data/aither/ai-platform` (PVC) | Running on n8 |
| aither-portal-frontend | `nginx:stable-alpine` | 80 | Stateless | Running on n7 |

### Container Registry

- **URL:** `10.129.13.78:5000`
- **Type:** `registry:2` OCI Distribution
- **Persistence:** Systemd-managed (`aither-registry.service`), bind-mounted to `/var/lib/aither-registry`
- **Storage path:** `/var/lib/aither-registry/docker/registry/v2`
- **Survives:** containerd restart, kubelet restart, node reboot

### Containerd Configuration (v2.2.1)

Both nodes use `version = 3` TOML configuration with `config_path` scheme:

```toml
[plugins.'io.containerd.cri.v1.images'.registry]
    config_path = '/etc/containerd/certs.d'
```

Per-registry configuration via `hosts.toml`:

```toml
# /etc/containerd/certs.d/10.129.13.78:5000/hosts.toml
server = "http://10.129.13.78:5000"
[host."http://10.129.13.78:5000"]
  capabilities = ["pull", "resolve", "push"]
  skip_verify = true
```

### Security Context

All service containers run as non-root:
- `runAsUser: 1000`
- `runAsGroup: 1000`
- `runAsNonRoot: true`
