# TASK: SCOPE-Q25-D1-CMAP-PROVENANCE-AUDIT

## Objective
Perform a repository-only provenance audit for the ConfigMap/configuration artifacts relevant to SCOPE-Q25-D1 and the Qwen model/scope contract. This is the first real Aither task transported automatically through the accepted GitHub -> Host Supervisor -> Codex path.

## Hard scope
You may read the entire repository and read Git history/metadata. You may create or modify exactly one implementation artifact:

`evidence/scope-q25-d1/configmap-provenance-audit.md`

Do not modify application source, manifests, configuration, workflows, governance files, or any other evidence file.

## Required audit questions
1. Identify every repository artifact that plausibly defines, generates, patches, deploys, or documents the ConfigMap/configuration involved in SCOPE-Q25-D1.
2. Trace the provenance of those artifacts through Git history as far as repository evidence permits: relevant paths, commits, and relationships between source/configuration and deployment evidence.
3. Determine whether the repository supports the intended model/scope contract:
   - `qwen2.5-32b-instruct` -> `model:qwen2.5:chat`
   - `qwen3-32b` -> `model:qwen3:chat`
   - legacy `model:32b:chat` is transition-only, not a new default.
4. Treat `UPSTREAM_14B_*` only as a potentially stale variable name. Do not infer incorrect runtime routing solely from that name.
5. Separate facts proven by repository contents from runtime claims reported previously. Do not invent runtime evidence.
6. Identify gaps explicitly. If ConfigMap provenance cannot be fully proven from the repository, say exactly what is missing.

## Required report structure
The report must contain these headings exactly:
- `# SCOPE-Q25-D1 ConfigMap Provenance Audit`
- `## Scope`
- `## Evidence`
- `## Provenance Chain`
- `## Findings`
- `## Unresolved`
- `## Result`

Under `## Evidence`, cite concrete repository paths and commit SHAs when available. Under `## Result`, use only one of:
- `PASS` — repository provenance is sufficiently demonstrated for this audit scope;
- `FAIL` — repository evidence demonstrates a contradiction/defect;
- `INCONCLUSIVE` — repository evidence is insufficient to prove or disprove provenance.

Do not claim `SCOPE-Q25-D1 PASSED`; only Architect may accept the milestone after Connector verification and the separate WUI evidence gate.

## Prohibited
- no Kubernetes access;
- no deployment/runtime changes;
- no DB changes;
- no secrets;
- no package installation;
- no network Git;
- no Git commit/push from Codex;
- no application/configuration fixes;
- no WUI substitution with curl/API/CLI;
- no next task.

Return PASS/FAIL/BLOCKED for executor completion and STOP.
