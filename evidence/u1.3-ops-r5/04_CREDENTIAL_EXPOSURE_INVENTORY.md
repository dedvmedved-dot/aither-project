# U1.3-OPS-R5 — Credential Exposure Inventory

| Credential | Purpose | Exposure Location | Status | Action |
|------------|---------|-------------------|--------|--------|
| BETA01 | E2E beta user | R4 evidence (logs/, junit/) | COMPROMISED | ROTATED |
| BETA02 | E2E beta user | R4 evidence (logs/, junit/) | COMPROMISED | ROTATED |
| OWNER | Owner/admin | R4 evidence (logs/, junit/) | COMPROMISED | ROTATED |

## R4 Credential Fingerprints (compromised)
```
E2E_BETA01_USERNAME: SHA256=a87e2a7fec189b6d1b739a68ea6364484ecbac142c4e54dad5e39262002534d4
E2E_BETA02_USERNAME: SHA256=10f83446e484dae4877fc1703ba93cc37a7420736457230945cfa4e23178b2fe
E2E_OWNER_USERNAME: SHA256=8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918
```

## R5 Rotated Fingerprints
```
E2E_BETA01_USERNAME: SHA256=a87e2a7fec189b6d1b739a68ea6364484ecbac142c4e54dad5e39262002534d4 (same username)
E2E_BETA02_USERNAME: SHA256=10f83446e484dae4877fc1703ba93cc37a7420736457230945cfa4e23178b2fe (same username)
E2E_OWNER_USERNAME: SHA256=44dd68aa87e01b70a80700495b75c1ce55c3ec8406e677dbccddeeb5975f6de6 (NEW: owner-r5)
```
Passwords fully rotated; hashes differ from R4.
