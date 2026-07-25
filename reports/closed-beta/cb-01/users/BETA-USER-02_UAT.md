# BETA-USER-02 UAT Report

**Key prefix:** aither_d8638ae8
**Date:** 2026-07-25 00:53–00:58 UTC

## UAT-01: Authentication (Valid)
```
GET /v1/models + valid Bearer token
→ HTTP 200
Status: ✅ PASS
```

## UAT-02: Models List
```
GET /v1/models → HTTP 200, 2 models
Status: ✅ PASS
```

## UAT-03: 14B Chat
```
POST /v1/chat/completions (qwen-14b)
→ HTTP 200, "Здравствуйте (Zdravstvuyte)"
Status: ✅ PASS
```

## UAT-04: 32B Base
```
POST /v1/chat/completions (qwen-32b-base) → HTTP 200
→ Base model completion text
Status: ✅ PARTIAL (v1/completions → 404)
```

## UAT-05: Invalid Authentication
```
→ HTTP 401
Status: ✅ PASS
```

## UAT-07: Repeated Use (10 sequential)
```
10/10 HTTP 200
Status: ✅ PASS
```

## UAT-08: User Feedback
Status: PENDING

## Summary
- **Passed:** 6/8
- **Partial:** 1/8
- **Pending:** 2/8 (UAT-06 inherited from U1, UAT-08)
