# U1.3-WUI — Zone Endpoints

## INTERNET_ZONE

- Web UI URL: https://fb1.spb.ru:443
- API base URL: https://fb1.spb.ru:443/api/v1
- TLS status: ✅ Let's Encrypt valid certificate
- Auth mechanism: Session cookie (BFF), Bearer token (API keys)
- Models: qwen-14b, qwen-32b-base
- Route: fb1.spb.ru:443 → nginx → k8s portal service
- Key creation: POST /api/v1/tokens
- Agent API: /api/v1/chat, /api/v1/models
- Health: GET /health → {"status":"ok","version":"0.5.0",...}
- Rate limit: enabled

## TEST_ZONE

- Web UI URL: http://10.129.13.78:30080
- API base URL: http://10.129.13.78:30080/api/v1
- TLS status: ⚠️ HTTP (no TLS, test zone only)
- Auth mechanism: Session cookie (BFF), Bearer token (API keys)
- Models: qwen-14b, qwen-32b-base
- Route: 10.129.13.78:30080 → k8s NodePort → portal service
- Key creation: POST /api/v1/tokens
- Agent API: /api/v1/chat, /api/v1/models
- Health: GET /health → {"status":"ok","version":"0.5.0",...}
- Rate limit: enabled

## Verified

Both zones accessible and operational. Test Zone uses HTTP (no TLS) — acceptable for internal testing.
