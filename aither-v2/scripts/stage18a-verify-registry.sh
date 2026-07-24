#!/usr/bin/env bash
# Stage 18A — Verify registry status on n8
# Usage: ./scripts/stage18a-verify-registry.sh [n8_host] [registry_port]
set -Eeuo pipefail

N8_HOST="${1:-10.129.13.78}"
REGISTRY="${2:-localhost:5000}"
SSH_KEY="${3:-}"
SSH_OPTS="-o ConnectTimeout=30 -o ServerAliveInterval=15 -o ServerAliveCountMax=3"
[ -n "$SSH_KEY" ] && SSH_OPTS="${SSH_OPTS} -i ${SSH_KEY}"

echo "=== Registry Status on ${N8_HOST} ==="

# Check services
echo ""
echo "--- Service Status ---"
for svc in containerd kubelet aither-registry; do
  STATUS=$(ssh ${SSH_OPTS} "root@${N8_HOST}" "sudo systemctl is-active ${svc}" 2>&1)
  echo "  ${svc}: ${STATUS}"
done

# Check registry API
echo ""
echo "--- Registry API ---"
VERSION=$(ssh ${SSH_OPTS} "root@${N8_HOST}" "curl -fsS http://${REGISTRY}/v2/" 2>&1)
echo "  GET /v2/: ${VERSION}"

CATALOG=$(ssh ${SSH_OPTS} "root@${N8_HOST}" "curl -fsS http://${REGISTRY}/v2/_catalog" 2>&1)
echo "  GET /v2/_catalog: ${CATALOG}"

# Check tags
echo ""
echo "--- Tags ---"
for repo in aither-identity aither-portal-backend aither-ai-platform; do
  TAGS=$(ssh ${SSH_OPTS} "root@${N8_HOST}" "curl -fsS http://${REGISTRY}/v2/${repo}/tags/list" 2>&1)
  echo "  ${repo}: ${TAGS}"
done

# Check CRI plugins
echo ""
echo "--- CRI Plugins ---"
ssh ${SSH_OPTS} "root@${N8_HOST}" \
  "sudo ctr plugins ls | grep -E 'io\.containerd\.cri|io\.containerd\.grpc\.v1\.cri'"

# Check CRI runtime
echo ""
echo "--- CRI Runtime ---"
ssh ${SSH_OPTS} "root@${N8_HOST}" \
  "sudo crictl info 2>&1 | grep -E 'RuntimeReady|NetworkReady'"

# Check node status
echo ""
echo "--- Node Status ---"
kubectl get node "${N8_HOST}" -o wide 2>&1 || \
  kubectl get nodes -o wide 2>&1 | grep "$(echo ${N8_HOST} | head -c12)"

echo ""
echo "=== Registry Verification Complete ==="
