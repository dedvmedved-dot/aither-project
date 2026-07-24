# VPS2 Edge Deployment

## Architecture
```
VPS2 (130.17.1.90)
├── vpn-cisco container → OpenConnect → Cisco VPN → tun0 → 10.129.13.0/24
└── aither-failover-nginx container → reverse proxy → Kubernetes NodePort
```

## Prerequisites
- Docker on VPS2
- Environment variables: `OPENCONNECT_PASSWORD`, `OPENCONNECT_GROUP` (never in Git)
- SSL cert/key at `/root/ssl-cert/cert.pem` and `/root/ssl-cert/key.pem`
- VPN image: `vpn-cisco-o` (locally built)

## Deployment

```bash
cd services/portal-frontend
export OPENCONNECT_PASSWORD="<from secret store>"
export OPENCONNECT_GROUP="<from secret store>"
bash ../../scripts/deploy-vps2-edge.sh
```

## Validation
1. `ip link show tun0` — tunnel interface present
2. `ip route get 10.129.13.78` — route via tun0
3. `curl -sk https://localhost/v1/models -H "Authorization: Bearer <api_key>"` — returns model list
4. `docker ps | grep vpn-cisco` — single OpenConnect process

## Rollback
```bash
docker stop aither-failover-nginx vpn-cisco
docker rm aither-failover-nginx vpn-cisco
cp /root/edge-backup-<timestamp>/nginx-failover.conf /root/
# Recreate from backup or previous known-good config
```

## Known Limitations
- Cisco VPN tunnel may have periodic latency spikes (handled by 30s connect timeout)
- Single point of failure: VPS2 itself (addressed in U3 production readiness)
- No automatic tunnel health monitoring (improvement tracked for U2)
