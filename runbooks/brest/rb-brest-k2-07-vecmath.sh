#!/bin/bash
# rb-brest-k2-07-vecmath — Брест FPU stress
# Часть ПМИ AIOps — испытания Aither + ПК СВ Брест
# Сгенерирован: 2026-07-15 14:00:47 MSK

set -e
LOG="/opt/aiops-aither/logs/runbooks/rb-brest-k2-07-vecmath.log"
SSH_KEY="/root/.ssh/id_ed25519_n7n8"

log() {
    echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"
}

log "=== START rb-brest-k2-07-vecmath ==="
log "Description: Брест FPU stress"

# Пре-проверка
log "Pre-check: health status"
curl -s --max-time 5 http://10.129.13.78:8080/health 2>/dev/null || echo "Gateway pre-check: UNREACHABLE"

# Инжекция
log "Injecting fault..."
ssh brest-node 'stress-ng --vecmath 4 --timeout 120s &'

sleep 2

# Диагностика
log "Diagnostics after injection..."
curl -s --max-time 5 http://10.129.13.78:8080/health 2>/dev/null || echo "Gateway: DOWN"
curl -s --max-time 5 http://10.129.13.77:8000/health 2>/dev/null || echo "vLLM 32B: DOWN"
ssh -i $SSH_KEY -o ConnectTimeout=5 root@10.129.13.78 'pg_isready -U aither' 2>/dev/null || echo "PostgreSQL: DOWN"
ssh -i $SSH_KEY -o ConnectTimeout=5 root@10.129.13.78 'redis-cli ping' 2>/dev/null || echo "Redis: DOWN"

# Восстановление
log "Recovering..."
ssh brest-node 'pkill -f stress-ng.*vecmath'

sleep 2

# Пост-проверка
log "Post-check..."
curl -s --max-time 10 http://10.129.13.78:8080/health 2>/dev/null && log "Gateway: RECOVERED" || log "Gateway: STILL DOWN"

log "=== END rb-brest-k2-07-vecmath ==="
