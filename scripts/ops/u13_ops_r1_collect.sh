#!/usr/bin/env bash
# u13_ops_r1_collect.sh — Evidence collection for U1.3-OPS-R1
set -Eeuo pipefail

NS="${NS:-aither-inference}"
EVIDENCE_DIR="${EVIDENCE_DIR:-evidence/u1.3-ops-r1}"

log() {
    local file="$1"
    shift
    mkdir -p "$(dirname "$EVIDENCE_DIR/$file")"
    {
        echo "=== $(date -u +'%Y-%m-%dT%H:%M:%SZ') ==="
        echo "COMMAND: $*"
        "$@" 2>&1
        echo "EXIT_CODE=$?"
        echo ""
    } >> "$EVIDENCE_DIR/$file"
}

# K8s baseline
log "logs/03-cluster-baseline.log" date -u +"%Y-%m-%dT%H:%M:%SZ"
log "logs/03-cluster-baseline.log" kubectl cluster-info
log "logs/03-cluster-baseline.log" kubectl get nodes -o wide
log "logs/03-cluster-baseline.log" kubectl get deployments -n "$NS" -o wide
log "logs/03-cluster-baseline.log" kubectl get pods -n "$NS" -o wide
log "logs/03-cluster-baseline.log" kubectl get services -n "$NS" -o wide
log "logs/03-cluster-baseline.log" kubectl get deployments -n "$NS" -o custom-columns='NAME:.metadata.name,DESIRED:.spec.replicas,READY:.status.readyReplicas,AVAILABLE:.status.availableReplicas,UPDATED:.status.updatedReplicas'

# Startup validation
for dep in $(kubectl get deployment -n "$NS" -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}'); do
    log "logs/04-startup.log" kubectl rollout status deployment/"$dep" -n "$NS" --timeout=300s
done

# Pod-wide status
log "logs/04-startup.log" kubectl get pods -n "$NS"
log "logs/04-startup.log" kubectl get deployments -n "$NS"

echo "Collection script ready at scripts/ops/u13_ops_r1_collect.sh"
