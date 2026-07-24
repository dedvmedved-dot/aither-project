# Dependency Map

> Mermaid diagram showing component dependencies and relationships in the Aither Project.

---

```mermaid
graph TD
    subgraph "Active Workspace (aither-v2/)"
        PM[PROJECT_MASTER.md]
        CH[CHAT_HANDOVER.md]
        CMS[current-mvp-status.md]
        
        subgraph "User Launch (Track A)"
            UAA[USER_ACCESS_ARCHITECTURE.md]
            EM[ENDPOINT_MATRIX.md]
            ASB[ACCESS_SECURITY_BASELINE.md]
            RM[STAGE_U1_ROADMAP.md]
            ADR[ADR_U1_ACCESS.md]
        end
        
        subgraph "Services"
            ID[Identity Service]
            PB[Portal Backend / BFF]
            PF[Portal Frontend]
            AP[AI Platform]
        end
        
        subgraph "K8s Manifests"
            M[MVP Roadmap Manifests]
        end
        
        subgraph "Stage Reports"
            S10[Stage 10 Reports]
            S10B[Stage 10B RC2R]
            BA[BA-02R Reports]
            RC1[RC1 Reports]
            U1[Stage U1.0 Reports]
        end
        
        subgraph "Documentation"
            D11[Stage 11]
            D13[Stage 13]
            D14[Stage 14]
            D15[Stage 15]
            D16[Stage 16]
            D17[Stage 17]
            D18[Stage 18]
            D18A[Stage 18A]
            D18B[Stage 18B]
            D10[Stage 10 Standards]
        end
    end
    
    subgraph "Historical (root level)"
        GW[Gateway]
        PT[Portal]
        MF[Manifests]
        OD[Offline Deploy]
        FT[Fine-tuning]
        DIAG[Diagrams]
        WIKI[LLM Wiki]
        REF[References]
        GC[Grafana Configs]
        HPA[HPA Configs]
        UC[Usage Collector]
        ART[Aither Article]
    end
    
    subgraph "Repository Management"
        GIT[Git - aither-v2 branch]
        GIT_M[Git - main branch]
        CI[CI/CD Workflows]
    end

    %% Governance dependencies
    PM --> CH
    PM --> CMS
    PM --> U1
    
    %% User Launch dependencies
    UAA --> EM
    UAA --> ASB
    RM --> UAA
    RM --> EM
    ADR --> UAA
    
    %% Service dependencies
    PF --> PB
    PB --> ID
    PB --> AP
    AP --> ID
    
    %% Manifest dependencies
    M --> PF
    M --> PB
    M --> ID
    M --> AP
    
    %% Report dependencies
    S10 --> PM
    BA --> PF
    BA --> PB
    BA --> ID
    BA --> AP
    RC1 --> BA
    U1 --> PM
    
    %% Historical to active mapping
    GW -.->|Superseded by| AP
    PT -.->|Superseded by| PF
    PT -.->|Superseded by| PB
    MF -.->|Superseded by| M
    OD -.->|Alternative| M
    FT -.->|Independent| FT
    
    %% Repository management
    CI --> GIT
    GIT_M -.->|Historical only| GIT
```

## Dependency Legend

| Line Style | Meaning |
|-----------|---------|
| `-->` | Direct dependency |
| `-.->` | Superseded/Historical relationship |
| Text in box | Active component |
| "Superseded by" | Historical code replaced by aither-v2/ equivalent |

## Key Dependency Chain

```
Git (aither-v2) → PROJECT_MASTER.md → CHAT_HANDOVER.md → Stage Reports → Services → K8s Manifests
```

## Component Count

| Layer | Components | Files |
|-------|-----------|-------|
| Governance | 3 core docs | 10+ files |
| User Launch | 5 documents | 5 files |
| Services | 4 services | 21 files |
| Manifests | 15 manifests | 15 files |
| Stage Reports | 7 report sets | 70 files |
| Stage Docs | 10 stage sets | 364 files |
| Historical | 12+ components | 292 files |
| CI/CD | 3 workflows | 3 files |

## Service Dependency Table

| Source | Destination | Protocol | Port | Auth | Config File | Status |
|--------|-------------|----------|------|------|-------------|--------|
| User Browser | Ingress / Reverse Proxy | HTTPS | 443 | Browser session | Not yet created — owning stage U1.2 | TARGET |
| Ingress | Portal Frontend | HTTP | 80 | None (internal) | Ingress config (U1.2) | TARGET |
| Portal Frontend (nginx) | Portal Backend | HTTP | 8000 | Session cookie (forwarded) | `services/portal-frontend/nginx.conf` | CURRENT |
| Portal Frontend (nginx) | AI Platform | HTTP | 8000 | API Key (X-API-Key / Bearer) | `services/portal-frontend/nginx.conf` | CURRENT (dual path) |
| Portal Backend | Identity Service | HTTP | 8000 | Session token (Bearer) | `services/portal-backend/app/main.py` | CURRENT |
| Portal Backend | AI Platform | HTTP | 8000 | Session token (Bearer) | `services/portal-backend/app/main.py` | CURRENT |
| AI Platform | LLM Gateway | HTTP | 8000 | GATEWAY_API_KEY (env) | `services/ai-platform/app/main.py` | CURRENT |
| AI Platform | Identity Service | HTTP | 8000 | Bearer token | `services/ai-platform/app/main.py` | CURRENT |
| LLM Gateway (nginx) | vLLM 32B | HTTP | 8000 | Gateway auth token | `manifests/mvp-roadmap/04-gateway/nginx-gateway-32b-hardened.yaml` | CURRENT |
| AI Platform | Redis (rate-limit) | TCP | 6379 | None (internal) | `manifests/mvp-roadmap/06-rate-limiting/redis-rate-limit.yaml` | CURRENT |
| Portal Backend | Redis (rate-limit) | TCP | 6379 | None (internal) | `manifests/mvp-roadmap/06-rate-limiting/redis-rate-limit.yaml` | CURRENT |

## Storage Dependencies

| Component | Storage | Type | Path | Config File |
|-----------|---------|------|------|-------------|
| AI Platform | SQLite | File (PVC) | `/data/ai-platform.db` | `services/ai-platform/k8s/ai-platform.yaml` |
| Identity Service | SQLite | File (PVC) | `/data/identity.db` | `services/identity/k8s/identity.yaml` |
| Redis | Memory + AOF | RAM + File | `/data` | `manifests/mvp-roadmap/06-rate-limiting/redis-rate-limit.yaml` |

## Network Dependencies

| Service | ClusterIP | Pod IP | Node |
|---------|-----------|--------|------|
| aither-portal-frontend | 10.105.195.81 | 10.244.1.23 | n7 |
| aither-portal-backend | 10.100.101.65 | 10.244.0.5 | n8 |
| aither-ai-platform | 10.107.239.156 | 10.244.0.7 | n8 |
| aither-identity | 10.105.189.202 | 10.244.0.245 | n8 |
| nginx-gateway-32b | 10.106.31.143 | 10.244.0.9, 10.244.1.37 | n7, n8 |
| vllm-14b-instruct | 10.108.67.57 | 10.244.1.3 | n7 |
| vllm-32b-gptq | 10.99.3.103 | 10.244.1.4 | n7 |
| aither-redis-rate-limit | 10.105.190.101 | 10.244.1.20 | n7 |
