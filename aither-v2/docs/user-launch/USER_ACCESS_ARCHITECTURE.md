# User Access Architecture — Aither / AI Hermes MVP

## 1. Purpose

This document defines the user access architecture for the Aither / AI Hermes MVP Internal Pilot. It describes how users connect to the system, which components handle each request, and the security boundaries between external access, internal access, and backend infrastructure.

## 2. External Access Point

| Property | Value |
|----------|-------|
| Domain | `fb1.spb.ru` |
| Public IP | `130.17.1.90` |
| Target DNS | `fb1.spb.ru` → `130.17.1.90` |
| Target Web Chat | `https://fb1.spb.ru/` |
| Target API Base URL | `https://fb1.spb.ru/api/v1` |
| Current DNS resolution | **NOT VERIFIED** — belongs to Stage U1.1 scope |
| TLS certificate | **NOT ACQUIRED** — belongs to Stage U1.1 scope |

> **Note:** At Stage U1.0, the external domain `fb1.spb.ru` and public IP `130.17.1.90` are accepted as target addresses but are not yet configured. DNS resolution, TLS certificate provisioning, and firewall rules are deferred to Stage U1.1.

## 3. Internal Access Point

| Property | Value |
|----------|-------|
| Internal IP | `10.129.13.78` |
| Physical location | `bootsman-k8s-clnt01-n8-gpu` node (Kubernetes control-plane + worker) |
| Role | K8s control-plane, container registry (`10.129.13.78:5000`), SSH gateway |
| Network | Internal (Astra Linux cluster network) |
| Target Web Chat | `https://10.129.13.78/` |
| Target API Base URL | `https://10.129.13.78/api/v1` |
| Current component accepting TCP/443 | **NONE** — no Ingress, no LoadBalancer, no reverse proxy on port 443 |
| Current component accepting TCP/80 | **NONE** — only `kube-apiserver` on TCP/6443 and registry on TCP/5000 |

**Critical observation:** IP `10.129.13.78` is the node IP of the K8s control-plane node (n8). It does **not** currently serve HTTPS or HTTP traffic. There is no Kubernetes Service of type LoadBalancer or NodePort that would expose the portal on this IP via standard ports 80/443. The internal access point `https://10.129.13.78/` is a **target state** that requires an Ingress, reverse proxy, or NodePort configuration (Stage U1.2).

The IP `10.129.13.78` is **not listed** in any existing TLS certificate's `subjectAltName`. TLS by IP would produce a certificate mismatch. A valid approach would be to either:
1. Use an internal DNS name (e.g., `aither.internal`) with a trusted internal CA
2. Accept the limitation and document it as a blocker

## 4. Component Diagram

```
                         Пользователь
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
       Внешний доступ                  Внутренний доступ
      fb1.spb.ru                       10.129.13.78
      130.17.1.90                           │
              │                             │
              └──────────────┬──────────────┘
                             ▼
                 [Ingress / Reverse Proxy]
                 (NOT YET DEPLOYED — Stage U1.2)
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
  Portal Frontend      Portal Backend        AI Platform
  nginx:stable-alpine  FastAPI proxy         FastAPI + SQLite
  (TCP/80 → static)    (TCP/8000)            (TCP/8000)
        │                    │                    │
        │                    ▼                    │
        │            Identity Service             │
        │            FastAPI + SQLite             │
        │            (TCP/8000)                   │
        │                                         │
        └────────────────┬───────────────────────┘
                         ▼
                   LLM Gateway
                   nginx:alpine
                   (TCP/8000)
                         │
                         ▼
                    vLLM Backend
                    (TCP/8000)
```

## 5. Web Chat Flow

```
User Browser
  │
  │ HTTPS GET https://fb1.spb.ru/  или  https://10.129.13.78/
  ▼
[Ingress / Reverse Proxy — Stage U1.2]
  │
  ▼
Portal Frontend (nginx, port 80)
  ├── Serves static SPA (index.html, app.js, styles.css)
  └── /api/* → proxy_pass → Portal Backend (port 8000)
         │
         ▼
    Portal Backend (FastAPI)
      ├── /api/v1/auth/login → POST → Identity Service (/v1/identity/auth)
      ├── /api/v1/auth/me → GET → Identity Service (/v1/identity/me)
      ├── /api/v1/tokens → GET/POST → AI Platform (/api/v1/api-keys)
      ├── /api/v1/conversations → POST → AI Platform
      └── /api/v1/chat → POST → AI Platform (/v1/chat/completions)
               │
               ▼
          AI Platform (FastAPI)
            ├── /v1/chat/completions → POST → LLM Gateway (/v1/completions)
            │
            ▼
          LLM Gateway (nginx, port 8000)
            └── /v1/completions → proxy_pass → vLLM 32B (10.99.3.103:8000)
```

## 6. API Flow

```
External Agent
  │
  │ POST https://fb1.spb.ru/api/v1/chat/completions
  │ Header: Authorization: Bearer <api_key>
  │ or: X-API-Key: <api_key>
  ▼
[Ingress — Stage U1.2]
  │
  ▼
Portal Frontend (nginx)
  │
  │ /api/* → proxy_pass
  ▼
Portal Backend
  │
  │ /api/v1/* → proxy_pass (with auth forwarding)
  ▼
AI Platform
  │
  │ POST /v1/chat/completions
  │ (validates API key from DB, proxies to Gateway)
  ▼
LLM Gateway
  │
  ▼
vLLM Backend
```

**Note:** The nginx portal-frontend also proxies `/v1/chat/completions` directly to `aither-ai-platform:8000`, bypassing the Portal Backend. This creates a dual-path routing scenario that must be resolved in Stage U1.3.

## 7. API Key Flow

```
1. User logs in via Web Portal (/api/v1/auth/login)
2. User navigates to Settings → API Keys
3. User enters token name and optional scopes
4. POST /api/v1/api-keys → Portal Backend → AI Platform
5. AI Platform:
   - Generates random API key (prefix + random suffix)
   - Stores SHA-256 hash in SQLite
   - Returns full key ONCE to the user
   - Full key is never stored again
6. User copies key (shown once, on a blue background)
7. For API access:
   - Key is sent as Bearer token or X-API-Key header
   - AI Platform hashes the incoming key
   - Looks up hash in DB
   - Returns 401 if not found or revoked

```

## 8. Trust Boundaries

| Boundary | Components | Trust Level | Notes |
|----------|-----------|-------------|-------|
| External ↔ Internal | Internet ↔ Cluster | UNTRUSTED | All external traffic must pass through Ingress with TLS termination, rate limiting, and auth |
| Ingress ↔ Portal Frontend | Ingress ↔ nginx | TRUSTED (internal) | Internal cluster network |
| Portal Frontend ↔ Portal Backend | nginx ↔ FastAPI | TRUSTED (internal) | Local service mesh within namespace |
| Portal Backend ↔ AI Platform | FastAPI ↔ FastAPI | TRUSTED (internal) | Internal service communication |
| AI Platform ↔ LLM Gateway | FastAPI ↔ nginx | TRUSTED (internal) | Gateway validates via API key |
| LLM Gateway ↔ vLLM | nginx ↔ vLLM | TRUSTED (internal) | Internal pod-to-pod |

## 9. Prohibited Direct Connections

Users must NOT have direct access to:

- **Kubernetes API** (TCP/6443) — control-plane only
- **Redis** (TCP/6379) — rate limit store, internal only
- **PostgreSQL** (TCP/5432) — aiops namespace, not user-facing
- **vLLM 14B / 32B** (TCP/8000) — must go through Gateway
- **LLM Gateway** (ClusterIP 10.106.31.143:8000) — must go through Portal Backend / AI Platform
- **NodePorts** (any port above 30000) — all must be blocked
- **Internal metrics endpoints** — `/metrics` on all services
- **Debug/administrative endpoints** — unless explicitly whitelisted

## 10. Current State

- 11 microservices running in `aither-inference` namespace
- All Services are `ClusterIP` — no external exposure
- **No Ingress, LoadBalancer, or NodePort** currently exists for user-facing traffic
- The only way to access services is via:
  - `kubectl port-forward` (internal/K8s API)
  - ClusterIP within the cluster
  - Direct NodeIP on node ports (not configured for user services)
- Portal Frontend nginx serves static SPA and proxies `/api/` and `/v1/chat/completions`
- Identity Service handles auth (`/v1/identity/*`)
- Portal Backend proxies all `/api/v1/*` to AI Platform
- AI Platform handles API keys, assistants, conversations, and proxied LLM calls
- LLM Gateway (nginx-gateway-32b) provides OpenAI-compatible `/v1/completions` and `/v1/models`

## 11. Target State

- External domain `fb1.spb.ru` resolves to `130.17.1.90`
- Ingress (or alternative) terminates TLS with a valid certificate for `fb1.spb.ru`
- All user traffic goes through the Ingress → Portal Frontend → Portal Backend → backend path
- `/api/v1` prefix consistently routed through Portal Backend (not dual-path)
- Internal access via `10.129.13.78` works with valid TLS (internal DNS name or IP SAN)
- API key management fully functional
- OpenAI-compatible API for agents at `/api/v1/chat/completions`
- Rate limiting at ingress layer + application layer
- Health endpoint publicly accessible (read-only)
- All other internal endpoints blocked from external access

## 12. GAP Analysis

| ID | Current State | Target State | SeverITY | Stage |
|----|--------------|-------------|----------|-------|
| U1-GAP-001 | DNS `fb1.spb.ru` not configured | `fb1.spb.ru` → `130.17.1.90` | HIGH | U1.1 |
| U1-GAP-002 | No TLS certificate for `fb1.spb.ru` | Valid public TLS certificate | HIGH | U1.1 |
| U1-GAP-003 | No TLS certificate for `10.129.13.78` | Valid TLS (internal DNS or IP SAN) | MEDIUM | U1.1 |
| U1-GAP-004 | No Ingress or reverse proxy deployed | Ingress serving portal on TCP/443 | HIGH | U1.2 |
| U1-GAP-005 | Portal Frontend nginx uses HTTP only | TLS termination at Ingress | HIGH | U1.2 |
| U1-GAP-006 | `/v1/chat/completions` has dual path (nginx + Portal Backend) | Single path through Portal Backend | MEDIUM | U1.3 |
| U1-GAP-007 | `/api/v1/chat/completions` route not implemented | OpenAI-compatible API for agents at `/api/v1/chat/completions` | HIGH | U1.4 |
| U1-GAP-008 | No user documentation | User guide for portal and API | MEDIUM | U1.5 |
| U1-GAP-009 | API Key management not accessible from external URL | Key management available via Web Portal | MEDIUM | U1.3 |
| U1-GAP-010 | `10.129.13.78` is a node IP, not a service endpoint | Clear internal entry point (Ingress or LoadBalancer) | MEDIUM | U1.2 |

## 13. Known Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|------------|------------|
| No dedicated public IP for Aither (shared with n8 node) | Port conflicts, security | LOW | Document as target-only in Stage U1.0 |
| Conntrack hash collision on n8 (1% K8s API timeout) | Ingress health checks may fail intermittently | MEDIUM | Sysctl mitigation applied; may need hardware fix |
| No monitoring/alerting stack | Cannot detect user-facing outages | HIGH | Deferred to post-U1 roadmap |
| TLS certificate cost for `fb1.spb.ru` | Operational cost | LOW | Free Let's Encrypt available |
| vLLM 32B on n7 with single GPU (no HA) | Single point of failure | MEDIUM | Post-MVP optimization |
| MissingClusterDNS on n7 | Pod-to-pod DNS unreliable | MEDIUM | Workaround via ClusterIP in ConfigMap |

## 14. Assumptions

- External domain `fb1.spb.ru` is registrable and controllable by the project owner
- Public IP `130.17.1.90` is routable and can receive TCP/80 and TCP/443
- Internal IP `10.129.13.78` can serve as an internal entry point (via Ingress or reverse proxy)
- No existing firewall on the public IP blocks HTTP/HTTPS traffic
- Let's Encrypt or similar ACME provider can issue a certificate for `fb1.spb.ru`
- Users will access the system via modern browsers (SPA-compatible)

## 15. Open Questions

1. Is `fb1.spb.ru` already configured with an A record pointing to `130.17.1.90`?
2. Is there an existing firewall configuration on `130.17.1.90`?
3. Does the project owner control the DNS zone for `fb1.spb.ru`?
4. Is `130.17.1.90` a dedicated IP for Aither, or shared with other services?
5. Should internal access use an internal DNS name instead of raw IP?
6. What is the expected number of concurrent users for the Internal Pilot?

## 16. Transition to U1.1

Stage U1.1 will require:

1. DNS verification: `fb1.spb.ru` → `130.17.1.90`
2. TLS certificate acquisition for `fb1.spb.ru`
3. Internal TLS certificate or DNS name decision for `10.129.13.78`
4. Firewall rule review for `130.17.1.90` (TCP/80, TCP/443)
5. Verification that `10.129.13.78` can accept TCP/80 and TCP/443 (or via Ingress controller)
