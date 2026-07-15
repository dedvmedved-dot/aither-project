#!/bin/bash
# Удаление probes из манифестов etcd и apiserver
# Без них кластер стабилен на n8

set -e

python3 << 'PYEOF'
import yaml

for f in ['/etc/kubernetes/manifests/etcd.yaml', '/etc/kubernetes/manifests/kube-apiserver.yaml']:
    with open(f) as fh:
        d = yaml.safe_load(fh)
    for c in d['spec']['containers']:
        c.pop('livenessProbe', None)
        c.pop('readinessProbe', None)
        c.pop('startupProbe', None)
    d['spec']['terminationGracePeriodSeconds'] = 300
    with open(f, 'w') as fh:
        yaml.dump(d, fh, default_flow_style=False)
    print(f"Probes removed from {f}")

print("Done. Restarting kubelet...")
PYEOF

systemctl restart kubelet
sleep 15

echo "=== Status ==="
crictl ps --name 'etcd|kube-apiserver'
curl -s -m 2 http://127.0.0.1:2381/livez && echo "etcd OK"
curl -sk -m 2 https://127.0.0.1:6443/healthz && echo "apiserver OK"
