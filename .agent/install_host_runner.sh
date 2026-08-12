#!/usr/bin/env bash
set -euo pipefail
REPO=/home/codex/aither-project
SERVICE_IN="$REPO/.agent/systemd/aither-codex-runner.service.in"; TIMER_IN="$REPO/.agent/systemd/aither-codex-runner.timer"
SERVICE_OUT=/etc/systemd/system/aither-codex-runner.service; TIMER_OUT=/etc/systemd/system/aither-codex-runner.timer
OBSERVER="$REPO/.agent/codex_observer.py"; STAGE=start
report_tag(){ local outcome="$1" stage="$2" stamp head tag; stamp="$(date -u +%Y%m%dT%H%M%SZ)"; head="$(runuser -u codex -- git -C "$REPO" rev-parse HEAD 2>/dev/null || true)"; [[ -n "$head" ]]||return 0; tag="runner-status/${outcome}-${stage}-${stamp}"; runuser -u codex -- git -C "$REPO" tag "$tag" "$head" >/dev/null 2>&1||return 0; runuser -u codex -- git -C "$REPO" push origin "refs/tags/$tag" >/dev/null 2>&1||true; }
trap 'rc=$?; report_tag fail "$STAGE"; exit $rc' ERR
[[ ${EUID:-$(id -u)} -eq 0 ]]||{ echo 'ERROR: run as root' >&2; exit 1; }
STAGE=codex-path
REAL_CODEX_BIN="$(runuser -u codex -- env HOME=/home/codex bash -c 'command -v codex 2>/dev/null || true')"
if [[ -z "$REAL_CODEX_BIN" ]]; then REAL_CODEX_BIN="$(runuser -u codex -- find /home/codex/.nvm/versions/node -type f -path '*/bin/codex' -perm -u+x -print 2>/dev/null|sort -V|tail -n1||true)"; fi
[[ -n "$REAL_CODEX_BIN" && -x "$REAL_CODEX_BIN" ]]||{ echo 'ERROR: codex binary not found' >&2; exit 1; }
REAL_CODEX_DIR="$(dirname "$REAL_CODEX_BIN")"
ENVV=(env HOME=/home/codex CODEX_HOME=/home/codex/.codex GIT_TERMINAL_PROMPT=0 CODEX_BIN="$OBSERVER" AITHER_REAL_CODEX_BIN="$REAL_CODEX_BIN" AITHER_HEARTBEAT_SECONDS=30 AITHER_STALL_WARNING_SECONDS=600 AITHER_HARD_TIMEOUT_SECONDS=3600 PATH="$REAL_CODEX_DIR:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin")
STAGE=tests
python3 -m py_compile "$REPO/.agent/host_task_runner.py" "$REPO/.agent/runner_live.py" "$REPO/.agent/codex_observer.py" "$REPO/.agent/systemd_runner.py" "$REPO/.agent/tests/test_live_observability.py"
runuser -u codex -- "${ENVV[@]}" bash -lc "cd '$REPO' && python3 .agent/tests/test_host_task_runner.py && PYTHONPATH=.agent python3 .agent/tests/test_live_observability.py && python3 .agent/host_task_runner.py --dry-run"
STAGE=systemd-install
sed -e "s|__REAL_CODEX_BIN__|$REAL_CODEX_BIN|g" -e "s|__REAL_CODEX_DIR__|$REAL_CODEX_DIR|g" "$SERVICE_IN" > "$SERVICE_OUT"; install -m0644 "$TIMER_IN" "$TIMER_OUT"; chmod 0644 "$SERVICE_OUT"
systemctl disable --now aither-codex-runner.timer >/dev/null 2>&1||true; systemctl stop aither-codex-runner.service >/dev/null 2>&1||true; systemctl daemon-reload
STAGE=service-proof
systemctl start aither-codex-runner.service; [[ "$(systemctl show -p Result --value aither-codex-runner.service)" == success ]]
STAGE=timer-enable
systemctl enable --now aither-codex-runner.timer; [[ "$(systemctl is-active aither-codex-runner.timer)" == active ]]
STAGE=success; report_tag success bootstrap-live; trap - ERR
echo INSTALLED=YES; echo TIMER_STATE="$(systemctl is-active aither-codex-runner.timer)"; echo SERVICE_RESULT="$(systemctl show -p Result --value aither-codex-runner.service)"; echo HEAD="$(runuser -u codex -- git -C "$REPO" rev-parse HEAD)"
