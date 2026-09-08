#!/usr/bin/env bash
# Aither R8-CONTROL Phase 8: canonical long-context control run (UNCHANGED harness).
# 5x56K + 5x58K + 3x60K = 13 cases. Runs AFTER Phase 7 (single-sequence model).
set -u

REPO=/root/aither-project-r7-canonical
VENV=/root/aither-venv/bin/python
LC_HARNESS=$REPO/aither-v2/tools/aither-agent-harness-longcontext
HARNESS=$REPO/aither-v2/tools/aither-agent-harness-lab
OUT=$REPO/docs/evidence/AITHER_R8_CONTROL_QWEN38_LONG_CONTEXT.csv
BASE=http://127.0.0.1:18000
MODEL=qwen3.8-27b
KEY=$(cat /tmp/aither_qwen38_api_key.txt)
LOG=$REPO/docs/evidence/AITHER_R8_CONTROL_QWEN38_LONG_CONTEXT.log

export HARNESS="$HARNESS"
echo "===== LONG-CONTEXT START $(date -u +%Y-%m-%dT%H:%M:%SZ) =====" | tee "$LOG"
"$VENV" "$LC_HARNESS" "$BASE" "$MODEL" "$KEY" "$OUT" >> "$LOG" 2>&1
echo "===== LONG-CONTEXT END $(date -u +%Y-%m-%dT%H:%M:%SZ) exit=$? =====" | tee -a "$LOG"
