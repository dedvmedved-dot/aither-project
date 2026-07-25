# Security Incident Report — INC-2026-TRACK-A-PRIVATE-KEY

**Incident ID:** INC-2026-TRACK-A-PRIVATE-KEY
**Severity:** CRITICAL
**Status:** CLOSED (Remediated)
**Date Published:** 2026-07-10
**Date Detected:** 2026-07-25
**Date Remediated:** 2026-07-25
**Detected By:** ChatGPT External Audit (GitHub Connector)
**Remediated By:** Hermes + DeepSeek
**Repository:** dedvmedved-dot/aither-project
**Branch:** aither-v2

---

## 1. Executive Summary

A delegation RSA-2048 private key (`portal/delegation-private.pem`) was accidentally committed to the Git repository on 2026-07-10 and remained in Git history until detected during external audit on 2026-07-25. The key was used to sign JWT delegation tokens (RS256 algorithm) for the Aither Portal's organization delegation feature. Previous remediation (commit `9a3ae81`) only removed the files from the current tree but did not clean Git history, leaving the key accessible in historical commits.

## 2. Affected Assets

| Asset | Path | Type | Introduced In |
|-------|------|------|---------------|
| Delegation private key | `portal/delegation-private.pem` | RSA-2048 Private Key | `d208621` (2026-07-10) |
| Delegation private key | `portal/delegation/private.pem` | RSA-2048 Private Key (copy) | `d208621` (2026-07-10) |

## 3. Purpose of Compromised Key

The key was used by the Aither Portal to sign JWT delegation tokens:

```typescript
// portal/server.ts, line 860
const delegationToken = jwt.sign(
  { org_id: orgId, key_id: k.rows[0].key_id, user_id: p.user_id },
  DELEGATION_PRIVATE_KEY,
  { algorithm: "RS256", expiresIn: "5m", issuer: "aither-portal" }
);
```

**Impact:** An attacker with this key could forge valid delegation tokens, gaining unauthorized access to any organization's API keys and AI platform resources through the Portal.

## 4. Timeline

| Time (UTC) | Event |
|------------|-------|
| 2026-07-10 00:53 | Private key committed in `d208621` (`portal/delegation-private.pem`) |
| 2026-07-10 00:53 | Private key copy committed (`portal/delegation/private.pem`) |
| 2026-07-25 04:39 | Files removed from working tree in commit `9a3ae81` (incomplete remediation) |
| 2026-07-25 | External audit detects key in Git history |
| 2026-07-25 | Incident documented, key rotated, history cleaned |

## 5. Containment Actions

1. New RSA-2048 key pair generated outside Git (`/root/.aither-delegation-keys/`)
2. Old public key fingerprint: `sha256:c29a51981e0b6ac3ad895a872c5e329e9ffbba9cf16ab5f9a7de00ecdf5c263a`
3. New public key fingerprint: `sha256:e4717c377b5613c3ad2aa6201839926d7b0e81b37552b159920aaa62ba5ce623`
4. Old keys removed from all trust stores and K8s Secrets
5. New keys deployed via protected storage (not in Git)

## 6. Eradication Actions

1. Git history cleaned using `git filter-repo` — all private key blobs purged
2. Old private key files removed from all branches and tags
3. GitHub caches, releases, and artifacts checked for key exposure
4. All collaborators notified: fresh clone required

## 7. Recovery Actions

1. New delegation key generated and deployed
2. Portal code updated to load key from K8s Secret / environment (not files)
3. Dependent services restarted with new key
4. Verification: old key rejected, new key accepted
5. Delegation token signing confirmed working with new key

## 8. Preventive Measures

1. `*.pem` added to `.gitignore`
2. Pre-commit hook: Gitleaks secret scanning
3. CI job: secret scan on every push
4. Git history scan: TruffleHog baseline established
5. Policy: private keys stored only in K8s Secrets / HashiCorp Vault / protected env vars
6. Policy: all PEM files in repo must be public keys only
7. Policy: `git rm` alone is insufficient for secret removal — full history cleanup required

## 9. Lessons Learned

1. `git rm` removes files from the current tree but NOT from Git history
2. Secret scanning must cover full history, not just the current working tree
3. Pre-commit hooks are essential to prevent secret commits
4. External audits should include Git history inspection for sensitive files
5. Key rotation must happen before declaring an incident closed

## 10. Verification

| Check | Result |
|-------|--------|
| Private keys in current tree | 0 ✅ |
| Private keys in full Git history | 0 ✅ |
| Old key accepted by Portal | NO ✅ |
| New key accepted by Portal | YES ✅ |
| `git filter-repo` executed | YES ✅ |
| Fresh clone verified clean | YES ✅ |
| Secret scan (current) | PASS ✅ |
| Secret scan (full history) | PASS ✅ |
| Pre-commit hook active | YES ✅ |
