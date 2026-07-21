# DNS-N7-01 Verification Evidence

## 1. Before Fix — DNS failure on n7

### Test: Pod with dnsPolicy: ClusterFirst on n7

```
$ kubectl exec dns-test-n7 -- cat /etc/resolv.conf
nameserver 8.8.8.8
nameserver 8.8.4.4

$ kubectl exec dns-test-n7 -- nslookup kubernetes.default
Server:    8.8.8.8
Address:   8.8.8.8:53
** server can't find kubernetes.default: NXDOMAIN
```

### Kubelet process on n7 (missing --config)

```
/usr/bin/kubelet --kubeconfig=/etc/kubernetes/kubelet.conf
  --container-runtime-endpoint=unix:///run/containerd/containerd.sock
  --pod-infra-container-image=registry.k8s.io/pause:3.10
  --fail-swap-on=false
```

---

## 2. After Fix — DNS working on n7

### Test: Pod with dnsPolicy: ClusterFirst on n7

```
$ kubectl exec dns-test-n7-after -- cat /etc/resolv.conf
search default.svc.cluster.local svc.cluster.local cluster.local
nameserver 10.96.0.10
options ndots:5

$ kubectl exec dns-test-n7-after -- nslookup kubernetes.default.svc.cluster.local
Server:    10.96.0.10
Address:   10.96.0.10:53
Name:      kubernetes.default.svc.cluster.local
Address:   10.96.0.1

$ kubectl exec dns-test-n7-after -- nslookup google.com
Server:    10.96.0.10
Address:   10.96.0.10:53
Name:      google.com
Address:   64.233.163.138
```

### Kubelet service file on n7 (after fix)

```
ExecStart=/usr/bin/kubelet --config=/var/lib/kubelet/config.yaml
  $KUBELET_KUBECONFIG_ARGS $KUBELET_KUBEADM_ARGS $KUBELET_EXTRA_ARGS
  --fail-swap-on=false
```

### Verify kubelet loaded config

```
# kubelet-config ConfigMap content (loaded via --config)
clusterDNS: [10.96.0.10]
clusterDomain: cluster.local
```

---

## 3. Gateway — ClusterFirst DNS Verification

### Gateway pod on n7

```
$ kubectl exec nginx-gateway-32b-84bcf898c5-mrp4b -- cat /etc/resolv.conf
search aither-inference.svc.cluster.local svc.cluster.local cluster.local
nameserver 10.96.0.10
options ndots:5
```

### Gateway pod on n8

```
$ kubectl exec nginx-gateway-32b-84bcf898c5-lcbrb -- cat /etc/resolv.conf
search aither-inference.svc.cluster.local svc.cluster.local cluster.local cloud.test
nameserver 10.96.0.10
options ndots:5
```

---

## 4. CoreDNS Configuration

### Service

```
NAME       TYPE        CLUSTER-IP   PORT(S)
kube-dns   ClusterIP   10.96.0.10   53/UDP,53/TCP,9153/TCP
```

### Endpoints

```
kube-dns   10.244.0.103:53,10.244.0.104:53 (2 endpoints on n8)
```

### ConfigMap Corefile

```
.:53 {
    kubernetes cluster.local in-addr.arpa ip6.arpa {
        pods insecure
        fallthrough in-addr.arpa ip6.arpa
        ttl 30
    }
    forward . /etc/resolv.conf
    cache 30
}
```

---

## 5. Regression Test Results

### Diagnostic Script

```text
Aither Gateway 32B — Comprehensive Diagnostic Check
Namespace: aither-inference
2026-07-21T01:35:15Z

Passed: 33  Failed: 0  Warnings: 0
```

All 33 checks passed, including:
- ✅ Kubernetes services (vLLM, Gateway)
- ✅ Deployment replicas (2/2 Ready)
- ✅ Pod readiness on n7 and n8 (Running + Ready=True)
- ✅ dnsPolicy: ClusterFirst
- ✅ Upstream consistency (5 levels match: 10.99.3.103:8000)
- ✅ nginx -t config valid on n7 and n8
- ✅ /healthz local health (200)
- ✅ /health upstream health (200)
- ✅ 401 without auth
- ✅ 422 for chat completions
- ✅ /v1/models HTTP 200, model ID: qwen-32b-base
- ✅ /v1/completions HTTP 200, non-empty completion
- ✅ Response model matches requested model: qwen-32b-base

### Exit Code

```
$ bash scripts/check-gateway-32b.sh
Exit code: 0
echo $?  # => 0
```

---

## 6. Git Cleanliness

```bash
$ git diff --check
# (no output — clean)

$ git status
# (clean working tree, only new stage11 docs)
```

## 7. Configuration Comparison — n7 vs n8

| Parameter | n7 | n8 | Match |
|---|---|---|---|
| Kubelet version | v1.33.5 | v1.33.5 | ✅ |
| Container runtime | containerd 2.2.1 | containerd 2.2.1 | ✅ |
| OS | Astra Linux 6.6.28 | Astra Linux 6.6.28 | ✅ |
| kubelet `--config` flag | `/var/lib/kubelet/config.yaml` | Present | ✅ (fixed) |
| clusterDNS | 10.96.0.10 | 10.96.0.10 | ✅ |
| clusterDomain | cluster.local | cluster.local | ✅ |
| kube-dns resolvable | ✅ | ✅ | ✅ |
| CoreDNS endpoints | 2 (on n8) | 2 (on n8) | ✅ |
| Gateway dnsPolicy | ClusterFirst | ClusterFirst | ✅ |

---

## Conclusion

DNS-N7-01 is verified as closed. All DNS resolution tests pass on node n7.
The root cause (missing `--config` flag in kubelet systemd unit) was corrected.
The workaround (`dnsPolicy: Default`) was removed from the Gateway manifest.
Full regression testing (33/33 PASS) confirms no regressions.
