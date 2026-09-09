# Aither — R7-C1 v2-R3-R1 Micro-Correction Catalog

TASK: `AITHER-HERMES-R8-BENCHMARK-REPAIR-R7C1-V2-R3-R1`
SOURCE: GitHub Connector audit of v2-R3 (`473e313`) — blocker `CON-03 EVIDENCE-SIDE HOST WILDCARD FALSE-POSITIVE`.

## CON-03 evidence-side host wildcard false-positive (FIXED)

v1 CON-03 key `docker exec app nslookup` is under-specified (hostname missing), but the
canonical evidence text `server can't find db.internal: NXDOMAIN` explicitly names
`db.internal`. R3 converted this to `docker_exec_dns(container="app", host="*")`, whose
matcher treated evidence-side `host="*"` as matching any hostname — a direct
false-positive evidence leak.

Fix:
- `EVIDENCE_CORRECTIONS = {("CON-03","E1"): {"host":"db.internal"}}` (explicit migration map,
  no free-text regex).
- Relevance rule: `docker_exec_dns(container="app", host="db.internal")` (no host wildcard).
- Reverse mapping: `docker_exec_dns(container="app", host="db.internal")` → `docker exec app nslookup db.internal`.

Verification: 6/6 CON-03 tests, `CON03_FALSE_EVIDENCE_REVEALS = 0`.

## Portability (FIXED)

Removed hard-coded absolute harness path from the converter and test runners; replaced with
script-relative resolution (`os.path.dirname(os.path.abspath(__file__))`).
`ABSOLUTE_ROOT_HARNESS_DEPENDENCY = NO`.
