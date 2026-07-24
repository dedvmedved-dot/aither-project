# Health Checklist

Run after every deployment or as daily health check.

## Gateway & Routing

- [ ] VPN tunnel exists: `ip link show tun0`
- [ ] Route to K8s: `ip route get 10.129.13.78`
- [ ] VPS2 nginx running: `docker ps | grep failover-nginx`
- [ ] :443 responding: `curl -sk https://localhost:443/v1/models -H "Authorization: Bearer <key>"`
- [ ] :10443 responding: `curl -sk https://localhost:10443/v1/models -H "Authorization: Bearer <key>"`
- [ ] :30902 responding: `curl -s http://10.129.13.78:30902/v1/models -H "Authorization: Bearer <key>"`

## AI Platform

- [ ] ai-platform pod Running: `kubectl get pods -n aither-inference -l app=aither-ai-platform`
- [ ] Health endpoint: `curl -s http://10.129.13.78:30902/health`
- [ ] /v1/models returns models: `curl -s http://10.129.13.78:30902/v1/models -H "Authorization: Bearer <key>"`
- [ ] 14B chat works: `curl -X POST .../v1/chat/completions -d '{"model":"qwen-14b-instruct",...}'`
- [ ] 32B completion works: `curl -X POST .../v1/chat/completions -d '{"model":"qwen-32b-gptq",...}'`

## Kubernetes

- [ ] Nodes Ready: `kubectl get nodes`
- [ ] All pods Running: `kubectl get pods -n aither-inference`
- [ ] No CrashLoopBackOff: `kubectl get pods -n aither-inference | grep -v Running | grep -v Completed`
- [ ] No recent restarts: `kubectl get pods -n aither-inference -o jsonpath='{.items[*].status.containerStatuses[*].restartCount}'`

## Inference (vLLM)

- [ ] 14B pod Running: `kubectl get pods -n aither-inference -l model=qwen-14b-instruct`
- [ ] 32B pod Running: `kubectl get pods -n aither-inference -l model=qwen-32b-gptq`
- [ ] GPU healthy: check pod logs for CUDA/OOM errors
- [ ] Models respond in <15s

## Storage

- [ ] VPS2 disk <85%: `df -h /`
- [ ] K8s node disks: `ssh n7 df -h /` and `ssh n8 df -h /`

## Logs

- [ ] No ERROR in ai-platform (last 5 min): `kubectl logs -n aither-inference deploy/aither-ai-platform --tail=50 | grep ERROR`
- [ ] No ERROR in nginx-gateway: `kubectl logs -n aither-inference deploy/nginx-gateway-32b --tail=20 | grep -i error`
- [ ] No VPN reconnects: `docker logs vpn-cisco --tail=20 | grep -c "reconnecting"` (should be 0)

## Metrics

- [ ] ai-platform metrics accessible: `curl -s http://10.129.13.78:30902/metrics`
- [ ] No spike in errors: check `gateway_errors_total` metric

## API

- [ ] GET /v1/models returns list
- [ ] POST /v1/chat/completions works for both models
- [ ] API key authentication works
- [ ] Response format matches OpenAI spec (14B returns chat.completion, 32B returns text_completion)
