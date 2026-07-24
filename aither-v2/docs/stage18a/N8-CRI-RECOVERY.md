# Stage 18H — n8 CRI Recovery

## Symptoms

- `kubectl get node n8` — `NotReady`
- `ctr plugins ls` — 3 CRI-related plugins in `error`:
  - `io.containerd.cri.v1.images` — **error**
  - `io.containerd.podsandbox.controller.v1.podsandbox` — **error**
  - `io.containerd.grpc.v1.cri` — **error**
  - `io.containerd.grpc.v1.sandbox-controllers` — **error**
- `crictl` — `unknown service runtime.v1.RuntimeService`
- `io.containerd.cri.v1.runtime` — **ok** (runtime plugin loaded successfully)

## Primary Error (from journalctl)

```
level=warning msg="failed to load plugin"
  error="invalid cri image config: `mirrors` cannot be set when `config_path` is provided"
  id=io.containerd.cri.v1.images

level=warning msg="failed to load plugin"
  error="unable to load CRI image service plugin dependency:
    invalid cri image config: `mirrors` cannot be set when `config_path` is provided"
  id=io.containerd.grpc.v1.cri

level=warning msg="Ignoring unknown key in TOML for plugin"
  error="strict mode: fields in the document are missing in the target struct"
  key="registry configs 10.129.13.78:5000 tls"
```

## Root Cause

**Category A + B — Error in containerd configuration + conflicting plugin configuration.**

containerd v2.2.1 defines `config_path = '/etc/containerd/certs.d'` in its default `[plugins.'io.containerd.cri.v1.images'.registry]` section. Stage 18A containerd configuration changes **overrode** this entire registry section with legacy containerd v1 syntax:

```toml
# Stage 18A — legacy v1 syntax (broken in containerd v2)
[plugins."io.containerd.cri.v1.images".registry]
  [plugins."io.containerd.cri.v1.images".registry.configs."10.129.13.78:5000".tls]
    insecure_skip_verify = true
  [plugins."io.containerd.cri.v1.images".registry.mirrors."10.129.13.78:5000"]
    endpoint = ["http://10.129.13.78:5000"]
```

This had two issues:
1. **`config_path` removed** — the default config_path was overwritten;
2. **`mirrors` + `configs` used** — these legacy keys conflict with `config_path` in containerd v2 strict mode.

containerd v2.2.1 treats `config_path` as the preferred scheme. `mirrors`/`configs` is the deprecated v1 scheme. When both are present (effectively: Stage 18 config removed `config_path` but containerd's parser still sees it in default struct merge), the CRI image plugin fails to load.

## Configuration Changes

**Before (Stage 18A — broken):**
```toml
# Registry hosts config
[plugins."io.containerd.cri.v1.images".registry]
  [plugins."io.containerd.cri.v1.images".registry.configs."10.129.13.78:5000".tls]
    insecure_skip_verify = true
  [plugins."io.containerd.cri.v1.images".registry.mirrors."10.129.13.78:5000"]
    endpoint = ["http://10.129.13.78:5000"]
```

**After (Stage 18H — fixed):**
```toml
# Registry config — config_path with hosts.toml (containerd v2 scheme)
[plugins."io.containerd.cri.v1.images".registry]
  config_path = "/etc/containerd/certs.d"
```

**`hosts.toml`** at `/etc/containerd/certs.d/10.129.13.78:5000/hosts.toml` already existed with correct content:
```toml
server = "http://10.129.13.78:5000"
[host."http://10.129.13.78:5000"]
  capabilities = ["pull", "resolve", "push"]
  skip_verify = true
```

**Files changed:**
- `/etc/containerd/config.toml` — lines 28-33 replaced

**Backups created:**
- `/etc/containerd/config.toml.stage18h-backup` (original pre-fix config)
- `/etc/containerd/config.toml.stage18h-pre` (pre-restart copy — identical to backup)

## Verification

### CRI plugins (after fix + restart)
```
io.containerd.cri.v1.images    — ok
io.containerd.cri.v1.runtime   — ok
io.containerd.grpc.v1.cri      — ok
```

### crictl info
```
RuntimeReady:  true
NetworkReady:  true
```

### crictl images / ps
Images preserved, pods operational.

### Node Ready
```
bootsman-k8s-clnt01-n8-gpu   Ready   control-plane   8d    v1.33.5
```

### Registry verification
```
GET /v2/ — {}
GET /v2/_catalog — {"repositories":["aither-ai-platform","aither-identity","aither-portal-backend"]}
```

## Timeline

| Time (MSK) | Event |
|---|---|
| 2026-07-21 | Initial containerd config created with legacy mirrors/configs |
| 2026-07-22 02:52 | Size validation errors in containerd (pre-existing content store corruption) |
| 2026-07-22 04:37 | containerd restart (Stage 18A) — CRI images plugin failed to load |
| 2026-07-22 ~10:00 | Diagnosis: `config_path` + `mirrors` conflict identified (Stage 18H) |
| 2026-07-22 ~10:15 | Fix applied: replaced mirrors/configs with config_path |
| 2026-07-22 ~10:20 | containerd restart successful — CRI plugins all ok |
| 2026-07-22 ~10:21 | kubelet restart — node Ready restored |

## Conclusion

**CRI recovered.** Root cause was containerd configuration mixing deprecated v1 `mirrors`/`configs` scheme with v2 `config_path` scheme. Hosts.toml-based registry config was already in place and correct. No kubelet endpoint changes were needed. No containerd downgrade. No image data loss.
