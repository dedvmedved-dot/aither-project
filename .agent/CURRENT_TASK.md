# AITHER — ARCHITECT HOLD: ALL AUTOMATED OPERATIONS STOPPED

Task: `AITHER-ARCHITECT-HOLD-ALL-AUTOMATION-R1`

Owner directive: **STOP ALL AUTOMATED OPERATIONS**.

Effective immediately, no automated implementation or runtime action is authorized.

## Mandatory hold

The following are prohibited until a new explicit Owner/Architect release task supersedes this HOLD:

- Hermes execution;
- source writes;
- Git network operations by the runner;
- Kubernetes reads/writes initiated by an executor;
- deployment/rollout/restart/scale/apply/delete operations;
- database writes;
- runtime writes;
- secret access;
- package installation;
- automated commit/push/finalization.

`agent_exec=false` is authoritative. The runner/root executor must fail closed and must not launch Hermes for implementation or diagnostics.

## State preservation

Do not modify Portal, Identity, Gateway, models, documentation, ConfigMaps, Deployments, Secrets, databases, task evidence, or any other project artifact.

The unresolved Portal defects remain open and unchanged:

1. Web Portal model catalog user path is not accepted.
2. User-facing `17_MODEL_USAGE_GUIDE` delivery is not accepted.

No corrective task is authorized while this HOLD is active.

## Release condition

Automation may resume only after a new explicit Owner instruction and a new Architect-published task that supersedes this HOLD.

STOP.
