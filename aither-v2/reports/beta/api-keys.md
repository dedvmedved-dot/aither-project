# Beta Acceptance — API Keys Report

**Date:** 2026-07-23
**Source:** Hermes Agent (Stage BA-01)
**Method:** SSH to n8 → curl to AI Platform API

## API Key Lifecycle Tests

### Test 1: Create API Key

| Check | Result |
|-------|--------|
| Endpoint | `POST /api/v1/api-keys` (via AI Platform) |
| Auth | JWT bearer token (admin) |
| HTTP Status | ✅ **201** |
| Response includes `full_key` | ✅ `aither_aa101d5b_eFQMBBouKkHmjU4tM1nvCJWkquhfxeRIo5gQtd7DlvW9EcT0Bjt8d7dqxQvYAotd` |
| Response includes `key_prefix` | ✅ `aither_aa101d5b` |
| Warning shown | ✅ "Save this key — it will not be shown again" |

### Test 2: List API Keys

| Check | Result |
|-------|--------|
| Endpoint | `GET /api/v1/api-keys` |
| Auth | JWT bearer token |
| HTTP Status | ✅ **200** |
| Shows prefix only (not full key) | ✅ `key_prefix: "aither_aa101d5b"` |
| Shows status | ✅ `revoked_at: null` (active) |

### Test 3: Revoke API Key

| Check | Result |
|-------|--------|
| Endpoint | `DELETE /api/v1/api-keys/1` |
| Auth | JWT bearer token |
| HTTP Status | ✅ **200** |
| Response | ✅ `{"message":"API Key id=1 revoked"}` |
| After revoke, `revoked_at` set | ✅ Timestamp present |
| After revoke, prefix still visible | ✅ Key still listed with revoked status |

### Test 4: Create Without Auth

| Check | Result |
|-------|--------|
| Endpoint | `POST /api/v1/api-keys` |
| Auth | ❌ **None** |
| HTTP Status | ✅ **401** |
| Response | ✅ `{"detail":"Authentication required"}` |

### Test 5: Create Second Key (After Revoke)

| Check | Result |
|-------|--------|
| Endpoint | `POST /api/v1/api-keys` |
| Auth | JWT bearer token |
| HTTP Status | ✅ **201** |
| New key generated | ✅ `aither_8bc5186f_6BVbA0ZIVEZ9PmG-S2guZ8Kujy2ogWlSHrt2FWgu4MY6bB9nVjrqsDPOd6LOWXvg` |
| Prefix unique | ✅ `aither_8bc5186f` (different from first) |

## Gateway Auth

| Gateway Endpoint | Method | Behaviour | Auth Mechanism | Notes |
|-----------------|--------|-----------|---------------|-------|
| `/v1/completions` | nginx → vLLM | Proxied to vLLM (32B GPTQ) | ❌ **None at nginx level** | Auth delegated to AI Platform service |
| `/v1/chat/completions` | nginx | Blocked (422) | N/A | Gateway for 32B Base model — no chat |
| `/health` | nginx → vLLM | Open | ❌ None | Public health endpoint |
| `/v1/models` | nginx → vLLM | Open | ❌ None | Public model list |
| `/healthz` | nginx built-in | Open | ❌ None | Internal health check |

**Finding:** The Gateway (nginx-gateway-32b) does not implement API Key validation. According to ARCHITECTURE.md, API Key authentication is handled at the AI Platform service level, not the Gateway. This is by design — the Gateway is a thin proxy to vLLM, and client-facing API Key validation happens in the AI Platform service.

## Verdict

```text
API KEYS:
  Create:        ✅ PASS
  List:          ✅ PASS
  Revoke:        ✅ PASS
  Re-create:     ✅ PASS
  No auth → 401: ✅ PASS
  ALL TESTS:     PASS

GATEWAY AUTH:
  Auth at Gateway level: ⚠️ NOT IMPLEMENTED (by design)
  Auth at AI Platform:   ✅ Expected (to be tested in OpenAI Compatibility)
```
