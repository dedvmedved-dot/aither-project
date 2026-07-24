# Beta Acceptance Checklist

Run immediately before granting user access.

## Pre-Flight

- [ ] Review release manifest: `01_RELEASE_MANIFEST.md`
- [ ] Confirm all components at correct versions
- [ ] Verify no uncommitted changes in critical files
- [ ] Notify users of upcoming access

## DNS & TLS

- [ ] `fb1.spb.ru` resolves to VPS2 IP
- [ ] TLS certificate valid (not expired)
- [ ] `curl -v https://fb1.spb.ru/v1/models` shows valid cert chain

## VPN & Gateway

- [ ] `ip link show tun0` — UP
- [ ] `ping -c 2 10.129.13.78` — replies
- [ ] `docker ps | grep vpn-cisco` — single container running
- [ ] `docker logs vpn-cisco --tail=5` — no recent reconnects
- [ ] `curl -sk https://localhost:443/ >/dev/null` — nginx responding
- [ ] `curl -sk https://localhost:10443/ >/dev/null` — nginx responding

## Kubernetes

- [ ] `kubectl get nodes` — both Ready
- [ ] `kubectl get pods -n aither-inference` — all Running (except Completed test pods)
- [ ] No CrashLoopBackOff pods
- [ ] No pods with restartCount > 2 (recent)

## API

- [ ] `GET /v1/models` returns `qwen-14b` and `qwen-32b-base`
- [ ] `POST 14B chat` returns valid response
- [ ] `POST 32B completion` returns valid response
- [ ] Invalid auth returns 401
- [ ] Invalid model returns 404

## Models

- [ ] 14B response is semantically correct (test with known prompt)
- [ ] 32B response is semantically correct (test with known prompt)
- [ ] Response times within expected ranges (14B: <15s, 32B: <2s)

## Monitoring

- [ ] Prometheus `/metrics` endpoint accessible
- [ ] No recent ERROR in ai-platform logs
- [ ] No recent ERROR in gateway logs
- [ ] `uptime` metric > 0 (service running)

## Logs

- [ ] ai-platform logs: check last 20 lines
- [ ] nginx-gateway logs: check last 20 lines
- [ ] vLLM logs: check for CUDA/OOM errors

## Backup

- [ ] Manual database backup performed (ai-platform + identity)
- [ ] Backup file stored outside VPS2
- [ ] Backup file verified (non-zero size, valid SQLite)

## Health

- [ ] Run full health checklist: `docs/stage-u1.3/03_HEALTH_CHECKLIST.md`
- [ ] All items pass

## User Readiness

- [ ] API keys generated for each beta user
- [ ] User documentation shared (`07_INTERNAL_USER_PACKAGE.md`)
- [ ] Bug reporting process communicated
- [ ] Support contact provided

## Sign-Off

| Role | Name | Date | Signature |
|---|---|---|---|
| Operator | | | |
| Platform Lead | | | |
