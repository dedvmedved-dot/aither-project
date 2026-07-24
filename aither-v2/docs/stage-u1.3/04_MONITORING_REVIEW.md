# Monitoring Review

## What IS Monitored

| Component | Metric | Source | Access |
|---|---|---|---|
| ai-platform | HTTP request count | Prometheus counter | `/metrics` |
| ai-platform | Request duration | Prometheus histogram | `/metrics` |
| ai-platform | Active requests | Prometheus gauge | `/metrics` |
| ai-platform | Gateway errors by type | Prometheus counter | `/metrics` |
| ai-platform | Auth failures | Prometheus counter | `/metrics` |
| ai-platform | Uptime, memory | Prometheus gauge | `/metrics` |
| ai-platform | API keys, conversations | Prometheus gauge (DB) | `/metrics` |
| K8s pods | Readiness/Liveness | Kubelet probes | `kubectl describe` |
| K8s pods | Restart count | K8s API | `kubectl get pods` |
| nginx-gateway | Stub status | nginx | `/nginx_status` (127.0.0.1 only) |
| VPS2 nginx | Access logs with timings | File | `docker logs` |

## What is NOT Monitored

| Gap | Severity | Impact |
|---|---|---|
| GPU utilization (n7) | HIGH | Cannot detect GPU saturation |
| GPU memory (n7) | HIGH | OOM only visible in logs |
| VPN tunnel health | HIGH | Failure only detected when API fails |
| VPS2 disk space | MEDIUM | No alert before disk full |
| VPS2 memory | MEDIUM | OOM killer may kill containers |
| SQLite database size | MEDIUM | Unbounded growth possible |
| API key usage per user | LOW | Cannot bill/track usage |
| Model response quality | LOW | No semantic monitoring |
| TLS certificate expiry | MEDIUM | Manual check only |
| Network latency VPS2→K8s | MEDIUM | Only visible in nginx logs |

## What to Add Before Internal Users (Minimum)

1. **VPN health check script** (cron every 5 min): check tun0 + route + ping
2. **Disk space alert** (cron): warn at 80%, critical at 90%
3. **GPU basic check**: `nvidia-smi` on n7 via SSH or K8s job
4. **Certificate expiry check**: `openssl s_client -connect fb1.spb.ru:443`

## What to Add Before Production (U3)

1. Prometheus + Grafana for centralized dashboards
2. Node exporter on both K8s nodes
3. GPU metrics exporter (nvidia-dcgm)
4. Alertmanager with email/webhook alerts
5. Centralized logging (ELK/Loki)
6. Uptime monitoring (external probe)
