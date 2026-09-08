#!/usr/bin/env bash
# Aither R8-CONTROL Phase 7 orchestration: run canonical R7-C1 harness (UNCHANGED)
# against production Qwen3.8 control. FULL (50) + ROUTED (50), F0 + F1 each.
set -u

REPO=/root/aither-project-r7-canonical
HARNESS=$REPO/aither-v2/tools/aither-agent-harness-lab
SCEN=$REPO/docs/evidence/AITHER_QWEN38_VLLM_HERMES_R7_SCENARIOS.json
OUT=$REPO/docs/evidence
BASE=http://127.0.0.1:18000
MODEL=qwen3.8-27b
KEY=$(cat /tmp/aither_qwen38_api_key.txt)
LEDGER=/tmp/aither_r8_control_tool_calls.csv
LOG=$REPO/docs/evidence/AITHER_R8_CONTROL_QWEN38_BENCHMARK_RUN.log

rm -f "$LEDGER"
: > "$LOG"

run_one() {
  local mode="$1" think="$2" outcsv="$3"
  echo "===== $mode $think START $(date -u +%Y-%m-%dT%H:%M:%SZ) =====" | tee -a "$LOG"
  python3 "$HARNESS" run "$SCEN" "$mode" "$think" "$BASE" "$MODEL" "$KEY" p0 "$outcsv" "$LEDGER" >> "$LOG" 2>&1
  echo "===== $mode $think END $(date -u +%Y-%m-%dT%H:%M:%SZ) exit=$? =====" | tee -a "$LOG"
}

run_one full f0 "$OUT/AITHER_R8_CONTROL_QWEN38_FULL_F0.csv"
run_one full f1 "$OUT/AITHER_R8_CONTROL_QWEN38_FULL_F1.csv"
run_one routed f0 "$OUT/AITHER_R8_CONTROL_QWEN38_ROUTED_F0.csv"
run_one routed f1 "$OUT/AITHER_R8_CONTROL_QWEN38_ROUTED_F1.csv"

echo "===== ALL DONE $(date -u +%Y-%m-%dT%H:%M:%SZ) =====" | tee -a "$LOG"
