#!/bin/bash
# collect-logs.sh — сбор логов для диагностики
set -e

OUTDIR="/tmp/aither-logs-$(date +%Y%m%d-%H%M)"
mkdir -p "$OUTDIR"

echo "=== Сбор логов в $OUTDIR ==="

kubectl logs -n aither deploy/gateway --tail=500 > "$OUTDIR/gateway.log" 2>&1 &
kubectl logs -n aither deploy/vllm-qwen --tail=500 > "$OUTDIR/vllm-14b.log" 2>&1 &
kubectl logs -n aither deploy/vllm-qwen32b --tail=500 > "$OUTDIR/vllm-32b.log" 2>&1 &
kubectl logs -n aither deploy/postgres --tail=200 > "$OUTDIR/postgres.log" 2>&1 &
wait

kubectl describe nodes > "$OUTDIR/nodes.txt" 2>&1
kubectl get events -n aither --sort-by='.lastTimestamp' > "$OUTDIR/events.txt" 2>&1

echo "✅ Логи собраны: $OUTDIR"
ls -la "$OUTDIR"
