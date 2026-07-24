# Rollback Plan

See `docs/operations/U1.2_ROLLBACK.md` for full procedures.

### Quick Summary

| Component | Rollback | Risk |
|---|---|---|
| VPS2 VPN | Restore old `expect eof` entrypoint | tun0 restart loop → Internet 504 |
| VPS2 nginx | Restore old config (HTTP/1.0, 10s timeout) | Intermittent 504 on VPN latency |
| ai-platform | `kubectl rollout undo` → revision 18 | 429→502 conversion returns |
| gateway 32B | `kubectl rollout undo` → old rate=30r/m | 502 under concurrency |
