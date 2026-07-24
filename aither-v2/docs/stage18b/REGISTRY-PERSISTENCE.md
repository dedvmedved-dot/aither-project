# Stage 18B — Registry Persistence Baseline

## Registry Details

| Field | Value |
|-------|-------|
| Host | 10.129.13.78:5000 |
| Type | `registry:2` OCI Distribution |
| Runtime | Systemd-managed (`aither-registry.service`) via containerd `ctr run` |
| Data path | `/var/lib/aither-registry/docker/registry/v2` |
| Restart policy | `always` |
| Dependency | `Wants=containerd.service` |
| Network | host network on n8 |

## Catalog (2026-07-22)

| Repository | Tags | Digest (from k8s describe) |
|------------|------|---------------------------|
| `aither-identity` | `stage18a-82fe433` | `sha256:427314f4294323dba9c445f21aedffa49133a0e516a3188e9707f2b5a7a69b93` |
| `aither-portal-backend` | `stage18a-82fe433` | `sha256:940bc63a2e5906d0a5fb36063135a4bf6591d5642bd3aaf008740a4f6b18c76a` |
| `aither-ai-platform` | `stage18a-82fe433` | `sha256:ab2825fcefaa7363b124edc1f8d644f7d551087eea2d6572e03bddc099c8961f` |

## Image Reference Verification

| Deployment | Image Reference | Registry Match | Tag Match | Digest Match |
|------------|----------------|----------------|-----------|--------------|
| aither-identity | `10.129.13.78:5000/aither-identity:stage18a-82fe433` | ✅ | ✅ | `sha256:427314f...` |
| aither-portal-backend | `10.129.13.78:5000/aither-portal-backend:stage18a-82fe433` | ✅ | ✅ | `sha256:940bc63...` |
| aither-ai-platform | `10.129.13.78:5000/aither-ai-platform:stage18a-82fe433` | ✅ | ✅ | `sha256:ab2825f...` |

All three deployments reference images from the correct registry with the correct tag. Digests match between `kubectl describe pod` output and Stage 18A evidence.
