# Stage 18A — Runtime Evidence

## Final Pod Status (2026-07-22 12:26 MSK)

| Pod | Node | Phase | Ready | Restarts | Image | Image ID |
|---|---|---|---|---|---|---|
| aither-identity | n8 | Running | 1/1 | 0 | `10.129.13.78:5000/aither-identity:stage18a-82fe433` | `sha256:427314f4294323dba9c445f21aedffa49133a0e516a3188e9707f2b5a7a69b93` |
| aither-portal-backend | n8 | Running | 1/1 | 0 | `10.129.13.78:5000/aither-portal-backend:stage18a-82fe433` | `sha256:940bc63a2e5906d0a5fb36063135a4bf6591d5642bd3aaf008740a4f6b18c76a` |
| aither-ai-platform | n8 | Running | 1/1 | 0 | `10.129.13.78:5000/aither-ai-platform:stage18a-82fe433` | `sha256:ab2825fcefaa7363b124edc1f8d644f7d551087eea2d6572e03bddc099c8961f` |
| aither-portal-frontend | n7 | Running | 1/1 | 0 | `nginx:stable-alpine` | `docker.io/library/nginx@sha256:...` |
| aither-bff | n7 | Running | 1/1 | 0 | Python (LinuxKit) | - |
| aither-portal | n7 | Running | 1/1 | 0 | nginx | - |
| vllm-14b-instruct | n7 | Running | 1/1 | 0 | `vllm/vllm-openai` | - |
| vllm-32b-gptq | n7 | Running | 1/1 | 0 | `vllm/vllm-openai` | - |

## Node Status (2026-07-22 12:14 MSK)

| Node | Status | Role | Version | Container Runtime |
|---|---|---|---|---|
| n7 (`bootsmam-k8s-clnt01-n7-gpu`) | Ready | Worker | v1.33.5 | containerd://2.2.1 |
| n8 (`bootsman-k8s-clnt01-n8-gpu`) | Ready | Control Plane | v1.33.5 | containerd://2.2.1 |

## Registry Status

| Component | Status |
|---|---|
| containerd (n8) | ✅ active |
| kubelet (n8) | ✅ active |
| aither-registry (n8) | ✅ active |
| Registry API `/v2/` | ✅ 200 OK |
| Registry catalog | ✅ 3 repositories |
| Tags | ✅ `stage18a-82fe433` on all |
| Storage path | `/var/lib/aither-registry/docker/registry/v2` |

## CRI Status (n8)

| Plugin | Status |
|---|---|
| `io.containerd.cri.v1.runtime` | ✅ ok |
| `io.containerd.cri.v1.images` | ✅ ok |
| `io.containerd.grpc.v1.cri` | ✅ ok |
| `RuntimeReady` | ✅ true |
| `NetworkReady` | ✅ true |

## Health Check Results

| Service | Endpoint | Health | Ready | Method |
|---|---|---|---|---|
| aither-identity | `GET /health` | ✅ 200 OK | ✅ 200 OK | port-forward |
| aither-portal-backend | `GET /health` | ✅ 200 OK | ✅ 200 OK | kubelet probes + logs |
| aither-ai-platform | `GET /health` | ✅ 200 OK | ✅ 200 OK | kubelet probes + logs |
