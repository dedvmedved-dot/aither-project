# Stage BA-02 — API Key Isolation Report

**Date:** 2026-07-23
**Status:** ✅ PASSED

## API Key Architecture

Aither uses **bearer token** model for API keys. API Key format: `aither_<random_prefix>_<random_suffix>`. Keys are hashed (SHA-256) before storage — raw keys are not persisted.

## API Key Validation Results

| Test | Endpoint | Expected | Actual | Result |
|------|----------|----------|--------|--------|
| No API Key | `POST /v1/chat/completions` | HTTP 401 | HTTP 401 | ✅ PASS |
| Invalid API Key | `POST /v1/chat/completions` | HTTP 401 | HTTP 401 | ✅ PASS |
| Valid API Key | `POST /v1/chat/completions` | HTTP 200 | HTTP 200 | ✅ PASS |

## API Key Lifecycle (via AI Platform)

| Operation | Method | Endpoint | Status |
|-----------|--------|----------|--------|
| Create key | POST | `/api/v1/api-keys` | ✅ Works (returns full key once) |
| List keys | GET | `/api/v1/api-keys` | ✅ Works (prefix + metadata only) |
| Revoke key | DELETE | `/api/v1/api-keys/{id}` | ✅ Works (sets revoked_at) |
| Use revoked key | POST | `/v1/chat/completions` | ✅ Returns 401 |

## Key Isolation Model

Aither uses a **shared-tenant** model for MVP:
- API Keys are not scoped per user — any valid key can access any enabled model
- Key ownership is tracked (user_id, name) but does not restrict model access
- User A **cannot see** User B's keys in the portal
- User A **cannot revoke** User B's keys
- Revoked keys stop working immediately for all users

This is by design for Beta v0.9. Per-user key scoping is a post-MVP feature.

## Evidence

The test API Key used:
```
[REDACTED-API-KEY]1hpDwqR5gcn1p
```
Created via `POST /api/v1/api-keys` with JWT admin token. Full key shown once only.
