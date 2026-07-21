# Aither Portal — Stage 15

## Overview

Stage 15 introduces the User Portal and Identity foundation for the Aither / AI
Hermes MVP. Users can open the Portal in a browser, authenticate, and access
their personal dashboard with system status information.

## Architecture

```
Browser
  │
  ▼
Portal Frontend (Nginx + HTML/CSS/JS)
  │  serves static SPA, proxies API to Portal Backend
  ▼
Portal Backend (BFF — FastAPI)
  │  proxying layer, /health, /ready, /version
  ▼
Identity Service (FastAPI + SQLite)
     user management, authentication, sessions
```

All components run in the `aither-inference` namespace.

## Components

### 1. Identity Service

- **Location:** `services/identity/`
- **Language:** Python (FastAPI)
- **Database:** SQLite (file-based, stored on `emptyDir` volume)
- **Authentication:** HMAC-signed tokens (JWT-like format)
- **Password storage:** bcrypt (12 rounds)
- **Token TTL:** 24 hours (configurable via `IDENTITY_TOKEN_TTL`)

### 2. Portal Backend (BFF)

- **Location:** `services/portal-backend/`
- **Language:** Python (FastAPI)
- **Role:** API proxy between frontend and Identity service
- **Additional:** CORS middleware, aggregated status endpoint

### 3. Portal Frontend

- **Location:** `services/portal-frontend/`
- **Runtime:** Nginx (static files + API proxy)
- **UI:** Single-page application (vanilla JS, no frameworks)
- **Pages:** Login, Dashboard, Profile, System Status

## Routes

| Path | Component | Description |
|---|---|---|
| `/` | Portal Frontend | SPA entry point |
| `/api/v1/*` | Portal Backend | API proxy |
| `/health` | Portal Backend | Health check |
| `/ready` | Portal Backend | Readiness check |
| `/version` | Portal Backend | Version info |

## Project Structure

```
services/
  identity/
    app/main.py          — Identity service code
    Dockerfile           — Container build
    requirements.txt     — Python dependencies
    k8s/identity.yaml    — K8s Secret + Deployment + Service
  portal-backend/
    app/main.py          — Portal Backend code
    Dockerfile           — Container build
    requirements.txt     — Python dependencies
    k8s/portal-backend.yaml — K8s Deployment + Service
  portal-frontend/
    index.html           — SPA HTML
    styles.css           — SPA styles
    app.js               — SPA application logic
    nginx.conf           — Nginx configuration
    Dockerfile           — Container build
    k8s/portal-frontend.yaml — K8s ConfigMap + Deployment + Service
scripts/
  bootstrap-admin.sh     — First admin creation
  test-stage15-acceptance.sh — Acceptance tests
```

## Login Process

1. User opens Portal in browser → sees login page
2. User enters username/password → POST `/api/v1/auth/login`
3. Portal Backend proxies to Identity Service → POST `/v1/identity/auth`
4. Identity Service validates credentials against SQLite (bcrypt)
5. On success: returns HMAC-signed token
6. Portal Frontend stores token in `localStorage`
7. Subsequent API calls include `Authorization: Bearer <token>` header
8. Token expires after 24 hours (configurable)
