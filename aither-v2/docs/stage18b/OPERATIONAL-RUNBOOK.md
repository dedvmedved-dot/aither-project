# Stage 18B — Operational Runbook

## 1. Prerequisites

- kubectl access to Aither cluster (`10.129.13.78:6443`)
- SSH access to nodes (n7: `10.129.13.77`, n8: `10.129.13.78`)
- Secret `aither-identity-secret` in namespace `aither-inference`

## 2. Check Cluster Context

```bash
kubectl config current-context
kubectl cluster-info
```

## 3. Check Nodes

```bash
kubectl get nodes -o wide
```

Expected: both nodes `Ready`.

## 4. Check containerd

```bash
# On each node
ssh root@<node> "systemctl is-active containerd && systemctl is-enabled containerd"
```

Expected: `active`, `enabled`.

## 5. Check Registry

```bash
# Via n8 (localhost access)
ssh root@n8 "curl -fsS http://localhost:5000/v2/ && echo ''"
ssh root@n8 "curl -fsS http://localhost:5000/v2/_catalog"
```

Expected: `{}` and 3 repositories: aither-identity, aither-portal-backend, aither-ai-platform.

## 6. Safe Secret Creation

```bash
# Copy example, replace values, apply — DO NOT commit real values
cp services/identity/k8s/identity-secret.example.yaml services/identity/k8s/identity-secret.yaml
# Edit identity-secret.yaml with real values
kubectl apply -f services/identity/k8s/identity-secret.yaml
# Verify
kubectl get secret aither-identity-secret -n aither-inference
```

## 7. Deployment

```bash
./scripts/stage18a-deploy-services.sh
```

Expected: exit 0, all rollouts successful.

## 8. Post-Deployment Verification

```bash
kubectl get pods -n aither-inference -o wide
kubectl get deployments -n aither-inference
```

## 9. Health Checks

```bash
for svc in aither-identity aither-portal-backend aither-ai-platform; do
  echo "$svc:"
  kubectl exec -n aither-inference deployment/$svc -- \
    python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').status)"
done
```

Expected: all return HTTP 200.

## 10. Pod Recovery

```bash
# Delete a single pod — ReplicaSet recreates it automatically
kubectl delete pod -n aither-inference <pod-name>
kubectl rollout status deployment/<deployment> -n aither-inference --timeout=180s
```

## 11. containerd Recovery

```bash
# Restart on ONE node at a time
ssh root@<node> "sudo systemctl restart containerd"
# Wait for node Ready
kubectl get node <node>
```

## 12. Registry Recovery

```bash
ssh root@n8 "sudo systemctl restart aither-registry"
# Verify
ssh root@n8 "curl -fsS http://localhost:5000/v2/_catalog"
```

## 13. Rollback

```bash
# Find previous ReplicaSet
kubectl rollout history deployment/<name> -n aither-inference
# Rollback to previous revision
kubectl rollout undo deployment/<name> -n aither-inference
# Verify rollback
kubectl rollout status deployment/<name> -n aither-inference
kubectl get pods -n aither-inference -l app=<name>
```

## 14. Diagnose ImagePullBackOff

```bash
kubectl describe pod -n aither-inference <pod>
# Check registry connectivity from node
ssh root@<node> "curl -fsS http://10.129.13.78:5000/v2/"
# Check hosts.toml exists
ssh root@<node> "cat /etc/containerd/certs.d/10.129.13.78:5000/hosts.toml"
```

## 15. Diagnose Rollout Timeout

```bash
kubectl get deployment <name> -n aither-inference -o yaml
kubectl get pods -n aither-inference -l app=<name>
kubectl describe pod -n aither-inference <pod>
```

## 16. Diagnose Missing Secret

```bash
kubectl get secret aither-identity-secret -n aither-inference
# If missing, create from example
```

## 17. Prohibited Actions

- `git commit --amend`, `git rebase`, `git reset --hard`, `git push --force`
- Running deploy script without Secret
- Applying `identity-secret.example.yaml` with placeholder values
- Deleting PVC/PV with production data
- Running registry garbage collection without verification
- Destroying containerd content store
- Simultaneous containerd restart on all nodes

## 18. Evidence Collection

```bash
# Standard evidence commands
kubectl get nodes -o wide
kubectl get pods -n aither-inference -o wide
kubectl get deployments -n aither-inference -o wide
kubectl get pvc -n aither-inference
# Registry evidence
ssh root@n8 "curl -fsS http://localhost:5000/v2/_catalog"
# CRI evidence
ssh root@n8 "crictl info"
```

## 19. Escalation Criteria

- Node not returning to `Ready` within 2 minutes of containerd restart
- Registry not responding after restart
- Image digest changes unexpectedly
- PVC enters `Lost` state
- Workload Secret deleted
- Deployment causes >50% pod failure
- Persistent data loss
