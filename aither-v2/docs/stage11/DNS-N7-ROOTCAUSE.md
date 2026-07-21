# DNS-N7-01 Root Cause Analysis

## Summary

**Issue:** DNS-N7-01 — Pods on node `bootsmam-k8s-clnt01-n7-gpu` could not resolve
Kubernetes Service DNS names through CoreDNS.

**Severity:** Critical (blocked cluster-internal service discovery)

**Status:** RESOLVED (see DNS-N7-REMEDIATION.md)

---

## Root Cause

### Primary Cause (kubelet config not loaded)

The kubelet process on node n7 was started **without the `--config` flag** in its
systemd unit file (`/etc/systemd/system/kubelet.service`). This caused kubelet to
use its **built-in defaults** instead of loading
`/var/lib/kubelet/config.yaml`, which contains the correct `clusterDNS`
configuration.

**Before fix** — kubelet service ExecStart on n7:

```
ExecStart=/usr/bin/kubelet $KUBELET_KUBECONFIG_ARGS $KUBELET_KUBEADM_ARGS $KUBELET_EXTRA_ARGS --fail-swap-on=false
```

**After fix** — kubelet service ExecStart on n7:

```
ExecStart=/usr/bin/kubelet --config=/var/lib/kubelet/config.yaml $KUBELET_KUBECONFIG_ARGS $KUBELET_KUBEADM_ARGS $KUBELET_EXTRA_ARGS --fail-swap-on=false
```

### Contributing Factors

1. **kubelet-config ConfigMap was correct** — contained `clusterDNS: [10.96.0.10]`
   but was never consumed because `--config` was missing in the systemd unit.
2. **Node n8 did not have this problem** — whether through different bootstrap or
   manual correction, n8's kubelet correctly loaded its config.
3. **CoreDNS configuration was correct** — Service ClusterIP `10.96.0.10`,
   endpoints pointing to 2 running pods on n8, valid Corefile.

---

## Diagnostic Evidence

### Before Fix — Pod on n7 with dnsPolicy: ClusterFirst

```
# /etc/resolv.conf (from test pod)
nameserver 8.8.8.8
nameserver 8.8.4.4

# nslookup kubernetes.default.svc.cluster.local
** server can't find kubernetes.default: NXDOMAIN
```

### After Fix — Pod on n7 with dnsPolicy: ClusterFirst

```
# /etc/resolv.conf (from test pod)
search default.svc.cluster.local svc.cluster.local cluster.local
nameserver 10.96.0.10
options ndots:5

# nslookup kubernetes.default.svc.cluster.local
Server:    10.96.0.10
Address:   10.96.0.10:53
Name:      kubernetes.default.svc.cluster.local
Address:   10.96.0.1

# nslookup google.com (external DNS via CoreDNS forward)
Server:    10.96.0.10
Address:   10.96.0.10:53
Name:      google.com
Address:   64.233.163.138
```

### Kubelet Process Verification

```
# n7 kubelet process (before fix)
/usr/bin/kubelet --kubeconfig=/etc/kubernetes/kubelet.conf
  --container-runtime-endpoint=unix:///run/containerd/containerd.sock
  --pod-infra-container-image=registry.k8s.io/pause:3.10
  --fail-swap-on=false
# NO --config flag

# kubelet-config ConfigMap (always correct)
clusterDNS:
- 10.96.0.10
clusterDomain: cluster.local
```

### Node Comparison

| Parameter | n7 (before) | n8 | Match |
|---|---|---|---|
| Kubelet version | v1.33.5 | v1.33.5 | ✅ |
| Container runtime | containerd 2.2.1 | containerd 2.2.1 | ✅ |
| OS | Astra Linux 6.6.28 | Astra Linux 6.6.28 | ✅ |
| kubelet `--config` flag | **MISSING** | Present | ❌ |
| clusterDNS (ConfigMap) | 10.96.0.10 | 10.96.0.10 | ✅ |
| clusterDomain (ConfigMap) | cluster.local | cluster.local | ✅ |
| CoreDNS reachable | ❌ (8.8.8.8 used) | ✅ (10.96.0.10) | ❌ |

---

## Resolution

See [DNS-N7-REMEDIATION.md](DNS-N7-REMEDIATION.md) for the remediation steps.

## Verification

See [DNS-N7-EVIDENCE.md](DNS-N7-EVIDENCE.md) for full verification and
regression test results.
