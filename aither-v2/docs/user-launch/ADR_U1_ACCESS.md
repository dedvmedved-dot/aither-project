# Architecture Decision Records — User Access (Stage U1)

---

## DEC-U1-ACCESS-01 — External Domain

### Context

Aither / AI Hermes MVP requires an external domain for user access during Internal Pilot.

### Decision

Use `fb1.spb.ru` as the external user-facing domain.

### Status

**ACCEPTED**

### Consequences

- All external user traffic will use `fb1.spb.ru`
- TLS certificate required for `fb1.spb.ru`
- DNS must be configured: `fb1.spb.ru` → `130.17.1.90`

### Security Impact

- Domain must have valid TLS certificate (Let's Encrypt or equivalent)
- HSTS should be configured to prevent downgrade attacks
- Domain name disclosure is acceptable for Internal Pilot

### Verification Method

- DNS resolution: `dig fb1.spb.ru` returns `130.17.1.90`
- TLS certificate: `openssl s_client -connect fb1.spb.ru:443` returns valid chain
- No mixed content warnings in browser

### Owning Stage

U1.1 (DNS and TLS)

---

## DEC-U1-ACCESS-02 — Public IPv4

### Context

A public IP address is needed to route external traffic to the Aither cluster.

### Decision

Use `130.17.1.90` as the public IPv4 address.

### Status

**ACCEPTED AS TARGET**

### Consequences

- The IP `130.17.1.90` must receive TCP/80 and TCP/443 traffic
- The IP is shared with the n8 node (`10.129.13.78`) — firewall rules must isolate Aither traffic
- NAT/port forwarding or Ingress controller must be configured to route from `130.17.1.90` to the cluster

### Security Impact

- The IP is publicly routable — all services on this IP must be secured
- Only TCP/80 and TCP/443 should be open from the Internet
- All other ports (e.g., SSH, K8s API, registry) must be restricted to internal network

### Verification Method

- `curl -I http://130.17.1.90` returns HTTP response
- `curl -I https://130.17.1.90` returns TLS handshake
- Port scan shows only 80 and 443 open from external network

### Owning Stage

U1.1 (Network)

---

## DEC-U1-ACCESS-03 — Internal Access Point

### Context

Internal users (within the same network as the cluster) need access to the Aither system. The internal access point `10.129.13.78` is the IP address of the n8 Kubernetes node.

### Decision

Use `10.129.13.78` as the internal user-facing entry point.

### Status

**ACCEPTED AS TARGET**

### Consequences

- `10.129.13.78` is a node IP, not a dedicated service endpoint
- An Ingress controller or reverse proxy must be deployed to handle traffic on this IP (Stage U1.2)
- TLS by IP requires IP SAN in certificate or internal DNS name

### Security Impact

- Internal access must still use TLS — no plaintext HTTP for authenticated operations
- Access from internal network should be limited to authorized subnets
- Internal access bypasses external firewall but must still pass through Ingress/routing layer

### Verification Method

- Browser navigation to `https://10.129.13.78/` returns portal
- API requests to `https://10.129.13.78/api/v1/` function correctly
- TLS certificate (or warning) is expected and documented

### Owning Stage

U1.1, U1.2

---

## DEC-U1-ACCESS-04 — Unified API Prefix

### Context

A consistent URL structure is needed for both web and API access to simplify routing and documentation.

### Decision

Use `/api/v1` as the unified API prefix for all user-facing API endpoints.

### Status

**ACCEPTED**

### Consequences

- All user-facing API endpoints are under `/api/v1/*`
- Portal Backend proxies `/api/v1/*` to AI Platform
- Identity Service uses `/v1/identity/*` (internal, not user-facing)
- FastAPI auto-docs via `/api/v1/docs` (Portal Backend) and `/api/v1/ai/docs` (AI Platform)

### Security Impact

- Clear separation between user-facing API prefix and internal service paths
- Rate limiting can be applied at the `/api/v1/` prefix level
- Internal paths (`/v1/identity/*`, `/v1/completions`) are not exposed

### Verification Method

- `GET /api/v1/models` returns 200 with model list
- `POST /api/v1/chat/completions` returns 200 with completion
- `GET /v1/identity/me` from external returns 404

### Owning Stage

U1.4

---

## DEC-U1-ACCESS-05 — OpenAI-Compatible API via Gateway

### Context

The system must expose an OpenAI-compatible API for external agents while preventing direct user access to the vLLM backend.

### Decision

All OpenAI-compatible API calls (`/api/v1/chat/completions`, `/api/v1/models`) pass through the application stack (Portal Frontend → Portal Backend → AI Platform → LLM Gateway → vLLM). Direct user access to vLLM is prohibited.

### Status

**ACCEPTED**

### Consequences

- vLLM is not directly accessible from outside the cluster (ClusterIP + NetworkPolicy)
- All requests are authenticated and authorized before reaching vLLM
- Additional latency due to multi-hop routing

### Security Impact

- Auth and API key validation happen before LLM Gateway
- LLM Gateway can apply additional rate limiting
- Raw model access is blocked

### Verification Method

- Direct `curl http://10.99.3.103:8000/v1/completions` from outside cluster fails
- `POST /api/v1/chat/completions` with valid API key returns completion
- `POST /api/v1/chat/completions` without auth returns 401

### Owning Stage

U1.4

---

## DEC-U1-ACCESS-06 — Dual Access for Web and API Features

### Context

Web Portal, Web Chat, and API Key management must be accessible through both the external (`fb1.spb.ru`) and internal (`10.129.13.78`) entry points.

### Decision

All three features (Web Portal, Web Chat, API Key management) are available through both user-facing entry points.

### Status

**ACCEPTED**

### Consequences

- Consistent user experience regardless of access method
- Single deployment serves both internal and external users
- Ingress configuration must handle both entry points (virtual hosting rules)

### Security Impact

- Internal access does not skip authentication
- API Key management requires authentication regardless of entry point

### Verification Method

- Login, chat, and API key management work from both `https://fb1.spb.ru/` and `https://10.129.13.78/`

### Owning Stage

U1.3

---

## DEC-U1-ACCESS-07 — Production v1.0 Remains NO-GO

### Context

Stage U1 is for Internal Pilot only. Production readiness is a separate milestone.

### Decision

Production v1.0 remains **NO-GO** throughout Stage U1. Stage U1 does not change the production readiness status.

### Status

**ACCEPTED**

### Consequences

- All U1 stages explicitly document: `Production v1.0: NO-GO`
- PROD-READY-01 remains OPEN
- Stage U2 (Limited Beta) is the next stage after U1

### Security Impact

- No production security review required for U1
- Production-grade TLS, monitoring, and HA are not requirements for U1

### Verification Method

- All U1 evidence documents state `Production v1.0: NO-GO`

### Owning Stage

U1.0–U1.7 (all stages)
