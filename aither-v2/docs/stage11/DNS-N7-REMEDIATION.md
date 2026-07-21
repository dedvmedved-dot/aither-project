# DNS-N7-01 Remediation Report

## Summary

**Issue:** DNS-N7-01 — kubelet on `bootsmam-k8s-clnt01-n7-gpu` missing `--config` flag
**Fix:** Added `--config=/var/lib/kubelet/config.yaml` to kubelet systemd unit
**Scope:** Node-level kubelet configuration + Gateway manifest workaround removal
**Result:** DNS-N7-01 CLOSED

---

## Remediation Steps

### Step 1 — Diagnose root cause

```bash
# Identified via debug pod with host filesystem access
kubectl exec node-debug-n7-v2 -- cat /host/etc/systemd/system/kubelet.service
# => ExecStart missing --config flag

# Verified kubelet process args
# on host PID via /proc: /usr/bin/kubelet [NO --config]
```

### Step 2 — Modify kubelet systemd unit on n7

```bash
# Backup
cp /host/etc/systemd/system/kubelet.service /host/etc/systemd/system/kubelet.service.bak

# Add --config flag
sed -i "s|ExecStart=/usr/bin/kubelet|ExecStart=/usr/bin/kubelet --config=/var/lib/kubelet/config.yaml|" \
  /host/etc/systemd/system/kubelet.service
```

**Before:**
```
ExecStart=/usr/bin/kubelet $KUBELET_KUBECONFIG_ARGS $KUBELET_KUBEADM_ARGS $KUBELET_EXTRA_ARGS --fail-swap-on=false
```

**After:**
```
ExecStart=/usr/bin/kubelet --config=/var/lib/kubelet/config.yaml $KUBELET_KUBECONFIG_ARGS $KUBELET_KUBEADM_ARGS $KUBELET_EXTRA_ARGS --fail-swap-on=false
```

### Step 3 — Reload systemd and restart kubelet

```bash
# Via nsenter (host PID namespace from debug pod)
nsenter -t 1 -m -u -i -n -p -- systemctl daemon-reload
nsenter -t 1 -m -u -i -n -p -- systemctl restart kubelet
```

### Step 4 — Verify DNS resolution on n7

Created test pod with `dnsPolicy: ClusterFirst` on n7:

```bash
kubectl run dns-test-n7-after --image=busybox:1.36 \
  --overrides='{"spec":{"nodeName":"bootsmam-k8s-clnt01-n7-gpu", "dnsPolicy":"ClusterFirst"}}' \
  -- sleep 600
```

Confirmed:
- `/etc/resolv.conf`: `nameserver 10.96.0.10` ✅
- `nslookup kubernetes.default.svc.cluster.local`: resolves to `10.96.0.1` ✅
- `nslookup google.com`: resolves via CoreDNS forward ✅

### Step 5 — Remove dnsPolicy: Default workaround from Gateway manifest

Changed `manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml`:

```yaml
# Before
spec:
  dnsPolicy: Default

# After
spec:
  dnsPolicy: ClusterFirst
```

Applied and rolled out:

```bash
kubectl apply -f manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml
```

### Step 6 — Update diagnostic script

Updated `scripts/check-gateway-32b.sh` to accept both `ClusterFirst` and `Default`
as valid dnsPolicy values (forward-compatible).

---

## Files Changed

| File | Change |
|---|---|
| `/etc/systemd/system/kubelet.service` (on n7) | Added `--config=/var/lib/kubelet/config.yaml` |
| `manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml` | `dnsPolicy: Default` → `ClusterFirst` |
| `scripts/check-gateway-32b.sh` | Accept both dnsPolicy values |
| `docs/stage11/DNS-N7-ROOTCAUSE.md` | New — root cause analysis |
| `docs/stage11/DNS-N7-REMEDIATION.md` | New — this document |
| `docs/stage11/DNS-N7-EVIDENCE.md` | New — verification evidence |

---

## Safety Notes

- kubelet restart caused <30s disruption on n7 for existing Pods (liveness probes)
- Deployment managed Pods recreated automatically
- No force restart was used
- Backup of original kubelet.service created
- All changes documented and reversible
