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

CODEX_BIN="$(runuser -u codex -- bash -lc 'command -v codex')"
[[ -n "$CODEX_BIN" && -x "$CODEX_BIN" ]] || { echo "ERROR: codex binary not found for user codex" >&2; exit 1; }
CODEX_DIR="$(dirname "$CODEX_BIN")"

python3 -m py_compile "$REPO/.agent/host_task_runner.py" "$REPO/.agent/tests/test_host_task_runner.py"
runuser -u codex -- bash -lc "cd '$REPO' && python3 .agent/tests/test_host_task_runner.py"
runuser -u codex -- bash -lc "cd '$REPO' && python3 .agent/host_task_runner.py --dry-run"

sed \
  -e "s|__CODEX_BIN__|$CODEX_BIN|g" \
  -e "s|__CODEX_DIR__|$CODEX_DIR|g" \
  "$SERVICE_IN" > "$SERVICE_OUT"
install -m 0644 "$TIMER_IN" "$TIMER_OUT"
chmod 0644 "$SERVICE_OUT"

systemctl daemon-reload
systemctl enable --now aither-codex-runner.timer
systemctl start aither-codex-runner.service

printf 'INSTALLED=YES\n'
printf 'CODEX_BIN=%s\n' "$CODEX_BIN"
printf 'TIMER_STATE=%s\n' "$(systemctl is-active aither-codex-runner.timer)"
printf 'SERVICE_RESULT=%s\n' "$(systemctl show -p Result --value aither-codex-runner.service)"
printf 'BRANCH_HEAD=%s\n' "$(runuser -u codex -- git -C "$REPO" rev-parse HEAD)"
