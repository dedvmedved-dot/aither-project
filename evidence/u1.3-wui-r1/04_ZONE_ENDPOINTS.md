# U1.3-WUI-R1 — ZONE ENDPOINTS

| Zone | URL | Protocol | TLS |
|------|-----|----------|-----|
| Internet | https://fb1.spb.ru:443 | HTTPS | Let's Encrypt (valid) |
| Test Zone | http://10.129.13.78:30080 | HTTP | N/A |

**Internet Zone deployment:** aither-portal-frontend (nginx → BFF)
**Test Zone deployment:** aither-portal (nginx → BFF)

**TLS status:**
- Internet: ✅ Valid certificate
- Test Zone: N/A (HTTP, internal network)

**SHA-256 match (index.html):** edc1ee8dde1745bcdf8f00dbdc6051074f1b530046c723b04f4fb46952f91f20 on all three points.
