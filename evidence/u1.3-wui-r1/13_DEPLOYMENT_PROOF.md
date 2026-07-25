# U1.3-WUI-R1 — DEPLOYMENT PROOF

## Deployment State at Test Time

| Property | aither-portal | aither-portal-frontend |
|----------|---------------|------------------------|
| Generation | 12 | 6 |
| ResourceVersion | 2201571 | 2201625 |
| Replicas | 1/1 Ready | 1/1 Ready |
| Pod | aither-portal-6c445cc9f-44dzd | aither-portal-frontend-5cc6d99997-btksr |
| Node | bootsman-k8s-clnt01-n8-gpu | bootsman-k8s-clnt01-n8-gpu |
| Pod IP | 10.244.0.53 | 10.244.0.54 |

## ConfigMap

| ConfigMap | Key | SHA-256 |
|-----------|-----|---------|
| aither-portal-config | index.html | edc1ee8dde1745bcdf8f00dbdc6051074f1b530046c723b04f4fb46952f91f20 |
| aither-portal-frontend-config | index.html | edc1ee8dde1745bcdf8f00dbdc6051074f1b530046c723b04f4fb46952f91f20 |
| aither-portal-config | nginx.conf | (unchanged) |
| aither-portal-frontend-config | nginx.conf | (unchanged) |

## Zone Endpoint Verification

| Zone | URL | SHA-256 |
|------|-----|---------|
| Internet | https://fb1.spb.ru:443/index.html | edc1ee8d...f91f20 |
| Test Zone | http://10.129.13.78:30080/index.html | edc1ee8d...f91f20 |
| Source | portal/static/index.html | edc1ee8d...f91f20 |

**Result: ALL MATCH — deployment is clean and synchronized.**
