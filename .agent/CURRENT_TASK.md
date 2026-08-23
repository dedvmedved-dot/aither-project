# AITHER — ARCHITECT HOLD / NO CODEX

## Status

`ARCHITECT HOLD`

No AI executor is authorized to run this task.

The machine task deliberately has:

- `executor: hermes` because Hermes is the only permitted Aither executor;
- `agent_exec: false` so the host runner must fail closed before invoking Hermes;
- all write/runtime/deployment capabilities disabled;
- an empty implementation allowlist.

## Governance correction

Codex is **not authorized for Aither** and must not be used as an Aither executor.

The prior task `AITHER-H2-HERMES-WATCHDOG-R1` with `executor: codex` was published by ChatGPT in error. Its runner result reported no implementation changes (`changed_paths=[]`, `implementation_paths=[]`). The Codex task is superseded by this Architect HOLD.

Do not invoke Codex. Do not invoke Hermes. Do not modify Portal, models, Kubernetes, documentation, runner code, secrets, or any project file.

The next executable task may be published only by ChatGPT Architect and must use Hermes under the established Aither governance.
