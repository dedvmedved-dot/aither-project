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
| `scripts/check-gateway-32b.sh` | **Fail-closed dnsPolicy**: strict `ClusterFirst` only, removed `|| echo "ClusterFirst"`, `Default` now FAILs |
| `scripts/test-check-gateway-dns-policy.sh` | **New** — isolated negative tests for dnsPolicy acceptance logic |
| `docs/stage11/DNS-N7-ROOTCAUSE.md` | New — root cause analysis |
| `docs/stage11/DNS-N7-REMEDIATION.md` | New — this document (updated with acceptance fix) |
| `docs/stage11/DNS-N7-EVIDENCE.md` | New — verification evidence (updated with acceptance fix) |

---

## Acceptance Gate Remediation (Follow-up)

### Defect

1. **`|| echo "ClusterFirst"`** caused fail-open: if kubectl failed to read
   dnsPolicy from the Deployment, the script silently defaulted to
   "ClusterFirst" and would PASS.
2. **`Default` accepted as PASS** — the workaround value was still valid,
   meaning the acceptance gate could not detect an unfixed DNS-N7-01.

### Fix

Replaced with strict fail-closed logic:

```bash
# Before (fail-open)
DNSPOLICY=$(kubectl ... || echo "ClusterFirst")
if [ "$DNSPOLICY" = "ClusterFirst" ] || [ "$DNSPOLICY" = "Default" ]; then ...

# After (fail-closed)
if ! DNSPOLICY=$(kubectl ...); then
    fail "..."
elif [ -z "$DNSPOLICY" ]; then
    fail "..."
elif [ "$DNSPOLICY" = "ClusterFirst" ]; then
    pass "..."
elif [ "$DNSPOLICY" = "Default" ]; then
    fail "..."
else
    fail "..."
fi
```

### Negative Tests

6 test cases executed via `scripts/test-check-gateway-dns-policy.sh`:
- ClusterFirst → PASS ✅
- Default → FAIL ✅
- kubectl error → FAIL ✅
- empty → FAIL ✅
- None → FAIL ✅
- ClusterFirstWithHostNet → FAIL ✅

### Production Validation

```
Passed: 33  Failed: 0  Warnings: 0
Exit code: 0
dnsPolicy: ClusterFirst
```

## Safety Notes

- kubelet restart caused <30s disruption on n7 for existing Pods (liveness probes)
- Deployment managed Pods recreated automatically
- No force restart was used
- Backup of original kubelet.service created
- All changes documented and reversible
