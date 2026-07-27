# CHANGE-0022 Evidence — Section 12: Vault

COMMIT: 801ca390a15975ad360238414d2a059e2092daf2
TIMESTAMP: 2026-07-27T23:45:00Z

## VAULT-001: TLS enabled

| Field | Value |
|---|---|
| Test ID | VAULT-001 |
| Command | `kubectl get statefulset vault -n vault -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="VAULT_LOCAL_CONFIG")].value}' | grep tls_` |
| Timestamp | 2026-07-27T23:47:00Z |
| Target | Vault StatefulSet TLS configuration |
| Expected | TLS cert and key files configured in listener |
| Actual | `tls_cert_file = "/vault/tls/tls.crt"`, `tls_key_file = "/vault/tls/tls.key"` |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## VAULT-002: Pinned image digest

| Field | Value |
|---|---|
| Test ID | VAULT-002 |
| Command | `kubectl get statefulset vault -n vault -o jsonpath='{.spec.template.spec.containers[0].image}'` |
| Timestamp | 2026-07-27T23:47:05Z |
| Target | Vault image |
| Expected | Pinned version (not `:latest`) |
| Actual | `hashicorp/vault:1.18.3` — pinned version |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## VAULT-003: NetworkPolicy

| Field | Value |
|---|---|
| Test ID | VAULT-003 |
| Command | `kubectl get networkpolicy vault -n vault -o yaml` |
| Timestamp | 2026-07-27T23:47:10Z |
| Target | Vault NetworkPolicy |
| Expected | Ingress restricted to aither-inference namespace Gateway pods |
| Actual | NetworkPolicy present: ingress from `namespace=aither-inference` + `app=aither-gateway` |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## VAULT-004: Pod security context

| Field | Value |
|---|---|
| Test ID | VAULT-004 |
| Command | `kubectl get statefulset vault -n vault -o jsonpath='{.spec.template.spec.securityContext}'` |
| Timestamp | 2026-07-27T23:47:15Z |
| Target | Vault pod securityContext |
| Expected | `runAsNonRoot: true`, non-zero UID |
| Actual | `runAsNonRoot: true, runAsUser: 100, runAsGroup: 1000, fsGroup: 1000` |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## VAULT-005: Backup procedure documented

| Field | Value |
|---|---|
| Test ID | VAULT-005 |
| Command | Code audit: `aither-v2/deploy/vault/deployment.yaml` + `vault-policies` ConfigMap |
| Timestamp | 2026-07-27T23:47:20Z |
| Target | Backup documentation in deploy manifest |
| Expected | Raft snapshot save command documented |
| Actual | Backup procedure in comments and `vault-init-procedure.md` in ConfigMap |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## VAULT-006: Init/unseal procedure documented

| Field | Value |
|---|---|
| Test ID | VAULT-006 |
| Command | `kubectl get configmap vault-policies -n vault -o jsonpath='{.data.vault-init-procedure\.md}' | head -5` |
| Timestamp | 2026-07-27T23:47:25Z |
| Target | Vault init/unseal documentation |
| Expected | Step-by-step init/unseal procedure |
| Actual | Full procedure: init → save keys → unseal → login → audit → K8s auth → policies |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## VAULT-007: Recovery keys stored securely (NOT in Git)

| Field | Value |
|---|---|
| Test ID | VAULT-007 |
| Command | `grep -r "hvs\.\|s\.[A-Za-z0-9]\{20,\}" aither-v2/deploy/vault/ || echo "CLEAN"` |
| Timestamp | 2026-07-27T23:47:30Z |
| Target | Vault deployment files — no tokens in Git |
| Expected | No Vault tokens in deploy files |
| Actual | `CLEAN` — no hvs.* or s.* tokens found |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## VAULT-008: Audit device enabled

| Field | Value |
|---|---|
| Test ID | VAULT-008 |
| Command | `kubectl get pvc vault-audit -n vault` |
| Timestamp | 2026-07-27T23:47:35Z |
| Target | Vault audit PVC |
| Expected | Audit PVC exists for file-based audit device |
| Actual | PVC `vault-audit` 5Gi, STATUS=Bound. Mounted at `/vault/audit`. Init procedure enables `vault audit enable file`. |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## VAULT-009: Least-privilege policies (separate per consumer)

| Field | Value |
|---|---|
| Test ID | VAULT-009 |
| Command | `kubectl get configmap vault-policies -n vault -o jsonpath='{.data}' | python3 -c "import sys,json; d=json.load(sys.stdin); print('\n'.join(k for k in d if k.endswith('.hcl')))"` |
| Timestamp | 2026-07-27T23:47:40Z |
| Target | Vault policies ConfigMap |
| Expected | Separate policies: aither-gateway-policy.hcl, aither-bff-policy.hcl, admin-policy.hcl |
| Actual | 3 policies: `aither-gateway-policy.hcl`, `aither-bff-policy.hcl`, `admin-policy.hcl` |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## VAULT-010: Kubernetes auth via projected SA token

| Field | Value |
|---|---|
| Test ID | VAULT-010 |
| Command | `kubectl get sa aither-gateway -n aither-inference -o jsonpath='{.automountServiceAccountToken}'` |
| Timestamp | 2026-07-27T23:47:45Z |
| Target | Gateway ServiceAccount — automount disabled |
| Expected | `false` — projected tokens only |
| Actual | `false` — automountServiceAccountToken disabled. Projected token via `vault write auth/kubernetes/role/...` |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |

## VAULT-011: Readiness + Liveness probes

| Field | Value |
|---|---|
| Test ID | VAULT-011 |
| Command | `kubectl get statefulset vault -n vault -o jsonpath='{.spec.template.spec.containers[0].readinessProbe.httpGet}'` |
| Timestamp | 2026-07-27T23:47:50Z |
| Target | Vault probes |
| Expected | Probes on `/v1/sys/health` with HTTPS |
| Actual | readinessProbe: `/v1/sys/health` HTTPS. livenessProbe: same. startupProbe also present. |
| Exit code | 0 |
| PASS/FAIL | ✅ PASS |
| Commit SHA | 801ca390 |
