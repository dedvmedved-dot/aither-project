# GAP Analysis — Stage U1.0

## Finding U1-GAP-001 — DNS Not Configured

**Severity:** CRITICAL
**Area:** External access
**Current state:** `fb1.spb.ru` DNS not verified or configured
**Target state:** `fb1.spb.ru` resolves to `130.17.1.90`
**Evidence:** No A/AAAA records found in repository or runtime; domain not mentioned in any existing configuration
**Risk:** External users cannot reach the system via domain name
**Required correction:** Configure DNS A record: `fb1.spb.ru` → `130.17.1.90`
**Owning stage:** U1.1
**Blocking:** Yes (blocks U1.2+)

## Finding U1-GAP-002 — No TLS Certificate for External Domain

**Severity:** CRITICAL
**Area:** TLS
**Current state:** No TLS certificate for `fb1.spb.ru`
**Target state:** Valid public TLS certificate from trusted CA (e.g., Let's Encrypt)
**Evidence:** No certificate files in repository; no TLS configuration found
**Risk:** HTTPS access to external domain will fail certificate validation
**Required correction:** Acquire and configure TLS certificate for `fb1.spb.ru`
**Owning stage:** U1.1
**Blocking:** Yes (blocks U1.2+)

## Finding U1-GAP-003 — No TLS for Internal IP

**Severity:** MEDIUM
**Area:** TLS
**Current state:** No TLS certificate for `10.129.13.78`
**Target state:** Valid TLS (IP SAN cert, internal DNS name, or internal CA)
**Evidence:** No TLS-related configuration found for internal IP
**Risk:** HTTPS access via IP will produce certificate mismatch warning
**Required correction:** Choose and implement internal TLS approach (IP SAN, internal DNS, or documented limitation)
**Owning stage:** U1.1
**Blocking:** No (can proceed with documented limitation)

## Finding U1-GAP-004 — No Ingress / Reverse Proxy

**Severity:** CRITICAL
**Area:** Networking
**Current state:** No Ingress, LoadBalancer, or NodePort exists for user-facing traffic
**Target state:** Ingress controller (or equivalent) deployed, serving Portal Frontend on TCP/443
**Evidence:** `kubectl get ingress -A` returns empty; `kubectl get svc -A` shows all services as ClusterIP; `kubectl get ingressclass` returns empty
**Risk:** No path exists for users to access the system
**Required correction:** Deploy Ingress controller and configure routing rules
**Owning stage:** U1.2
**Blocking:** Yes (blocks all subsequent stages)

## Finding U1-GAP-005 — Portal Frontend Uses HTTP Only

**Severity:** HIGH
**Area:** TLS
**Current state:** Portal Frontend nginx listens on TCP/80 only, no TLS configured
**Target state:** TLS termination at Ingress; Portal Frontend serves over HTTPS
**Evidence:** `services/portal-frontend/nginx.conf` line 2: `listen 80;`
**Risk:** User traffic is unencrypted between user and Ingress (until Ingress terminates TLS)
**Required correction:** TLS termination at Ingress layer
**Owning stage:** U1.2
**Blocking:** Yes (for secure access)

## Finding U1-GAP-006 — Dual Routing Path for Chat Completions

**Severity:** MEDIUM
**Area:** Architecture
**Current state:** `/v1/chat/completions` is proxied directly from Portal Frontend nginx (`services/portal-frontend/nginx.conf` line 26) and also available through Portal Backend → AI Platform
**Target state:** Single routing path through Portal Backend for all `/api/v1/*` including chat
**Evidence:** `services/portal-frontend/nginx.conf` line 26: `location /v1/chat/completions { proxy_pass http://aither-ai-platform:8000; }`
**Risk:** Inconsistent auth enforcement; nginx proxy bypasses Portal Backend auth
**Required correction:** Remove direct `/v1/chat/completions` proxy from nginx; route only through Portal Backend
**Owning stage:** U1.3
**Blocking:** No (but should be resolved before opening to users)

## Finding U1-GAP-007 — `/api/v1/chat/completions` Not Exposed Externally

**Severity:** HIGH
**Area:** API
**Current state:** `/api/v1/chat/completions` (OpenAI-compatible) exists in AI Platform code but is not exposed through any external path
**Target state:** External agents can call `POST /api/v1/chat/completions` with API key authentication
**Evidence:** `services/ai-platform/app/main.py` line 1108: `@app.post("/v1/chat/completions")` — uses `/v1/` prefix, not `/api/v1/`. Portal Backend does not proxy this path.
**Risk:** External agents cannot use the system via OpenAI-compatible API
**Required correction:** Add `/api/v1/chat/completions` route in Portal Backend that proxies to AI Platform, or add nginx routing rule
**Owning stage:** U1.4
**Blocking:** Yes (for agent access)

## Finding U1-GAP-008 — No User Documentation

**Severity:** MEDIUM
**Area:** User experience
**Current state:** No user guide, API reference, or FAQ exists in the repository
**Target state:** User documentation covering portal usage, API access, and troubleshooting
**Evidence:** No documentation files under `docs/user-launch/` or `docs/` for users
**Risk:** Users have no reference material for using the system
**Required correction:** Create user guide and API reference
**Owning stage:** U1.5
**Blocking:** No

## Finding U1-GAP-009 — API Key Management Not Externally Accessible

**Severity:** MEDIUM
**Area:** User interface
**Current state:** API Key management works internally through Portal Frontend but is not accessible from external URL
**Target state:** API Key management available via Web Portal at `https://fb1.spb.ru/settings/api-keys`
**Evidence:** Portal SPA has token management UI; no external entry point exists
**Risk:** Users cannot manage API keys without kubectl port-forward
**Required correction:** Deploy Ingress (U1.2) to expose Portal Frontend; verify key management works through external URL
**Owning stage:** U1.3
**Blocking:** No (but needed for user access)

## Finding U1-GAP-010 — `10.129.13.78` Is Node IP, Not Service Endpoint

**Severity:** MEDIUM
**Area:** Architecture
**Current state:** Target internal IP `10.129.13.78` is the node IP of n8 (control-plane node). It does not currently serve HTTP/HTTPS.
**Target state:** Clear internal service endpoint (Ingress controller or reverse proxy serving on this IP)
**Evidence:** No Service of type LoadBalancer or NodePort exists; no process on n8 serves TCP/80 or TCP/443
**Risk:** Internal access URL is misleading — points to a node, not a service
**Required correction:** Deploy Ingress controller that binds to this IP, or use a NodePort/LoadBalancer service
**Owning stage:** U1.2
**Blocking:** No (but creates confusion)
