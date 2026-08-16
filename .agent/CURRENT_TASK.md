# TASK: HERMES-INTEGRATION-H8-FINAL-AUTONOMOUS-HANDOFF-GATE

## Goal

Final integration gate before normal Aither development resumes.

Prove the already-built autonomous loop end to end:

`Architect task -> GitHub -> persistent scheduler -> Hermes -> validation -> EXECUTION_RESULT.json -> result-only commit -> next poll IDLE`.

This is a strict read-only executor canary. No implementation changes are authorized.

## Starting state

- Branch: `aither-v2`.
- Baseline: `349b285f603430e4015980df8bc5cef758a1885b`.
- H6 persistent scheduler is accepted.
- H7A/H7A-R1 result publication and ownership safeguards are installed.
- H7B autonomous result-only publication passed.

## Required behavior

1. The persistent scheduler must discover H8 automatically. No manual host sync or manual runner start.
2. Hermes must read the current task and perform only read-only checks of task identity, branch, HEAD and clean worktree.
3. Hermes must make zero repository or application changes and return PASS only when the task is correctly loaded and the existing execution path is healthy.
4. Existing host-runner validations must pass.
5. The host runner alone must update `.agent/EXECUTION_RESULT.json`.
6. Exactly one result-only commit must be pushed with message `gate: prove final autonomous Hermes handoff`.
7. That commit must contain only `.agent/EXECUTION_RESULT.json`.
8. Result JSON must report this H8 task, `executor=hermes`, `result=PASS`, and empty `changed_paths` / `implementation_paths`.
9. The next unchanged scheduler poll must return IDLE without executor reinvocation and without another result commit.
10. The persistent scheduler remains active after PASS.

## Restrictions

- Do not modify source files or task-control locally.
- Do not modify `.agent/EXECUTION_RESULT.json` from Hermes; it is runner-managed.
- Do not manually start the scheduler execution chain.
- Do not invoke another executor.
- Do not change application runtime, cluster state, database, deployment, packages, access configuration or repository ownership.
- Do not print sensitive values.

## PASS criteria

PASS requires autonomous discovery, exactly one Hermes execution for the H8 fingerprint, zero executor file changes, successful validation, exactly one result-only commit, safe H8 PASS result JSON, and next-poll IDLE with no repeated executor.

After independent Architect verification of the H8 result commit, the integration-canary sequence is complete. Subsequent work must return to normal bounded Aither development tasks unless a new integration fault appears.

Do not declare Architect acceptance. STOP.
