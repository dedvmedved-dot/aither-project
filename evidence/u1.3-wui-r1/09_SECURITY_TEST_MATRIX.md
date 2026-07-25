# U1.3-WUI-R1 — SECURITY TEST MATRIX

| ID | Requirement | Test | Status |
|----|-------------|------|--------|
| WUI-SEC-001 | No secrets in Git | secret-scan.txt | PENDING |
| WUI-SEC-002 | No secrets in JUnit XML | junit/ scan | PENDING |
| WUI-SEC-003 | One-time secret display | test_one_time_secret | PENDING |
| WUI-SEC-004 | Revoked key denial | test_revoke_denial | PENDING |
| WUI-SEC-005 | Owner isolation | test_r3_identities regression | PENDING |
| WUI-SEC-006 | Model scope enforcement | API key creation with model:14b:chat / model:32b:chat-adapter | VERIFIED |
| WUI-SEC-007 | No admin substitution in Web UI | Login via end-user credentials only | VERIFIED |
