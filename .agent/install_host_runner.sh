#!/usr/bin/env bash
set -euo pipefail

REPO=/home/codex/aither-project
SERVICE_IN="$REPO/.agent/systemd/aither-codex-runner.service.in"
TIMER_IN="$REPO/.agent/systemd/aither-codex-runner.timer"
SERVICE_OUT=/etc/systemd/system/aither-codex-runner.service
TIMER_OUT=/etc/systemd/system/aither-codex-runner.timer

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "ERROR: run installer as root" >&2
  exit 1
fi

id codex >/dev/null 2>&1 || { echo "ERROR: user codex not found" >&2; exit 1; }
[[ -d "$REPO/.git" ]] || { echo "ERROR: repository not found at $REPO" >&2; exit 1; }
[[ -f "$SERVICE_IN" && -f "$TIMER_IN" ]] || { echo "ERROR: systemd templates missing" >&2; exit 1; }
[[ -f "$REPO/.agent/host_task_runner.py" ]] || { echo "ERROR: host runner missing" >&2; exit 1; }

CODEX_BIN="$(runuser -u codex -- env HOME=/home/codex bash -lc 'command -v codex')"
[[ -n "$CODEX_BIN" && -x "$CODEX_BIN" ]] || { echo "ERROR: codex binary not found for user codex" >&2; exit 1; }
CODEX_DIR="$(dirname "$CODEX_BIN")"
RUNNER_ENV=(env HOME=/home/codex CODEX_HOME=/home/codex/.codex GIT_TERMINAL_PROMPT=0 CODEX_BIN="$CODEX_BIN" PATH="$CODEX_DIR:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin")

python3 -m py_compile "$REPO/.agent/host_task_runner.py" "$REPO/.agent/tests/test_host_task_runner.py"
runuser -u codex -- "${RUNNER_ENV[@]}" bash -lc "cd '$REPO' && python3 .agent/tests/test_host_task_runner.py"
runuser -u codex -- "${RUNNER_ENV[@]}" bash -lc "cd '$REPO' && python3 .agent/host_task_runner.py --dry-run"

sed \
  -e "s|__CODEX_BIN__|$CODEX_BIN|g" \
  -e "s|__CODEX_DIR__|$CODEX_DIR|g" \
  "$SERVICE_IN" > "$SERVICE_OUT"
install -m 0644 "$TIMER_IN" "$TIMER_OUT"
chmod 0644 "$SERVICE_OUT"

systemctl daemon-reload
systemctl disable --now aither-codex-runner.timer >/dev/null 2>&1 || true

# Prove the autonomous path directly as user codex before relying on systemd.
runuser -u codex -- "${RUNNER_ENV[@]}" bash -lc "cd '$REPO' && python3 .agent/host_task_runner.py --run-once"

systemctl enable --now aither-codex-runner.timer

printf 'INSTALLED=YES\n'
printf 'CODEX_BIN=%s\n' "$CODEX_BIN"
printf 'TIMER_STATE=%s\n' "$(systemctl is-active aither-codex-runner.timer)"
printf 'BRANCH_HEAD=%s\n' "$(runuser -u codex -- git -C "$REPO" rev-parse HEAD)"
