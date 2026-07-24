# API Key Security Report

**Stage:** BA-02R  
**Date:** 2026-07-23  
**Author:** Hermes + DeepSeek  

## Test Results

| # | Test | Method | Result | Evidence |
|---|------|--------|--------|----------|
| 1 | Create API Key (admin) | POST /api/v1/api-keys | ✅ 201 | Full key returned once |
| 2 | List API Keys | GET /api/v1/api-keys | ✅ 200 | All user's keys listed (prefix only) |
| 3 | OpenAI via Bearer (full key) | POST /v1/chat/completions | ✅ 200 | Valid AI response |
| 4 | OpenAI via X-API-Key header | POST /v1/chat/completions | ✅ 200 | Valid AI response |
| 5 | Revoke API Key | DELETE /api/v1/api-keys/{id} | ✅ 200 | "API Key id=N revoked" |
| 6 | Use revoked key | POST /v1/chat/completions | ✅ 401 | "API Key has been revoked" |

## Key Format

```
aither_{8_hex_chars}_{48_urlsafe_chars}
Example: aither_d4108e4f_kMLj... (64+ chars total)
```

## Security Properties

| Property | Status | Implementation |
|----------|--------|---------------|
| Full key returned once | ✅ | Only on creation, then SHA256-hashed in DB |
| Key prefix only in listing | ✅ | Prefix + status, no secret stored |
| SHA256 hash storage | ✅ | `hashlib.sha256(full_key.encode()).hexdigest()` |
| API Key not recoverable | ✅ | Only hash stored; brute-force infeasible |
| Revocation | ✅ | Sets `revoked_at` timestamp; checked on every request |
| Expiration | ✅ | `expires_at` field available (not used in Beta) |
| Per-user isolation | ✅ | Keys filtered by `user_id` in SQL queries |
| Cross-user isolation | ✅ | Cannot list/delete another user's keys (SQL filter by user_id) |

## Auth Flow

```
User → Portal Backend login → JWT
User → Create API Key (via JWT) → AI Platform → returns full_key
User → Use API Key → AI Platform:
  1. Parse prefix (aither_{8hex})
  2. SHA256 hash full key
  3. Lookup by prefix + hash in DB
  4. Check revoked_at, expires_at
  5. Update last_used_at
  6. Return user info
```

## Vulnerability Assessment

| Issue | Severity | Notes |
|-------|----------|-------|
| No rate limiting on key validation | Low | Could be used in brute force (Mitigated by SHA256 + prefix lookup) |
| Key stored in request logs | Medium | Ensure logs don't capture Authorization header |
| No key rotation | Low | Manual revoke+create required |
| Admin key in env var | Low | `AI_PLATFORM_GATEWAY_API_KEY` stored in K8s Secret (base64) |

## Conclusion

**✅ API Key security is properly implemented.** Key lifecycle (create → use → revoke) works correctly. Isolation between users is enforced at DB level.
