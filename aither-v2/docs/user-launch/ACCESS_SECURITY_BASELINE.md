# Access Security Baseline — Aither / AI Hermes MVP Internal Pilot

## 1. Allowed Ports

| Port | Protocol | Direction | Purpose | Allowed From |
|------|----------|-----------|---------|-------------|
| 80 | TCP | Inbound | HTTP redirect to HTTPS (external) | Internet (via Ingress) |
| 443 | TCP | Inbound | HTTPS — Portal, Chat, API | Internet (via Ingress) |
| 22 | TCP | Inbound | SSH administration | Internal network only |
| 6443 | TCP | Inbound | Kubernetes API | Internal network only |
| 5000 | TCP | Inbound | Container registry | Internal network only |

## 2. Prohibited Ports

| Port | Protocol | Risk | Reason |
|------|----------|------|--------|
| 6379 | TCP | Redis exposed | No authentication, data store |
| 5432 | TCP | PostgreSQL exposed | Database access |
| 8000 | TCP | Direct service access | Bypass Portal Frontend and Gateway |
| 30000-32767 | TCP | NodePort range | Direct pod access, circumvents auth |

## 3. TLS

- External access (`fb1.spb.ru`): **REQUIRED** — trusted public certificate (Let's Encrypt or equivalent)
- Internal access (`10.129.13.78`): **REQUIRED** — one of:
  1. Certificate with IP in `subjectAltName`
  2. Internal DNS name with trusted internal CA
  3. Internal DNS name with self-signed CA (documented limitation)
- TLS termination: at Ingress (Stage U1.2)
- TLS version: minimum TLS 1.2, prefer TLS 1.3
- HSTS: `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `curl -k` is **NOT** an acceptable verification method

## 4. API Key Security

| Requirement | Status | Notes |
|------------|--------|-------|
| Key belongs to specific user | ✅ IMPLEMENTED | Key created via POST /api/v1/api-keys with user context |
| Full key shown only once | ✅ IMPLEMENTED | Returned in create response, never stored |
| Hash stored in database | ✅ IMPLEMENTED | SHA-256 hash in SQLite |
| Key not in application logs | ✅ IMPLEMENTED | Prefix logged, not full key |
| Key not in access logs | ⚠️ NOT VERIFIED | Depends on Ingress log configuration (Stage U1.2) |
| Key not in Git | ✅ VERIFIED | No API keys found in committed code |
| Key not in evidence | ✅ ENFORCED | All keys redacted to `***REDACTED***` |
| Key can be revoked | ✅ IMPLEMENTED | DELETE /api/v1/api-keys/{id} |
| Revoked key stops working | ✅ IMPLEMENTED | Hash lookup checks `revoked` field |
| No shared key for all users | ✅ IMPLEMENTED | Per-user key generation |

## 5. Logging

| Component | Log Type | Sensitive Data Risk | Mitigation |
|-----------|----------|--------------------|------------|
| Ingress / Reverse Proxy | Access logs | API keys in URL/headers | Ingress must redact Authorization header (Stage U1.2) |
| Portal Backend | Application logs | User content, session IDs | No secrets logged; full request body not logged |
| AI Platform | Application logs | API keys at creation | Only prefix logged |
| LLM Gateway | Access logs | API keys in Authorization header | Configured not to log full header |
| vLLM | Application logs | Prompt content | Stays within cluster network |

## 6. Rate Limiting

| Layer | Mechanism | Limits | Status |
|-------|-----------|--------|--------|
| Gateway (network) | Ingress rate limiting | TBD | NOT DEPLOYED (Stage U1.2) |
| Application (Portal Backend) | Redis fixed-window | 10 req/60s default | ✅ DEPLOYED |
| LLM Gateway | nginx rate limiting | 30 req/min per IP | ✅ DEPLOYED |

## 7. Direct Backend Bypass Prevention

| Bypass Path | Risk | Prevention |
|------------|------|------------|
| Direct ClusterIP access | User accesses service without auth | All services are ClusterIP — requires cluster network access |
| NodePort exposure | Direct pod access | No NodePort services defined for user-facing components |
| Ingress skipping | Bypass TLS and rate limiting | No Ingress currently exists; will be the only external entry |
| `kubectl port-forward` | Admin bypass | Requires K8s API access (admin only) |
| Service mesh bypass | Direct vLLM access | vLLM is ClusterIP + NetworkPolicy restricts ingress |

## 8. Secrets Handling

- No secrets in Git: ✅ VERIFIED (secret scan in Stage 10B: 0 REAL/LIKELY secrets in 67 files)
- Secrets in Kubernetes Secrets: ✅ DEPLOYED (auth secrets, API keys)
- Secrets in environment variables: ✅ IMPLEMENTED (K8s Secrets → env vars)
- Secrets in evidence: ❌ REDACTED (all secrets replaced with `***REDACTED***`)
- Bootstrap admin credentials: ⚠️ WARNING (admin/admin exists in test scripts, not committed)

## 9. Health Endpoint

| Path | Component | Public? | Notes |
|------|-----------|---------|-------|
| `/health` | Portal Frontend → Portal Backend | ✅ Read-only | Returns service status |
| `/ready` | Portal Frontend → Portal Backend | Internal | Readiness probe |
| `/healthz` | LLM Gateway (local nginx) | Internal | Local nginx process health |
| `/version` | All services | Internal | Version information |

## 10. Error Disclosure

- User-facing errors: Return generic messages, not stack traces
- Internal errors: Logged to application logs, not exposed to user
- Authentication errors: Return 401 without revealing user existence
- API Key errors: Return 401 without revealing key format
- Rate limit errors: Return 429 with Retry-After header ✅ IMPLEMENTED

## 11. External/Internal Trust Boundary

| Zone | Components | Trust |
|------|-----------|-------|
| **External (Internet)** | User browser, external agents | UNTRUSTED |
| **DMZ (Ingress)** | Ingress controller (TLS termination) | SEMI-TRUSTED |
| **Application** | Portal Frontend, Portal Backend, AI Platform | TRUSTED |
| **Data** | Identity Service, Redis | TRUSTED |
| **Model** | LLM Gateway, vLLM | TRUSTED |

The trust boundary between External and DMZ is enforced by:
- TLS encryption
- Rate limiting
- Authentication (session for web, API key for API)
- Input validation at Portal Backend and AI Platform
