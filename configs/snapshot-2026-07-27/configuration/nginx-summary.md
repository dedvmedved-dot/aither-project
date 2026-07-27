# Nginx Configuration Summary

## aither-portal (main nginx, NodePort 30080)

- Serves static SPA from `/usr/share/nginx/html`
- Proxies `/api/` → `aither-bff:8000`
- Proxies `/docs/` → `aither-portal-frontend:80`
- `default_type text/plain; charset utf-8;`
- SSE-compatible (proxy_buffering off, chunked_transfer_encoding on)

## aither-portal-frontend

- Serves `/usr/share/nginx/html/docs/` — documentation files
- `default_type text/plain; charset utf-8;`

## nginx-gateway-32b (2 replicas)

- Reverse proxy for Gateway service
- Routes to internal vLLM endpoints
