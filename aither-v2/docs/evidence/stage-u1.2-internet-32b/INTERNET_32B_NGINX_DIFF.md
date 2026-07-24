# Internet 32B — nginx Configuration Diff

**Date:** 2026-07-24  
**File:** `/root/nginx-failover.conf` → `/etc/nginx/conf.d/default.conf` (Docker bind mount)

## Changes Summary

| Parameter | Before | After | Rationale |
|---|---|---|---|
| `proxy_connect_timeout` (server level) | 10s | REMOVED | Moved to location level |
| `proxy_send_timeout` (server level) | 10s | REMOVED | Moved to location level |
| `proxy_http_version` | (default 1.0) | 1.0 (explicit in location) | Force non-keepalive |
| `proxy_set_header Connection` | (none) | "close" (in location) | Explicit close |
| `proxy_connect_timeout` (location /v1/) | (inherited 10s) | 30s | VPN tunnel tolerance |
| Upstream type | Direct `proxy_pass http://IP` | `upstream` block with `keepalive 0` | Prevent connection reuse |

## Full Diff

```diff
--- before (original)
+++ after (current)

+upstream ai_platform {
+    server 10.129.13.78:30902;
+    keepalive 0;
+}

 server {
     listen 443 ssl;
     ...
-    proxy_connect_timeout 10s;
-    proxy_send_timeout 10s;
-    proxy_read_timeout 300s;

     location /v1/ {
-        proxy_pass http://10.129.13.78:30902;
+        proxy_pass http://ai_platform;
+        proxy_http_version 1.0;
+        proxy_set_header Connection "close";
         ...
+        proxy_connect_timeout 30s;
+        proxy_send_timeout 30s;
+        proxy_read_timeout 300s;
     }
     ...
 }

 server {
     listen 10443 ssl;
     ...
-    proxy_connect_timeout 10s;
-    proxy_send_timeout 10s;
-    proxy_read_timeout 300s;

     location /v1/ {
-        proxy_pass http://10.129.13.78:30902;
+        proxy_pass http://ai_platform;
+        proxy_http_version 1.0;
+        proxy_set_header Connection "close";
         ...
+        proxy_connect_timeout 30s;
+        proxy_send_timeout 30s;
+        proxy_read_timeout 300s;
     }
     ...
 }
```

## nginx Validation

```bash
$ docker exec aither-failover-nginx nginx -t
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

## Container Identity

| Property | Before Reload | After Reload |
|---|---|---|
| Container ID | 2368797 | 77464cd00522 |
| Image | nginx:alpine | nginx:alpine |
| Network | host | host |
| Status | running | running |
