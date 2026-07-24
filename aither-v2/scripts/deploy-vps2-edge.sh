#!/bin/bash
# deploy-vps2-edge.sh — Deploy VPS2 edge services (VPN + nginx)
# Source-of-truth: services/portal-frontend/
#
# Prerequisites:
#   - Docker on VPS2
#   - OPENCONNECT_PASSWORD in environment (never logged)
#   - OPENCONNECT_GROUP in environment
#   - SSL cert at /root/ssl-cert/
#
# Usage: ./deploy-vps2-edge.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EDGE_DIR="$REPO_ROOT/services/portal-frontend"

# ── Pre-flight checks ────────────────────────────────
echo "=== Pre-flight ==="

if [ -z "${OPENCONNECT_PASSWORD:-}" ]; then
  echo "ERROR: OPENCONNECT_PASSWORD not set" >&2
  exit 1
fi
if [ -z "${OPENCONNECT_GROUP:-}" ]; then
  echo "ERROR: OPENCONNECT_GROUP not set" >&2
  exit 1
fi
if [ ! -f "$EDGE_DIR/nginx-failover-vps2.conf" ]; then
  echo "ERROR: nginx-failover-vps2.conf not found" >&2
  exit 1
fi
if [ ! -f "$EDGE_DIR/vpn-cisco-entrypoint.sh" ]; then
  echo "ERROR: vpn-cisco-entrypoint.sh not found" >&2
  exit 1
fi
if [ ! -f "/root/ssl-cert/cert.pem" ] || [ ! -f "/root/ssl-cert/key.pem" ]; then
  echo "ERROR: SSL certificates not found at /root/ssl-cert/" >&2
  exit 1
fi

# Validate shell syntax
bash -n "$EDGE_DIR/vpn-cisco-entrypoint.sh"
echo "✅ vpn-cisco-entrypoint.sh syntax OK"

# Validate nginx config
docker run --rm -v "$EDGE_DIR/nginx-failover-vps2.conf:/etc/nginx/conf.d/default.conf:ro" nginx:alpine nginx -t 2>/dev/null
echo "✅ nginx config syntax OK"

# ── Backup current runtime config ────────────────────
BACKUP_DIR="/root/edge-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
if [ -f "/root/nginx-failover.conf" ]; then
  cp /root/nginx-failover.conf "$BACKUP_DIR/"
fi
docker inspect aither-failover-nginx --format='{{.Config.Image}}' > "$BACKUP_DIR/nginx-image.txt" 2>/dev/null || true
docker inspect vpn-cisco --format='{{.Config.Image}}' > "$BACKUP_DIR/vpn-image.txt" 2>/dev/null || true
echo "✅ Backup saved to $BACKUP_DIR"

# ── Deploy nginx config ──────────────────────────────
cp "$EDGE_DIR/nginx-failover-vps2.conf" /root/nginx-failover.conf

# ── Recreate containers ──────────────────────────────
echo "=== Restarting containers ==="

# Stop and remove only our containers
docker stop aither-failover-nginx 2>/dev/null || true
docker rm aither-failover-nginx 2>/dev/null || true
docker stop vpn-cisco 2>/dev/null || true
docker rm vpn-cisco 2>/dev/null || true

# Start VPN
docker run -d \
  --name vpn-cisco \
  --restart unless-stopped \
  --cap-add NET_ADMIN \
  --network host \
  -e OPENCONNECT_PASSWORD \
  -e OPENCONNECT_GROUP \
  -v "$EDGE_DIR/vpn-cisco-entrypoint.sh:/entrypoint.sh:ro" \
  vpn-cisco-o /bin/bash /entrypoint.sh

echo "Waiting for VPN tunnel..."
for i in $(seq 1 30); do
  if ip link show tun0 >/dev/null 2>&1; then
    echo "✅ tun0 ready"
    break
  fi
  sleep 2
done

if ! ip link show tun0 >/dev/null 2>&1; then
  echo "ERROR: tun0 not created after 60s" >&2
  exit 1
fi

# Verify route
if ! ip route get 10.129.13.78 >/dev/null 2>&1; then
  echo "ERROR: No route to 10.129.13.78" >&2
  exit 1
fi
echo "✅ Route to 10.129.13.78 present"

# Start nginx
docker run -d \
  --name aither-failover-nginx \
  --restart unless-stopped \
  -p 443:443 -p 10443:10443 -p 30901:30901 \
  -v /root/nginx-failover.conf:/etc/nginx/conf.d/default.conf:ro \
  -v /root/ssl-cert:/etc/nginx/ssl:ro \
  nginx:alpine

sleep 2

# Health check — must pass (fail-closed)
echo "Running health check..."
HEALTH_OK=1

# Test nginx is listening on 443
if ! curl -sk --connect-timeout 5 https://localhost:443/ >/dev/null 2>&1; then
  echo "ERROR: nginx not responding on :443" >&2
  HEALTH_OK=0
fi

# Test nginx is listening on 10443
if ! curl -sk --connect-timeout 5 https://localhost:10443/ >/dev/null 2>&1; then
  echo "ERROR: nginx not responding on :10443" >&2
  HEALTH_OK=0
fi

if [ $HEALTH_OK -eq 0 ]; then
  echo "FATAL: Health check failed — deployment aborted" >&2
  echo "Rollback: docker stop aither-failover-nginx vpn-cisco; docker rm aither-failover-nginx vpn-cisco; cp \$BACKUP_DIR/nginx-failover.conf /root/"
  exit 1
fi
echo "✅ Health check passed (all ports responding)"

echo "=== Deploy complete ==="
echo "Backup: $BACKUP_DIR"
echo "Rollback: docker stop aither-failover-nginx vpn-cisco; docker rm aither-failover-nginx vpn-cisco; cp \$BACKUP_DIR/nginx-failover.conf /root/"
