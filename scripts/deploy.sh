#!/bin/bash
# Aither Platform — Deploy script
# Запуск: ./deploy.sh [all|gateway|vllm|portal|config]
# Вызывается из GitHub Actions после git pull

set -euo pipefail

COMPONENT="${1:-all}"
NAMESPACE="default"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[deploy]${NC} $1"; }
warn() { echo -e "${YELLOW}[deploy]${NC} $1"; }

deploy_configmaps() {
    log "Updating Gateway ConfigMap..."
    kubectl delete configmap gateway-code --ignore-not-found=true
    kubectl create configmap gateway-code \
        --from-file=gateway/gateway.py \
        --from-file=gateway/admin.py \
        --from-file=gateway/metrics.py \
        --from-file=gateway/routing.py \
        --from-file=gateway/reaper.py \
        --from-file=gateway/catalog.py \
        --from-file=gateway/security.py \
        --from-file=gateway/security_egress.py \
        --from-file=gateway/vault.py \
        --from-file=gateway/hybrid_rag.py \
        --from-file=gateway/wiki_graph.py \
        --from-file=gateway/catalog.yaml

    log "Updating Gateway Catalog ConfigMap..."
    kubectl delete configmap gateway-catalog --ignore-not-found=true
    kubectl create configmap gateway-catalog --from-file=gateway/catalog.yaml
}

deploy_gateway() {
    log "Deploying Gateway..."
    deploy_configmaps
    kubectl rollout restart deployment/gateway -n "$NAMESPACE"
    kubectl rollout status deployment/gateway -n "$NAMESPACE" --timeout=120s
}

deploy_vllm() {
    log "Deploying vLLM..."
    # Drain models before restart
    for model in qwen2.5-coder-14b-instruct qwen2.5-32b-instruct; do
        curl -s -X POST "http://localhost:30900/admin/models/$model/drain" 2>/dev/null || true
    done

    # Restart with 60s gap between pods
    kubectl rollout restart deployment/vllm-qwen -n "$NAMESPACE"
    kubectl rollout status deployment/vllm-qwen -n "$NAMESPACE" --timeout=300s

    kubectl rollout restart deployment/vllm-qwen32b -n "$NAMESPACE"
    kubectl rollout status deployment/vllm-qwen32b -n "$NAMESPACE" --timeout=300s

    # Undrain
    sleep 30
    for model in qwen2.5-coder-14b-instruct qwen2.5-32b-instruct; do
        curl -s -X POST "http://localhost:30900/admin/models/$model/undrain" 2>/dev/null || true
    done
}

deploy_portal() {
    log "Deploying Portal (VPS2 + VPS3)..."
    cd /opt/aither
    docker-compose up -d --build portal
    log "Portal deployed on VPS2"

    # Deploy to VPS3 failover
    if ssh -o ConnectTimeout=5 vps3 "test -d /opt/aither" 2>/dev/null; then
        ssh vps3 "cd /opt/aither && git pull && docker-compose up -d --build portal"
        log "Portal deployed on VPS3"
    else
        warn "VPS3 not reachable — skipping failover deploy"
    fi
}

deploy_hpa() {
    log "Applying HPA configuration..."
    kubectl apply -f k8s/hpa/hpa.yaml
}

deploy_all() {
    log "=== Full deployment started ==="
    deploy_configmaps
    deploy_gateway
    deploy_hpa
    deploy_portal
    log "=== Full deployment complete ==="
}

# ── Main ──

case "$COMPONENT" in
    all)
        deploy_all
        ;;
    gateway)
        deploy_gateway
        ;;
    vllm)
        deploy_vllm
        ;;
    portal)
        deploy_portal
        ;;
    config)
        deploy_configmaps
        deploy_hpa
        ;;
    hpa)
        deploy_hpa
        ;;
    *)
        echo "Usage: $0 [all|gateway|vllm|portal|config|hpa]"
        exit 1
        ;;
esac

# Health check
log "Running health check..."
bash scripts/health-check.sh 2>/dev/null || warn "Health check script not available"
