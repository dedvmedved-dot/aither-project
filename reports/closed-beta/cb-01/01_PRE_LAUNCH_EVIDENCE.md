# CB-01 Pre-Launch Evidence

**Timestamp:** 2026-07-25 00:56:43 UTC

## K8s Nodes
```
NAME                         STATUS   ROLES           AGE   VERSION
bootsmam-k8s-clnt01-n7-gpu   Ready    <none>          11d   v1.33.5
bootsman-k8s-clnt01-n8-gpu   Ready    control-plane   11d   v1.33.5
```

## K8s Pods (aither-inference)
```
aither-ai-platform-84c478c874-75plb        1/1   Running   0     3h16m
aither-bff-656ff579b9-fccrq                1/1   Running   0     3d8h
aither-identity-67b5994997-2jdvd           1/1   Running   0     2d2h
aither-portal-56d684769b-kkpw5             1/1   Running   0     3d8h
aither-portal-backend-559754567d-599kk     1/1   Running   0     2d
aither-portal-frontend-f85dc7769-dlcll     1/1   Running   0     3d8h
aither-redis-rate-limit-754cdd9784-stnl6   1/1   Running   0     3d8h
nginx-gateway-32b-65786797-k8skw           1/1   Running   0     4h25m
nginx-gateway-32b-65786797-px4rz           1/1   Running   0     4h25m
vllm-14b-instruct-7f6f784dcb-g2h5d         1/1   Running   0     5d15h
vllm-32b-gptq-7d6dc7c64-r82nh              1/1   Running   0     5d15h
```

## VPS2 Edge (Docker)
```
vpn-cisco               Up 6 hours
aither-failover-nginx   Up 5 hours  (ports 443, 10443, 30901)
```

## Ports Listening
```
:443   → nginx (aither-failover-nginx)
:10443 → nginx
:30901 → nginx
```

## VPN
```
tun0: inet 10.129.100.53/32 scope global tun0 — UP
```

## Disk
```
/dev/vda1  50G  27G  20G  58% /
```

## Memory
```
Mem: 7.8Gi total, 6.1Gi available
```

## API Tests (valid key)
```
GET /v1/models → HTTP 200 (qwen-14b + qwen-32b-base)
POST /v1/chat/completions 14B → HTTP 200 ("Здравствуйте")
POST /v1/chat/completions 32B → HTTP 200 (completion text)
```

## Git
```
d07011d docs(u1.4): beta release candidate
2b7f5d8 docs(u1.3): operational readiness assessment
b1dd011 docs(u1.2): finalize CAP-01 evidence
```
