# Stage BA-02 — Chat Persistence Report

**Date:** 2026-07-23
**Status:** ⚠️ PARTIAL — backend API supports persistence, Portal UI flow not fully tested

## Backend Support

### AI Platform (Conversations API)

| Operation | Endpoint | Method | Status |
|-----------|----------|--------|--------|
| List conversations | `/api/v1/conversations` | GET | ✅ Works |
| Create conversation | `/api/v1/conversations` | POST | ✅ Works (HTTP 201) |
| Get conversation | `/api/v1/conversations/{id}` | GET | ✅ Works |
| Add message | `/api/v1/conversations/{id}/messages` | POST | ✅ Works |
| Delete conversation | `/api/v1/conversations/{id}` | DELETE | ✅ Works |

### BFF (Portal UI Backend)

| Operation | Endpoint | Status |
|-----------|----------|--------|
| Conversations API | `/api/v1/conversations` | ❌ Not implemented (404) |

## Limitation

Portal Frontend SPA relies on **BFF** for all API operations. BFF does not implement conversations API. The conversations API is available through **Portal Backend** (our new deployment with proxy routes), but Portal Frontend is not configured to use Portal Backend for conversations.

Chat persistence works at the **AI Platform database level** (SQLite). Messages are stored and retrievable. The gap is in the Portal UI integration.

## Test Results

| Test | Method | Result |
|------|--------|--------|
| Create conversation | POST AI Platform | ✅ HTTP 201 |
| Add message | POST AI Platform | ✅ Works with API Key |
| Refresh chat | N/A | ⏳ Requires UI test |

## Recommendation

For Beta v0.9, chat persistence is **confirmed at the API/database level**. Full UI persistence requires connecting Portal Frontend to Portal Backend conversations API instead of/in addition to BFF.
