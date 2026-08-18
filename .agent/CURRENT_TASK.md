# TASK: AITHER-MVP-E1-FINAL-ACCEPTANCE-R1

## Goal
Close the remaining autonomously verifiable portion of roadmap item E1 by performing a strict read-only final security acceptance audit. Produce a single evidence document covering the outstanding E1 acceptance artifacts: Acceptance Matrix, Behavioral Compliance Checklist, fresh-clone reproducibility assessment, placeholder/secret scan, and final gate conclusion.

## Baseline
- Repository: `dedvmedved-dot/aither-project`
- Branch: `aither-v2`
- Baseline SHA: `28ddccd02fa9ef28086f8565681f4a5dbd4a9488`
- GitHub is Source of Truth.
- Prior accepted governance finalization: `AITHER-MVP-GOV-R2-FINALIZE-R1` = PASS / CONNECTOR VERIFIED / ACCEPTED.

## Critical behavior requirements
1. This task is READ-ONLY with respect to runtime, Kubernetes, databases, services, host configuration, secrets, scheduler, runner, H2 bridge, Telegram gateway, and `/root/.hermes`.
2. The ONLY repository path Hermes may create/modify is `docs/evidence/E1_FINAL_ACCEPTANCE_R1.md`.
3. Hermes MUST NOT run `git add`, `git commit`, `git push`, `git reset`, `git clean`, `git checkout`, `git switch`, `git merge`, `git rebase`, `git tag`, or any command that changes refs/index/history. Read-only git commands are allowed.
4. `network_git=false` is binding. Host runner alone stages, commits, pushes, and writes `.agent/EXECUTION_RESULT.json`.
5. Do not modify `.agent/*`, ROADMAP, manifests, source code, tests, configuration, or documentation other than the one evidence file.
6. Never print secret values. Scan for placeholders/secrets using names/patterns only; redact any accidental value immediately and mark the affected check FAIL/BLOCKED.
7. Do not claim PASS from historical reports alone where direct repository verification is possible. Re-check the current baseline.
8. If a check cannot be completed read-only, mark it BLOCKED with the exact reason. Do not improvise or widen scope.

## Required verification

### A. E1 Acceptance Matrix
Build a matrix for the remaining E1/R6 closure requirements. At minimum include:
- authentication/authorization boundaries;
- internal endpoint protection;
- model access/scope enforcement;
- API-key lifecycle and scope restrictions;
- session invalidation / credential rotation evidence already present in Git;
- BFF/model-switch race or equivalent historical blocker closure;
- secret handling / no embedded production credentials;
- acceptance evidence traceability.

For each row provide: requirement, current evidence path/commit, verification performed now, result PASS/PARTIAL/BLOCKED/FAIL.

### B. Behavioral Compliance Checklist
Create a concise checklist that proves the current repository contract does not regress accepted behavior. Use current source/tests/docs only. Include negative-path expectations where represented in the repository (forbidden/internal access, wrong secret/token, scope denial, invalid/expired credential behavior).

### C. Fresh-clone reproducibility assessment
Without changing the repository or installing packages:
- inspect bootstrap/deployment/test documentation and scripts needed to reproduce the accepted system from a fresh clone;
- verify referenced paths exist;
- identify stale, missing, environment-specific, or non-reproducible steps;
- distinguish a true blocker from an external dependency.
Do NOT actually redeploy the production system.

### D. Placeholder / secret scan
Perform a repository-wide read-only scan appropriate to the current checkout for:
- obvious credential placeholders (`TODO`, `CHANGEME`, example passwords/tokens, unresolved secret markers);
- accidental hard-coded secrets/private keys/tokens;
- legacy model names/config drift where it materially affects security acceptance.
Do not output any discovered secret value. Report path + category only.

### E. Final E1 gate
State whether the autonomously verifiable E1 portion can be closed on the current baseline.
PASS requires:
- no unresolved security-critical repository blocker found in A-D;
- no secret exposure;
- acceptance matrix and behavioral checklist complete enough to trace all E1 closure claims;
- fresh-clone assessment has no security-critical undocumented gap.
If not, state exact remaining blockers and the narrow next corrective action.

## Required evidence conclusion
The file must end with:
- `TASK_ID: AITHER-MVP-E1-FINAL-ACCEPTANCE-R1`
- `BASELINE_SHA: 28ddccd02fa9ef28086f8565681f4a5dbd4a9488`
- `E1_ACCEPTANCE_MATRIX: PASS|PARTIAL|BLOCKED|FAIL`
- `BEHAVIORAL_COMPLIANCE: PASS|PARTIAL|BLOCKED|FAIL`
- `FRESH_CLONE_ASSESSMENT: PASS|PARTIAL|BLOCKED|FAIL`
- `PLACEHOLDER_SECRET_SCAN: PASS|PARTIAL|BLOCKED|FAIL`
- `E1_FINAL_GATE: PASS|PARTIAL|BLOCKED|FAIL`
- `HERMES_GIT_WRITE_USED: NO`
- `RUNTIME_MUTATIONS: NO`
- `SECRET_VALUES_PRINTED: NO`
- `SECRETS_EXPOSED: NO`

## Acceptance
Hermes writes exactly one evidence file and STOPs. Host runner must then validate the one allowed path, write a fresh PASS/FAIL `.agent/EXECUTION_RESULT.json`, commit with `security: verify E1 final acceptance gate`, push, and leave a clean worktree. Only ChatGPT Architect may assign CONNECTOR VERIFIED / ACCEPTED after independent audit.
