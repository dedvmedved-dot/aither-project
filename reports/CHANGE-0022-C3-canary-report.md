# CHANGE-0022-C3 Canary Report

**Date:** 2026-07-27
**Commit:** 801ca390a15975ad360238414d2a059e2092daf2
**Status:** READY FOR CANARY DEPLOYMENT

## Canary Deployment Plan

### Phase 1: Deploy Infrastructure (independent services)
```
kubectl apply -f aither-v2/deploy/vault/deployment.yaml
kubectl apply -f aither-v2/deploy/siem/deployment.yaml
```
- Verify Vault: `kubectl wait --for=condition=ready pod vault-0 -n vault --timeout=120s`
- Verify SIEM: `kubectl wait --for=condition=ready pod -l app=aither-siem -n aither-inference --timeout=120s`

### Phase 2: Init Vault (manual)
```
kubectl exec -n vault vault-0 -- vault operator init -key-shares=5 -key-threshold=3
# Save 5 unseal keys + root token to 1Password
kubectl exec -n vault vault-0 -- vault operator unseal <key1>
kubectl exec -n vault vault-0 -- vault operator unseal <key2>
kubectl exec -n vault vault-0 -- vault operator unseal <key3>
```

### Phase 3: Deploy Gateway Canary (1 replica)
```
# Update Gateway ConfigMap with new rate_limit.py + app.py
kubectl create configmap gateway-code --from-file=gateway/ -n aither-inference --dry-run=client -o yaml | kubectl apply -f -

# Set feature flags in deployment env
kubectl set env deploy/aither-gateway -n aither-inference \
  RATE_LIMIT_ENABLED=true \
  SIEM_ENABLED=true \
  SIEM_HOST=aither-siem.aither-inference.svc \
  SIEM_PORT=8080 \
  RAG_ENABLED=true \
  VAULT_ENABLED=false  # Start with Vault off, enable after verification

# Rolling restart
kubectl rollout restart deploy/aither-gateway -n aither-inference
kubectl rollout status deploy/aither-gateway -n aither-inference --timeout=120s
```

### Phase 4: Smoke Tests (5 minutes)

```bash
# 1. Health check
curl http://gateway:8080/health

# 2. Rate limiting functional (should allow normal traffic)
curl -X POST http://gateway:8080/v1/chat/completions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-14b","messages":[{"role":"user","content":"ping"}],"max_tokens":5}'
# Expected: HTTP 200

# 3. SIEM receiving events
curl http://aither-siem.aither-inference.svc:8080/events/summary
# Expected: total > 0, covered_types includes auth_success

# 4. RAG status
curl http://gateway:8080/v1/rag/status \
  -H "Authorization: Bearer $TOKEN"
# Expected: ready: true or rag_not_available

# 5. Rate limit fail-closed (simulate Redis down — optional)
# If Redis is temporarily stopped, chat request should return 503
```

### Phase 5: Monitor (30 minutes)

Metrics to watch:
- `rate_limit_denied_total` — should be zero (no false positives)
- `gateway_503_total` — watch for unexpected rate_limit_unavailable
- `siem_events_total` — should be growing
- Gateway pod restart count — should be 0

### Phase 6: Full Rollout

If smoke tests pass and metrics are clean after 30 minutes:
```bash
kubectl scale deploy/aither-gateway -n aither-inference --replicas=2
# Enable Vault after verification
kubectl set env deploy/aither-gateway -n aither-inference VAULT_ENABLED=true
```

## Rollback Triggers

Immediate rollback if:
- `rate_limit_unavailable` errors > 0 (false positive deny)
- Gateway 503 rate > 1% of traffic
- RAG queries return 500 errors
- SIEM not receiving events after 2 minutes
- Gateway pod crashes (CrashLoopBackOff)

Rollback command:
```bash
kubectl rollout undo deploy/aither-gateway -n aither-inference
```

## Canary Verification Checklist

- [ ] Phase 1: Vault + SIEM pods Running
- [ ] Phase 2: Vault initialized + unsealed
- [ ] Phase 3: Gateway canary pod Running (1 replica)
- [ ] Phase 4.1: /health returns 200
- [ ] Phase 4.2: Normal chat request returns 200
- [ ] Phase 4.3: SIEM receiving events
- [ ] Phase 4.4: RAG status accessible
- [ ] Phase 5: 30-min monitoring window clean
- [ ] Phase 5: rate_limit_denied_total = 0
- [ ] Phase 5: gateway_503_total normal
- [ ] Phase 6: Full rollout (2 replicas)
- [ ] Phase 6: Vault enabled

## Pre-requisites

- [ ] Vault TLS cert generated (`vault-tls` Secret in `vault` namespace)
- [ ] SIEM admin key set in `aither-siem-auth` Secret
- [ ] Gateway has network access to `aither-siem.aither-inference.svc:8080`
- [ ] Gateway has network access to `vault.vault.svc:8200`
- [ ] RAG_ENABLED tier set for test org in `subscription_tiers`
- [ ] PostgreSQL `subscription_tiers` has RAG-enabled tiers (vip, enterprise)
- [ ] Redis cluster healthy
- [ ] PVCs provisioned (vault-data, vault-audit, aither-siem-data)
