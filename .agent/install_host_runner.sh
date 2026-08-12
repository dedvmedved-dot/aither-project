#!/usr/bin/env bash
set -euo pipefail

REPO=/home/codex/aither-project
SERVICE_IN="$REPO/.agent/systemd/aither-codex-runner.service.in"
TIMER_IN="$REPO/.agent/systemd/aither-codex-runner.timer"
SERVICE_OUT=/etc/systemd/system/aither-codex-runner.service
TIMER_OUT=/etc/systemd/system/aither-codex-runner.timer
STAGE=start

report_tag() {
  local outcome="$1" stage="$2" stamp head tag
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  head="$(runuser -u codex -- git -C "$REPO" rev-parse HEAD 2>/dev/null || true)"
  [[ -n "$head" ]] || return 0
  tag="runner-status/${outcome}-${stage}-${stamp}"
  runuser -u codex -- git -C "$REPO" tag "$tag" "$head" >/dev/null 2>&1 || return 0
  runuser -u codex -- git -C "$REPO" push origin "refs/tags/$tag" >/dev/null 2>&1 || true
}
trap 'rc=$?; report_tag fail "$STAGE"; exit $rc' ERR

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then echo "ERROR: run installer as root" >&2; exit 1; fi
id codex >/dev/null 2>&1 || { echo "ERROR: user codex not found" >&2; exit 1; }
[[ -d "$REPO/.git" ]] || { echo "ERROR: repository not found at $REPO" >&2; exit 1; }

STAGE=codex-path
CODEX_BIN="$(runuser -u codex -- env HOME=/home/codex bash -c 'command -v codex 2>/dev/null || true')"
if [[ -z "$CODEX_BIN" ]]; then
  CODEX_BIN="$(runuser -u codex -- find /home/codex/.nvm/versions/node -type f -path '*/bin/codex' -perm -u+x -print 2>/dev/null | sort -V | tail -n 1 || true)"
fi
[[ -n "$CODEX_BIN" && -x "$CODEX_BIN" ]] || { echo "ERROR: codex binary not found for user codex" >&2; exit 1; }
CODEX_DIR="$(dirname "$CODEX_BIN")"
RUNNER_ENV=(env HOME=/home/codex CODEX_HOME=/home/codex/.codex GIT_TERMINAL_PROMPT=0 CODEX_BIN="$CODEX_BIN" PATH="$CODEX_DIR:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin")

STAGE=pycompile
python3 -m py_compile "$REPO/.agent/host_task_runner.py" "$REPO/.agent/tests/test_host_task_runner.py"
STAGE=tests
runuser -u codex -- "${RUNNER_ENV[@]}" bash -lc "cd '$REPO' && python3 .agent/tests/test_host_task_runner.py"
STAGE=dry-run
runuser -u codex -- "${RUNNER_ENV[@]}" bash -lc "cd '$REPO' && python3 .agent/host_task_runner.py --dry-run"

STAGE=systemd-install
sed -e "s|__CODEX_BIN__|$CODEX_BIN|g" -e "s|__CODEX_DIR__|$CODEX_DIR|g" "$SERVICE_IN" > "$SERVICE_OUT"
install -m 0644 "$TIMER_IN" "$TIMER_OUT"; chmod 0644 "$SERVICE_OUT"; systemctl daemon-reload
systemctl disable --now aither-codex-runner.timer >/dev/null 2>&1 || true

STAGE=run-once
runuser -u codex -- "${RUNNER_ENV[@]}" bash -lc "cd '$REPO' && python3 .agent/host_task_runner.py --run-once"

STAGE=timer-enable
systemctl enable --now aither-codex-runner.timer
STAGE=success
report_tag success bootstrap
trap - ERR
printf 'INSTALLED=YES\nCODEX_BIN=%s\nTIMER_STATE=%s\nBRANCH_HEAD=%s\n' "$CODEX_BIN" "$(systemctl is-active aither-codex-runner.timer)" "$(runuser -u codex -- git -C "$REPO" rev-parse HEAD)"
