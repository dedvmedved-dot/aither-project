# Internet 32B — Stability Tests

**Date:** 2026-07-24  
**Test:** 10 sequential POST /v1/chat/completions (model=qwen-32b-gptq) per route  
**API Key:** aither_e38bd264_... (U1.2 test key)

## Results

### Internet :443 (fb1.spb.ru)

| # | Timestamp (UTC) | HTTP | Time | Status |
|---|---|---|---|---|
| 1 | 18:34:53 | 200 | 5.43s | ✅ |
| 2 | 18:34:58 | 200 | 5.43s | ✅ |
| 3 | 18:35:04 | 200 | 5.42s | ✅ |
| 4 | 18:35:09 | 200 | 5.43s | ✅ |
| 5 | 18:35:15 | 504 | 35.05s | ❌ |
| 6 | 18:35:50 | 504 | 35.02s | ❌ |
| 7 | 18:36:25 | 504 | 35.04s | ❌ |
| 8 | 18:37:00 | 504 | 35.05s | ❌ |
| 9 | 18:37:35 | 504 | 35.04s | ❌ |
| 10 | 18:38:10 | 504 | 35.14s | ❌ |

**Result: 4/10 PASS** ❌ (below 10/10 target)

### Internet :10443 (fb1.spb.ru:10443)

| # | Timestamp (UTC) | HTTP | Time | Status |
|---|---|---|---|---|
| 1 | 18:38:45 | 000 | 45.00s | ❌ |
| 2 | 18:39:30 | 504 | 5.10s | ❌ |
| 3 | 18:39:35 | 200 | 5.42s | ✅ |
| 4 | 18:39:41 | 200 | 5.42s | ✅ |
| 5 | 18:39:46 | 200 | 5.42s | ✅ |
| 6 | 18:39:52 | 200 | 5.42s | ✅ |
| 7 | 18:39:57 | 504 | 10.24s | ❌ |
| 8 | 18:40:07 | 504 | 5.10s | ❌ |
| 9 | 18:40:12 | 200 | 5.42s | ✅ |
| 10 | 18:40:18 | 200 | 5.42s | ✅ |

**Result: 6/10 PASS** ❌ (below 10/10 target)

### Test Zone :30902 (10.129.13.78 direct)

| # | Timestamp (UTC) | HTTP | Time | Status |
|---|---|---|---|---|
| 1 | 18:40:23 | 200 | 0.39s | ✅ |
| 2 | 18:40:24 | 200 | 0.39s | ✅ |
| 3 | 18:40:24 | 200 | 0.39s | ✅ |
| 4 | 18:40:24 | 200 | 0.39s | ✅ |
| 5 | 18:40:25 | 200 | 0.39s | ✅ |
| 6 | 18:40:25 | 200 | 0.39s | ✅ |
| 7 | 18:40:26 | 200 | 0.39s | ✅ |
| 8 | 18:40:26 | 200 | 0.39s | ✅ |
| 9 | 18:40:26 | 200 | 0.39s | ✅ |
| 10 | 18:40:27 | 200 | 0.39s | ✅ |

**Result: 10/10 PASS** ✅

## Summary

| Route | Pass Rate | Status |
|---|---|---|
| Internet :443 | 4/10 | ❌ |
| Internet :10443 | 6/10 | ❌ |
| Test Zone :30902 | 10/10 | ✅ |

**Stability criterion (10/10) NOT MET for Internet routes.**  
Root cause: Cisco VPN tunnel intermittent connectivity between VPS2 and n8:30902.
