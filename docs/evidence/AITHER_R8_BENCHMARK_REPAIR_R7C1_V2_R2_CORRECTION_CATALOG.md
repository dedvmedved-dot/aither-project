# Aither — R7-C1 v2-R2 Correction Catalog

TASK: `AITHER-HERMES-R8-BENCHMARK-REPAIR-R7C1-V2-R2`
SOURCE: GitHub Connector audit of v2-R1 (`b02e204`) — `R7C1_V2_R2_CORRECTION_REQUIRED`.

## R2-1 — Scenario-specific semantic relevance (FIXED)

v2-R1 used domain-wide operation-type sets, so `systemctl_status(postgresql)` in the
nginx scenario (LIN-01) was scored `RELEVANT_NEGATIVE` merely because `service_status`
belongs to the Linux domain.

Fix: each scenario now defines explicit `relevance_rules` — typed operations with
explicit `ANY` wildcards. A caller operation is:
- `RELEVANT_REVEAL` if it matches an evidence operation;
- `RELEVANT_NEGATIVE` if it matches a scenario relevance rule;
- `IRRELEVANT` otherwise.

LIN-01 now: `systemctl_status(nginx)`→REVEAL, `ss -ltnp`→RELEVANT_NEGATIVE,
`systemctl_status(postgresql)`→IRRELEVANT, `git_status(app)`→IRRELEVANT.

## R2-2 — Match all significant operation dimensions (FIXED)

The operation-dimension audit disagreed with the code: `psql_query` matched every query,
`docker_exec_dns` ignored hostname, `docker_build` ignored path.

Fix: `psql_query` now compares canonical SQL (lowercase/collapsed); `docker_exec_dns`
matches container AND hostname (host wildcard only when evidence declares it);
`docker_build` matches tag AND path (path wildcard only when evidence declares it).
Wildcards are explicit evidence-side data (`*` / `ANY`), not hard-coded omission.

An executable operation-dimension audit (82 tests) now verifies every typed matcher:
exact match, per-field mutation mismatch, and explicit wildcard behaviour.
`SIGNIFICANT_FIELDS_SILENTLY_IGNORED = 0`.
