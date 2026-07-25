# CB-01 Access Validation

**Timestamp:** 2026-07-25 00:52–00:54 UTC

## Created API Keys

| User | Key Prefix | DB Status |
|---|---|---|
| BETA-USER-01 | aither_7dfc3372 | Inserted, active |
| BETA-USER-02 | aither_d8638ae8 | Inserted, active |
| BETA-USER-03 | aither_78f86855 | Inserted, active |
| BETA-USER-04 | aither_e42200f0 | Inserted, active |
| BETA-USER-05 | aither_2ef9f024 | Inserted, active |

## Validation Tests

### Valid Key Test (all 5 users)
```
BETA-USER-01: GET /v1/models → HTTP 200 ✅
BETA-USER-02: GET /v1/models → HTTP 200 ✅
BETA-USER-03: GET /v1/models → HTTP 200 ✅
BETA-USER-04: GET /v1/models → HTTP 200 ✅
BETA-USER-05: GET /v1/models → HTTP 200 ✅
```

### Invalid Key Test
```
Authorization: Bearer aither_deadbeef_invalid_key_here
→ HTTP 401 "Invalid API Key" ✅
```

### No Key Test
```
No Authorization header
→ HTTP 401 "Valid API Key required (format: aither_...)" ✅
```

### Wrong Format Test
```
Non-aither prefix key
→ HTTP 401 "Invalid API Key format" ✅
```

## Key Storage
- Full keys: /tmp/beta_keys_secure.txt (chmod 600, NOT in Git)
- DB storage: SHA-256 hashed only
- Key format: aither_XXXXXXXX_<48-char-urlsafe-secret>
