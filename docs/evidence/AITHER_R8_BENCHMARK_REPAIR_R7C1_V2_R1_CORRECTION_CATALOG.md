# Aither — R7-C1 v2-R1 Correction Catalog

TASK: `AITHER-HERMES-R8-BENCHMARK-REPAIR-R7C1-V2-R1`
SOURCE: independent GitHub Connector audit of commit `bd534bc` (R7C1_V2_CORRECTION_REQUIRED).

Each blocker below is fixed in this task with deterministic tests.

## R1-1 — Evidence provenance enforcement (FIXED)

`score_final` accepted `fj["evidence_ids"]` without proving they were actually revealed by
the simulator. An agent could claim valid IDs (E1, E2) without ever obtaining them.

Fix: credited evidence = `claimed ∩ valid ∩ revealed`. Metrics recorded:
`claimed_evidence_ids`, `valid_claimed_ids`, `revealed_evidence_ids`,
`credited_evidence_ids`, `unrevealed_claimed_ids`, `fabricated_claimed_ids`.

## R1-2 — Service normalization (FIXED)

`rstrip(".service")` removed trailing chars from the character SET `.service`, corrupting
`worker`→`work`, `docker`→`dock`, `redis`→`red`, `service`→"".

Fix: exact suffix `endswith(".service")` + slice. `nginx.service`→`nginx`, `worker`→`worker`.

## R1-3 — Kubernetes namespace semantics (FIXED)

Converter forced `namespace="default"`, corrupting K8S-01 ("Pod web in prod") to `default`.

Fix: deterministic namespace extraction (explicit prompt "in <ns>" + documented normative
map). K8S-01 → `prod`. No silent default corruption; unknown → `default` (documented).

## R1-4 — Alternative diagnostic semantics (FIXED)

`ss`/`netstat` port-listener diagnostics were `UNSUPPORTED_SEMANTIC_OPERATION`.

Fix: `SocketListeners(port=None|int)` operation family; `ss -ltnp`, `ss -tlnp`,
`netstat -ltnp`, `... | grep ':80'` parse deterministically. See ALTERNATIVE_DIAGNOSTICS.md.

## R1-5 — Semantic relevance (FIXED)

Relevance fell back to `tool in evidence_tools` (tool-presence).

Fix: explicit `relevant_operation_types` per scenario (domain diagnostic family ∪ evidence
op types). Relevance is now semantic; a different tool with a valid diagnostic intent is
RELEVANT_NEGATIVE, not IRRELEVANT. `read_file` vs shell `cat` unified (both read file content).

## R1-6 — Operation dimension audit (FIXED)

Matchers must not ignore semantically significant fields. Audited all operation types;
`docker_exec_dns.host` and `docker_build.path` are explicit wildcards (documented in the
operation dimension audit). `read_file`/`read_file_via_shell` unified on `path`; k8s ops
match on resource/pod AND namespace.
