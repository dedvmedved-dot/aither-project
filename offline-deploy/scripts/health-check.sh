#!/bin/bash
# health-check.sh — проверка всех компонентов платформы
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

check() {
    local name=$1 cmd=$2
    if eval "$cmd" &>/dev/null; then
        echo -e "${GREEN}✅${NC} $name"
    else
        echo -e "${RED}❌${NC} $name"
    fi
}

echo "=== Aither Health Check ==="
echo "Узлы K8s:"
kubectl get nodes --no-headers 2>/dev/null || echo "  ❌ kubectl недоступен"

echo ""
echo "Поды:"
kubectl get pods -n aither --no-headers 2>/dev/null | awk '{printf "  %-30s %s\n", $1, $3}'

echo ""
echo "Сервисы:"
check "PostgreSQL" "kubectl exec -n aither deploy/postgres -- pg_isready -U aither 2>/dev/null"
check "Redis" "kubectl exec -n aither deploy/redis -- redis-cli ping 2>/dev/null | grep -q PONG"
check "Gateway :8080" "curl -sf http://localhost:30900/health"
check "vLLM 14B" "curl -sf http://localhost:32293/health"
check "vLLM 32B" "curl -sf http://localhost:32294/health"
check "Prometheus :9090" "curl -sf http://localhost:30909/-/healthy"
check "Grafana :3000" "curl -sf http://localhost:30300/api/health"

echo ""
echo "GPU:"
kubectl exec -n aither deploy/vllm-qwen -- nvidia-smi --query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total --format=csv,noheader 2>/dev/null

echo ""
echo "=== Health check завершён ==="
