# U1.3-OPS-R2 — 07_POD_RECREATION

**Date/Time (UTC):** 2026-07-26T02:19:36Z

## Procedure

Delete one BFF pod from the 2-replica deployment, verify replacement with different UID.

## Results

| Parameter | Value |
|-----------|-------|
| Old pod | aither-bff-75d9bf999c-9shpd |
| Old UID | e41b0191-89af-4ef1-adba-0c0650cc78fe |
| New pod | aither-bff-75d9bf999c-x5rgt |
| New UID | 8c68aa25-5fec-48b6-be63-ab8423b5a81d |
| UID different | YES (PASS) |
| Elapsed time | 31 seconds |
| Service available during | YES (2nd pod continued serving) |

## Verification

| Check | Result |
|-------|--------|
| Old pod deleted | ✓ |
| New pod created by same ReplicaSet | ✓ |
| New pod UID ≠ old UID | ✓ |
| Service health check passed | ✓ (200 OK) |
| Final available replicas | 2/2 |

## Pod Recreation: PASS

Raw log: `logs/07-pod-recreation.log`
