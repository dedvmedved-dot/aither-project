# Stage 18B — Secret Lifecycle Validation

## Baseline Secret Metadata

| Field | Value |
|-------|-------|
| Name | `aither-identity-secret` |
| Namespace | `aither-inference` |
| UID | `4bfb16b9-7cee-46a4-9e5a-951a9195549b` |
| ResourceVersion (baseline) | `1289109` |

## Validation: Secret NOT in identity.yaml

```bash
grep -c 'kind: Secret' services/identity/k8s/identity.yaml
# Result: 0 — Secret resource removed from identity.yaml
```

## Validation: Example file exists

```bash
ls -la services/identity/k8s/identity-secret.example.yaml
# Result: File exists with REPLACE_ME placeholders
```

## Validation: Deploy script does NOT apply Secret

```bash
grep -n 'kubectl.*apply.*secret\|kubectl.*create.*secret' scripts/stage18a-deploy-services.sh
# Result: NO MATCHES — script does not create or apply secrets
```

## Validation: Deploy stops on missing Secret

From `scripts/stage18a-deploy-services.sh`:
```bash
if ! kubectl get secret aither-identity-secret -n "${NAMESPACE}" &>/dev/null; then
  echo "[deploy] ERROR: Secret 'aither-identity-secret' not found in namespace '${NAMESPACE}'"
  exit 1
fi
```

## Validation: No real secrets in repository

```bash
grep -RIn --exclude='*.example.yaml' --exclude-dir='.git' 'IDENTITY_SECRET_KEY\|IDENTITY_ADMIN_PASS' .
# Result: Only identity.yaml contains environment variable names (env var references, not values)
```

## Post-Deployment Secret Verification

After deployment (see DEPLOYMENT-REPRODUCIBILITY.md), Secret was verified:
- **UID unchanged:** `4bfb16b9-7cee-46a4-9e5a-951a9195549b` ✅
- **ResourceVersion may increment** due to metadata changes (not data)
- **Real Secret values never logged or saved to files**

## Repository Secret Scan

```bash
grep -RInE '(password|passwd|secret|token|api[_-]?key|private[_-]?key)' \
  docs/stage18b scripts --exclude-dir='.git'
# Result: Only references to "Secret" resource name or documentation — NO real secrets
```
