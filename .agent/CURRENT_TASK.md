# TASK: CODEX-HARNESS-S2-HOST-BOOTSTRAP-R1

## MODE
ARCHITECT MANAGEMENT HOST BOOTSTRAP CORRECTION

This Architect-owned management commit hardens unattended host execution. It is not an executor task and must not be executed by Codex.

Changes:
- allow up to 30 minutes for a systemd oneshot agent run;
- set explicit CODEX_HOME for unattended ChatGPT-authenticated Codex execution;
- remove extra systemd privilege clamps that may interfere with Linux bubblewrap while the process still runs as the unprivileged `codex` user;
- make the installer prove the autonomous `--run-once` path directly as user `codex` before enabling the timer.

The next Architect commit publishes canary v2 with exact content validation.
