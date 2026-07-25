# CB-01 Access Provisioning

**Date:** 2026-07-25 01:00 UTC

---

## Provisioning Process

Each beta user received a personal API key generated via `aither-ai-platform` pod with the standard `generate_api_key()` function.

### Key Creation Method
```python
raw_secret = secrets.token_urlsafe(48)
hex_part = secrets.token_hex(4)
full_key = f"aither_{hex_part}_{raw_secret}"
key_prefix = f"aither_{hex_part}"
key_hash = hashlib.sha256(full_key.encode()).hexdigest()
```

### Schema: aither_XXXX_<48-char-urlsafe-secret>

---

## Access Validation Matrix

| ID | Key Prefix | Created | Delivered | Activated | Validated | Status |
|---|---|---|---|---|---|---|
| BETA-USER-01 | aither_7dfc3372 | ✅ | PENDING* | ✅ | ✅ | CREATED |
| BETA-USER-02 | aither_d8638ae8 | ✅ | PENDING* | ✅ | ✅ | CREATED |
| BETA-USER-03 | aither_78f86855 | ✅ | PENDING* | ✅ | ✅ | CREATED |
| BETA-USER-04 | aither_e42200f0 | ✅ | PENDING* | ✅ | ✅ | CREATED |
| BETA-USER-05 | aither_2ef9f024 | ✅ | PENDING* | ✅ | ✅ | CREATED |

*Delivery pending assignment of actual internal users.

---

## Security Tests

| Test | Expected | Actual | Status |
|---|---|---|---|
| Valid key → /v1/models | HTTP 200 | HTTP 200 | ✅ PASS |
| Invalid key → /v1/models | HTTP 401 | HTTP 401 "Invalid API Key" | ✅ PASS |
| No key → /v1/models | HTTP 401 | HTTP 401 "Valid API Key required" | ✅ PASS |
| Wrong format key → /v1/models | HTTP 401 | HTTP 401 "Invalid API Key format" | ✅ PASS |
| Key isolation (user1 ≠ user2) | Separate keys | 5 unique keys created | ✅ PASS |

---

## Key Management

- **Full keys stored ONLY in:** `/tmp/beta_keys_secure.txt` (chmod 600, NOT in Git)
- **In Git:** Only key prefixes (aither_XXXXXXXX)
- **Revocation:** Via `DELETE /api/v1/api-keys/{id}` or direct DB update
- **No shared keys:** Each user has a unique key

---

**Status: CREATED — All 5 keys created, validated, pending user assignment.**
---
*Evidence: reports/closed-beta/cb-01/04_ACCESS_VALIDATION.md*
