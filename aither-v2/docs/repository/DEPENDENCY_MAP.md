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
