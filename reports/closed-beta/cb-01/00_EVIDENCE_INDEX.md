# CB-01 Evidence Index

| # | Claim | Evidence File | Source | DateTime (UTC) | Result | Verified |
|---|---|---|---|---|---|---|
| 1 | K8s nodes Ready | 01_PRE_LAUNCH_EVIDENCE.md | kubectl get nodes | 2026-07-25 00:56 | 2/2 Ready | ✅ |
| 2 | All pods Running | 01_PRE_LAUNCH_EVIDENCE.md | kubectl get pods | 2026-07-25 00:56 | 11/11 Running | ✅ |
| 3 | VPS2 Edge UP | 01_PRE_LAUNCH_EVIDENCE.md | docker ps + ss | 2026-07-25 00:56 | nginx listening 443/10443 | ✅ |
| 4 | VPN stable | 01_PRE_LAUNCH_EVIDENCE.md | ip a show tun0 | 2026-07-25 00:56 | UP, no reconnects | ✅ |
| 5 | API keys created | 04_ACCESS_VALIDATION.md | DB insert + curl | 2026-07-25 00:52 | 5 keys, all 200 | ✅ |
| 6 | Valid auth → 200 | 04_ACCESS_VALIDATION.md | curl test | 2026-07-25 00:53 | HTTP 200 | ✅ |
| 7 | Invalid auth → 401 | 04_ACCESS_VALIDATION.md | curl test | 2026-07-25 00:54 | HTTP 401 | ✅ |
| 8 | 14B chat works | users/BETA-USER-01_UAT.md | curl test | 2026-07-25 00:54 | HTTP 200, coherent | ✅ |
| 9 | 32B base works | users/BETA-USER-01_UAT.md | curl test | 2026-07-25 00:55 | HTTP 200 via chat | ✅ |
| 10 | Invalid model → 404 | users/BETA-USER-01_UAT.md | curl test | 2026-07-25 00:54 | HTTP 404, graceful | ✅ |
| 11 | Sequential 10 req | users/BETA-USER-01_UAT.md | curl loop | 2026-07-25 00:55 | 10/10 HTTP 200 | ✅ |
| 12 | Concurrent load | 07_CONTROLLED_LOAD_EVIDENCE.md | Python subprocess | 2026-07-25 00:58 | 20/20 HTTP 200 | ✅ |
| 13 | No 5xx errors | 07_CONTROLLED_LOAD_EVIDENCE.md | Log analysis | 2026-07-25 00:58 | 0 | ✅ |
| 14 | No pod restarts | 08_OBSERVATION_LOG.md | kubectl get pods | 2026-07-25 01:00 | 0 delta | ✅ |
| 15 | Backup created | 02_BACKUP_VALIDATION.md | DB dump | 2026-07-25 00:57 | 2 DBs backed up | ✅ |
| 16 | Disk healthy | 01_PRE_LAUNCH_EVIDENCE.md | df -h | 2026-07-25 00:56 | 20G free | ✅ |
| 17 | No secret leaks | Git audit | grep scan | 2026-07-25 01:00 | 0 found | ✅ |
