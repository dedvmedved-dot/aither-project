# Governance

## Permanent Operating Model

Architect publishes `CURRENT_TASK` in GitHub
-> host supervisor fast-forwards `aither-v2`
-> supervisor validates branch/baseline/task fingerprint
-> supervisor invokes Codex in `workspace-write`
-> Codex implements only executor-authorized scope
-> supervisor rejects task-control tampering or paths outside allowlist
-> validator/tests/diff checks
-> supervisor stages only implementation paths
-> supervisor performs at most the host-authorized commit and non-force push
-> GitHub/CI
-> Architect independent Connector audit
-> PASSED / CONNECTOR VERIFIED or correction task

The Owner is not a manual task transport between Architect and Codex.

## Permission Separation

`capabilities` apply to the Codex executor. In particular, `network_git=false` means Codex does not receive Git network authority and `agent_exec` controls whether the supervisor may invoke Codex for the task.

`host_capabilities` apply only to the trusted host supervisor and may independently authorize `sync`, `commit`, and `push`. Host Git authority never becomes executor Git authority because Codex runs with Git metadata outside its writable sandbox.

The supervisor:
- uses fast-forward synchronization only;
- never rebases, amends, or force-pushes;
- verifies the remote did not move before committing executor output;
- stages only validated implementation paths;
- stores lock/state in Git metadata, not the worktree;
- records a task fingerprint so a successful task is not executed twice;
- restores launch HEAD after failed executor output before any push.

## Evidence Classes
- HERMES EXECUTION EVIDENCE
- CODEX EXECUTION EVIDENCE
- OWNER MANUAL EVIDENCE
- CONNECTOR VERIFIED

Runtime facts reported by Codex are not Connector verification.

## Emergency Mode
Emergency mode remains active until the Owner says exactly:
`ФОРС-МАЖОРНЫЙ РЕЖИМ ЗАВЕРШЁН`

Emergency focus:
- Permanent external agent/API path.
- Blocking security defects.
- No unrelated backlog work.

External API target:
`https://fb1.spb.ru:10443/v1/*`

Normal external user path:
registered account -> `aither_...` API key -> Bearer authentication

Normal external users must not require admin credentials, browser JWT, SSH, kubectl,
port-forward, cron, Redis token, gateway admin key, or password as agent credential.

## Scope Contract
- `qwen2.5-32b-instruct` -> `model:qwen2.5:chat`
- `qwen3-32b` -> `model:qwen3:chat`

Legacy transition scope:
- `model:32b:chat`
- Temporary compatibility only; never reintroduce as a new issuer default.

`UPSTREAM_14B_*` is a stale variable name only; do not change routing merely because of the name.
