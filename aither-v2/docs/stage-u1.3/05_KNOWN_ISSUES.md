# Known Issues

## Functional

| ID | Issue | Impact | Workaround | Severity | Status |
|---|---|---|---|---|---|
| KI-01 | 32B is base completion model, not chat | `/v1/chat/completions` returns text_completion | Use 14B for chat, 32B for completion | MEDIUM | Open |
| KI-02 | nginx-gateway-32b hard-blocks `/v1/chat/completions` with 422 | Direct chat calls to 32B fail | Use ai-platform which adapts chat→completion | LOW | By design |
| KI-03 | No streaming support | All responses are complete (non-streaming) | Wait for full response | LOW | Open |
| KI-04 | SQLite concurrency limit | >10 concurrent writes may timeout | Sequential writes, WAL mode enabled | MEDIUM | Mitigated |

## Operational

| ID | Issue | Impact | Workaround | Severity | Status |
|---|---|---|---|---|---|
| KI-05 | No automated database backup | Pod restart = all user data lost | Manual sqlite3 dump before maintenance | HIGH | Open |
| KI-06 | No centralized logging | Debugging requires checking multiple sources | Check each component separately | MEDIUM | Open |
| KI-07 | No alerting | Issues found only when users report | Manual health checks | MEDIUM | Open |
| KI-08 | Single replica per service | Any pod crash = service unavailable for restart duration | Accept downtime for now | MEDIUM | Open |
| KI-09 | vLLM startup takes 5-10 min | Planned maintenance requires long outage window | Schedule during low usage | MEDIUM | Inherent |

## Infrastructure

| ID | Issue | Impact | Workaround | Severity | Status |
|---|---|---|---|---|---|
| KI-10 | Cisco VPN is single point of failure | Internet access lost if VPN fails | Test Zone :30902 still works locally | HIGH | Accepted for U1 |
| KI-11 | VPS2 is single point of failure | Both Internet routes lost if VPS2 down | Direct :30902 access if on same network | HIGH | Accepted for U1 |
| KI-12 | No TLS auto-renewal | Certificate expiry breaks HTTPS | Manual cert replacement | MEDIUM | Open |
| KI-13 | No GPU redundancy | GPU failure on n7 = both models down | None | HIGH | Accepted for U1 |
| KI-14 | Manual image builds | ai-platform updates require manual Docker build + push | Use documented procedure | LOW | Open |

## Security

| ID | Issue | Impact | Workaround | Severity | Status |
|---|---|---|---|---|---|
| KI-15 | API keys stored as SHA256 hash only | Cannot recover lost keys | Create new key | LOW | By design |
| KI-16 | No rate limiting on external API | Single user can exhaust resources | Gateway rate limit 300r/m protects 32B path | MEDIUM | Mitigated |
| KI-17 | No audit log for API key usage | Cannot trace who made which request | None | LOW | Open |
