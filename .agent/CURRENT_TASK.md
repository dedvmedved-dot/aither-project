# TASK: AITHER-MVP-GOV-R2-FINALIZE-R1

## Goal
Perform a narrow governance finalization audit for `AITHER-MVP-OPS-RC1-R2` after implementation commit `e51f06b3d38906ac1c3c33a0c2bf1f8516f3b4c1` appeared in GitHub without an R2 `.agent/EXECUTION_RESULT.json` update. Do not repeat OPS-RC1 implementation. Do not change Kubernetes/runtime. Do not change governance code.

## Baseline
- Branch: `aither-v2`
- Baseline SHA: `e51f06b3d38906ac1c3c33a0c2bf1f8516f3b4c1`
- R2 implementation commit is one commit ahead of Architect publication `d850f55a18c0370ea3a0e196c5043b0fc0ba6981`.
- Independent Architect audit confirmed that the R2 commit changed only exact R2-authorized implementation/evidence paths.
- Current anomaly: `.agent/EXECUTION_RESULT.json` still describes R1, while runner-live reports retry suppression for R2.

## Critical behavior requirements
1. GitHub is Source of Truth. Read `.agent/CURRENT_TASK.json`, this file, `.agent/host_task_runner.py`, and the relevant local git state before acting.
2. This is a governance-finalization audit only. Do not modify or redeploy any application, Kubernetes object, database, network, monitoring stack, backup job, CNI, model, portal, identity service, scheduler, runner, H2 bridge, Telegram gateway, or `/root/.hermes`.
3. The ONLY repository path Hermes may create/modify is `docs/operations/OPS_RC1_R2_GOVERNANCE_AUDIT.md`.
4. ABSOLUTE PROHIBITION for Hermes: do not run `git add`, `git commit`, `git push`, `git reset`, `git clean`, `git checkout`, `git switch`, `git merge`, `git rebase`, `git tag`, or any command that changes refs/index/history. Host runner alone must stage, commit and push this task result.
5. `network_git=false` is binding. Git network operations by Hermes are forbidden. Read-only local commands such as `git status`, `git log`, `git show`, `git diff`, `git rev-parse`, and `git reflog` are allowed if they do not mutate state.
6. Do not modify `.agent/EXECUTION_RESULT.json`; it is runner-managed.
7. Do not declare Architect acceptance. Produce the audit file, leave it uncommitted in the worktree, and STOP so host runner can validate, write EXECUTION_RESULT, commit, and push.
8. Never print or copy secret values.

## Audit questions to answer with evidence
Write `docs/operations/OPS_RC1_R2_GOVERNANCE_AUDIT.md` and answer:

### A. R2 commit provenance
- Confirm HEAD and parent relationship for `e51f06b3d38906ac1c3c33a0c2bf1f8516f3b4c1`.
- Enumerate changed paths in `d850f55a..e51f06b3` and confirm whether they are all within R2 exact allowlist.
- Determine, from available local git/runner evidence, which actor/path created and pushed `e51f06b3...`.
- If exact provenance cannot be proven, state `PROVENANCE: INDETERMINATE` rather than guessing.

### B. Why R2 EXECUTION_RESULT was not finalized
- Inspect host runner logic and available runner/local state.
- Determine the most evidence-backed root cause for R2 being `SUPPRESSED` while `.agent/EXECUTION_RESULT.json` remains R1.
- Specifically test the hypothesis that remote HEAD moved during executor execution before host runner `stage_commit_push` could publish its own PASS result.
- Distinguish confirmed facts from inference.

### C. R2 implementation integrity
- Read-only verify that R2 evidence file exists and its task/baseline match R2.
- Verify no path outside the R2 allowlist was committed in `e51f06b3...`.
- Do not re-run destructive/runtime tests; this task audits repository/governance only.

### D. Host-runner finalization test
- Before stopping, leave exactly one worktree change: `docs/operations/OPS_RC1_R2_GOVERNANCE_AUDIT.md`.
- Do not commit it yourself.
- The expected success condition is that host runner detects that one allowed path, writes a PASS `.agent/EXECUTION_RESULT.json`, creates the commit with message `governance: finalize OPS-RC1-R2 handoff`, pushes it, and leaves a clean worktree.

## Required audit conclusion
The file must include:
- `R2_IMPLEMENTATION_COMMIT: e51f06b3d38906ac1c3c33a0c2bf1f8516f3b4c1`
- `R2_SCOPE_INTEGRITY: PASS|FAIL`
- `R2_EXECUTION_RESULT_PRESENT: NO` (unless current facts change before execution; then state exact new fact)
- `ROOT_CAUSE: ...`
- `ROOT_CAUSE_CONFIDENCE: CONFIRMED|HIGH|MEDIUM|LOW`
- `HERMES_GIT_WRITE_USED_IN_THIS_TASK: NO`
- `RUNTIME_MUTATIONS_IN_THIS_TASK: NO`
- `SECRET_VALUES_PRINTED: NO`
- `SECRETS_EXPOSED: NO`

## Acceptance
This corrective task is successful only if Hermes does not self-commit/push and the host runner itself publishes the audit plus a fresh PASS `.agent/EXECUTION_RESULT.json` for `AITHER-MVP-GOV-R2-FINALIZE-R1`.

After writing the one allowed audit file, STOP.
