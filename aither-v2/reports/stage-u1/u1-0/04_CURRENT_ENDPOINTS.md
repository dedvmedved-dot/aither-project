# Current Endpoints — Stage U1.0

## Summary

At Stage U1.0, there are NO externally accessible user-facing endpoints. All services are ClusterIP type and only reachable from within the Kubernetes cluster network. The system currently relies on `kubectl port-forward` for any external access.

## Currently Working Internal Endpoints (within cluster)

| Endpoint | Method | Component | Auth | Status |
|----------|--------|-----------|------|--------|
| `http://aither-portal-frontend:80/` | GET | Portal Frontend (nginx) | None | ✅ Working (serves SPA) |
| `http://aither-portal-frontend:80/api/v1/auth/login` | POST | Portal Backend | Public | ✅ Working |
| `http://aither-portal-frontend:80/api/v1/auth/me` | GET | Portal Backend → Identity | Session | ✅ Working |
| `http://aither-portal-frontend:80/api/v1/api-keys` | GET/POST | Portal Backend → AI Platform | Session | ✅ Working |
| `http://aither-portal-frontend:80/api/v1/assistants` | GET/POST | Portal Backend → AI Platform | Session | ✅ Working |
| `http://aither-portal-frontend:80/api/v1/conversations` | GET/POST | Portal Backend → AI Platform | Session | ✅ Working |
| `http://aither-portal-frontend:80/health` | GET | Portal Backend | None | ✅ Working |
| `http://aither-portal-frontend:80/v1/chat/completions` | POST | AI Platform (via nginx direct proxy) | API Key | ✅ Working (dual path) |
| `http://nginx-gateway-32b:8000/v1/completions` | POST | LLM Gateway → vLLM 32B | API Key | ✅ Working |
| `http://nginx-gateway-32b:8000/v1/models` | GET | LLM Gateway → vLLM 32B | API Key | ✅ Working |

## Critical Gap

**NO external or internal HTTP/HTTPS entry point exists.** There is no:
- Ingress controller
- LoadBalancer Service
- NodePort Service for user traffic
- Reverse proxy listening on TCP/80 or TCP/443 on any node

The target URLs (`https://fb1.spb.ru/`, `https://10.129.13.78/`) will require Ingress deployment (Stage U1.2).
