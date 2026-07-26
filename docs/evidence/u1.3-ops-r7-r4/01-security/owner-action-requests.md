# U1.3-OPS-R7-R4 — Owner Action Requests

## OAR-001: BMC credentials (techvit)

- **Finding ID:** GITLEAKS-BMC-001
- **Credential type:** BMC (Baseboard Management Controller) login
- **Affected system:** Server BMC (bootsmam-k8s-clnt01-n7-gpu or related)
- **Safe fingerprint:** SHA-256 of credential redacted
- **Files:** `references/bmc-admin-rights-guide.md`, `references/openbmc-admin-guide.md`
- **Required Owner action:** Rotate BMC password for user `techvit` on affected server(s)
- **Reason Hermes cannot perform it:** No BMC access; requires physical/network BMC access with existing credentials
- **Required verification:** 
  1. Old BMC password (SHA-256: `9b7b2c3e...`) rejected by BMC
  2. New password works for BMC login
  3. Redact credentials from both reference files
- **Deadline:** Before final Critical Gate

## OAR-002: BMC credentials (techvirt)

- **Finding ID:** GITLEAKS-BMC-002
- **Credential type:** BMC login
- **Affected system:** Deployment target BMC
- **Safe fingerprint:** SHA-256 of credential redacted
- **File:** `manifests/deployment-plan.md`
- **Required Owner action:** Verify if `techvirt` account exists with a default/weak password; rotate/disable if active
- **Reason Hermes cannot perform it:** No BMC access
- **Required verification:**
  1. Confirm whether account is active
  2. If active: rotate password
  3. If inactive: document as historical artifact
  4. Redact from manifest
- **Deadline:** Before final Critical Gate

## OAR-003: JWT_SECRET verification

- **Finding ID:** GITLEAKS-JWT-001
- **Credential type:** JWT signing secret
- **Affected system:** VPS3 BFF wrapper
- **Safe fingerprint:** SHA-256 of value redacted
- **File:** `configs/vps3/bff-wrapper.sh` (redacted in Commit B)
- **Required Owner action:** Verify if the JWT secret (SHA-256: `d4e5f6a7...`) was ever used as production secret
- **Reason Hermes cannot perform it:** Cannot determine historical usage without access to VPS3 logs/configs
- **Required verification:**
  1. Confirm production JWT secret is different from this value
  2. If this value was ever active: rotate and document
  3. If never active: document as example/default
- **Deadline:** Before final Critical Gate

---

**Status:** AWAITING OWNER ACTION
**R7-R4 Directions blocked:** 13, 14, 15
