# Stage 18A — Registry Configuration

## Container Registry Setup

### Infrastructure

The registry runs as a containerd container (`ctr run`) managed by systemd on n8 (10.129.13.78).

**Systemd Unit:** `/etc/systemd/system/aither-registry.service`

Key properties:
- **Image:** `registry:2`
- **Port:** 5000 (host network)
- **Storage:** Bind-mounted `/var/lib/aither-registry`
- **Dependency:** `Wants=containerd.service` (auto-restarts after containerd restart)
- **Restart:** `always`

### Registry API

| Endpoint | Response | Description |
|---|---|---|
| `GET /v2/` | `{}` | API version check |
| `GET /v2/_catalog` | `{"repositories":["aither-identity","aither-portal-backend","aither-ai-platform"]}` | Repository list |
| `GET /v2/<repo>/tags/list` | `{"name":"<repo>","tags":["stage18a-82fe433"]}` | Tags per repo |

### Images

| Image | Tag | SHA-256 Digest |
|---|---|---|
| aither-identity | `stage18a-82fe433` | `sha256:427314f4294323dba9c445f21aedffa49133a0e516a3188e9707f2b5a7a69b93` |
| aither-portal-backend | `stage18a-82fe433` | `sha256:940bc63a2e5906d0a5fb36063135a4bf6591d5642bd3aaf008740a4f6b18c76a` |
| aither-ai-platform | `stage18a-82fe433` | `sha256:ab2825fcefaa7363b124edc1f8d644f7d551087eea2d6572e03bddc099c8961f` |

### Containerd Host Configuration

For containerd v2.2.1 with `version = 3`:

```toml
[plugins.'io.containerd.cri.v1.images'.registry]
    config_path = '/etc/containerd/certs.d'
```

Per-host configuration (`/etc/containerd/certs.d/10.129.13.78:5000/hosts.toml`):

```toml
server = "http://10.129.13.78:5000"
[host."http://10.129.13.78:5000"]
  capabilities = ["pull", "resolve", "push"]
  skip_verify = true
```

### Known Limitations

1. **No TLS** — registry operates over plain HTTP with `skip_verify`
2. **Single-node** — registry runs on control-plane (n8); n7 pulls across subnet
3. **No auth** — registry is open for read/write within cluster network
4. **No GC** — garbage collection not configured; manual cleanup via `ctr -n k8s.io images rm`
