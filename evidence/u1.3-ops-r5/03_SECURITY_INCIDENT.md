# U1.3-OPS-R5 — Security Incident

**Incident ID:** AITHER-SEC-2026-U13-OPS-R5-001

**Detection source:** ChatGPT R4 external audit

**Affected repository:** dedvmedved-dot/aither-project

**Affected branch:** aither-v2

**Affected commits:** 9f570fc (R4 Commit E), 2dc6cbb (R4 Commit F)

**Affected credential classes:**
- BETA01 (E2E beta user)
- BETA02 (E2E beta user)
- OWNER (admin)

**Potentially affected key files:**
- portal/delegation/private.pem (untracked, RSA 2048, in .gitignore)
- portal/delegation-private.pem (untracked, identical RSA 2048, in .gitignore)

**Initial severity:** CRITICAL

**Containment status:** COMPLETE

**Credential rotation:** COMPLETE (BETA01, BETA02, OWNER)

**Session invalidation:** COMPLETE (BFF restart with new SESSION_SECRET)

**Private key investigation:** COMPLETE
- Both files identical (SHA256: 32f033dc...)
- RSA 2048-bit, unencrypted
- Referenced in docs for Portal BFF delegation JWT signing
- Already in .gitignore since R3
- No active K8S mounts found
- Files removed from current tree (Commit G)

**History rewrite:** NOT PERFORMED

**User impact:** Controlled Beta blocked

**Owner:** Hermes implementation / ChatGPT acceptance
