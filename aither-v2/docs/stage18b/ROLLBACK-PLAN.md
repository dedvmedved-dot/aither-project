# Stage 18B — Rollback Plan

## Principles

- **Non-destructive** — Does not delete persistent data, Secret, or registry images
- **Verifiable** — Every step can be confirmed before proceeding
- **Reversible** — Rollback to any previous revision via `kubectl rollout undo`

## How to Determine Previous ReplicaSet

```bash
kubectl rollout history deployment/<name> -n aither-inference
```

Output shows revision numbers and — if configured — change causes. The previous revision is typically `REVISION - 1`.

To see the exact image used by each revision:

```bash
kubectl describe replicaset -n aither-inference | grep "Image:" | head -5
```

## Rollback Procedure

```bash
# 1. Rollback specific deployment
kubectl rollout undo deployment/aither-identity -n aither-inference

# 2. Verify rollback
kubectl rollout status deployment/aither-identity -n aither-inference --timeout=180s

# 3. Check new pod is Running
kubectl get pods -n aither-inference -l app=aither-identity -o wide

# 4. Verify health
kubectl exec -n aither-inference deployment/aither-identity -- \
  python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').status)"

# 5. Verify the rolled-back image tag
kubectl describe pod -n aither-inference -l app=aither-identity | grep "Image:"
```

## Rollback to Specific Revision

```bash
kubectl rollout undo deployment/aither-identity -n aither-inference --to-revision=<N>
```

## How to Restore Image Digest

If rollback is not sufficient and you need to restore a specific image:

1. Identify the correct image tag/digest from `crictl images` or registry:
   ```bash
   ssh root@n8 "crictl images | grep aither-identity"
   ```

2. Update the deployment:
   ```bash
   kubectl set image deployment/aither-identity \
     -n aither-inference \
     identity=10.129.13.78:5000/aither-identity:<original-tag>
   ```

## How to Verify Rollback

1. Pod `Running` and `Ready` (1/1)
2. Health endpoint returns HTTP 200
3. Correct image tag in `kubectl describe pod`
4. Other Aither services unaffected
5. PVC data preserved

## When Rollback is Prohibited

- **Registry unavailable** — Pods cannot pull the rolled-back image
- **containerd CRI not operational** — Image pull will fail
- **Rollback to unknown revision** — Always verify the target revision's image first
- **Simultaneous rollback of all deployments** — Roll back one deployment at a time
- **PVC data format changed** — If the new image wrote data in a different format, rolling back the application may cause schema mismatch

## No Real Rollback Performed

Stage 18B did not execute a real rollback of a working deployment. The revision history is available via `kubectl rollout history`. No destructive actions were taken.
