# AITHER-H2-HERMES-WATCHDOG-R1

## Status

`ACTIVE`

## Purpose

Correct the control-plane behavior discovered during `AITHER-PORTAL-MODEL-UI-DOCSYNC-R1`: the H2 Hermes observer can wait for a final bridge response for up to 3600 seconds while publishing heartbeats that do not prove executor progress. This creates a blind one-hour wait and can mislead operators into treating socket liveness as Hermes progress.

## Scope

Modify only:

- `.agent/hermes_observer.py`
- `.agent/tests/test_hermes_observer.py`
- `docs/evidence/AITHER_H2_HERMES_WATCHDOG_R1.md`

Do not touch Portal, Kubernetes workloads, model configuration, task runner semantics, `/root/.hermes`, Telegram gateway, secrets, or unrelated files.

## Required behavior

1. Reduce the default Hermes H2 hard timeout from 3600 seconds to **900 seconds (15 minutes)**.
2. Preserve environment override `AITHER_HERMES_TIMEOUT` for deliberate longer/shorter controlled runs.
3. Add explicit stall observability before the hard timeout:
   - default stall-warning threshold: **300 seconds (5 minutes)** without any response bytes from the H2 bridge;
   - expose a safe status phase such as `HERMES_STALL_WARNING` while keeping the process alive until hard timeout;
   - repeated heartbeat must not masquerade as executor progress.
4. Continue to fail closed on timeout, connection failure, empty response, `BLOCKED_*`, or `FAIL*` response.
5. Do not add arbitrary command/prompt execution. Observer must still send only fixed `RUN\n` to the accepted Unix socket bridge.
6. Keep response bounded and do not expose response content in runner-live status.
7. Add/adjust unit tests proving:
   - new default timeout is 900 seconds;
   - env timeout override still works;
   - stall warning occurs after configured threshold when no response bytes arrive;
   - normal delayed success before timeout still succeeds;
   - timeout still fails closed;
   - fixed RUN signal and no-shell/no-direct-Hermes invariants remain intact.

## Evidence

Create `docs/evidence/AITHER_H2_HERMES_WATCHDOG_R1.md` with:

- base HEAD;
- exact changed paths;
- before/after timeout values;
- stall-warning semantics;
- unit-test command and result;
- explicit statement that no runtime Portal/model/Kubernetes state was changed;
- `SECRETS EXPOSED: NO`.

## Acceptance

Machine PASS is not acceptance. ChatGPT must independently verify the commit, tests/evidence, and scope before this control-plane correction is accepted.
