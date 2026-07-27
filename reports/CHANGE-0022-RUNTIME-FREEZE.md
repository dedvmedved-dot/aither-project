# CHANGE-0022 — RUNTIME FREEZE SNAPSHOT

**Directive:** R7-R5-EMG-FM-01  
**Date:** 2026-07-28T02:30:00Z  

Snapshot of cluster runtime state at freeze point.  
**No changes were made to production BFF or Gateway runtime during freeze.**

---

## Kubernetes Deployments

### Production BFF
```
NAME         READY   UP-TO-DATE   AVAILABLE   AGE
aither-bff   2/2     2            2           6h+
```
- Image: production BFF (unchanged)
- Routing: BFF → vLLM 14B directly; BFF → nginx proxy → vLLM 32B
- Gateway cutover: NOT PERFORMED
- BFF_MODE env: unspecified (production default)

### Gateway
```
NAME            READY   UP-TO-DATE   AVAILABLE   AGE
aither-gateway  2/2     2            2           6h+
```
- Image: `aither-gateway:change-0022-c4-r6b`
- Vault K8s auth: configured (VAULT_REQUIRED=false)
- SIEM: configured (port 1514)
- RAG: configured (fail-closed, org isolation)

### BFF Canary
```
NAME                        READY   UP-TO-DATE   AVAILABLE   AGE
aither-bff-gateway-canary   0/0     0            0           6h+
```
- Scaled to 0 replicas (FM-01 freeze)
- No external access
- Manifest preserved, manifests unchanged

---

## Infrastructure Services

| Service | Namespace | Status | Notes |
|---------|-----------|--------|-------|
| vLLM 14B | aither-inference | Running | Production model, direct BFF access |
| vLLM 32B | aither-inference | Running | Production model, via nginx proxy |
| Redis | aither-inference | Running | Rate limiting + sessions |
| PostgreSQL | aither-inference | Running | Billing + identity |
| Vault | vault | Running | K8s auth configured |
| SIEM | aither-inference | Running | UDP 1514, key rotated |
| ChromaDB | aither-inference | Running | RAG vector store |

---

## Secrets (Post-Rotation)

| Secret | Namespace | Status |
|--------|-----------|--------|
| aither-siem-auth | aither-inference | Rotated (C5), old key invalid |
| aither-bff-canary-secrets | aither-inference | Rotated (FM-01), old values invalid |
| aither-bff-delegation-key | aither-inference | Unchanged (private key, in-cluster only) |
| aither-gateway-public-key | aither-inference | Unchanged (public key, derived from private) |

---

## Git State (Pre-Freeze Commit)

```
HEAD:       28d9c13310a00022bb042b8db2f98d5ffde23701
origin:     28d9c13310a00022bb042b8db2f98d5ffde23701
Branch:     aither-v2
Tree:       CLEAN at 28d9c13 (dirty with freeze changes pending)
```
